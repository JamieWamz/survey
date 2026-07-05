import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

import geopandas as gpd
from shapely.geometry import mapping, shape
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


class DatabaseManager:
    def __init__(self, db_url: str, base_dir: Optional[Path] = None):
        self.db_url = db_url
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.engine: Engine = create_engine(self.db_url, future=True)

    def initialize(self):
        if self.engine.dialect.name.startswith('postgres'):
            self._initialize_postgres()
        else:
            self._initialize_sqlite()

        if not self.get_user('admin'):
            self.create_user('admin', 'admin123', role='admin')
        if not self.get_user('surveyor'):
            self.create_user('surveyor', 'survey123', role='surveyor')
        if not self.get_user('viewer'):
            self.create_user('viewer', 'view123', role='viewer')

    def _initialize_sqlite(self):
        schema_file = self.base_dir / 'database' / 'schema.sql'
        with open(schema_file, 'r', encoding='utf-8') as fp:
            sql = fp.read()
        with self.engine.begin() as conn:
            conn.execute(text(sql))

    def _initialize_postgres(self):
        create_sql = '''
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS parcels (
    id SERIAL PRIMARY KEY,
    parcel_number TEXT,
    lot_name TEXT,
    owner TEXT,
    land_use TEXT,
    status TEXT,
    area_ha DOUBLE PRECISION,
    properties_json JSONB,
    geom_geojson TEXT,
    geom geometry(Geometry, 4326),
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS query_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    query_text TEXT,
    params JSONB,
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''
        with self.engine.begin() as conn:
            conn.execute(text(create_sql))

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def create_user(self, username: str, password: str, role: str = 'viewer') -> bool:
        pw_hash = self._hash_password(password)
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text('INSERT INTO users (username, password_hash, role) VALUES (:u, :p, :r)'),
                    {'u': username, 'p': pw_hash, 'r': role},
                )
            return True
        except SQLAlchemyError:
            return False

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text('SELECT id, username, role FROM users WHERE username = :u'), {'u': username}).fetchone()
            if result:
                return {'id': result[0], 'username': result[1], 'role': result[2]}
        return None

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        pw_hash = self._hash_password(password)
        with self.engine.connect() as conn:
            result = conn.execute(
                text('SELECT id, username, role FROM users WHERE username = :u AND password_hash = :p'),
                {'u': username, 'p': pw_hash},
            ).fetchone()
            if result:
                self.log_audit(result[0], 'login', f'User {username} logged in')
                return {'id': result[0], 'username': result[1], 'role': result[2]}
        return None

    def log_audit(self, user_id: Optional[int], action: str, details: str):
        with self.engine.begin() as conn:
            conn.execute(
                text('INSERT INTO audit_log (user_id, action, details) VALUES (:u, :a, :d)'),
                {'u': user_id, 'a': action, 'd': details},
            )

    def record_query(self, user_id: Optional[int], query_text: str, params: Dict[str, Any], result_count: int):
        with self.engine.begin() as conn:
            conn.execute(
                text('INSERT INTO query_history (user_id, query_text, params, result_count) VALUES (:u, :q, :p, :r)'),
                {'u': user_id, 'q': query_text, 'p': json.dumps(params), 'r': result_count},
            )

    def count_parcels(self) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(text('SELECT COUNT(*) FROM parcels')).scalar_one()
            return int(result)

    def create_parcel(self, parcel: Dict[str, Any]) -> int:
        properties = {k: v for k, v in parcel.items() if k not in ['geometry']}
        geometry = parcel.get('geometry')
        geom_text = json.dumps(geometry) if geometry else None
        if self.engine.dialect.name.startswith('postgres') and geometry:
            insert_sql = text(
                'INSERT INTO parcels (parcel_number, lot_name, owner, land_use, status, area_ha, properties_json, geom_geojson, geom, source_file) '
                'VALUES (:pn, :ln, :o, :lu, :st, :ah, :pj, :gj, ST_GeomFromGeoJSON(:gj), :sf) RETURNING id'
            )
            params = {
                'pn': properties.get('parcel_number'),
                'ln': properties.get('lot_name'),
                'o': properties.get('owner'),
                'lu': properties.get('land_use'),
                'st': properties.get('status'),
                'ah': properties.get('area_ha'),
                'pj': json.dumps(properties.get('properties', {})),
                'gj': geom_text,
                'sf': properties.get('source_file'),
            }
        else:
            insert_sql = text(
                'INSERT INTO parcels (parcel_number, lot_name, owner, land_use, status, area_ha, properties_json, geom_geojson, source_file) '
                'VALUES (:pn, :ln, :o, :lu, :st, :ah, :pj, :gj, :sf)'
            )
            params = {
                'pn': properties.get('parcel_number'),
                'ln': properties.get('lot_name'),
                'o': properties.get('owner'),
                'lu': properties.get('land_use'),
                'st': properties.get('status'),
                'ah': properties.get('area_ha'),
                'pj': json.dumps(properties.get('properties', {})),
                'gj': geom_text,
                'sf': properties.get('source_file'),
            }

        with self.engine.begin() as conn:
            result = conn.execute(insert_sql, params)
            if self.engine.dialect.name.startswith('postgres') and result.returns_rows:
                return int(result.scalar_one())
            return int(result.lastrowid)

    def get_parcel(self, parcel_id: int) -> Optional[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text('SELECT * FROM parcels WHERE id = :id'), {'id': parcel_id}).fetchone()
            if not result:
                return None
            return dict(result)

    def update_parcel(self, parcel_id: int, updates: Dict[str, Any]) -> bool:
        assignments = []
        params = {'id': parcel_id}
        for key, value in updates.items():
            if key == 'geometry':
                params['geom'] = json.dumps(value)
                if self.engine.dialect.name.startswith('postgres'):
                    assignments.append('geom = ST_GeomFromGeoJSON(:geom)')
                    assignments.append('geom_geojson = :geom')
                else:
                    assignments.append('geom_geojson = :geom')
            else:
                assignments.append(f'{key} = :{key}')
                params[key] = value

        with self.engine.begin() as conn:
            conn.execute(text(f'UPDATE parcels SET {", ".join(assignments)} WHERE id = :id'), params)
        return True

    def delete_parcel(self, parcel_id: int) -> bool:
        with self.engine.begin() as conn:
            conn.execute(text('DELETE FROM parcels WHERE id = :id'), {'id': parcel_id})
        return True

    def _rows_to_gdf(self, rows) -> gpd.GeoDataFrame:
        records = []
        for row in rows:
            record = dict(row)
            geom_text = record.get('geom_geojson')
            geometry = None
            if geom_text:
                geometry = shape(json.loads(geom_text))
            record['geometry'] = geometry
            records.append(record)
        return gpd.GeoDataFrame(records, geometry='geometry', crs='EPSG:4326')

    def search_parcels(self, criteria: Dict[str, Any], spatial: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> gpd.GeoDataFrame:
        where = []
        params: Dict[str, Any] = {}
        for key in ['parcel_number', 'lot_name', 'owner', 'land_use', 'status']:
            value = criteria.get(key)
            if value:
                where.append(f"{key} ILIKE :{key}")
                params[key] = f"%{value}%"
        if criteria.get('area_min') is not None:
            where.append('area_ha >= :area_min')
            params['area_min'] = criteria['area_min']
        if criteria.get('area_max') is not None:
            where.append('area_ha <= :area_max')
            params['area_max'] = criteria['area_max']

        if spatial and spatial.get('bbox'):
            minx, miny, maxx, maxy = spatial['bbox']
            if self.engine.dialect.name.startswith('postgres'):
                where.append('ST_Intersects(geom, ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))')
                params.update({'minx': minx, 'miny': miny, 'maxx': maxx, 'maxy': maxy})
            else:
                params.update({'minx': minx, 'miny': miny, 'maxx': maxx, 'maxy': maxy})

        sql = 'SELECT * FROM parcels'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)

        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()

        gdf = self._rows_to_gdf(rows)
        if spatial and spatial.get('bbox') and not self.engine.dialect.name.startswith('postgres'):
            minx, miny, maxx, maxy = spatial['bbox']
            bbox = shape({
                'type': 'Polygon',
                'coordinates': [[[minx, miny], [minx, maxy], [maxx, maxy], [maxx, miny], [minx, miny]]],
            })
            gdf = gdf[gdf.geometry.notnull() & gdf.geometry.intersects(bbox)]

        self.record_query(user_id, sql, params, len(gdf))
        return gdf

    def seed_parcels(self, gdf: gpd.GeoDataFrame):
        if self.count_parcels() > 0:
            return
        for _, row in gdf.iterrows():
            geometry = None
            if row.geometry is not None:
                geometry = mapping(row.geometry)
            parcel = {
                'parcel_number': row.get('parcel_number') or row.get('ParcelID') or '',
                'lot_name': row.get('LOT_NAME'),
                'owner': row.get('owner'),
                'land_use': row.get('land_use'),
                'status': row.get('status'),
                'area_ha': float(row.get('area_hectares', 0) or 0),
                'properties': {k: v for k, v in row.items() if k not in ['geometry']},
                'geometry': geometry,
                'source_file': row.get('SOURCE_FILE'),
            }
            self.create_parcel(parcel)
