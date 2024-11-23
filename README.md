# Nepal-Landslide-Susceptibility-Mapping
This project implements a geospatial analysis pipeline to create landslide susceptibility maps. 


# Project Readme: Landslide Susceptibility Mapping

## Overview
This project provides a comprehensive pipeline for generating **landslide susceptibility maps** using multi-source geospatial and meteorological data. The system integrates static geographic factors (e.g., slope, curvature, soil type) and dynamic meteorological data (e.g., rainfall forecasts) to create susceptibility maps.

## Directory Structure
- **Input/**: Contains raw data including:
  - `Raw/Vector/`: Shapefiles for geographical boundaries.
  - `Raw/Raster/`: Raster data for static geographic factors.
  - `Raw/Csv/`: Rainfall forecast and recorded data in CSV format.
- **Output/**: Stores final output maps (classified and susceptibility maps).
- **Processed/**: Stores intermediate outputs such as processed raster files and parsed rainfall data.

## Prerequisites
1. **Python 3.8+**
2. Required Python packages:
   - `gdal`
   - `numpy`
   - `pandas`
   - `osgeo`
   Install these using the provided `requirements.txt`.

3. Ensure that all directories and filepaths are correctly structured as defined in `constants.py`.

## Project Files
### 1. **constants.py**
Defines constants and configurations for:
- **Classification Parameters**: Rules to classify raster data (e.g., slope, NDVI).
- **File Paths**: Input, output, and processed data paths.
- **Weights**: Importance weights assigned to each static factor for susceptibility analysis.
- Contains runtime validation for file existence and consistency.

### 2. **functions.py**
Core functions for geospatial processing:
- **Raster Operations**:
  - `classify_raster()`: Classifies raster data based on specified rules.
  - `clip_raster()`: Clips raster files using shapefile boundaries.
  - `reproject_raster()`: Reprojects raster to a specified coordinate reference system.
  - `resample_raster()`: Resamples raster resolution.
- **Rainfall Parsing**:
  - `parse_rainfall_csv()`: Splits rainfall data by date and generates daily CSV files.
- **Pipeline Functions**:
  - `forecast_pipeline()`: Processes forecast data into classified raster files.
  - `constants_raster_pipeline()`: Handles static geographic data.
- **Final Map Generation**:
  - `create_final_landslide_susceptibility_map()`: Combines static and dynamic data to generate susceptibility maps.

### 3. **main.py**
Executes the full workflow:
1. **Static Data Preprocessing**:
   - Checks and processes rasters for static factors.
   - Generates a base landslide susceptibility map using static factors and weights.
2. **Rainfall Data Handling**:
   - Parses recorded rainfall CSVs and generates classified rasters.
   - Processes forecast rainfall data if `FLAG_UPDATE_FORECAST_RASTERS` is set.
3. **Final Map Generation**:
   - Combines static and dynamic data to generate susceptibility maps for multiple forecast days.

## Usage
1. **Prepare Inputs**:
   - Place all required input files in the designated `Input/` subdirectories.
   - Rainfall CSVs must adhere to the column format specified in `main.py`.
2. **Run Pipeline**:
   Execute `main.py`:
   ```bash
   python main.py
   ```
3. **Outputs**:
   - Final susceptibility maps are saved in `Output/`.
   - Intermediate files are in `Processed/`.

## Notes
- Date columns in rainfall CSVs must be correct and consistent. No automated checks are implemented for this.
- Ensure the sum of weights in `constants.FinalWeights` equals 1.

## Future Improvements
- Add error handling for rainfall date validation.
- Introduce a GUI or CLI interface for easier parameter configuration.
- Optimize computational performance for large raster datasets.

---
