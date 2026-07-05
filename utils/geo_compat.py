from pathlib import Path
import json
from typing import Any, Iterable, List

import pandas as pd
from shapely.geometry import shape, mapping
import shapefile


class GeometryAccessor:
    def __init__(self, series: pd.Series):
        self._s = series

    @property
    def area(self) -> pd.Series:
        return self._s.apply(lambda g: g.area if g is not None else 0)

    def notnull(self) -> pd.Series:
        return self._s.notnull()

    def intersects(self, other) -> pd.Series:
        return self._s.apply(lambda g: g.intersects(other) if g is not None else False)


class GeoDataFrame:
    def __init__(self, data: Any = None, geometry: str = 'geometry', crs: str | None = None):
        self._df = pd.DataFrame(data)
        self._geom_col = geometry
        self.crs = crs

    @property
    def geometry(self) -> GeometryAccessor:
        return GeometryAccessor(self._df[self._geom_col])

    @property
    def columns(self):
        return self._df.columns

    @property
    def empty(self):
        return self._df.empty

    def __getitem__(self, key):
        return self._df[key]

    def __setitem__(self, key, value):
        self._df[key] = value

    def __len__(self):
        return len(self._df)

    def iterrows(self):
        return self._df.iterrows()

    def copy(self):
        return GeoDataFrame(self._df.copy(), geometry=self._geom_col, crs=self.crs)

    def set_crs(self, crs: str):
        self.crs = crs
        return self

    def to_crs(self, crs: str):
        # no-op for simple compatibility shim
        self.crs = crs
        return self

    def to_json(self) -> str:
        features = []
        for _, row in self._df.iterrows():
            geom = row.get(self._geom_col)
            props = {k: v for k, v in row.items() if k != self._geom_col}
            feature = {
                'type': 'Feature',
                'geometry': mapping(geom) if geom is not None else None,
                'properties': props,
            }
            features.append(feature)
        return json.dumps({'type': 'FeatureCollection', 'features': features})

    def to_file(self, path: Path | str, driver: str = 'GeoJSON'):
        p = Path(path)
        if driver == 'GeoJSON':
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'w', encoding='utf-8') as fp:
                fp.write(self.to_json())
            return
        # ESRI Shapefile fallback: write GeoJSON instead (Streamlit: client can consume geojson)
        if driver.upper().startswith('ESRI'):
            geojson_path = p.with_suffix('.geojson')
            self.to_file(geojson_path, driver='GeoJSON')
            return
        # default: write GeoJSON
        self.to_file(p.with_suffix('.geojson'), driver='GeoJSON')

    @property
    def total_bounds(self) -> List[float]:
        if self._df.empty:
            return [0, 0, 0, 0]
        xs = []
        ys = []
        minx = miny = float('inf')
        maxx = maxy = float('-inf')
        for geom in self._df[self._geom_col]:
            if geom is None:
                continue
            b = geom.bounds
            minx = min(minx, b[0])
            miny = min(miny, b[1])
            maxx = max(maxx, b[2])
            maxy = max(maxy, b[3])
        if minx == float('inf'):
            return [0, 0, 0, 0]
        return [minx, miny, maxx, maxy]

    def __getattr__(self, item):
        # delegate DataFrame methods where reasonable
        return getattr(self._df, item)


def read_file(path: Path | str) -> GeoDataFrame:
    r = shapefile.Reader(str(path))
    fields = r.fields[1:]
    field_names = [f[0] for f in fields]
    records = []
    for sr in r.iterShapeRecords():
        rec = {name: val for name, val in zip(field_names, sr.record)}
        geom = shape(sr.shape.__geo_interface__)
        rec['geometry'] = geom
        records.append(rec)
    return GeoDataFrame(records, geometry='geometry', crs='EPSG:4326')


# Expose a module-level name `gpd` for minimal compatibility with imports
class _GPDShim:
    GeoDataFrame = GeoDataFrame

    @staticmethod
    def read_file(path):
        return read_file(path)


gpd = _GPDShim()
