# Interactive dashboard user guide (v12.4)

## Analysis layer

- **Parking Violations:** map road-segment ticket counts and status-based metrics.
- **Traffic Collisions:** inspect ICBC crash counts and categories (2021–2025 only).
- **Parking vs. Collisions:** exploratory comparison of the two spatial distributions; not causal inference.

## Analysis period

- **Selected years · aggregate:** select one or more years; All years and Clear help change selection.
- **Year comparison (B − A):** compare different years. Same-year comparisons are not meaningful; the interface provides feedback.
- ICBC 2020 is unavailable. The interface explains why a collision-related 2020 selection is blocked.

## Metrics and highlights

- Parking metrics: all tickets, status counts, VA/Warning shares.
- Collision metrics: total crashes, casualty, pedestrian, cyclist, parked-vehicle, and exploratory severity-weighted score.
- Road highlights: top volume and (in Year Comparison) most improved or deteriorated by count change. Choose top 50/100/150/250. Color indicates selected category, not validated risk.

## Inspect locations

- Hover over road segments for infraction-type Top 10. Click to lock and use Unlock / Follow mouse to resume hover.
- Collision detail panel: choose 100–1,000 m search radius, toggle nearby markers/circle, follow mouse or lock location.
- Multiple geometries may represent the same ticket block; do not sum all displayed road-segment values to infer citywide totals.

## Known limitations

Approximate collision locations, incomplete geocoding, road-label ambiguity, differing 2020 coverage and absent exposure denominators. Internet access is needed for Leaflet assets loaded from CDNs.
