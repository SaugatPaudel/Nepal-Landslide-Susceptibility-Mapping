import numpy as np
from osgeo import ogr, gdal
from pathlib import Path
import pandas as pd

ogr.UseExceptions()
gdal.UseExceptions()

gdal.SetConfigOption('GDAL_USE_CPL_MULTITHREAD', 'YES')
gdal.SetConfigOption('GDAL_NUM_THREADS', 'ALL_CPUS')


def _clear_memory(filepath: str | Path) -> None:
    if isinstance(filepath, Path):
        pass
    else:
        gdal.Unlink(filepath)


def _create_vrt(*, csv_path: Path, parameter: str) -> str:
    vrt_content = f'''
    <OGRVRTDataSource>
        <OGRVRTLayer name="{csv_path.stem}">
            <SrcDataSource>{csv_path}</SrcDataSource>
            <GeometryType>wkbPoint</GeometryType>
            <GeometryField encoding="PointFromColumns" x="lat" y="lon" z="{parameter}"/>
        </OGRVRTLayer>
    </OGRVRTDataSource>'''
    return vrt_content


def _get_raster_info(*, input_raster_filepath: Path) -> dict:
    raster_ds = gdal.Open(input_raster_filepath)

    band_ds = raster_ds.GetRasterBand(1)
    stats = band_ds.ComputeRasterMinMax(True, False)
    raster_min = stats[0]
    raster_max = stats[1]
    nodata_value = band_ds.GetNoDataValue()
    band_ds = None
    stats = None

    raster_x_size_or_width = raster_ds.RasterXSize
    raster_y_size_or_height = raster_ds.RasterYSize
    geo_transform = raster_ds.GetGeoTransform()
    raster_ds = None

    min_lon_or_min_x = geo_transform[0]
    max_lon_or_max_x = geo_transform[0] + geo_transform[1] * raster_x_size_or_width
    max_lat_or_max_y = geo_transform[3]
    min_lat_or_min_y = geo_transform[3] + geo_transform[5] * raster_y_size_or_height
    xres = geo_transform[1]
    yres = geo_transform[5]

    geo_transform = None

    return {
        'x_size_or_width': raster_x_size_or_width,
        'y_size_or_height': raster_y_size_or_height,
        'min_lon_or_min_x': min_lon_or_min_x,
        'max_lon_or_max_x': max_lon_or_max_x,
        'max_lat_or_max_y': max_lat_or_max_y,
        'min_lat_or_min_y': min_lat_or_min_y,
        'xres': xres,
        'yres': yres,
        'nodata': nodata_value,
        'min': raster_min,
        'max': raster_max
    }


def parse_rainfall_csv(*,
                       raw_rainfall_csv_filepath: Path,
                       output_folderpath: Path,
                       date_column_name: str
                       ) -> dict:
    print(f'\n Parsing {raw_rainfall_csv_filepath} ... ')
    individual_filepaths = {}
    forecast_df = pd.read_csv(raw_rainfall_csv_filepath)

    forecast_dates = forecast_df[date_column_name].unique()

    for counter, single_date in enumerate(forecast_dates):
        daily_data = forecast_df[forecast_df[date_column_name] == single_date]

        output_filename = f'{date_column_name}_{counter + 1}_rainfall.csv'
        output_filepath = output_folderpath.joinpath(output_filename)

        daily_data.to_csv(output_filepath, index=False)
        if output_filepath.exists():
            individual_filepaths[counter + 1] = output_filepath
            print(f'... saved to {output_filepath}')
        else:
            raise FileExistsError(f'Could not create csv file at --> {output_filepath}')

    return individual_filepaths


def classify_raster(*,
                    input_raster_path: Path | str,
                    output_raster_path: Path | str,
                    classification_range: tuple | dict | None
                    ) -> str | Path:
    print(f'Classifying raster ...')

    raster_ds = gdal.Open(input_raster_path)
    band_ds = raster_ds.GetRasterBand(1)

    raster_x_size = raster_ds.RasterXSize
    raster_y_size = raster_ds.RasterYSize
    raster_geotransform = raster_ds.GetGeoTransform()
    raster_projection = raster_ds.GetProjection()

    nodata = band_ds.GetNoDataValue()
    if nodata is None:
        nodata = -128

    array_ds = band_ds.ReadAsArray()
    array_shape = array_ds.shape
    raster_ds = None
    band_ds = None

    if classification_range is not None:
        classified_array = np.full(array_shape, nodata, dtype=np.int8)

        for low, high, value in classification_range:
            if low is None:
                classified_array[(array_ds < high) & (array_ds != nodata)] = value
            elif high is None:
                classified_array[(array_ds >= low) & (array_ds != nodata)] = value
            else:
                classified_array[(array_ds >= low) & (array_ds < high)] = value
        classified_array[array_ds == nodata] = -128
    else:
        classified_array = array_ds
        pass

    array_ds = None

    raster_driver = gdal.GetDriverByName('GTiff')

    out_ds = raster_driver.Create(output_raster_path, raster_x_size, raster_y_size, 1, gdal.GDT_Int8)
    out_ds.SetGeoTransform(raster_geotransform)
    out_ds.SetProjection(raster_projection)

    out_band_ds = out_ds.GetRasterBand(1)
    out_band_ds.WriteArray(classified_array)
    out_band_ds.SetNoDataValue(-128)

    out_ds = None
    out_band_ds = None

    return output_raster_path


