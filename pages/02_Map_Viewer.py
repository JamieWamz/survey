import streamlit as st
from streamlit_folium import st_folium
from utils.map_utils import add_floating_legend, add_parcel_layer, create_base_map, get_center, get_optimal_zoom


def render(db, parcels):
    st.title('Map Viewer')

    if parcels is None or parcels.empty:
        st.warning('No parcel data available for map display.')
        return

    view = st.selectbox('View mode', ['Parcel View', 'LOT View', 'Land Use View', 'Ownership View'])
    if view == 'LOT View':
        color_field = 'LOT_NAME'
    elif view == 'Land Use View':
        color_field = 'land_use'
    elif view == 'Ownership View':
        color_field = 'owner'
    else:
        color_field = None

    center = get_center(parcels)
    zoom = get_optimal_zoom(parcels)
    m = create_base_map(center=center, zoom_start=zoom)
    add_parcel_layer(m, parcels, name='Parcels', color_field=color_field)
    add_floating_legend(m, 'Legend', {'Parcels': '#3388ff'})

    st.markdown('### Interactive map')
    st_folium(m, width=900, height=600)
    st.markdown('### Summary')
    st.write(f'Parcels loaded: {len(parcels)}')
