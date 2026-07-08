# Running the Yengwe Ward Cadastre System on Windows (with VS Code)

This guide explains how to set up and run the **Yengwe Ward Cadastre System** (`app.py`, a Streamlit application) on **Windows 10/11** using **Visual Studio Code**, including all required dependencies.

---

## 1. What this app is

A single-file [Streamlit](https://streamlit.io) web app for cadastral parcel management. It loads shapefiles from the `Yengwe SHP/` folder, displays them on an interactive map, and supports search, dashboards, and KML/KMZ/GeoJSON/CSV export.

Key dependencies:

| Type | Packages |
|---|---|
| App / UI | `streamlit`, `folium`, `streamlit-folium`, `streamlit-option-menu`, `plotly` |
| Geospatial (native libs) | `geopandas`, `pyogrio`, `pyproj`, `shapely` |
| Data / export | `pandas`, `numpy`, `simplekml` |

> **Windows gotcha:** The geospatial packages (`geopandas`, `pyogrio`, `pyproj`, `shapely`) depend on native C libraries (GDAL, GEOS, PROJ). On Windows these are easiest to install through **conda/conda-forge** (Option A below). A pure `pip` install (Option B) also works on 64-bit Windows thanks to modern wheels, but is less foolproof.

---

## 2. Prerequisites

- **Windows 10 or 11**, 64-bit
- **Visual Studio Code** — https://code.visualstudio.com
- **Python extension for VS Code** (by Microsoft) — install from the Extensions view (`Ctrl+Shift+X`)
- **Git for Windows** — https://git-scm.com/download/win
- **(Option A only)** **Miniconda** (or Anaconda) — https://docs.conda.io/en/latest/miniconda.html

> The repo's `runtime.txt` pins `python-3.12` (used only by Streamlit Cloud). Locally, **Python 3.10–3.12** works.

---

## 3. Step 1 — Install the tooling

1. Install **VS Code**, **Git for Windows**, and (if using Option A) **Miniconda**.
   - During Miniconda install, choose **"Add Miniconda3 to my PATH"** (or just use the *Anaconda Prompt* / *Miniconda Prompt* it adds to the Start menu).
2. In VS Code, open the Extensions panel (`Ctrl+Shift+X`) and install **Python** (Microsoft).

---

## 4. Step 2 — Get the code

Open **Git Bash** (or the VS Code terminal) and clone the repo:

```bash
git clone https://github.com/JamieWamz/survey.git
cd survey
```

> If you already have the files, just open the project folder in VS Code instead.

---

## 5. Step 3 — Create a Python environment

### Option A — Recommended: Miniconda (most reliable for geospatial libs)

Open the **Miniconda Prompt** (or any terminal) and run:

```bash
# Create an environment with Python 3.12
conda create -n yengwe python=3.12 -y

# Activate it
conda activate yengwe

# Install the native geospatial stack from conda-forge
conda install -c conda-forge geopandas pyogrio pyproj shapely -y

# Install the remaining pure-Python dependencies with pip
pip install -r requirements.txt
```

### Option B — Alternative: built-in `venv` + `pip`

From the project folder in a normal terminal (PowerShell or Command Prompt):

```bash
# Create a virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate

# Install everything from requirements
pip install -r requirements.txt
```

> If Option B fails with GDAL/GEOS/PROJ import errors, switch to **Option A**.

---

## 6. Step 4 — Open the project in VS Code

1. Open VS Code and choose **File → Open Folder…**, then select the `survey` project folder.
2. Open the integrated terminal in VS Code: **Terminal → New Terminal** (`Ctrl+Shift+` ` `).
3. Make sure the correct environment is selected:
   - Press `Ctrl+Shift+P` → **Python: Select Interpreter**.
   - Choose the interpreter from your environment:
     - Option A: the `yengwe` conda environment.
     - Option B: `.\venv\Scripts\python.exe` (it should already be active if the terminal shows `(venv)`).
4. In the VS Code terminal, confirm the environment is active (you should see `(yengwe)` or `(venv)` at the prompt).

---

## 7. Step 5 — Run the application

From the VS Code terminal (with the environment activated):

```bash
streamlit run app.py
```

Streamlit will print a local URL. Open it in your browser:

```
http://localhost:8501
```

> The app reads all `.shp` files under `Yengwe SHP/` on startup, so keep that folder next to `app.py`.

---

## 8. Default login credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Surveyor | `surveyor` | `survey123` |
| Viewer | `viewer` | `view123` |

> **Security:** Change these default passwords before any public/production use.

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `ImportError` / `DLL load failed` for `geopandas`, `pyproj`, `pyogrio`, or `shapely` | The native GDAL/GEOS/PROJ libraries are missing. Use **Option A (conda-forge)**. |
| `ModuleNotFoundError: No module named 'streamlit'` | Your environment isn't activated, or dependencies weren't installed. Re-run `pip install -r requirements.txt` inside the activated env. |
| `Shapefile directory not found` / no parcels on the map | Ensure the `Yengwe SHP/` folder (with its `.shp`/`.shx`/`.dbf`/`.prj` files) is present next to `app.py`. |
| `conda` not recognized | Miniconda wasn't added to PATH; use the **Miniconda Prompt** from the Start menu instead. |
| Long path / filename errors | Windows has a 260-char path limit. Keep the project in a short path like `C:\dev\survey`. Enable long paths if needed (Group Policy → *Enable Win32 long paths*). |
| Port 8501 already in use | Run `streamlit run app.py --server.port 8502` and open the printed URL. |
| `venv\Scripts\activate` permission error in PowerShell | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry. |

### WSL note (optional)
You can also run this under **WSL2** (Ubuntu) following the Linux steps in `README.md`. VS Code's **Remote - WSL** extension lets you open the folder in WSL and use the same `streamlit run app.py` workflow.

---

## 10. Notes

- `runtime.txt` (`python-3.12`) is only used by **Streamlit Cloud** deployment and is ignored locally.
- `webServerApiSettings.json` is unrelated to running the app locally.
- The SQLite database (`yengwe.db`) is created automatically on first run and is git-ignored.
- The `Yengwe SHP/` directory contains spaces in its name — this is fine on Windows, but keep the folder structure intact.