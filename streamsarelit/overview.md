# Trout Stream Data Explorer — Architecture Walkthrough

A high-level narrative of how the app is built, from raw data to deployed app.

---

## 1. The data story

State fish & wildlife agencies publish electrofishing survey results — NC DEQ, TN TWRA, GA DNR, NPS. We pulled those raw CSVs, cleaned and standardized them with a Python pipeline, and landed on two flat JSON files the app reads directly. No database needed.

- `master_trout_density.json` — one aggregated record per stream (density, samples, location, species)
- `sa_samples_data.js` — individual survey visit records per stream (fish counts, reach dimensions, pass-by-pass data)

## 2. From raw data to pandas

`json.load()` into a pandas DataFrame — one row per stream. All the filtering (species, state, density range) is just boolean pandas masks. Sorting is one line. Nothing fancy, just the stuff pandas was made for.

```python
df = pd.DataFrame(json.load(f))
df = df[df["state"].isin(state_filter)]
df = df.sort_values("avg_density_per_100m2", ascending=False)
```

## 3. The map

Folium lets you build a Leaflet map entirely in Python — loop over the DataFrame rows, add a colored circle per stream, done. `streamlit-folium` embeds the whole thing in the page with a single function call. Dot color is a log-scale HSL gradient computed in pure Python — log scale because trout densities are heavily skewed and a linear scale would wash out most streams.

```python
for _, row in df.iterrows():
    folium.CircleMarker([row["latitude"], row["longitude"]], color=...).add_to(m)

st_folium(m, height=520)
```

## 4. The Streamlit glue

The key insight: Streamlit re-runs the whole script on every interaction. So the sidebar filters are just variables at the top, and the map and table below them naturally react — no callbacks, no event handlers, no JavaScript written by hand.

`st.dataframe` with `on_select="rerun"` makes rows clickable and drives the detail panel the same way — when a row is selected, the script re-runs and the selected index is available to render the drill-down view.

```python
species_filter = st.sidebar.multiselect("Species", all_species)
# ... filter df ...
selected = st.dataframe(df, on_select="rerun", selection_mode="single-row")
if selected["selection"]["rows"]:
    # render detail panel
```

## 5. Deploy

`streamlit run streamlit_app.py` locally, or `rsconnect deploy streamlit` to push to a shared Posit Connect server. The whole app travels as one `.py` file plus the data.
