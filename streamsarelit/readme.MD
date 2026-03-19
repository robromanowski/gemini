# Trout Stream Data Explorer — Overview

## Data

State and federal fish survey agencies (NC DEQ, TN TWRA, GA DNR, NPS/GRSM) conduct electrofishing surveys on mountain streams — wading with a backpack shocker, counting and measuring trout. We pulled those datasets from public agency portals, standardized stream names, geocoded locations, and aggregated to one record per stream with density calculations.

## App

Built two versions — a vanilla JS/Leaflet web app for the full dataset (Southern Appalachians + New England), and a Streamlit version focused on the Southern Appalachians for easier sharing. The Streamlit app reads the pre-processed JSON files, runs all filtering/sorting in pandas on each interaction, and renders an interactive Folium map alongside a selectable ranked table.
