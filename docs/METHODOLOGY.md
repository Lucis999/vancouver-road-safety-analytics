# Methodology

## Parking geocoding

`01_add_coordinates.py` normalizes street suffixes, parses official `HBLOCK` street ranges and joins each unique parking `Block + Street` to candidate road ranges. `ExactStart` matches are preferred over `InclusiveRange`; candidate coordinates are aggregated by median if multiple candidates remain. Ticket rows are streamed and preserved in the intermediate export.

`02_add_block_info.py` finds the nearest official block-number annotation using a KD-tree and a local planar approximation, accepting annotations within 150 m. This is **not** a verified parcel or block polygon assignment.

`03_audit_and_clean.py` retains `ExactStart` and `InclusiveRange` coordinate matches within broad Vancouver-area bounds. It writes included and excluded records separately, plus grouped QA summaries. A plausible coordinate does not prove correct street placement.

## Collision geocoding

`05_collision_extension.py` filters the ICBC export to Vancouver, sums `Total Crashes` rather than counting rows, and parses block-range and intersection descriptions. Road geometries provide approximate points. Locations with multiple plausible intersections may remain unmatched/ambiguous. `06_review_collision_matches.py` records inclusion decisions and reasons; it does not delete raw data.

The final dashboard independently assigns approximate collision points to road labels using a nearest-road threshold of 50 m and rejects locations near multiple road labels within 12 m of the nearest distance. These are heuristic quality controls, **not measured geocoding accuracy**.

## Dashboard metrics

- Parking: ticket totals and status-coded counts by road, year and type; annual summaries.
- Collision: sum of ICBC `Total Crashes`; casualty, pedestrian, cyclist and parked-vehicle categories derived from supplied flags.
- Severity-weighted score: exploratory **3:1 casualty/non-casualty** weighting; not an official ICBC metric.
- Year comparison: B minus A; changes describe counts, not rates or causal effects.
- Parking/collision comparison: exploratory spatial association, not evidence of causality.
- Top infraction types: grouped by unique `Block + Street + Year + InfractionText`, avoiding naïve totals across duplicate road geometries.

## Interpretation limits

Collision data begin in 2021; 2020 parking data cannot be directly paired with ICBC collisions. Ticket totals are affected by parking activity and enforcement; collision totals by road use approximate location assignment. No parking exposure, traffic volumes or enforcement-hour denominator is available. Do not call ranked roads the 'most dangerous' or infer that parking violations cause collisions.