def create_gridded_raster_from_csv(*,
                                   input_csv_filepath: Path,
                                   output_raster_filepath: str | Path,
                                   information_raster_filepath: Path,
                                   create_raster_from_field: str
                                   ) -> str | Path:
    print(f'\nCreating gridded raster for -> {input_csv_filepath} ')

    csv_vrt = _create_vrt(csv_path=input_csv_filepath, parameter=create_raster_from_field)
    vrt_ds = gdal.OpenEx(csv_vrt, gdal.OF_VECTOR, open_options=['VRT'])

    raster_info = _get_raster_info(input_raster_filepath=information_raster_filepath)

    grid_options = gdal.GridOptions(
        format='GTiff',
        outputType=gdal.GDT_Float32,
        outputBounds=[
            raster_info['min_lon_or_min_x'],
            raster_info['min_lat_or_min_y'],
            raster_info['max_lon_or_max_x'],
            raster_info['max_lat_or_max_y']
        ],
        outputSRS='EPSG:4326',
        noData=-9999,
        # TODO: Define suitable algorithm here. Defaults to inverse distance.
        algorithm='invdist:power=2.0:smoothing=0.0:radius1=0.0:radius2=0.0:angle=0.0:max_points=0:min_points=0:nodata=-128',
        zfield=create_raster_from_field
    )

    gridded_raster = gdal.Grid(
        destName=output_raster_filepath,
        srcDS=vrt_ds,
        options=grid_options
    )

    vrt_ds = None
    grid_options = None
    gridded_raster = None

    return output_raster_filepath


def reproject_raster(*, input_raster_filepath: Path, output_raster_filepath: str | Path) -> str | Path:
    print('Reprojecting raster ... ')

    warp_options = gdal.WarpOptions(
        format='Gtiff',
        srcSRS='EPSG:4326',
        dstSRS='EPSG:32645',
        outputType=gdal.GDT_Float32,
        srcNodata=_get_raster_info(input_raster_filepath=input_raster_filepath)['nodata'],
        dstNodata=-9999,
        multithread=True,
        resampleAlg=gdal.GRA_Bilinear,
        warpMemoryLimit=8192
    )

    reprojected_raster = gdal.Warp(
        destNameOrDestDS=output_raster_filepath,
        srcDSOrSrcDSTab=input_raster_filepath,
        options=warp_options
    )

    warp_options = None
    reprojected_raster = None

    return output_raster_filepath


def resample_raster(*, input_raster_filepath: Path, output_raster_filepath: str | Path) -> str | Path:
    print('Resampling raster ...')

    warp_options = gdal.WarpOptions(
        format='Gtiff',
        xRes=30,
        yRes=30,
        srcSRS='EPSG:32645',
        dstSRS='EPSG:32645',
        outputType=gdal.GDT_Float32,
        srcNodata=_get_raster_info(input_raster_filepath=input_raster_filepath)['nodata'],
        dstNodata=-9999,
        multithread=True,
        # TODO: Appropriate algorithm as per use case.
        # resampleAlg=gdal.GRA_NearestNeighbour,
        # resampleAlg=gdal.GRA_Bilinear,
        # resampleAlg=gdal.GRA_Cubic,
        resampleAlg=gdal.GRA_CubicSpline,
        warpMemoryLimit=8192
    )

    resampled_raster = gdal.Warp(
        srcDSOrSrcDSTab=input_raster_filepath,
        destNameOrDestDS=output_raster_filepath,
        options=warp_options
    )

    warp_options = None
    resampled_raster = None

    return output_raster_filepath


def clip_raster(*,
                input_shapefile_filepath: Path,
                input_raster_filepath: Path,
                output_raster_filepath: str | Path
                ) -> str | Path:
    print(f'Clipping raster ...')

    warp_options = gdal.WarpOptions(
        format='Gtiff',
        xRes=30,
        yRes=30,
        srcSRS='EPSG:32645',
        dstSRS='EPSG:32645',
        outputType=gdal.GDT_Float32,
        dstNodata=-9999,
        multithread=True,
        cutlineLayer=input_shapefile_filepath.stem,
        cutlineDSName=input_shapefile_filepath,
        cropToCutline=True,
        cutlineSRS='EPSG:32645',
        warpMemoryLimit=8192
    )

    clipped_raster = gdal.Warp(
        srcDSOrSrcDSTab=input_raster_filepath,
        destNameOrDestDS=output_raster_filepath,
        options=warp_options
    )

    warp_options = None
    clipped_raster = None

    return output_raster_filepath


