# ======================================================================================================================
#
#  Project:  GENERATING LANDSLIDE SUSCEPTIBILITY MAP FOR NEPAL
#  Purpose:  Given rainfall forecast, this will generate landslide susceptibility map for nepal.
#  Author:   Saugat Paudel, saugat.email@gmail.com
#
# ======================================================================================================================


# ======================================================================================================================
#
# Usage:
#   1. Provide a rainfall forecast csv file that has at least the following columns. Exact names required.
#       - municipality_id, rainfall, forecast_date, forecasted_on, lat, lon
#
#   2. Provide a recorded rainfall csv file that has at least the following columns. Exact names required.
#       - municipality_id, record_date, recorded_on, rainfall, lat, lon
#
#   3. ENSURE THAT ALL DATES ARE CORRECT, NO MISSING VALUES.
#       - no check of dates are performed. recorded_on and forecasted_on columns must have only one date value.
#       - forecasted_on date value and recorded_on date value must be same. However, no checks are performed.
#       - record_date value must start from 1 day before recorded_on date value. However, no checks performed.
#       - forecast_date must start from the same date that is in forecasted_date. No checks performed.
#
#   4. ENSURE ALL RAW RASTER FILES ARE IN PLACE.
#
#   5. functions.py contains all required functions.
#
#   6. constants.py contains all constants. eg: filepaths, weights etc.
#       If needed, change these data while instantiating.
#
# Requirements: All required libraries were automatically generated by conda. Available at requirements.txt
#
# ======================================================================================================================

from pathlib import Path
import pandas as pd
import constants
from dataclasses import asdict
import functions
from osgeo import gdal
import numpy as np
from time import time
from datetime import timedelta

start_time = time()

gdal.UseExceptions()

gdal.SetConfigOption('GDAL_USE_CPL_MULTITHREAD', 'YES')
gdal.SetConfigOption('GDAL_NUM_THREADS', 'ALL_CPUS')

# ======================================================================================================================
# INSTANTIATE ALL DATACLASSES. CHANGE DEFAULT PATHS/VALUES/PARAMETERS IF NEEDED WHILE INSTANTIATING.
# ======================================================================================================================

print('\nSetting up all filepaths, folderpaths and required data ... ')
FOLDER_PATHS = asdict(constants.FolderPaths())

RAW_VECTORS_FILEPATHS = asdict(constants.RawVectorsFilePaths())
RAW_RASTERS_FILEPATHS = asdict(constants.RawRastersFilePaths())
CLASSIFIED_RASTERS_FILEPATHS = asdict(constants.ClassifiedRastersFilePaths())

CLASSIFICATION_PARAMETERS = asdict(constants.ClassificationParameters())

FINAL_WEIGHTS = asdict(constants.FinalWeights())

RAW_FORECAST_RAINFALL_CSV_FILEPATH = Path('Input/Raw/Csv/municipalities_rain_forecast.csv')
RAW_RECORDED_RAINFALL_CSV_FILEPATH = Path('Input/Raw/Csv/municipalities_rain_record.csv')
BASE_LANDSLIDE_SUSCEPTIBILITY_MAP_FILEPATH = Path('./Input/Processed/landslide_susceptibility_map_base.tif')
CLASSIFIED_BASEMAP_FILEPATH = Path('./Output/landslide_susceptibility_map_cls.tif')

INFORMATION_RASTER_FILEPATH = Path('Input/Raw/Raster/dem_wgs84.tif')

# TODO: Keep this to 0 while testing. Setting it to 1 will recalculate all forecast rasters
FLAG_UPDATE_FORECAST_RASTERS = 1

# ======================================================================================================================


# ======================================================================================================================
# CHECK IF CLASSIFIED RASTERS EXIST FOR CONSTANT RASTERS. IF NOT, CREATE.
# ======================================================================================================================

for raster_type, raster_path in CLASSIFIED_RASTERS_FILEPATHS.items():
    if Path.exists(raster_path):
        print(f'\nClassified raster \'{raster_path.name}\' for \'{raster_type}\' already exists. Skipping.')
        pass
    else:
        functions.constants_raster_pipeline(
            input_raster_filepath=RAW_RASTERS_FILEPATHS[raster_type],
            output_raster_filepath=raster_path,
            input_shapefile_filepath=RAW_VECTORS_FILEPATHS['exact_boundary_utm45n'],
            classification_range=CLASSIFICATION_PARAMETERS[raster_type]
        )
# ======================================================================================================================


# ======================================================================================================================
# CHECK IF BASE LANDSLIDE SUSCEPTIBILITY MAP EXISTS. IF NOT, CREATE.
# ======================================================================================================================
if BASE_LANDSLIDE_SUSCEPTIBILITY_MAP_FILEPATH.exists():
    print(f'\nBase map already exists. Skipping.')
    pass
