"""
Yengwe Ward Cadastre System
Single-file Streamlit application for Streamlit Cloud deployment.
Handles 16 shapefiles from "Yengwe SHP" folder with user authentication,
interactive mapping, search, and KML/KMZ/GeoJSON/CSV export.
"""

import hashlib
import io
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import folium
from folium.features import GeoJson
import geopandas as gpd
import pandas as pd
import plotly.express as px
import simplekml
import streamlit as st
import geopandas as gpd
gpd.options.io_engine = "pyogrio"
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu

# ---------------------------------------------------------------------------
# PAGE CONFIG - MUST BE FIRST STREAMLIT COMMAND
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Yengwe Ward Cadastre System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ZAMBIA_CENTER = (-13.133897, 27.849332)
DEFAULT_ZOOM = 12

LAYER_COLORS: Dict[str, str] = {
    "residential": "#ffeda0",
    "commercial": "#feb24c",
    "industrial": "#f03b20",
    "agriculture": "#31a354",
    "default": "#3388ff",
    "unknown": "#6c757d",
}

BASE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Database Functions (SQLite only)
# ---------------------------------------------------------------------------


def get_db_connection() -> sqlite3.Connection:
    """Return a connection to the local SQLite database."""
    db_path = BASE_DIR / "yengwe.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database() -> None:
    """Create the users table and insert default users if they don't exist."""
    conn = get_db_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

        # Default users: (username, password, role)
        default_users = [
            ("admin", "admin123", "admin"),
            ("surveyor", "survey123", "surveyor"),
            ("viewer", "view123", "viewer"),
        ]
        for username, password, role in default_users:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            if existing is None:
                pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) "
                    "VALUES (?, ?, ?)",
                    (username, pw_hash, role),
                )
        conn.commit()
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify username/password against the users table. Returns user dict or None."""
    pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT id, username, role FROM users "
            "WHERE username = ? AND password_hash = ?",
            (username, pw_hash),
        ).fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "role": row["role"]}
        return None
    finally:
        conn.close()


def update_last_login(user_id: int) -> None:
    """Update the last_login timestamp for the given user."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Shapefile Loader
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600, show_spinner="Loading shapefiles...")
def load_shapefiles(
    base_path: Path,
) -> Tuple[Optional[gpd.GeoDataFrame], List[str], Optional[str]]:
    """
    Load all shapefiles from subdirectories under base_path.

    Parameters
    ----------
    base_path : Path
        Directory containing LOT subdirectories with .shp files.

    Returns
    -------
    Tuple[Optional[gpd.GeoDataFrame], List[str], Optional[str]]
        (combined_gdf, lot_names_list, error_message).
    """
    if not base_path.exists():
        return None, [], f"Shapefile directory not found: {base_path}"

    shp_files = sorted(base_path.rglob("*.shp"))
    if not shp_files:
        return None, [], f"No .shp files found under {base_path}"

    frames: List[gpd.GeoDataFrame] = []
    lot_names: List[str] = []
    errors: List[str] = []

    for shp_path in shp_files:
        # Skip lock files
        if ".~lock." in shp_path.name:
            continue
        try:
            gdf = gpd.read_file(str(shp_path))
            if gdf.empty:
                continue

            # Ensure CRS is WGS84
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")
            elif str(gdf.crs).upper() != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")

            # Make a copy before adding columns to avoid SettingWithCopyWarning
            gdf = gdf.copy()

            # Add source metadata
            lot_name = shp_path.parent.name
            gdf["LOT_NAME"] = lot_name
            gdf["SOURCE_FILE"] = shp_path.name

            # Calculate area in hectares (reproject to UTM for accurate area)
            try:
                gdf_utm = gdf.to_crs("EPSG:32735")  # UTM zone 35S for Zambia
                gdf["area_hectares"] = gdf_utm.geometry.area / 10000.0
            except Exception:
                gdf["area_hectares"] = gdf.geometry.area / 10000.0

            # Ensure standard attribute columns exist with defaults
            if "parcel_number" not in gdf.columns:
                # Try common alternatives
                for alt in ["ParcelID", "PARCEL_NO", "parcel_no", "PARCELID"]:
                    if alt in gdf.columns:
                        gdf["parcel_number"] = gdf[alt]
                        break
                else:
                    gdf["parcel_number"] = f"PARCEL-{lot_name}-{len(frames) + 1}"

            if "owner_name" not in gdf.columns:
                for alt in ["owner", "OWNER", "OWNER_NAME"]:
                    if alt in gdf.columns:
                        gdf["owner_name"] = gdf[alt]
                        break
                else:
                    gdf["owner_name"] = "Unknown"

            if "land_use" not in gdf.columns:
                for alt in ["LAND_USE", "landuse", "LANDUSE"]:
                    if alt in gdf.columns:
                        gdf["land_use"] = gdf[alt]
                        break
                else:
                    gdf["land_use"] = "unknown"

            if "status" not in gdf.columns:
                for alt in ["STATUS", "parcel_status", "PARCEL_STATUS"]:
                    if alt in gdf.columns:
                        gdf["status"] = gdf[alt]
                        break
                else:
                    gdf["status"] = "active"

            frames.append(gdf)
            if lot_name not in lot_names:
                lot_names.append(lot_name)

        except Exception as exc:
            errors.append(f"{shp_path.name}: {exc}")
            continue

    if not frames:
        error_msg = "No valid shapefiles could be loaded."
        if errors:
            error_msg += " Errors: " + "; ".join(errors[:5])
        return None, [], error_msg

    # Combine all frames into a single GeoDataFrame
    combined = pd.concat(frames, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")

    error_msg = None
    if errors:
        error_msg = (
            f"Loaded {len(frames)} file(s) with {len(errors)} warning(s): "
            + "; ".join(errors[:3])
        )

    return combined, lot_names, error_msg


# ---------------------------------------------------------------------------
# Map Functions
# ---------------------------------------------------------------------------


def get_center(gdf: gpd.GeoDataFrame) -> Tuple[float, float]:
    """Calculate the map center from a GeoDataFrame's total bounds."""
    if gdf is None or gdf.empty:
        return ZAMBIA_CENTER
    try:
        minx, miny, maxx, maxy = gdf.total_bounds
        return ((miny + maxy) / 2.0, (minx + maxx) / 2.0)
    except (ValueError, AttributeError):
        return ZAMBIA_CENTER


def get_optimal_zoom(gdf: gpd.GeoDataFrame) -> int:
    """Calculate an appropriate zoom level based on the data extent."""
    if gdf is None or gdf.empty:
        return DEFAULT_ZOOM
    try:
        bounds = gdf.total_bounds
        width = bounds[2] - bounds[0]
        if width < 0.05:
            return 16
        if width < 0.1:
            return 14
        if width < 0.5:
            return 13
        if width < 1.0:
            return 12
        if width < 5.0:
            return 10
        return 8
    except (ValueError, AttributeError):
        return DEFAULT_ZOOM


def _choose_color(value: Optional[str]) -> str:
    """Map a land_use value to a color."""
    if not value:
        return LAYER_COLORS["unknown"]
    key = str(value).strip().lower()
    return LAYER_COLORS.get(key, LAYER_COLORS["default"])


def create_map(gdf: gpd.GeoDataFrame) -> folium.Map:
    """Create a Folium map with colored parcel polygons and hover tooltips."""
    center = get_center(gdf)
    zoom = get_optimal_zoom(gdf)

    m = folium.Map(location=list(center), zoom_start=zoom, tiles="OpenStreetMap")

    # Determine which fields are available for tooltips
    tooltip_fields = ["parcel_number", "LOT_NAME", "owner_name", "land_use", "status"]
    available_fields = [f for f in tooltip_fields if f in gdf.columns]

    def style_fn(feature):
        props = feature.get("properties", {})
        land_use_val = props.get("land_use")
        color = _choose_color(land_use_val)
        return {
            "fillColor": color,
            "color": "#333333",
            "weight": 1,
            "fillOpacity": 0.6,
        }

    # Convert to GeoJSON for Folium
    geojson_str = gdf.to_json()
    geojson_data = json.loads(geojson_str)

    geo_json = GeoJson(
        data=geojson_data,
        name="Parcels",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=available_fields,
            labels=True,
            sticky=True,
        ),
        highlight_function=lambda x: {
            "weight": 2, "color": "#2a5298", "fillOpacity": 0.8
        },
    )
    geo_json.add_to(m)

    folium.LayerControl(position="topright").add_to(m)

    # Add a floating legend
    legend_html = """
    <div style="position: fixed; bottom: 20px; left: 20px; z-index: 9999;
                background: rgba(255,255,255,0.95); padding: 10px;
                border: 1px solid #ccc; border-radius: 8px; font-size: 12px;
                max-width: 180px;">
        <strong>Land Use</strong><br>
        <span style="display:inline-block;width:12px;height:12px;background:#ffeda0;margin-right:6px;"></span>Residential<br>
        <span style="display:inline-block;width:12px;height:12px;background:#feb24c;margin-right:6px;"></span>Commercial<br>
        <span style="display:inline-block;width:12px;height:12px;background:#f03b20;margin-right:6px;"></span>Industrial<br>
        <span style="display:inline-block;width:12px;height:12px;background:#31a354;margin-right:6px;"></span>Agriculture<br>
        <span style="display:inline-block;width:12px;height:12px;background:#3388ff;margin-right:6px;"></span>Other
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


# ---------------------------------------------------------------------------
# Export Functions
# ---------------------------------------------------------------------------


def export_to_kml(gdf: gpd.GeoDataFrame, layer_name: str) -> bytes:
    """
    Export a GeoDataFrame to KML format (WGS84).

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The parcel data to export.
    layer_name : str
        Name for the KML layer.

    Returns
    -------
    bytes
        KML content as bytes.
    """
    # Ensure WGS84
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif str(gdf.crs).upper() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    kml = simplekml.Kml(name=layer_name)

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue

        # Build name and description from attributes
        name = str(row.get("parcel_number", row.get("LOT_NAME", "Parcel")))
        desc_lines = []
        for col in gdf.columns:
            if col == "geometry":
                continue
            val = row.get(col)
            if val is not None and val != "":
                desc_lines.append(f"{col}: {val}")
        description = "\n".join(desc_lines)

        geom_type = geom.geom_type
        try:
            if geom_type == "Point":
                pnt = kml.newpoint(name=name)
                pnt.coords = [(geom.x, geom.y)]
                pnt.description = description
            elif geom_type == "Polygon":
                poly = kml.newpolygon(name=name)
                poly.outerboundaryis = list(geom.exterior.coords)
                poly.description = description
            elif geom_type == "MultiPolygon":
                poly = kml.newpolygon(name=name)
                poly.outerboundaryis = list(geom.geoms[0].exterior.coords)
                poly.description = description
            else:
                pnt = kml.newpoint(name=name)
                pnt.coords = [(geom.centroid.x, geom.centroid.y)]
                pnt.description = description
        except Exception:
            continue

    # Save to a temporary file, then read back as bytes
    with tempfile.NamedTemporaryFile(suffix=".kml", delete=True) as tmp:
        kml.save(tmp.name)
        tmp.seek(0)
        return tmp.read()


def export_to_kmz(gdf: gpd.GeoDataFrame, layer_name: str) -> bytes:
    """
    Export a GeoDataFrame to KMZ (compressed KML).

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        The parcel data to export.
    layer_name : str
        Name for the KML layer.

    Returns
    -------
    bytes
        KMZ content as bytes.
    """
    kml_bytes = export_to_kml(gdf, layer_name)
    kmz_buf = io.BytesIO()
    with zipfile.ZipFile(kmz_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{layer_name}.kml", kml_bytes)
    kmz_buf.seek(0)
    return kmz_buf.getvalue()


def export_to_geojson(gdf: gpd.GeoDataFrame) -> bytes:
    """Export a GeoDataFrame to GeoJSON bytes."""
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif str(gdf.crs).upper() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    return gdf.to_json().encode("utf-8")


def export_to_csv(gdf: gpd.GeoDataFrame) -> bytes:
    """Export a GeoDataFrame to CSV bytes (excluding geometry column)."""
    df = gdf.copy()
    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])
    return df.to_csv(index=False).encode("utf-8")


# ---------------------------------------------------------------------------
# Page Functions
# ---------------------------------------------------------------------------


def dashboard_page(gdf: gpd.GeoDataFrame) -> None:
    """Render the Dashboard page with statistics and charts."""
    st.title("Dashboard")
    st.markdown("### Yengwe Ward Cadastre -- Overview")

    if gdf is None or gdf.empty:
        st.warning("No parcel data available. Please check the shapefile directory.")
        return

    # Summary statistics
    total_parcels = len(gdf)
    total_lots = gdf["LOT_NAME"].nunique() if "LOT_NAME" in gdf.columns else 0
    total_area = gdf["area_hectares"].sum() if "area_hectares" in gdf.columns else 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Parcels", f"{total_parcels:,}")
    with col2:
        st.metric("Total Lots", f"{total_lots}")
    with col3:
        st.metric("Total Area (ha)", f"{total_area:,.2f}")
    with col4:
        avg_area = total_area / total_parcels if total_parcels > 0 else 0
        st.metric("Avg Parcel Area (ha)", f"{avg_area:.2f}")

    st.markdown("---")

    # Charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Land use distribution (bar chart)
        if "land_use" in gdf.columns:
            land_use_counts = gdf["land_use"].value_counts().reset_index()
            land_use_counts.columns = ["land_use", "count"]
            fig = px.bar(
                land_use_counts,
                x="land_use",
                y="count",
                title="Parcels by Land Use",
                color="land_use",
                color_discrete_map={
                    "residential": "#ffeda0",
                    "commercial": "#feb24c",
                    "industrial": "#f03b20",
                    "agriculture": "#31a354",
                },
                text_auto=True,
            )
            fig.update_layout(xaxis_title="Land Use", yaxis_title="Number of Parcels")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Land use data not available.")

    with chart_col2:
        # Status distribution (pie chart)
        if "status" in gdf.columns:
            status_counts = gdf["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            fig = px.pie(
                status_counts,
                values="count",
                names="status",
                title="Parcels by Status",
                hole=0.4,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Status data not available.")

    # Area distribution histogram
    if "area_hectares" in gdf.columns:
        st.markdown("### Parcel Area Distribution")
        fig = px.histogram(
            gdf,
            x="area_hectares",
            nbins=30,
            title="Distribution of Parcel Areas (hectares)",
            color_discrete_sequence=["#2a5298"],
        )
        fig.update_layout(xaxis_title="Area (ha)", yaxis_title="Number of Parcels")
        st.plotly_chart(fig, use_container_width=True)

    # Top 10 lots by parcel count
    if "LOT_NAME" in gdf.columns:
        st.markdown("### Top 10 Lots by Parcel Count")
        lot_counts = gdf["LOT_NAME"].value_counts().head(10).reset_index()
        lot_counts.columns = ["LOT_NAME", "count"]
        fig = px.bar(
            lot_counts,
            x="count",
            y="LOT_NAME",
            orientation="h",
            title="Top 10 Lots by Number of Parcels",
            color="count",
            color_continuous_scale="Blues",
            text_auto=True,
        )
        fig.update_layout(yaxis_title="Lot Name", xaxis_title="Number of Parcels")
        st.plotly_chart(fig, use_container_width=True)


def map_page(gdf: gpd.GeoDataFrame) -> None:
    """Render the Map Viewer page with an interactive Folium map."""
    st.title("Map Viewer")
    st.markdown("### Interactive Parcel Map")

    if gdf is None or gdf.empty:
        st.warning("No parcel data available. Please check the shapefile directory.")
        return

    # Lot filter
    if "LOT_NAME" in gdf.columns:
        lot_names = sorted(gdf["LOT_NAME"].unique())
        selected_lots = st.multiselect(
            "Filter by Lot",
            options=lot_names,
            default=lot_names[:3] if len(lot_names) > 3 else lot_names,
        )
        if selected_lots:
            filtered_gdf = gdf[gdf["LOT_NAME"].isin(selected_lots)].copy()
        else:
            filtered_gdf = gdf.copy()
    else:
        filtered_gdf = gdf.copy()

    if filtered_gdf.empty:
        st.warning("No parcels match the selected filters.")
        return

    st.markdown(f"**Showing {len(filtered_gdf):,} parcels**")

    # Create and display the map
    m = create_map(filtered_gdf)
    st_folium(m, width=None, height=600, returned_objects=[])

    # Show data table below map
    with st.expander("View Parcel Data Table"):
        display_cols = [
            c
            for c in [
                "parcel_number",
                "LOT_NAME",
                "owner_name",
                "land_use",
                "status",
                "area_hectares",
            ]
            if c in filtered_gdf.columns
        ]
        if display_cols:
            st.dataframe(
                filtered_gdf[display_cols].head(100),
                use_container_width=True,
                hide_index=True,
            )
            if len(filtered_gdf) > 100:
                st.caption(f"Showing first 100 of {len(filtered_gdf):,} records")


def search_page(gdf: gpd.GeoDataFrame) -> None:
    """Render the Search page with multi-field search capabilities."""
    st.title("Search Parcels")
    st.markdown("### Find parcels by various criteria")

    if gdf is None or gdf.empty:
        st.warning("No parcel data available. Please check the shapefile directory.")
        return

    # Search filters
    col1, col2 = st.columns(2)
    with col1:
        search_parcel = st.text_input("Parcel Number", placeholder="e.g., PARCEL-001")
        search_owner = st.text_input("Owner Name", placeholder="e.g., John")
    with col2:
        if "LOT_NAME" in gdf.columns:
            lot_options = ["All"] + sorted(gdf["LOT_NAME"].unique().tolist())
            search_lot = st.selectbox("Lot Name", options=lot_options)
        else:
            search_lot = "All"
        if "land_use" in gdf.columns:
            lu_options = ["All"] + sorted(gdf["land_use"].unique().tolist())
            search_land_use = st.selectbox("Land Use", options=lu_options)
        else:
            search_land_use = "All"

    if "status" in gdf.columns:
        status_options = ["All"] + sorted(gdf["status"].unique().tolist())
        search_status = st.selectbox("Status", options=status_options)
    else:
        search_status = "All"

    # Area range filter
    st.markdown("### Area Range Filter (hectares)")
    area_col1, area_col2 = st.columns(2)
    with area_col1:
        min_area = st.number_input(
            "Min Area (ha)",
            min_value=0.0,
            max_value=float(gdf["area_hectares"].max()) if "area_hectares" in gdf.columns else 10000.0,
            value=0.0,
            step=0.1,
            format="%.2f",
        )
    with area_col2:
        max_area = st.number_input(
            "Max Area (ha)",
            min_value=0.0,
            max_value=float(gdf["area_hectares"].max()) if "area_hectares" in gdf.columns else 10000.0,
            value=float(gdf["area_hectares"].max()) if "area_hectares" in gdf.columns else 10000.0,
            step=0.1,
            format="%.2f",
        )

    search_clicked = st.button("Search", type="primary")

    if search_clicked:
        # Apply filters
        result = gdf.copy()

        if search_parcel:
            result = result[
                result["parcel_number"].str.contains(
                    search_parcel, case=False, na=False
                )
            ]

        if search_owner:
            if "owner_name" in result.columns:
                result = result[
                    result["owner_name"].str.contains(
                        search_owner, case=False, na=False
                    )
                ]

        if search_lot != "All" and "LOT_NAME" in result.columns:
            result = result[result["LOT_NAME"] == search_lot]

        if search_land_use != "All" and "land_use" in result.columns:
            result = result[result["land_use"] == search_land_use]

        if search_status != "All" and "status" in result.columns:
            result = result[result["status"] == search_status]

        # Apply area range filter
        if "area_hectares" in result.columns:
            result = result[
                (result["area_hectares"] >= min_area)
                & (result["area_hectares"] <= max_area)
            ]

        # Store in session state
        st.session_state.search_results = result

    # Display results
    if st.session_state.get("search_results") is not None:
        result = st.session_state.search_results
        st.markdown(f"**Found {len(result):,} matching parcel(s)**")

        if not result.empty:
            # Show map of results
            m = create_map(result)
            st_folium(m, width=None, height=400, returned_objects=[])

            # Show data table
            display_cols = [
                c
                for c in [
                    "parcel_number",
                    "LOT_NAME",
                    "owner_name",
                    "land_use",
                    "status",
                    "area_hectares",
                ]
                if c in result.columns
            ]
            if display_cols:
                st.dataframe(
                    result[display_cols],
                    use_container_width=True,
                    hide_index=True,
                )

            # Export searched results
            st.markdown("### Export Search Results")
            export_col1, export_col2, export_col3, export_col4 = st.columns(4)
            with export_col1:
                kml_bytes = export_to_kml(result, "search_results")
                st.download_button(
                    "Download KML",
                    data=kml_bytes,
                    file_name="search_results.kml",
                    mime="application/vnd.google-earth.kml+xml",
                )
            with export_col2:
                kmz_bytes = export_to_kmz(result, "search_results")
                st.download_button(
                    "Download KMZ",
                    data=kmz_bytes,
                    file_name="search_results.kmz",
                    mime="application/vnd.google-earth.kmz",
                )
            with export_col3:
                geojson_bytes = export_to_geojson(result)
                st.download_button(
                    "Download GeoJSON",
                    data=geojson_bytes,
                    file_name="search_results.geojson",
                    mime="application/geo+json",
                )
            with export_col4:
                csv_bytes = export_to_csv(result)
                st.download_button(
                    "Download CSV",
                    data=csv_bytes,
                    file_name="search_results.csv",
                    mime="text/csv",
                )
        else:
            st.info("No parcels match your search criteria.")
    else:
        st.info("Enter search criteria and click 'Search' to find parcels.")


def export_page(gdf: gpd.GeoDataFrame) -> None:
    """Render the Export page with options to download data in various formats."""
    st.title("Export Data")
    st.markdown("### Download parcel data in your preferred format")

    if gdf is None or gdf.empty:
        st.warning("No parcel data available. Please check the shapefile directory.")
        return

    # Lot selection for export
    if "LOT_NAME" in gdf.columns:
        lot_names = sorted(gdf["LOT_NAME"].unique())
        selected_lots = st.multiselect(
            "Select Lots to Export",
            options=lot_names,
            default=lot_names,
        )
        if selected_lots:
            export_gdf = gdf[gdf["LOT_NAME"].isin(selected_lots)].copy()
        else:
            export_gdf = gdf.copy()
    else:
        export_gdf = gdf.copy()

    st.markdown(f"**{len(export_gdf):,} parcels selected for export**")

    st.markdown("---")
    st.markdown("### Export Formats")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**KML**")
        st.caption("Keyhole Markup Language for Google Earth")
        if st.button("Generate KML", key="btn_kml"):
            with st.spinner("Generating KML..."):
                try:
                    kml_bytes = export_to_kml(export_gdf, "yengwe_parcels")
                    st.download_button(
                        "Download KML",
                        data=kml_bytes,
                        file_name="yengwe_parcels.kml",
                        mime="application/vnd.google-earth.kml+xml",
                        key="dl_kml",
                    )
                except Exception as e:
                    st.error(f"KML export failed: {e}")

    with col2:
        st.markdown("**KMZ**")
        st.caption("Compressed KML (smaller file)")
        if st.button("Generate KMZ", key="btn_kmz"):
            with st.spinner("Generating KMZ..."):
                try:
                    kmz_bytes = export_to_kmz(export_gdf, "yengwe_parcels")
                    st.download_button(
                        "Download KMZ",
                        data=kmz_bytes,
                        file_name="yengwe_parcels.kmz",
                        mime="application/vnd.google-earth.kmz",
                        key="dl_kmz",
                    )
                except Exception as e:
                    st.error(f"KMZ export failed: {e}")

    with col3:
        st.markdown("**GeoJSON**")
        st.caption("GeoJSON format for web mapping")
        if st.button("Generate GeoJSON", key="btn_geojson"):
            with st.spinner("Generating GeoJSON..."):
                try:
                    geojson_bytes = export_to_geojson(export_gdf)
                    st.download_button(
                        "Download GeoJSON",
                        data=geojson_bytes,
                        file_name="yengwe_parcels.geojson",
                        mime="application/geo+json",
                        key="dl_geojson",
                    )
                except Exception as e:
                    st.error(f"GeoJSON export failed: {e}")

    with col4:
        st.markdown("**CSV**")
        st.caption("Comma-separated values (tabular)")
        if st.button("Generate CSV", key="btn_csv"):
            with st.spinner("Generating CSV..."):
                try:
                    csv_bytes = export_to_csv(export_gdf)
                    st.download_button(
                        "Download CSV",
                        data=csv_bytes,
                        file_name="yengwe_parcels.csv",
                        mime="text/csv",
                        key="dl_csv",
                    )
                except Exception as e:
                    st.error(f"CSV export failed: {e}")


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for the Streamlit application."""

    # Initialize database on first run
    if "db_initialized" not in st.session_state:
        init_database()
        st.session_state.db_initialized = True

    # Initialize session state
    if "user" not in st.session_state:
        st.session_state.user = None
    if "search_results" not in st.session_state:
        st.session_state.search_results = None

    # -----------------------------------------------------------------------
    # Sidebar
    # -----------------------------------------------------------------------
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0;">
                <h2 style="color: #2a5298; margin: 0;">Yengwe</h2>
                <h3 style="color: #4a7cbd; margin: 0;">Cadastre</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Login/Logout section
        if st.session_state.user:
            user = st.session_state.user
            st.markdown(f"**Logged in:** {user['username']}")
            st.markdown(f"**Role:** `{user['role']}`")
            if st.button("Logout", use_container_width=True):
                st.session_state.user = None
                st.session_state.search_results = None
                st.rerun()
        else:
            st.markdown("### Login")
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input(
                    "Password", type="password", placeholder="Enter password"
                )
                submitted = st.form_submit_button("Login", use_container_width=True)
                if submitted:
                    if username.strip() and password:
                        user = authenticate_user(username.strip(), password)
                        if user:
                            st.session_state.user = user
                            update_last_login(user["id"])
                            st.success(f"Welcome, {user['username']}!")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
                    else:
                        st.warning("Please enter both username and password")

        st.markdown("---")

        # Navigation menu
        menu_options = ["Dashboard", "Map Viewer", "Search", "Export"]
        menu_icons = ["bar-chart-fill", "map-fill", "search", "download"]

        selected = option_menu(
            menu_title="Navigation",
            options=menu_options,
            icons=menu_icons,
            default_index=0,
        )

    # -----------------------------------------------------------------------
    # Load shapefiles
    # -----------------------------------------------------------------------
    shp_dir = BASE_DIR / "Yengwe SHP"

    parcels_gdf = None
    load_error = None

    if shp_dir.exists():
        parcels_gdf, _lot_names, load_error = load_shapefiles(shp_dir)
    else:
        load_error = f"Shapefile directory not found: {shp_dir}"

    # Show loading errors/warnings
    if load_error and parcels_gdf is None:
        st.error(load_error)
        st.stop()
    elif load_error:
        st.warning(load_error)

    # If no data loaded, show a helpful message
    if parcels_gdf is None or parcels_gdf.empty:
        st.info(
            "No parcel data loaded. Ensure the 'Yengwe SHP' folder exists with "
            "valid shapefiles (.shp) organized in subdirectories."
        )
        st.stop()

    # -----------------------------------------------------------------------
    # Page routing
    # -----------------------------------------------------------------------
    if selected == "Dashboard":
        dashboard_page(parcels_gdf)
    elif selected == "Map Viewer":
        map_page(parcels_gdf)
    elif selected == "Search":
        search_page(parcels_gdf)
    elif selected == "Export":
        export_page(parcels_gdf)


if __name__ == "__main__":
    main()