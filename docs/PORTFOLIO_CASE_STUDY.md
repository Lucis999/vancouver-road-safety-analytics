# Portfolio case study — Vancouver Road Safety Analytics

## Problem

Parking enforcement records and road-collision records reveal different aspects of Vancouver street activity. The analytical challenge is to align heterogeneous sources to comparable road labels while communicating uncertainty rather than equating counts with risk.

## Approach

1. Normalize and geocode parking `Block + Street` values using municipal road data.
2. Annotate nearby block labels and audit geographic inclusion/exclusion.
3. Convert ICBC textual road descriptions into approximate points; flag unmatched and ambiguous locations.
4. Aggregate by year, road label and metric; build a Folium/Leaflet interface for filtering, comparisons and inspection.
5. Publish methods and limitations alongside the dashboard.

## Skills demonstrated

Python ETL (pandas/NumPy), geospatial joins and nearest-neighbour searches (SciPy/Shapely), data-quality auditing, exploratory analysis, interactive Folium/Leaflet, browser UX, documentation, reproducible workflows and static deployment.

## Contribution and academic context

The original parking-ticket visualization was developed in a university group project with Jonny Wu, Jackie Chang, Ana Karen Luque Flores, Yanqing Li and Anirudha Nair. Yanqing's documented work included Python cleaning/geographic matching, Folium map implementation, selected Tableau work and presentation integration. Later ICBC integration and v12-series dashboard development were subsequent extensions; **verify exact authorship/assistance and dates before presenting them as solely individual work**. Disclose AI assistance where required by course, portfolio or professional norms.

## Interpretation and impact

The dashboard supports exploration of spatial concentration, year-to-year change, infraction mix and proximity of approximate collision records. It does not establish collision causality, enforcement fairness or exposure-adjusted safety risk. The primary value is an inspectable analytical workflow with explicit limitations.
