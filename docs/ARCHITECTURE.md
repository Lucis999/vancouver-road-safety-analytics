# Architecture and file dependencies

```mermaid
flowchart TD
  A[Parking tickets 2020–2025] --> B[01 Add coordinates]
  S[Public streets] --> B
  B --> C[01 coordinate lookup + enriched tickets]
  C --> D[02 Add block annotation]
  N[Block numbers] --> D
  D --> E[02 enriched tickets with blocks]
  E --> F[03 Audit and clean]
  F --> G[Clean geocoded tickets + parking QA]
  I[ICBC Lower Mainland export] --> J[05 Collision extension]
  S --> J
  J --> K[Collision locations + match audit]
  K --> L[06 Collision QA review]
  G --> M[04 v12.4 Dashboard generator]
  K --> M
  S --> M
  M --> H[04_map_results HTML + JSON]
  H --> P[Copy after QA: site/index.html]
```

The optional `04_local_street_map.py` is an earlier standalone map prototype. It is not called by the v12.4 pipeline.

## Direct input contract for v12.4

- `data_source/processed/03_quality_results/parking_tickets_clean_geocoded.csv`: semicolon-delimited; `Block`, `Street`, `Year`, `Status`, `InfractionText`.
- `data_source/raw/public-streets.csv`: semicolon-delimited; `HBLOCK`, `Geom`.
- `data_source/processed/05_collision_results/collision_locations.csv`: includes `Latitude`, `Longitude`, `Year`, `Crashes`, `Crash Severity`, `Derived Crash Configuration`, `Pedestrian Flag`, `Cyclist Flag`, `Parked Vehicle Flag`.

All Python scripts currently locate their project root via `Path(__file__).resolve().parent`; do not move scripts without updating those paths. The Dockerfile only serves the pre-generated `site/index.html`; it does not execute the Python pipeline.
