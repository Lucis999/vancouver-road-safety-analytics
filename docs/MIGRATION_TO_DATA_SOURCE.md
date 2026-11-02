# Migration to centralized `data_source/` (RC2)

The project code stays in the root; **all local raw, intermediate, processed and generated data** now live under `data_source/`. This is a path refactor, not a change to geocoding algorithms.

## Copy from the original project (do not move/delete originals)

```powershell
$old = 'C:\Users\liluc\OneDrive\Desktop\Vancouver-Parking-Analytics'
$new = 'C:\Users\liluc\OneDrive\Desktop\Vancouver_Road_Safety_Release_v1.0'
Copy-Item "$old\parking-tickets-2020-2025.csv" "$new\data_source\raw\" -Force
Copy-Item "$old\public-streets.csv" "$new\data_source\raw\" -Force
Copy-Item "$old\block-numbers.csv" "$new\data_source\raw\" -Force
Copy-Item "$old\Lower Mainland_Full Data_data.csv" "$new\data_source\raw\" -Force
Copy-Item "$old\03_quality_results\*" "$new\data_source\processed\03_quality_results\" -Force
Copy-Item "$old\05_collision_results\*" "$new\data_source\processed\05_collision_results\" -Force
```

If the previous results are unavailable, run `rebuild_all.bat` **after** copying the four raw CSVs. This may consume several GB of disk and overwrite outputs under `data_source/`.

## Test and publish

```powershell
conda activate vancouver-parking
python run_tests.py
python run_tests.py --full
python 04_vancouver_road_safety_dashboard_v12_4.py
Copy-Item 'data_source/output/04_map_results/vancouver_road_safety_dashboard_v12_4.html' 'site/index.html' -Force
```

The last copy command is a publication step. Only do it after reviewing the generated map and QA results. Byte-for-byte equality with a previous HTML is **not required** for a new rebuild; differences should be reviewed.

## Important

The `site/index.html` snapshot is public, while `data_source/` is intentionally excluded from GitHub. Docker serves `site/` only. No raw data are embedded in the ZIP.
