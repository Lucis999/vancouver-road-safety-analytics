# Vancouver Road Safety Analytics

**Release v1.0 RC2 · Interactive dashboard v12.4 · Vancouver, BC**

An end-to-end geospatial analytics project combining **City of Vancouver parking-ticket records (2020–2025)** with **ICBC collision records (2021–2025)**. The project documents data cleaning, street-block matching, approximate collision geocoding, data-quality checks, exploratory comparisons, and an interactive Folium/Leaflet dashboard.

> **Interpretation warning:** Ticket counts and collision counts are not adjusted for parking activity, vehicle kilometres, enforcement intensity, or other exposure. They must **not** be interpreted as probabilities of receiving a ticket or having a collision. ICBC locations are approximations derived from textual road descriptions; ambiguous locations are excluded from road-level assignments.

## Open the dashboard

- **GitHub Pages:** Once Pages is enabled for this repository, open the published site URL. The `site/index.html` file is the ready-to-publish dashboard.
- **Local:** Open `site/index.html` in a browser with internet access (Leaflet CSS/JS are fetched from CDNs), or run `python -m http.server 8000 --directory site` and visit `http://localhost:8000`.
- **Docker (optional):** `docker build -t vancouver-road-safety .` then `docker run --rm -p 8080:80 vancouver-road-safety`; visit `http://localhost:8080`.

## Key features

- Parking ticket counts and coded statuses, 2020–2025
- Collision counts and categories, 2021–2025 (no ICBC 2020 data)
- Year selection and year-over-year comparisons (B − A)
- Road highlighting for highest-volume, improved, and deteriorated road labels
- Infraction-type Top 10 on hover/click, collision details within a selectable radius
- Exploratory parking/collision association, with explicit uncertainty notes
- Contextual feedback when a control is unavailable

## Repository layout

```text
.
├── README.md                     Project overview and quick start
├── 01_add_coordinates.py         Parking street-block geocoding
├── 02_add_block_info.py          Nearby block-number annotation
├── 03_audit_and_clean.py         Parking quality audit and clean export
├── 04_local_street_map.py        Optional earlier street-map prototype
├── 05_collision_extension.py     ICBC textual-location geocoding
├── 06_review_collision_matches.py Collision quality review
├── 04_vancouver_road_safety_dashboard_v12_4.py Final dashboard generator
├── run_dashboard.bat             Windows: generate/open final dashboard
├── rebuild_all.bat              Windows: rebuild full pipeline (large-data inputs required)
├── requirements.txt              Python packages
├── Dockerfile                    Optional static HTML serving only
├── site/index.html               Pre-generated interactive dashboard
├── project_paths.py             Centralized data paths
├── data_source/README.md         Local data directory layout
├── data/README.md                Legacy pointer / sample information
├── docs/                         Methods, operation, QA, architecture, deployment
└── assets/                       Screenshots and visuals (add before portfolio launch)
```

**Why scripts remain at repository root:** They use centralized paths from `project_paths.py`, with all raw and generated datasets under `data_source/`.

## Centralized local data layout (RC2)

All raw and generated datasets now live under `data_source/`, not beside the Python scripts. See [migration instructions](docs/MIGRATION_TO_DATA_SOURCE.md) and [data workspace](data_source/README.md). Source code, tests, documentation and `site/index.html` remain in the root.

## Python setup and regeneration

Requires Python 3.12 recommended. Install packages:

```powershell
python -m pip install -r requirements.txt
```

To **regenerate only the dashboard**, supply the three direct input files:

```text
data_source/raw/public-streets.csv
data_source/processed/03_quality_results/parking_tickets_clean_geocoded.csv
data_source/processed/05_collision_results/collision_locations.csv
```

Then:

```powershell
python 04_vancouver_road_safety_dashboard_v12_4.py
```

The output is `data_source/output/04_map_results/vancouver_road_safety_dashboard_v12_4.html`. The pre-generated `site/index.html` is a separate release snapshot: rerunning the generator **does not automatically update** the published file. Copy the new output into `site/index.html` after QA.

To rebuild **from original data**, see [docs/RUNBOOK.md](docs/RUNBOOK.md) and [data/README.md](data/README.md). The rebuild uses large CSVs and may take significant time and disk space.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — processing stages and dependencies
- [Methodology](docs/METHODOLOGY.md) — matching logic, metrics, interpretation
- [Data and quality](docs/DATA_QUALITY.md) — exclusions, uncertainty, QA
- [Runbook](docs/RUNBOOK.md) — commands, outputs, troubleshooting
- [Dashboard guide](docs/DASHBOARD_GUIDE.md) — control-by-control user guide
- [Deployment](docs/DEPLOYMENT.md) — GitHub Pages and Docker
- [Release checklist](docs/RELEASE_CHECKLIST.md) — verification before public launch
- [Changelog](CHANGELOG.md) — version history
- [Portfolio case study](docs/PORTFOLIO_CASE_STUDY.md) — project narrative and contributions

## Data access and provenance

Raw source files and large processed outputs are **not included** in this release package. Retrieve them from their respective official publishers and verify current terms of use before redistributing. See [data/README.md](data/README.md). Do not commit raw ICBC or parking records simply because they were downloaded for analysis.

## Project history and attribution

This repository builds on an academic Vancouver parking-violations group project, extended with ICBC collision integration and the v12 dashboard. Distinguish original group contributions from later individual extensions; see [docs/PORTFOLIO_CASE_STUDY.md](docs/PORTFOLIO_CASE_STUDY.md). Official data remain the property of their respective publishers. This project is not affiliated with or endorsed by the City of Vancouver or ICBC.

**Status:** Release candidate. Python source syntax and packaging can be checked independently, but a full clean-room data rebuild, browser cross-platform test, and data-publication licence review remain required before describing the project as fully reproducible or production validated.

## Release QA

Run `python run_tests.py` for non-destructive static checks or `python run_tests.py --full` when local processed datasets are available. See [Validation guide](docs/VALIDATION.md). Results are written to `validation_results/`. A PASS on static HTML checks does not establish browser interactivity.
