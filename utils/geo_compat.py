from pathlib import Path
import json
from typing import Any, List

import pandas as pd
import shapefile
from shapely.geometry import mapping, shape


class GeometryAccessor:
    def __init__(self, series: pd.Series):
        self._series = series

    @property
    def area(self) -> pd.Series:
        return self._series.apply(lambda geom: geom.area if geom is not None else 0)

    def notnull(self) -> pd.Series:
        return self._series.notnull()

    def intersects(self, other) -> pd.Series:
        return self._series.apply(lambda geom: geom.intersects(other) if geom is not None else False)

    def __getattr__(self, item: str):
        return getattr(self._series, item)

    def __iter__(self):
        return iter(self._series)

    def __len__(self) -> int:
        return len(self._series)


class GeoDataFrame(pd.DataFrame):
    _metadata = ['crs', '_geom_col']

    def __init__(self, data: Any = None, geometry: str = 'geometry', crs: str | None = None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        self._geom_col = geometry
        self.crs = crs

    @property
    def _constructor(self):
        return GeoDataFrame

    @property
    def geometry(self) -> GeometryAccessor:
        if self._geom_col in self.columns:
            return GeometryAccessor(self[self._geom_col])
        return GeometryAccessor(pd.Series([None] * len(self), index=self.index))

    def set_crs(self, crs: str):
        self.crs = crs
        return self

    def to_crs(self, crs: str):
        self.crs = crs
        return self

    def to_json(self) -> str:
        features = []
        for _, row in self.iterrows():
            geom = row.get(self._geom_col)
            props = {key: value for key, value in row.items() if key != self._geom_col}
            features.append({
                'type': 'Feature',
                'geometry': mapping(geom) if geom is not None else None,
                'properties': props,
            })
        return json.dumps({'type': 'FeatureCollection', 'features': features})

    def to_file(self, path: Path | str, driver: str = 'GeoJSON'):
        p = Path(path)
        if str(driver).lower() == 'geojson':
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(self.to_json(), encoding='utf-8')
            return
        if str(driver).upper().startswith('ESRI'):
            self.to_file(p.with_suffix('.geojson'), driver='GeoJSON')
            return
        self.to_file(p.with_suffix('.geojson'), driver='GeoJSON')

    @property
    def total_bounds(self) -> List[float]:
        if self.empty:
            return [0.0, 0.0, 0.0, 0.0]
        minx = miny = float('inf')
        maxx = maxy = float('-inf')
        for geom in self[self._geom_col] if self._geom_col in self.columns else []:
            if geom is None:
                continue
            bounds = geom.bounds
            minx = min(minx, bounds[0])
            miny = min(miny, bounds[1])
            maxx = max(maxx, bounds[2])
            maxy = max(maxy, bounds[3])
        if minx == float('inf'):
            return [0.0, 0.0, 0.0, 0.0]
        return [minx, miny, maxx, maxy]


def read_file(path: Path | str) -> GeoDataFrame:
    reader = shapefile.Reader(str(path))
    field_names = [field[0] for field in reader.fields[1:]]
    records = []
    for shape_record in reader.iterShapeRecords():
        record = {name: value for name, value in zip(field_names, shape_record.record)}
        record['geometry'] = shape(shape_record.shape.__geo_interface__)
        records.append(record)
    return GeoDataFrame(records, geometry='geometry', crs='EPSG:4326')


class _GPDShim:
    GeoDataFrame = GeoDataFrame

    @staticmethod
    def read_file(path: Path | str) -> GeoDataFrame:
        return read_file(path)


gpd = _GPDShim()
