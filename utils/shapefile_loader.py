from pathlib import Path
from typing import Callable, Optional

import geopandas as gpd
import pandas as pd


def load_shapefiles(root_dir: Path, progress_callback: Optional[Callable[[int, int, Path], None]] = None) -> gpd.GeoDataFrame:
    shapefiles = list(root_dir.rglob('*.shp'))
    if not shapefiles:
        raise FileNotFoundError(f'No shapefiles found under {root_dir}')

    frames = []
    for idx, shp_path in enumerate(sorted(shapefiles), start=1):
        if progress_callback:
            progress_callback(idx, len(shapefiles), shp_path)

        gdf = gpd.read_file(shp_path)
        if gdf.crs is None:
            gdf = gdf.set_crs('EPSG:4326')
        else:
            gdf = gdf.to_crs('EPSG:4326')

        gdf['LOT_NAME'] = shp_path.parent.name
        gdf['SOURCE_FILE'] = shp_path.name
        gdf['area_hectares'] = gdf.geometry.area / 10000
        frames.append(gdf)

    combined = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs='EPSG:4326')
    if 'parcel_number' not in combined.columns:
        combined['parcel_number'] = combined.get('ParcelID')
    return combined
