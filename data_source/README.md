# Local data workspace (not included in GitHub)

All raw and generated data stay under `data_source/`. The Python source, documentation, tests, and published `site/index.html` remain in the repository root.

| Directory | Contents |
|---|---|
| `raw/` | Four source CSVs, retaining exact filenames |
| `intermediate/` | Stage 01/02 lookups and enriched ticket CSVs |
| `processed/03_quality_results/` | Cleaned parking data and QA audits |
| `processed/05_collision_results/` | Collision geocodes and QA audits |
| `output/04_map_results/` | Generated dashboard HTML, QA JSON, local street map |

Required raw filenames:
- `parking-tickets-2020-2025.csv`
- `public-streets.csv`
- `block-numbers.csv`
- `Lower Mainland_Full Data_data.csv`

Do not commit large datasets to GitHub. To reuse previous results, copy (do not move) the CSVs from the old project's `03_quality_results` and `05_collision_results` into the corresponding `data_source/processed/` directories.

The prebuilt dashboard is in `site/index.html` and needs no CSVs to open. A new generator run writes under `data_source/output/04_map_results/`, not directly into `site/`.
