# Yengwe Cadastre Streamlit App

A production-ready Streamlit app for exploring cadastre data, loading shapefiles, and exporting KML/KMZ/GeoJSON/CSV.

## Features

- User login/logout and session management
- Shapefile ingestion with WGS84 reprojection
- Interactive parcel mapping with Folium
- Search by parcel attributes and bounding box
- Export to GeoJSON, CSV, KML, KMZ, Shapefile
- SQLite first, PostGIS-ready option via `DATABASE_URL`

## Project Structure

- `app.py` — main Streamlit app entry point
- `database/` — DB manager, schema, and seed logic
- `utils/` — shapefile loading, exports, mapping helpers
- `pages/` — Streamlit page modules
- `.streamlit/` — Streamlit configuration

## Setup

1. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment variables:

```bash
cp .env.example .env
```

4. Run the app:

```bash
streamlit run app.py
```

## Notes

- Place parcel shapefiles in `Yengwe SHP/` or provide another folder via the app UI.
- Exports are written to `exports/`.
- Use `DATABASE_URL` in `.env` to switch to PostgreSQL/PostGIS.
