# Yengwe Ward Cadastre System

A deployment-ready spatial land records management web application built with Streamlit, designed for cadastral survey and parcel administration in Yengwe Ward, Copperbelt Province, Zambia.

---

## Features

- **Interactive Map** — Folium-powered map with color-coded parcels by land use, floating legend, and per-parcel tooltips
- **Spatial Data Ingestion** — Shapefile upload and auto-reprojection to WGS84 (EPSG:4326), with area calculation in UTM Zone 35S (EPSG:32735)
- **Dashboard Analytics** — Plotly charts including land use distribution (bar + pie), parcel area histogram, and top parcels by area
- **Advanced Search** — Multi-field filtering (parcel ID, owner, land use, status) with area range sliders; results rendered on a dedicated map
- **Multi-Format Export** — Download filtered or full datasets as KML, KMZ, GeoJSON, or CSV
- **Role-Based Access Control** — Three user roles (Admin, Surveyor, Viewer) with SQLite-backed authentication and SHA-256 password hashing
- **Single-File Deployment** — Entire application in one `app.py` file; deployable to Streamlit Cloud with zero additional infrastructure

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend / App | [Streamlit](https://streamlit.io) |
| Map Rendering | [Folium](https://python-visualization.github.io/folium/) + streamlit-folium |
| Spatial Processing | [GeoPandas](https://geopandas.org/), [Shapely](https://shapely.readthedocs.io/) |
| Charts | [Plotly Express](https://plotly.com/python/plotly-express/) |
| KML/KMZ Export | [SimpleKML](https://simplekml.readthedocs.io/) |
| Database | SQLite (stdlib) |
| Navigation | streamlit-option-menu |
| Language | Python 3.10+ |

---

## Project Structure

```
survey/
├── app.py                  # Main application (single-file)
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Streamlit theme and server config
└── Yengwe SHP/             # Shapefile bundle (required)
    ├── *.shp
    ├── *.shx
    ├── *.dbf
    └── *.prj
```

> **Note:** The `Yengwe SHP/` directory must contain a valid shapefile set. The application will attempt to load all `.shp` files found in that directory on startup.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Local Installation

```bash
# 1. Clone the repository
git clone https://github.com/JamieWamz/survey.git
cd survey

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

### Default Login Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Surveyor | `surveyor` | `survey123` |
| Viewer | `viewer` | `view123` |

> **Security:** Change all default passwords before any production or public deployment.

---

## Deploying to Streamlit Cloud

1. Push the repository to GitHub (ensure `Yengwe SHP/` shapefiles are committed or accessible)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in
3. Click **New app** → select this repo → set main file to `app.py`
4. Click **Deploy**

Streamlit Cloud will automatically install dependencies from `requirements.txt`.

---

## User Roles

| Role | Permissions |
|---|---|
| **Admin** | Full access: view map, dashboard, search, export, and user management |
| **Surveyor** | Map, dashboard, search, and export |
| **Viewer** | Map and dashboard only |

---

## Export Formats

| Format | Use Case |
|---|---|
| **KML** | Google Earth, GIS desktop tools |
| **KMZ** | Compressed KML; suitable for sharing |
| **GeoJSON** | Web GIS, QGIS, Leaflet/Mapbox |
| **CSV** | Spreadsheets, tabular reporting |

---

## Coordinate Reference Systems

| Purpose | CRS |
|---|---|
| Map display | WGS84 — EPSG:4326 |
| Area calculation | UTM Zone 35S — EPSG:32735 |

The application automatically reprojects input shapefiles to WGS84 if they use a different CRS.

---

## License

This project is developed for cadastral survey purposes in Yengwe Ward, Copperbelt Province, Zambia.  
© 2025 JamieWamz. All rights reserved.