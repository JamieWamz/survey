import json
import zipfile
from pathlib import Path
from typing import Dict

import geopandas as gpd
import pandas as pd
import simplekml


def export_to_kml(gdf: gpd.GeoDataFrame, output_path: Path):
    if gdf.crs is None:
        gdf = gdf.set_crs('EPSG:4326')
    else:
        gdf = gdf.to_crs('EPSG:4326')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    kml = simplekml.Kml()

    for _, row in gdf.iterrows():
        geom = row.geometry
        props = row.drop(labels='geometry').to_dict()
        if geom is None:
            continue

        name = str(props.get('parcel_number', props.get('LOT_NAME', 'Parcel')))
        description_lines = [f'{k}: {v}' for k, v in props.items() if v is not None and k != 'geometry']
        description = '\n'.join(description_lines)

        if geom.geom_type == 'Point':
            point = kml.newpoint(name=name)
            point.coords = [(geom.x, geom.y)]
            point.description = description
        elif geom.geom_type in ['Polygon', 'MultiPolygon']:
            polygon = kml.newpolygon(name=name)
            if geom.geom_type == 'Polygon':
                polygon.outerboundaryis = list(geom.exterior.coords)
            else:
                polygon.outerboundaryis = list(geom.geoms[0].exterior.coords)
            polygon.description = description
        else:
            point = kml.newpoint(name=name)
            point.coords = [(geom.centroid.x, geom.centroid.y)]
            point.description = description

    kml.save(str(output_path))


def export_to_kmz(gdf: gpd.GeoDataFrame, output_path: Path):
    kml_path = output_path.with_suffix('.kml')
    export_to_kml(gdf, kml_path)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(kml_path, arcname=kml_path.name)
    kml_path.unlink(missing_ok=True)


def export_to_geojson(gdf: gpd.GeoDataFrame, output_path: Path):
    if gdf.crs is None:
        gdf = gdf.set_crs('EPSG:4326')
    else:
        gdf = gdf.to_crs('EPSG:4326')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver='GeoJSON')


def export_to_csv(gdf: gpd.GeoDataFrame, output_path: Path):
    out = gdf.copy()
    if 'geometry' in out.columns:
        out = out.drop(columns='geometry')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)


def export_to_shapefile(gdf: gpd.GeoDataFrame, output_path: Path):
    temp_dir = output_path.parent / 'shapefile_export'
    temp_dir.mkdir(parents=True, exist_ok=True)
    if gdf.crs is None:
        gdf = gdf.set_crs('EPSG:4326')
    gdf.to_file(temp_dir / 'parcels.shp', driver='ESRI Shapefile')
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for shp_file in temp_dir.glob('*'):
            zf.write(shp_file, arcname=shp_file.name)
    for shp_file in temp_dir.glob('*'):
        shp_file.unlink()
    temp_dir.rmdir()
