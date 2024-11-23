from dataclasses import dataclass
from pathlib import Path


# Classification parameters
# classification_ranges:
#     (None, 50, 1),  values < 50 are classified as 1
#     (50, 100, 2),  values from >=50 to <100 are classified as 2
#     (100, 150, 3),  values from >=100 to <150 are classified as 3
#     (150, None, 4)  values >=150 are classified as 4
#     None -> No classification is done.


@dataclass(frozen=True)
class ClassificationParameters:
    slope: tuple[tuple] = (
        (None, 15, 1),
        (15, 30, 8),
        (30, 60, 10),
        (60, None, 4))

    curvature: tuple[tuple] = (
        (None, 0, 2),
        (0, 0.001, 1),
        (0.01, None, 3))

    lulc: tuple[tuple] = (
        (None, 1, 1),
        (1, 2, 1),
        (2, 4, 3),
        (4, 5, 7),
        (5, 7, 3),
        (7, 8, 2),
        (8, 9, 8),
        (9, 11, 1),
        (11, None, 7))

    ndvi: tuple[tuple] = (
        (None, 0, 9),
        (0, 0.2, 7),
        (0.2, 0.4, 5),
        (0.4, None, 2))

    aspect: tuple[tuple] = (
        (0, 22.5, 2),  # N
        (22.5, 67.5, 2),  # NE
        (67.5, 112.5, 3),  # E
        (112.5, 157.5, 4),  # SE
        (157.5, 202.5, 6),  # S
        (202.5, 247.5, 4),  # SW
        (247.5, 292.5, 6),  # W
        (292.5, 337.5, 2),  # NW
        (337.5, 360, 2))  # N

    river: tuple[tuple] = (
        (None, 100, 5),
        (100, 500, 3),
        (500, None, 2))

    road: tuple[tuple] = (
        (None, 100, 5),
        (100, 500, 3),
        (500, None, 2))

    fault: tuple[tuple] = (
        (None, 100, 5),
        (100, 500, 3),
        (500, None, 2))

    soil: tuple[tuple] = (
        (None, 2, 2),
        (2, 3, 6),
        (3, 4, 7),
        (4, 5, 3),
        (5, 12, 2),
        (12, 13, 2),
        (13, 14, 3),
        (14, 15, 4),
        (15, None, 2))

    geology: tuple[tuple] = None


@dataclass(frozen=True)
class FolderPaths:
    input: Path = Path('./Input/')
    output: Path = Path('./Output/')
    processed: Path = Path('./Input/Processed/')

    def __post_init__(self):
        folder_paths = [self.input, self.output, self.processed]
        missing_folder = [str(path) for path in folder_paths if not path.exists()]
        if missing_folder:
            raise FileNotFoundError(f"The following folders are missing: {', '.join(missing_folder)}")


@dataclass(frozen=True)
class RawVectorsFilePaths:
    buffered_boundary_utm45n: Path = Path('Input/Raw/Vector/nepal_boundary_buffered_3km_utm45n.shp')
    exact_boundary_utm45n: Path = Path('Input/Raw/Vector/nepal_boundary_exact_utm45n.shp')

    def __post_init__(self):
        file_paths = [self.buffered_boundary_utm45n, self.exact_boundary_utm45n]
        missing_files = [str(path) for path in file_paths if not path.exists()]
        if missing_files:
            raise FileNotFoundError(f"The following folders are missing: {', '.join(missing_files)}")


@dataclass(frozen=True)
class RawRastersFilePaths:
    slope: Path = Path('Input/Raw/Raster/slope_utm45n.tif')
    curvature: Path = Path('Input/Raw/Raster/curvature_utm45n.tif')
    lulc: Path = Path('Input/Raw/Raster/lulc_utm45n.tif')
    ndvi: Path = Path('Input/Raw/Raster/ndvi_utm45n.tif')
    aspect: Path = Path('Input/Raw/Raster/aspect_utm45n.tif')
    river: Path = Path('Input/Raw/Raster/river_utm45n.tif')
    road: Path = Path('Input/Raw/Raster/road_utm45n.tif')
    fault: Path = Path('Input/Raw/Raster/thrust_utm45n.tif')
    soil: Path = Path('Input/Raw/Raster/soil_utm45n.tif')
    geology: Path = Path('Input/Raw/Raster/geology_utm45n.tif')

    def __post_init__(self):
        file_paths = [
            self.slope,
            self.curvature,
            self.lulc, self.ndvi,
            self.aspect,
            self.river,
            self.road,
            self.fault,
            self.soil
        ]

        missing_files = [str(path) for path in file_paths if not path.exists()]
        if missing_files:
            raise FileNotFoundError(f"The following files are missing: {', '.join(missing_files)}")


@dataclass(frozen=True)
class ClassifiedRastersFilePaths:
    slope: Path = Path('Input/Processed/Raster/slope_utm45n_cls.tif')
    curvature: Path = Path('Input/Processed/Raster/curvature_utm45n_cls.tif')
    lulc: Path = Path('Input/Processed/Raster/lulc_utm45n_cls.tif')
    ndvi: Path = Path('Input/Processed/Raster/ndvi_utm45n_cls.tif')
    aspect: Path = Path('Input/Processed/Raster/aspect_utm45n_cls.tif')
    river: Path = Path('Input/Processed/Raster/river_utm45n_cls.tif')
    road: Path = Path('Input/Processed/Raster/road_utm45n_cls.tif')
    fault: Path = Path('Input/Processed/Raster/thrust_utm45n_cls.tif')
    soil: Path = Path('Input/Processed/Raster/soil_utm45n_cls.tif')
    geology: Path = Path('Input/Processed/Raster/geology_utm45n_cls.tif')


@dataclass(frozen=True)
class FinalWeights:
    slope: float = 0.15
    curvature: float = 0.08
    lulc: float = 0.09
    ndvi: float = 0.08
    aspect: float = 0.09
    river: float = 0.07
    road: float = 0.09
    fault: float = 0.13
    soil: float = 0.1
    geology: float = 0.12

    def __post_init__(self):
        weight_values = [
            self.slope,
            self.curvature,
            self.lulc, self.ndvi,
            self.aspect,
            self.river,
            self.road,
            self.soil,
            self.geology
        ]

        if any(weight == 0 for weight in weight_values):
            raise ValueError('All weights must be non-zero.')
        elif round(sum(weight_values)) != 1:
            # The above check is not fool-proof.
            # Floating point calculation.
            # Should be fine for the use case.
            raise ValueError('Ensure that the sum of all weights is 1.')
        else:
            pass
        del weight_values


if __name__ == '__main__':
    print('This file is meant to be run from main.py')
    exit()