def forecast_pipeline(*,
                      individual_rainfall_forecast_csv_filepath: Path,
                      rainfall_field_name_in_csv: str = 'rainfall',
                      information_raster_filepath: Path,
                      classification_range: tuple | dict | None,
                      input_shapefile_filepath: Path,
                      output_raster_filepath: str | Path
                      ) -> str | Path:
    step0 = create_gridded_raster_from_csv(
        input_csv_filepath=individual_rainfall_forecast_csv_filepath,
        output_raster_filepath='/vsimem/step0.tif',
        create_raster_from_field=rainfall_field_name_in_csv,
        information_raster_filepath=information_raster_filepath
    )

    step1 = reproject_raster(
        input_raster_filepath=step0,
        output_raster_filepath='/vsimem/step1.tif'
    )

    _clear_memory(step0)

    step2 = resample_raster(
        input_raster_filepath=step1,
        output_raster_filepath='/vsimem/step2.tif'
    )

    _clear_memory(step1)

    step3 = clip_raster(
        input_shapefile_filepath=input_shapefile_filepath,
        input_raster_filepath=step2,
        output_raster_filepath='/vsimem/step3.tif'
    )

    _clear_memory(step2)

    step4 = classify_raster(
        input_raster_path=step3,
        output_raster_path=output_raster_filepath,
        classification_range=classification_range
    )

    _clear_memory(step3)
    _clear_memory(step4)

    return output_raster_filepath


def constants_raster_pipeline(*,
                              input_raster_filepath: Path,
                              output_raster_filepath: Path,
                              input_shapefile_filepath: Path,
                              classification_range: dict | tuple | None
                              ) -> str | Path:
    print(f'Processing raster --> {input_raster_filepath}')

    step1 = classify_raster(
        input_raster_path=input_raster_filepath,
        output_raster_path='/vsimem/step1.tif',
        classification_range=classification_range
    )

    step2 = clip_raster(
        input_raster_filepath=step1,
        output_raster_filepath=output_raster_filepath,
        input_shapefile_filepath=input_shapefile_filepath
    )

    _clear_memory(step1)
    _clear_memory(step2)

    return output_raster_filepath


def create_final_landslide_susceptibility_map(*,
                                              base_map_filepath: Path | str,
                                              recorded_rainfall_raster_filepath: Path | str,
                                              forecast_rainfall_raster_filepath: Path | str,
                                              output_raser_filepath: Path | str,
                                              recorded_rainfall_weight: float,
                                              forecast_rainfall_weight: float
                                              ) -> Path:
    basemap_info = _get_raster_info(input_raster_filepath=base_map_filepath)
    basemap_min = basemap_info['min']
    basemap_max = basemap_info['max']
    scaling_factor = basemap_max - basemap_min
    del basemap_info, basemap_max, basemap_min

    basemap_ds = gdal.Open(base_map_filepath)
    recorded_rainfall_ds = gdal.Open(recorded_rainfall_raster_filepath)
    forecast_rainfall_ds = gdal.Open(forecast_rainfall_raster_filepath)

    basemap_band = basemap_ds.GetRasterBand(1)
    basemap_array = basemap_band.ReadAsArray()
    # basemap_masked = basemap_array[basemap_array <= 0]
    basemap_masked = basemap_array
    basemap_masked[basemap_masked <= 0] = -128

    recorded_rainfall_band = recorded_rainfall_ds.GetRasterBand(1)
    recorded_rainfall_array = recorded_rainfall_band.ReadAsArray()
    # recorded_rainfall_array = recorded_rainfall_array[recorded_rainfall_array < 0]
    recorded_rainfall_masked = recorded_rainfall_array
    recorded_rainfall_masked[recorded_rainfall_masked < 0] = -128

    forecast_rainfall_band = forecast_rainfall_ds.GetRasterBand(1)
    forecast_rainfall_array = forecast_rainfall_band.ReadAsArray()
    # forecast_rainfall_masked = forecast_rainfall_array[forecast_rainfall_array < 0]
    forecast_rainfall_masked = forecast_rainfall_array
    forecast_rainfall_masked[forecast_rainfall_masked < 0] = -128

    step1 = scaling_factor / basemap_masked
    step2 = step1 * recorded_rainfall_masked * recorded_rainfall_weight
    step3 = step1 * forecast_rainfall_masked * forecast_rainfall_weight
    result = basemap_array + step2 + step3

    result[result < 0] = -128

    driver = gdal.GetDriverByName("GTiff")
    final_ds = driver.Create(
        output_raser_filepath,
        basemap_ds.RasterXSize,
        basemap_ds.RasterYSize,
        1,
        gdal.GDT_Float32
    )

    final_ds.SetGeoTransform(basemap_ds.GetGeoTransform())
    final_ds.SetProjection(basemap_ds.GetProjection())

    out_band = final_ds.GetRasterBand(1)
    out_band.WriteArray(result)
    out_band.SetNoDataValue(-128)
    out_band.FlushCache()

    basemap_ds = None
    recorded_rainfall_ds = None
    forecast_rainfall_ds = None
    final_ds = None

    basemap_band = None
    recorded_rainfall_band = None
    forecast_rainfall_band = None
    out_band = None

    return output_raser_filepath


if __name__ == '__main__':
    print('Hya bata chalauni haina. main.py bata chalauni.')
    exit()
