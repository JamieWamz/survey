from typing import Dict, Optional, Tuple

import folium
import geopandas as gpd
from folium import Map
from folium.features import GeoJson
from shapely.geometry import mapping

LAYER_COLORS = {
    'default': '#3388ff',
    'residential': '#ffeda0',
    'commercial': '#feb24c',
    'industrial': '#f03b20',
    'agriculture': '#31a354',
    'unknown': '#6c757d',
}

ZAMBIA_CENTER = (-13.133897, 27.849332)


def create_base_map(center: Tuple[float, float] = ZAMBIA_CENTER, zoom_start: int = 12) -> folium.Map:
    return folium.Map(location=list(center), zoom_start=zoom_start, tiles='OpenStreetMap')


def _choose_color(value: Optional[str]) -> str:
    if not value:
        return LAYER_COLORS['unknown']
    key = str(value).strip().lower()
    return LAYER_COLORS.get(key, LAYER_COLORS['default'])


def add_parcel_layer(m: folium.Map, gdf: gpd.GeoDataFrame, name: str = 'Parcels', color_field: Optional[str] = None) -> folium.Map:
    def style_fn(feature):
        props = feature.get('properties', {})
        color_value = props.get(color_field) if color_field else None
        return {
            'fillColor': _choose_color(color_value),
            'color': _choose_color(color_value),
            'weight': 1,
            'fillOpacity': 0.55,
        }

    tooltip_fields = ['parcel_number', 'LOT_NAME', 'owner', 'land_use', 'status']
    tooltip = folium.GeoJsonTooltip(fields=[field for field in tooltip_fields if field in gdf.columns], labels=True)
    geo_json = GeoJson(data=gdf.to_json(), name=name, style_function=style_fn, tooltip=tooltip)
    geo_json.add_to(m)
    folium.LayerControl(position='topright').add_to(m)
    return m


def get_bounds(gdf: gpd.GeoDataFrame):
    if gdf is None or gdf.empty:
        return None
    return gdf.total_bounds.tolist()


def get_center(gdf: gpd.GeoDataFrame):
    if gdf is None or gdf.empty:
        return ZAMBIA_CENTER
    minx, miny, maxx, maxy = gdf.total_bounds
    return ((miny + maxy) / 2.0, (minx + maxx) / 2.0)


def get_optimal_zoom(gdf: gpd.GeoDataFrame):
    if gdf is None or gdf.empty:
        return 6
    bounds = gdf.total_bounds
    width = bounds[2] - bounds[0]
    if width < 0.1:
        return 14
    if width < 1:
        return 12
    if width < 5:
        return 10
    return 8


def add_floating_legend(m: folium.Map, title: str, items: Dict[str, str]) -> folium.Map:
    html = '<div style="position: fixed; bottom: 20px; left: 20px; z-index:9999; background: rgba(255,255,255,0.95); padding: 10px; border: 1px solid #ccc; border-radius: 8px; font-size: 12px;">'
    html += f'<strong>{title}</strong><br>'
    for label, color in items.items():
        html += f'<span style="display:inline-block;width:12px;height:12px;background:{color};margin-right:6px;"></span>{label}<br>'
    html += '</div>'
    m.get_root().html.add_child(folium.Element(html))
    return m
