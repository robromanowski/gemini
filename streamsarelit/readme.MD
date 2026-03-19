# Trout Stream Data Explorer — Overview

## Data

State and federal fish survey agencies (NC DEQ, TN TWRA, GA DNR, NPS/GRSM) conduct electrofishing surveys on mountain streams — wading with a backpack shocker, counting and measuring trout. We pulled those datasets from public agency portals, standardized stream names, geocoded locations, and aggregated to one record per stream with density calculations.

## App

Built two versions — a vanilla JS/Leaflet web app for the full dataset (Southern Appalachians + New England), and a Streamlit version focused on the Southern Appalachians for easier sharing. The Streamlit app reads the pre-processed JSON files, runs all filtering/sorting in pandas on each interaction, and renders an interactive Folium map alongside a selectable ranked table.

Users can filter by species, state, region, and minimum density, sort by any metric, and click any stream to see its full survey history — individual electrofishing visits with fish counts, reach dimensions, and pass-by-pass data.

## Streamlit

The app is a single Python script with no backend or database. Streamlit re-runs the script on every interaction, so filters and selections instantly update the map and table without any manual state management. Data is loaded once from flat JSON files and cached in memory. The map is rendered with Folium (Leaflet under the hood) and embedded via `streamlit-folium`.
