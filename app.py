import os
from pathlib import Path

import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import pandas as pd
from branca.element import Template, MacroElement

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Survey Maps",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CUSTOM CSS – Modern, clean, professional
# ============================================================
st.markdown(
    """
    <style>
    /* Global */
    .main {
        background-color: #f5f7fb;
        padding: 0 1rem;
    }
    /* Header */
    .header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .header h1 {
        color: white;
        font-weight: 600;
        font-size: 2.2rem;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .header p {
        color: rgba(255,255,255,0.85);
        margin: 0;
        font-size: 1rem;
    }
    /* Sidebar */
    .css-1d391kg, .css-1lcbmhc {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
        padding: 1.5rem 1rem;
        border-radius: 0 12px 12px 0;
        box-shadow: 2px 0 10px rgba(0,0,0,0.05);
    }
    .sidebar-content {
        padding: 0.5rem 0;
    }
    .sidebar-title {
        font-weight: 600;
        color: #1e3c72;
        font-size: 1.1rem;
        border-bottom: 2px solid #2a5298;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    /* Cards */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #e9ecef;
        transition: box-shadow 0.2s;
    }
    .card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    /* Map container */
    .map-container {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e9ecef;
        background: white;
    }
    /* Buttons */
    .stButton button {
        background: #2a5298;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        transition: background 0.2s;
    }
    .stButton button:hover {
        background: #1e3c72;
        color: white;
    }
    /* Info boxes */
    .stAlert {
        border-radius: 8px;
    }
    /* Success message */
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: #155724;
        margin: 1rem 0;
    }
    /* Footer */
    .footer {
        text-align: center;
        color: #6c757d;
        font-size: 0.85rem;
        padding: 1.5rem 0 0.5rem;
        border-top: 1px solid #e9ecef;
        margin-top: 2rem;
    }
    /* Progress bar */
    .stProgress > div > div {
        background-color: #2a5298;
    }
    /* Tabs (if any) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1rem;
        background: #f1f3f5;
        transition: background 0.2s;
    }
    .stTabs [aria-selected="true"] {
        background: #2a5298;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CONSTANTS
# ============================================================
ZAMBIA_CENTER = (-13.1338, 27.8493)
DEFAULT_ZOOM = 6
DEFAULT_SHAPEFILE_PATH = os.getenv("SHAPEFILE_PATH", "/home/jamie/msd/Yengwe SHP")
SHAPEFILE_PATH = Path(DEFAULT_SHAPEFILE_PATH)

CADASTRE_VIEWS = [
    "General Location Map",
    "Active Exploration Licences",
    "Restricted Environmental Areas",
    "Combined Survey View",
]

EXPLORATION_LICENCES = [
    {
        "name": "EL-2024-0117 (Kitwe Block)",
        "bounds": [[-12.95, 28.10], [-12.75, 28.30]],
        "holder": "Mock Mining Co. Ltd",
    },
    {
        "name": "EL-2024-0142 (Chingola Block)",
        "bounds": [[-12.65, 27.75], [-12.45, 27.95]],
        "holder": "Copperbelt Exploration Ltd",
    },
    {
        "name": "EL-2023-0288 (Mufulira Block)",
        "bounds": [[-12.62, 28.18], [-12.45, 28.36]],
        "holder": "Northern Minerals Plc",
    },
]

RESTRICTED_AREAS = [
    {
        "name": "Kafue National Park Buffer Zone",
        "bounds": [[-16.50, 25.20], [-15.00, 26.40]],
        "category": "Protected Wildlife Area",
    },
    {
        "name": "Lower Zambezi Catchment Reserve",
        "bounds": [[-15.90, 28.90], [-15.60, 29.40]],
        "category": "Watershed Protection Zone",
    },
]

REFERENCE_CITIES = [
    {"name": "Lusaka (Capital)", "lat": -15.3875, "lon": 28.3228},
    {"name": "Kitwe", "lat": -12.8024, "lon": 28.2132},
    {"name": "Ndola", "lat": -12.9587, "lon": 28.6366},
    {"name": "Livingstone", "lat": -17.8419, "lon": 25.8543},
    {"name": "Chingola", "lat": -12.5289, "lon": 27.8839},
]

LAYER_COLORS = {
    "licence": "#f5a623",
    "restricted": "#d0021b",
    "overlay": "#2f6fed",
    "general": "#7f8c8d",
    "yengwe": "#1f77b4",
    "lot_colors": [
        "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
        "#a65628", "#f781bf", "#999999", "#66c2a5", "#fc8d62",
        "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494",
        "#b3b3b3", "#1b9e77", "#d95f02", "#7570b3", "#e7298a",
    ]
}

# ============================================================
# SESSION STATE
# ============================================================
def initialize_session_state():
    if "gdf" not in st.session_state:
        st.session_state.gdf = None
    if "shapefile_loaded" not in st.session_state:
        st.session_state.shapefile_loaded = False
    if "filtered_gdf" not in st.session_state:
        st.session_state.filtered_gdf = None
    if "view" not in st.session_state:
        st.session_state.view = CADASTRE_VIEWS[0]
    if "error_msg" not in st.session_state:
        st.session_state.error_msg = None
    if "lot_names" not in st.session_state:
        st.session_state.lot_names = []
    if "load_all" not in st.session_state:
        st.session_state.load_all = True

# ============================================================
# SHAPEFILE LOADING – includes LOT and L0T, no low_memory
# ============================================================
def load_all_shapefiles(base_path: Path, progress_placeholder=None) -> tuple[gpd.GeoDataFrame | None, list, str | None]:
    try:
        if progress_placeholder:
            progress_placeholder.text("Scanning for shapefiles...")
            progress_bar = progress_placeholder.progress(0)

        if not base_path.exists():
            return None, [], f"Path not found: {base_path}"

        # Include folders containing "LOT" or "L0T" (case-insensitive)
        lot_folders = []
        for d in base_path.iterdir():
            if d.is_dir():
                name_upper = d.name.upper()
                if "LOT" in name_upper or "L0T" in name_upper:
                    lot_folders.append(d)

        if not lot_folders:
            return None, [], f"No LOT/L0T folders found in {base_path}"

        st.sidebar.info(f"Found {len(lot_folders)} LOT/L0T folders")

        combined_gdf = None
        lot_names = []

        for i, folder in enumerate(lot_folders):
            if progress_bar:
                progress_bar.progress((i + 1) / len(lot_folders))
                progress_placeholder.text(f"Loading {folder.name}...")

            shp_files = list(folder.glob("*.shp"))
            if not shp_files:
                continue

            shp_file = shp_files[0]
            lot_name = folder.name

            try:
                # No low_memory parameter to avoid warnings
                gdf = gpd.read_file(shp_file)
                if gdf.empty:
                    continue

                if gdf.crs is None:
                    gdf = gdf.set_crs("EPSG:4326")
                elif gdf.crs.to_epsg() != 4326:
                    gdf = gdf.to_crs("EPSG:4326")

                gdf["LOT_NAME"] = lot_name
                gdf["SOURCE_FILE"] = shp_file.name

                lot_names.append(lot_name)

                if combined_gdf is None:
                    combined_gdf = gdf
                else:
                    combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)

            except Exception as e:
                st.warning(f"Failed to load {folder.name}: {str(e)}")

        if combined_gdf is None or combined_gdf.empty:
            return None, [], "No valid shapefiles could be loaded"

        if progress_bar:
            progress_bar.progress(1.0)
            progress_placeholder.text(f"Loaded {len(lot_names)} shapefiles!")

        return combined_gdf, lot_names, None

    except Exception as e:
        return None, [], f"Error loading shapefiles: {str(e)}"

# ============================================================
# MAP HELPERS
# ============================================================
def get_shapefile_bounds(gdf):
    if gdf is None or gdf.empty:
        return None
    return gdf.total_bounds

def get_shapefile_center(gdf):
    minx, miny, maxx, maxy = get_shapefile_bounds(gdf)
    return (miny + maxy) / 2, (minx + maxx) / 2

def get_optimal_zoom(gdf):
    minx, miny, maxx, maxy = get_shapefile_bounds(gdf)
    max_extent = max(maxx - minx, maxy - miny)
    if max_extent > 10: return 6
    elif max_extent > 5: return 7
    elif max_extent > 2: return 8
    elif max_extent > 1: return 9
    elif max_extent > 0.5: return 10
    elif max_extent > 0.2: return 11
    elif max_extent > 0.1: return 12
    else: return 13

def create_base_map(center, zoom):
    return folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True,
    )

# ============================================================
# LAYER FUNCTIONS
# ============================================================
def add_general_location_layer(m):
    for city in REFERENCE_CITIES:
        folium.CircleMarker(
            location=[city["lat"], city["lon"]],
            radius=6,
            color=LAYER_COLORS["general"],
            fill=True,
            fill_color=LAYER_COLORS["general"],
            fill_opacity=0.85,
            weight=1.5,
            tooltip=folium.Tooltip(f"<b>{city['name']}</b>", sticky=True),
        ).add_to(m)

def add_licence_layer(m):
    for blk in EXPLORATION_LICENCES:
        html = f"<b>{blk['name']}</b><br>Status: Active<br>Holder: {blk['holder']}"
        folium.Rectangle(
            bounds=blk["bounds"],
            color=LAYER_COLORS["licence"],
            weight=2,
            fill=True,
            fill_color=LAYER_COLORS["licence"],
            fill_opacity=0.30,
            tooltip=folium.Tooltip(html, sticky=True),
        ).add_to(m)

def add_restricted_layer(m):
    for area in RESTRICTED_AREAS:
        html = f"<b>{area['name']}</b><br>Classification: {area['category']}<br>Mining Restricted"
        folium.Rectangle(
            bounds=area["bounds"],
            color=LAYER_COLORS["restricted"],
            weight=2,
            fill=True,
            fill_color=LAYER_COLORS["restricted"],
            fill_opacity=0.30,
            dash_array="6,4",
            tooltip=folium.Tooltip(html, sticky=True),
        ).add_to(m)

def add_cadastre_layers(m, view):
    if view == "General Location Map":
        add_general_location_layer(m)
    elif view == "Active Exploration Licences":
        add_licence_layer(m)
    elif view == "Restricted Environmental Areas":
        add_restricted_layer(m)
    elif view == "Combined Survey View":
        add_general_location_layer(m)
        add_licence_layer(m)
        add_restricted_layer(m)

def add_shapefile_layer(m, gdf, lot_names):
    if gdf is None or gdf.empty:
        return
    gdf_copy = gdf.copy()
    color_map = {lot: LAYER_COLORS["lot_colors"][i % len(LAYER_COLORS["lot_colors"])] for i, lot in enumerate(lot_names)}

    def style_function(feature):
        lot_name = feature['properties'].get('LOT_NAME', 'Unknown')
        color = color_map.get(lot_name, LAYER_COLORS["yengwe"])
        return {"fillColor": color, "color": color, "weight": 2, "fillOpacity": 0.5, "opacity": 0.9}

    columns = [col for col in gdf_copy.columns if col != 'geometry']
    tooltip = folium.GeoJsonTooltip(
        fields=columns,
        aliases=columns,
        sticky=True,
        localize=True,
        style="background-color:white; padding:8px 12px; border-radius:6px; border:1px solid #ccc; font-family:Arial; font-size:12px; max-width:300px;",
    )

    folium.GeoJson(
        gdf_copy.to_json(),
        name="All LOTs",
        style_function=style_function,
        highlight_function=lambda x: {"weight": 3, "fillOpacity": 0.8},
        tooltip=tooltip,
    ).add_to(m)

# ============================================================
# LEGEND – highly transparent with blur effect
# ============================================================
def legend_swatch(color, shape="square"):
    if shape == "circle":
        return f"<span style='display:inline-block;width:12px;height:12px;border-radius:50%;background:{color};margin-right:8px;vertical-align:middle;border:1px solid rgba(0,0,0,.2);'></span>"
    return f"<span style='display:inline-block;width:14px;height:14px;background:{color};opacity:.75;margin-right:8px;vertical-align:middle;border:1px solid rgba(0,0,0,.2);'></span>"

def add_floating_legend(m, view, has_shapefile, lot_names):
    rows = []
    if has_shapefile and lot_names:
        rows.append("<div style='margin-bottom:8px;font-weight:bold;'>LOT Parcels</div>")
        for i, lot in enumerate(lot_names[:15]):
            color = LAYER_COLORS["lot_colors"][i % len(LAYER_COLORS["lot_colors"])]
            rows.append(f"<div style='margin-bottom:3px;display:flex;align-items:center;'>{legend_swatch(color)}<span style='font-size:12px;'>{lot}</span></div>")
        if len(lot_names) > 15:
            rows.append(f"<div style='font-size:11px;color:#999;'>+ {len(lot_names)-15} more</div>")
        rows.append("<div style='border-top:1px solid #ddd;margin:6px 0;'></div>")

    if view in ("General Location Map", "Combined Survey View"):
        rows.append(f"<div style='margin-bottom:3px;display:flex;align-items:center;'>{legend_swatch(LAYER_COLORS['general'], 'circle')}<span>Reference Cities</span></div>")
    if view in ("Active Exploration Licences", "Combined Survey View"):
        rows.append(f"<div style='margin-bottom:3px;display:flex;align-items:center;'>{legend_swatch(LAYER_COLORS['licence'])}<span>Exploration Licences</span></div>")
    if view in ("Restricted Environmental Areas", "Combined Survey View"):
        rows.append(f"<div style='margin-bottom:3px;display:flex;align-items:center;'>{legend_swatch(LAYER_COLORS['restricted'])}<span>Restricted Areas</span></div>")

    rows_html = "".join(rows) or "<div style='font-size:12px;color:#777;'>No active layers</div>"

    macro_template = f"""
    {{% macro html(this, kwargs) %}}
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:rgba(255,255,255,0.4);padding:12px 16px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.25);font-family:Arial,sans-serif;font-size:13px;color:#222;max-width:300px;max-height:400px;overflow-y:auto;border:1px solid rgba(255,255,255,0.3);backdrop-filter:blur(6px);">
        <div style="font-weight:700;margin-bottom:8px;font-size:14px;">Cadastre Legend</div>
        {rows_html}
        <div style="margin-top:8px;font-size:10px;color:#999;border-top:1px solid rgba(0,0,0,0.1);padding-top:6px;">View: {view}</div>
    </div>
    {{% endmacro %}}
    """
    macro = MacroElement()
    macro._template = Template(macro_template)
    m.get_root().add_child(macro)

# ============================================================
# SIDEBAR
# ============================================================
def render_sidebar():
    st.sidebar.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-title">Controls</div>', unsafe_allow_html=True)

    view_choice = st.sidebar.selectbox(
        "Cadastre View",
        options=CADASTRE_VIEWS,
        index=0,
        help="Choose the map overlay layers.",
    )
    st.session_state.view = view_choice

    st.sidebar.markdown("---")
    st.sidebar.markdown('<div class="sidebar-title">Shapefiles</div>', unsafe_allow_html=True)

    if not st.session_state.shapefile_loaded:
        progress_placeholder = st.sidebar.empty()
        with st.spinner("Loading LOT shapefiles..."):
            gdf, lot_names, error_msg = load_all_shapefiles(SHAPEFILE_PATH, progress_placeholder)
            progress_placeholder.empty()

        if gdf is not None:
            st.session_state.gdf = gdf
            st.session_state.lot_names = lot_names
            st.session_state.shapefile_loaded = True
            st.session_state.error_msg = None
            st.sidebar.success(f"Loaded {len(gdf)} features from {len(lot_names)} LOTs")
        else:
            st.session_state.error_msg = error_msg
            st.sidebar.error(f"Error: {error_msg}")

    gdf = st.session_state.gdf
    lot_names = st.session_state.lot_names
    has_shapefile = st.session_state.shapefile_loaded

    if has_shapefile and gdf is not None:
        with st.sidebar.expander("Loaded LOTs"):
            st.write(f"**Total:** {len(lot_names)} LOTs")
            for lot in lot_names[:20]:
                st.caption(f"• {lot}")
            if len(lot_names) > 20:
                st.caption(f"... and {len(lot_names)-20} more")

    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    return view_choice, gdf, has_shapefile, lot_names, st.session_state.error_msg

# ============================================================
# MAIN
# ============================================================
def main():
    initialize_session_state()

    # ---- HEADER ----
    st.markdown(
        """
        <div class="header">
            <div style="flex:1;">
                <h1>Survey Maps</h1>
                <p>Interactive Cadastre Viewer for Zambia – Multiple LOT Parcels</p>
            </div>
            <div style="font-size:0.9rem; color:rgba(255,255,255,0.7);">
                <span>Hover for details</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- SIDEBAR ----
    view_choice, gdf, has_shapefile, lot_names, error_msg = render_sidebar()

    # ---- MAP ----
    if has_shapefile and gdf is not None and not gdf.empty:
        center_lat, center_lon = get_shapefile_center(gdf)
        zoom = get_optimal_zoom(gdf)
        minx, miny, maxx, maxy = get_shapefile_bounds(gdf)
        st.sidebar.info(
            f"Auto-focused on {len(lot_names)} LOTs\n"
            f"Bounds: {minx:.4f}E – {maxx:.4f}E\n"
            f"         {miny:.4f}S – {maxy:.4f}S"
        )
    else:
        center_lat, center_lon = ZAMBIA_CENTER
        zoom = DEFAULT_ZOOM

    fmap = create_base_map((center_lat, center_lon), zoom)
    add_cadastre_layers(fmap, view_choice)

    if has_shapefile and gdf is not None and not gdf.empty:
        add_shapefile_layer(fmap, gdf, lot_names)
        st.sidebar.info("Hover over any parcel to see its attributes")

    add_floating_legend(fmap, view_choice, has_shapefile, lot_names)

    # ---- MAP CONTAINER ----
    with st.container():
        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        st_folium(
            fmap,
            height=650,
            use_container_width=True,
            returned_objects=[],
            key="cadastre_map",
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # ---- EXPORT ----
    with st.sidebar.expander("Export Map"):
        if st.button("Download HTML"):
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                fmap.save(tmp.name)
                with open(tmp.name, "r") as f:
                    html_data = f.read()
                st.download_button(
                    label="Download",
                    data=html_data,
                    file_name="survey_maps.html",
                    mime="text/html"
                )
                os.unlink(tmp.name)

    # ---- STATUS MESSAGES ----
    if not has_shapefile:
        st.warning(
            f"No shapefiles found at `{SHAPEFILE_PATH}`.\n\n"
            "Please ensure the Yengwe SHP folder contains LOT/L0T subfolders with .shp files."
        )
    else:
        st.markdown(
            f"""
            <div class="success-box">
                Loaded <strong>{len(lot_names)}</strong> LOT shapefiles successfully.
                Each LOT is displayed in a different color. Hover to inspect attributes.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- FOOTER ----
    st.markdown(
        """
        <div class="footer">
            Survey Maps v2.1 &bull; Powered by Streamlit &amp; Folium
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
if __name__ == "__main__":
    main()