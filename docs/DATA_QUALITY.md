# Data quality, uncertainty and exclusions

## Parking

Stage 01 stores candidate counts, matching method and unmatched reason. Stage 02 records nearest block-number annotation status and distance. Stage 03 outputs matching summaries and excludes unmatched or implausible-coordinate rows from the geographic analysis copy; original raw data remain unchanged.

Key files: `data_source/processed/03_quality_results/matching_summary.csv`, `cleaning_summary.csv`, `location_audit.csv`, `unmatched_locations_ranked.csv`, `parking_tickets_excluded_review.csv`.

## Collisions

The source ICBC export may aggregate multiple crashes in one row. The correct measure is the `Total Crashes` weight. The approximate geocoding process has unmatched and ambiguous cases, which should be disclosed as a selection limitation.

Key files: `data_source/processed/05_collision_results/matching_audit.csv`, `collision_quality_summary.csv`, `collision_excluded_review.csv`, `collision_mapped_approximate.csv`.

The dashboard uses `collision_locations.csv`, drops rows missing location/year and independently filters road assignments; therefore stage-06 included totals are **not necessarily identical** to dashboard road-assigned totals.

## QA before public release

1. Verify source schemas, years, raw row counts and weighted crash totals.
2. Verify stage-03 `InputTickets = KeptTickets + ExcludedTickets` and investigate geographic exclusions.
3. Check collision matched/unmatched/ambiguous weighted shares; manually inspect a sample of street and intersection matches.
4. Compare dashboard annual parking totals with source summaries and collision totals with accepted mapped records, explaining any denominator differences.
5. Verify no collision 2020 controls are enabled, same-year comparison warnings work, and Year Comparison-only road highlights are constrained.
6. Test on Chrome/Edge and narrow screens, plus GitHub Pages CDN loading and performance.
7. Review source attribution, licensing and privacy before publishing any data extract.

**No independent full-data rebuild or browser test was performed as part of this documentation-only release.** Do not represent these checks as passed until completed.
