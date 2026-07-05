import os
import importlib.util
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from database.db_manager import DatabaseManager
from utils.shapefile_loader import load_shapefiles

BASE_DIR = Path(__file__).parent

load_dotenv(BASE_DIR / '.env')

@st.cache_resource
def get_db():
    db_url = os.getenv('DATABASE_URL', '')
    db_path = BASE_DIR / 'yengwe.db'
    if not db_url:
        db_url = f'sqlite:///{db_path}'
    db = DatabaseManager(db_url=db_url, base_dir=BASE_DIR)
    db.initialize()
    return db

@st.cache_data(ttl=3600)
def load_parcels(shp_dir: Path):
    return load_shapefiles(shp_dir)


def load_page_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    st.set_page_config(page_title='Yengwe Cadastre', layout='wide')

    db = get_db()

    if 'user' not in st.session_state:
        st.session_state.user = None

    if 'search_results' not in st.session_state:
        st.session_state.search_results = None

    with st.sidebar:
        st.title('Yengwe Cadastre')

        if st.session_state.user:
            st.markdown(f'**Logged in:** {st.session_state.user["username"]}')
            st.markdown(f'**Role:** {st.session_state.user["role"]}')
            if st.button('Logout'):
                st.session_state.user = None
                st.session_state.search_results = None
                if hasattr(st, 'rerun'):
                    st.rerun()
                else:
                    st.experimental_rerun()
        else:
            st.subheader('Login')
            username = st.text_input('Username')
            password = st.text_input('Password', type='password')
            if st.button('Login'):
                user = db.authenticate_user(username.strip(), password)
                if user:
                    st.session_state.user = user
                    st.success('Logged in successfully')
                    if hasattr(st, 'rerun'):
                        st.rerun()
                    else:
                        st.experimental_rerun()
                else:
                    st.error('Invalid username or password')

        st.markdown('---')
        pages = []
        pages_dir = BASE_DIR / 'pages'
        for page_file in sorted(pages_dir.glob('*.py')):
            if page_file.name != '__init__.py':
                pages.append(page_file)
        page_names = []
        for page in pages:
            display_name = page.stem.replace('01_', '').replace('02_', '').replace('03_', '').replace('04_', '').replace('_', ' ')
            page_names.append(display_name)
        choice = st.selectbox('Select page', ['Home'] + page_names)

    parcels_gdf = None
    shp_dir = BASE_DIR / 'Yengwe SHP'
    if shp_dir.exists():
        with st.spinner('Loading shapefiles...'):
            parcels_gdf = load_parcels(shp_dir)
            if db.count_parcels() == 0 and parcels_gdf is not None:
                db.seed_parcels(parcels_gdf)

    if choice == 'Home':
        st.title('Yengwe Cadastre')
        st.markdown('Welcome to the Yengwe Cadastre application. Use the sidebar to navigate between Dashboard, Map Viewer, Search, and Export pages.')
        st.write('This app loads shapefiles automatically and supports SQLite deployment as well as PostgreSQL/PostGIS development.')
    else:
        page_path = BASE_DIR / 'pages' / f'{pages[page_names.index(choice)].name}'
        module = load_page_module(page_path)
        if hasattr(module, 'render'):
            module.render(db=db, parcels=parcels_gdf)
        else:
            st.error('Selected page does not implement a render(db, parcels) function.')


if __name__ == '__main__':
    main()
