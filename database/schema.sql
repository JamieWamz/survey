-- Schema for Yengwe Cadastre

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parcels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parcel_number TEXT,
    lot_name TEXT,
    owner TEXT,
    land_use TEXT,
    status TEXT,
    area_ha REAL,
    properties_json TEXT, -- additional attributes as JSON
    geom_geojson TEXT, -- store geometry as GeoJSON text for SQLite
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    query_text TEXT,
    params TEXT,
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PostGIS-specific geometry column (added dynamically when using PostgreSQL/PostGIS)
-- Example (run only for PostgreSQL with PostGIS extension):
-- SELECT PostGIS_Version();
-- ALTER TABLE parcels ADD COLUMN geom geometry;
