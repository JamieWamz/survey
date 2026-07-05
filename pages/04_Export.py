import streamlit as st
from pathlib import Path
from utils.export_utils import export_to_csv, export_to_geojson, export_to_kml, export_to_kmz, export_to_shapefile


def render(db, parcels):
    st.title('Export')

    if parcels is None or parcels.empty:
        st.warning('No parcel data available for export.')
        return

    source_option = st.radio('Data source', ['All Parcels', 'Search Results'])
    format_option = st.selectbox('Export format', ['GeoJSON', 'CSV', 'KML', 'KMZ', 'Shapefile'])

    if source_option == 'Search Results' and st.session_state.get('search_results') is not None:
        source = st.session_state.search_results
    else:
        source = parcels

    if source is None or source.empty:
        st.warning('No data selected for export.')
        return

    output_dir = Path('exports')
    output_dir.mkdir(exist_ok=True)

    if st.button('Export'):
        if format_option == 'GeoJSON':
            path = output_dir / 'yengwe_parcels.geojson'
            export_to_geojson(source, path)
        elif format_option == 'CSV':
            path = output_dir / 'yengwe_parcels.csv'
            export_to_csv(source, path)
        elif format_option == 'KML':
            path = output_dir / 'yengwe_parcels.kml'
            export_to_kml(source, path)
        elif format_option == 'KMZ':
            path = output_dir / 'yengwe_parcels.kmz'
            export_to_kmz(source, path)
        else:
            path = output_dir / 'yengwe_parcels.zip'
            export_to_shapefile(source, path)

        st.success(f'Export generated: {path.name}')
        with open(path, 'rb') as f:
            st.download_button('Download file', f.read(), path.name)

    st.markdown('### Export tips')
    st.write('- Use GeoJSON for GIS interoperability.')
    st.write('- Use KML/KMZ for Google Earth.')
    st.write('- Use Shapefile ZIP for desktop GIS tools.')
