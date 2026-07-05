import streamlit as st
import plotly.express as px


def render(db, parcels):
    st.title('Dashboard')

    if parcels is None or parcels.empty:
        st.warning('No parcel data loaded yet.')
        return

    total_parcels = len(parcels)
    total_area = parcels['area_hectares'].sum()
    unique_lots = parcels['LOT_NAME'].nunique() if 'LOT_NAME' in parcels.columns else 0
    avg_area = parcels['area_hectares'].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Total parcels', total_parcels)
    col2.metric('Total area (ha)', f'{total_area:,.2f}')
    col3.metric('Unique LOTs', unique_lots)
    col4.metric('Average parcel (ha)', f'{avg_area:,.2f}')

    st.markdown('### Area distribution')
    fig = px.histogram(parcels, x='area_hectares', nbins=20, title='Parcel area distribution')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('### Parcels by LOT')
    if 'LOT_NAME' in parcels.columns:
        lot_counts = parcels['LOT_NAME'].value_counts().reset_index()
        lot_counts.columns = ['LOT_NAME', 'count']
        fig = px.bar(lot_counts.head(15), x='LOT_NAME', y='count', title='Top LOTs by parcel count')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('LOT_NAME attribute is not present in parcel data.')

    st.markdown('### Land use and status')
    cols = st.columns(2)
    with cols[0]:
        if 'land_use' in parcels.columns:
            fig = px.pie(parcels, names='land_use', title='Land use distribution')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('Land use data unavailable.')
    with cols[1]:
        if 'status' in parcels.columns:
            fig = px.pie(parcels, names='status', title='Status distribution')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('Status data unavailable.')

    st.markdown('### Parcel preview')
    preview = parcels.drop(columns=['geometry']) if 'geometry' in parcels.columns else parcels
    st.dataframe(preview.head(20))
