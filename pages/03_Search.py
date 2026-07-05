import streamlit as st
from streamlit_folium import st_folium
from utils.map_utils import add_parcel_layer, create_base_map, get_center, get_optimal_zoom


def render(db, parcels):
    st.title('Search')

    if parcels is None or parcels.empty:
        st.warning('No parcel data available for search.')
        return

    with st.form('search_form'):
        parcel_number = st.text_input('Parcel number')
        lot_name = st.text_input('LOT name')
        owner = st.text_input('Owner')
        land_use = st.text_input('Land use')
        status = st.text_input('Status')
        ward = st.text_input('Ward')
        district = st.text_input('District')
        area_min = st.number_input('Min area (ha)', min_value=0.0, value=0.0)
        area_max = st.number_input('Max area (ha)', min_value=0.0, value=0.0)
        st.markdown('**Spatial search**')
        col1, col2 = st.columns(2)
        with col1:
            minx = st.number_input('Min longitude', value=float(parcels.total_bounds[0]))
            miny = st.number_input('Min latitude', value=float(parcels.total_bounds[1]))
        with col2:
            maxx = st.number_input('Max longitude', value=float(parcels.total_bounds[2]))
            maxy = st.number_input('Max latitude', value=float(parcels.total_bounds[3]))
        submitted = st.form_submit_button('Search')

    if submitted:
        criteria = {
            'parcel_number': parcel_number.strip(),
            'lot_name': lot_name.strip(),
            'owner': owner.strip(),
            'land_use': land_use.strip(),
            'status': status.strip(),
            'ward': ward.strip(),
            'district': district.strip(),
            'area_min': area_min if area_min > 0 else None,
            'area_max': area_max if area_max > 0 else None,
        }
        spatial = None
        if minx < maxx and miny < maxy:
            spatial = {'bbox': [minx, miny, maxx, maxy]}

        results = db.search_parcels(criteria, spatial=spatial, user_id=st.session_state.user['id'] if st.session_state.user else None)
        st.session_state.search_results = results

    results = st.session_state.get('search_results')
    if results is None or results.empty:
        st.info('Build a search query and submit to display results.')
        return

    st.markdown(f'### Results ({len(results)} parcels)')
    m = create_base_map(center=get_center(results), zoom_start=get_optimal_zoom(results))
    add_parcel_layer(m, results, name='Search results', color_field='land_use')
    st_folium(m, width=900, height=500)

    table = results.drop(columns=['geometry']) if 'geometry' in results.columns else results
    st.dataframe(table.reset_index(drop=True))
    st.download_button('Download results CSV', table.to_csv(index=False).encode('utf-8'), 'search_results.csv', 'text/csv')
    st.download_button('Download results GeoJSON', results.to_json().encode('utf-8'), 'search_results.geojson', 'application/json')
