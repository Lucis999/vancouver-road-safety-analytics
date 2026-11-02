# Operations runbook (Windows / PowerShell)

## A. View prebuilt dashboard (no Python or raw CSV needed)

Open `site/index.html` with internet access, or run:

```powershell
python -m http.server 8000 --directory site
```

Then open `http://localhost:8000`. Leaflet and supporting CSS/JS use CDNs.

## B. Regenerate dashboard from processed data

Place these files under `data_source/` in the required subdirectories:

```text
data_source/raw/public-streets.csv
data_source/processed/03_quality_results/parking_tickets_clean_geocoded.csv
data_source/processed/05_collision_results/collision_locations.csv
```

Activate the `vancouver-parking` conda environment if installed, or create a Python 3.12 environment. Install dependencies:

```powershell
python -m pip install -r requirements.txt
python 04_vancouver_road_safety_dashboard_v12_4.py
```

Or run `run_dashboard.bat`. Generated HTML: `data_source/output/04_map_results/vancouver_road_safety_dashboard_v12_4.html`.

To publish the newly generated output after testing:

```powershell
Copy-Item "data_source/output/04_map_results/vancouver_road_safety_dashboard_v12_4.html" "site/index.html" -Force
```

## C. Rebuild everything from original inputs

Place four original CSVs in `data_source/raw/` as described in `data/README.md`. Ensure ample free disk space for multi-million-row intermediates, then run:

```powershell
python 01_add_coordinates.py
python 02_add_block_info.py
python 03_audit_and_clean.py
python 05_collision_extension.py
python 06_review_collision_matches.py
python 04_vancouver_road_safety_dashboard_v12_4.py
```

Or use `rebuild_all.bat`. Stage 01 and 02 intermediate files are absent from the user's current inventory; this is expected when only final outputs have been retained, but they will be regenerated during a full rebuild.

**Caution:** Stages 01–03 and 05–06 write to their configured output paths; a rebuild can overwrite existing results. Back up `data_source/processed/03_quality_results/` and `data_source/processed/05_collision_results/` first if you need to preserve them.

## Troubleshooting

- `FileNotFoundError`: check exact filenames, directory nesting and root-relative paths.
- `ModuleNotFoundError: shapely`: reinstall updated `requirements.txt` in the active Python environment.
- Empty/incorrect map: check official road schema (`HBLOCK`, `Geom`) and cleaned ticket schema (`Block`, `Street`, `Year`, `Status`, `InfractionText`).
- Missing collision layer: check `collision_locations.csv`, years, coordinates and column names.
- Blank page or broken controls: check browser console and network access to external Leaflet CDNs.
- HTML updated locally but not online: copy generator output to `site/index.html`, commit/push, then wait for Pages deployment.

## RC2 data paths

All input and output paths are managed by `project_paths.py`. Do not put CSVs beside Python scripts. Use `data_source/raw/`, `data_source/intermediate/`, `data_source/processed/`, and `data_source/output/`. See [migration guide](MIGRATION_TO_DATA_SOURCE.md).