else:
    summed_array = None
    geo_transform = None
    projection = None

    nodata = -128
    for raster_type, raster_path in CLASSIFIED_RASTERS_FILEPATHS.items():
        print(f'raster_type = {raster_type}, raster path = {raster_path}, weight = {FINAL_WEIGHTS[raster_type]}')
        if summed_array is None:

            raster_ds = gdal.Open(raster_path)
            band_ds = raster_ds.GetRasterBand(1)
            raster_nodata = band_ds.GetNoDataValue()

            geo_transform = raster_ds.GetGeoTransform()
            projection = raster_ds.GetProjection()

            initial_array = band_ds.ReadAsArray()

            summed_array = np.full_like(initial_array, nodata, dtype=np.float32)

            valid_mask = initial_array != raster_nodata
            # valid_mask = initial_array < 0
            summed_array[valid_mask] = initial_array[valid_mask] * FINAL_WEIGHTS[raster_type]

            initial_array = None
            raster_ds = None
            band_ds = None

        else:
            raster_ds = gdal.Open(raster_path)
            band_ds = raster_ds.GetRasterBand(1)
            array_ds = band_ds.ReadAsArray()

            raster_nodata = band_ds.GetNoDataValue()

            valid_mask = array_ds != raster_nodata
            # valid_mask = array_ds < 0
            summed_array[valid_mask] += array_ds[valid_mask] * FINAL_WEIGHTS[raster_type]

            raster_ds = None
            band_ds = None
            array_ds = None

    summed_array[summed_array < 0] = -128

    driver = gdal.GetDriverByName('GTiff')
    output_ds = driver.Create(
        BASE_LANDSLIDE_SUSCEPTIBILITY_MAP_FILEPATH,
        summed_array.shape[1],
        summed_array.shape[0],
        1,
        gdal.GDT_Float32
    )

    output_ds.SetGeoTransform(geo_transform)
    output_ds.SetProjection(projection)

    output_band = output_ds.GetRasterBand(1)
    output_band.SetNoDataValue(-128)
    output_band.WriteArray(summed_array)

    output_band.FlushCache()

    output_ds = None
    del output_ds
    output_band = None

    print(f'\nBase Landslide Susceptibility Map successfully created.')
# ======================================================================================================================


# ======================================================================================================================
# CREATE AND CLASSIFY RASTER FROM RECORDED RAINFALL.
# ======================================================================================================================

print(f'\nDealing with recorded rainfall data ... ')
recorded_rainfall_df = pd.read_csv(
    RAW_RECORDED_RAINFALL_CSV_FILEPATH,
    parse_dates=['record_date', 'recorded_on']
)

summed_rainfall = recorded_rainfall_df.groupby('municipality_id', as_index=False).agg({
    'rainfall': 'sum',
    'lat': 'first',
    'lon': 'first'
})

summed_recorded_rainfall_csv_filepath = FOLDER_PATHS['processed'] / 'Csv' / 'summed_rainfall.csv'
summed_rainfall.to_csv(summed_recorded_rainfall_csv_filepath, index=False)

print('\nParsing recorded rainfall data ...')

if Path.exists(FOLDER_PATHS['processed'] / 'Raster' / 'recorded_rainfall_utm45n_cls.tif'):
    recorded_rainfall_raster_filepath = FOLDER_PATHS['processed'] / 'Raster' / 'recorded_rainfall_utm45n_cls.tif'
else:
    recorded_rainfall_raster_filepath = functions.forecast_pipeline(
        individual_rainfall_forecast_csv_filepath=summed_recorded_rainfall_csv_filepath,
        rainfall_field_name_in_csv='rainfall',
        input_shapefile_filepath=RAW_VECTORS_FILEPATHS['exact_boundary_utm45n'],
        classification_range=None,
        output_raster_filepath=FOLDER_PATHS['processed'] / 'Raster' / 'recorded_rainfall_utm45n_cls.tif',
        information_raster_filepath=INFORMATION_RASTER_FILEPATH
    )

# ======================================================================================================================


# ======================================================================================================================
# CREATE FORECAST RASTERS
# ======================================================================================================================

classified_forecasted_rainfall_filepaths = []

if FLAG_UPDATE_FORECAST_RASTERS == 0:
    print('\nForecast rasters not updated ... Skipping.')
    pass
elif FLAG_UPDATE_FORECAST_RASTERS == 1:
    list_of_forecast_csv = functions.parse_rainfall_csv(
        raw_rainfall_csv_filepath=RAW_FORECAST_RAINFALL_CSV_FILEPATH,
        output_folderpath=FOLDER_PATHS['processed'] / 'Csv/',
        date_column_name='forecast_date'
    )

    for forecast_day, individual_filepath in list_of_forecast_csv.items():
        cls_forecast_rainfall_filepath = functions.forecast_pipeline(
            information_raster_filepath=INFORMATION_RASTER_FILEPATH,
            output_raster_filepath=FOLDER_PATHS[
                                       'processed'] / 'Raster' / f'./{forecast_day}_day_forecast_rainfall_cls.tif',
            individual_rainfall_forecast_csv_filepath=individual_filepath,
            rainfall_field_name_in_csv='rainfall',
            input_shapefile_filepath=RAW_VECTORS_FILEPATHS['exact_boundary_utm45n'],
            classification_range=None
        )

        classified_forecasted_rainfall_filepaths.append(cls_forecast_rainfall_filepath)
else:
    print('\nki 0 ki 1.')
    exit()

# ======================================================================================================================


# ======================================================================================================================
# CREATE FINAL LANDSLIDE SUSCEPTIBILITY MAP.
# ======================================================================================================================

if classified_forecasted_rainfall_filepaths:
    for forecast_day, forecast_raster_filepath in enumerate(classified_forecasted_rainfall_filepaths):
        print(f'\nCreating final susceptibility map for forecast day {forecast_day + 1}..')
        functions.create_final_landslide_susceptibility_map(
            base_map_filepath=BASE_LANDSLIDE_SUSCEPTIBILITY_MAP_FILEPATH,
            recorded_rainfall_raster_filepath=recorded_rainfall_raster_filepath,
            forecast_rainfall_raster_filepath=forecast_raster_filepath,
            output_raser_filepath=FOLDER_PATHS['output']/f'{forecast_day + 1}_day_landslide_map_FINAL.tif',
            recorded_rainfall_weight=0.02,
            forecast_rainfall_weight=0.1
        )
else:
    print('\nThere are no forecast rasters to calculate. Ensure proper filepaths.')
    exit()
# ======================================================================================================================

end_time = time()
print('\n', timedelta(seconds=end_time - start_time))