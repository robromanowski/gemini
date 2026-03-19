# Trout Stream Data Explorer — Overview

## Data

- State and federal agencies (NC DEQ, TN TWRA, GA DNR, NPS/GRSM) conduct electrofishing surveys on mountain streams — wading with a backpack shocker, counting and measuring trout
- Datasets pulled from public agency portals, stream names standardized, locations geocoded
- Aggregated to one record per stream with density calculations

## App

- Two versions: a vanilla JS/Leaflet web app covering Southern Appalachians + New England, and a Streamlit version focused on the Southern Appalachians for easier sharing
- Filter by species, state, region, and minimum density; sort by any metric
- Click any stream to see its full survey history — individual electrofishing visits with fish counts, reach dimensions, and pass-by-pass data

## Streamlit

- Single Python script — no backend or database
- Streamlit re-runs the script on every interaction, so filters and selections instantly update the map and table without manual state management
- Data loaded once from flat JSON files and cached in memory
- Map rendered with Folium (Leaflet under the hood), embedded via `streamlit-folium`
