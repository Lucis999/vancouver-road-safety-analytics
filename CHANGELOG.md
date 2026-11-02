## v1.0 RC2 — centralized data workspace

- Added `project_paths.py` and moved all local data inputs and generated outputs under `data_source/`.
- Updated all seven Python scripts, QA paths, Windows launchers and documentation.
- Kept published `site/index.html` unchanged pending regeneration and manual QA.
- Added migration instructions and data-directory placeholders.
- Full end-to-end rebuild and browser tests remain pending.

# Changelog

## [1.0.0] — Release candidate (2026-11-01)

- Designated **dashboard v12.4** as the public-facing interactive release.
- Added documentation for architecture, methods, QA, operations, deployment, user controls and data provenance.
- Updated `requirements.txt` to include Shapely.
- Updated Windows batch scripts to target v12.4 and complete the two data-processing branches.
- Corrected v12.4 script header command and renamed the new quality JSON output to `v12_4_geocoding_quality.json` (a naming change only).
- Bundled a pre-generated HTML snapshot at `site/index.html` and an optional Nginx Dockerfile.
- Excluded large source/derived datasets from public package pending licence review.

## Dashboard development history (summary)

- v3–v8: parking status and road-level map iterations.
- v9–v11: ICBC collision integration and grouped markers.
- v12–v12.2: unified analysis, hover/location controls and performance/association work.
- v12.3: multi-select road highlights.
- v12.4: contextual feedback for unavailable selections and invalid comparisons.

The dashboard feature version and repository release version are independent.
