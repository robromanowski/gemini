# Trout Stream Data Explorer — Streamlit App

Interactive explorer for Southern Appalachian trout stream electrofishing data, built with Streamlit and Folium.

---

## Files

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Main application (single-file) |
| `requirements.txt` | Python dependencies |
| `data/master_trout_density.json` | Stream-level aggregated density records |
| `data/sa_samples_data.js` | Individual survey visit records per stream |

---

## Architecture

The app is a single Python script with no backend server or database. All data is loaded from flat files at startup and cached in memory. Streamlit re-runs the script top-to-bottom on every user interaction (filter change, row click, etc.), which is the standard Streamlit execution model.

```
streamlit_app.py
│
├── Data loading (@st.cache_data)
│   ├── master_trout_density.json  →  df_all (one row per stream)
│   └── sa_samples_data.js         →  samples_all (dict: stream → list of visits)
│
├── Sidebar filters (run first, control everything below)
│   ├── Density metric selector
│   ├── Species / State / Region multiselects
│   ├── Min density slider
│   ├── Min samples input
│   └── Sort by selector
│
├── Filter + sort → df (filtered DataFrame)
│
├── Two-column layout [2 : 3]
│   ├── Left: Folium map (st_folium)
│   └── Right: Interactive table (st.dataframe, selectable rows)
│
└── Detail panel (renders below when a table row is selected)
    ├── 4 stat cards (density, avg fish/sample, # samples, last year)
    ├── Species / region / state caption
    ├── Notes expander
    └── Survey visits table (from sa_samples_data.js)
```

---

## Data

### `master_trout_density.json`
One record per stream per species. Key fields:

| Field | Description |
|-------|-------------|
| `stream_name` | Stream name |
| `state` | Full state name (e.g. "North Carolina") |
| `region` | Sub-region (e.g. "Western NC (Watauga Basin)") |
| `species` | Trout species present (comma-separated) |
| `avg_density_per_100m2` | Average area density across all survey sites |
| `best_site_density` | Highest single-site area density recorded |
| `peak_sample_density` | Highest single-sample area density recorded |
| `avg_fish_per_sample` | Average fish count per electrofish pass |
| `num_samples` | Total number of survey visits |
| `years_sampled` | Number of distinct years sampled |
| `first_year` / `last_year` | Survey date range |
| `latitude` / `longitude` | Stream coordinates |
| `density_estimated` | `true` if density was derived/estimated rather than directly measured |
| `data_source` | Originating agency/dataset |

Tailwater streams (regulated below dams) are excluded from the app — they are not comparable to wild freestone/mountain streams.

### `sa_samples_data.js`
A JavaScript file containing a JSON object keyed by stream name. Each value is a list of individual survey visit records with fields: `date`, `year`, `fish`, `yoy`, `adult`, `density`, `length_m`, `width_m`, `passes`, `p1y`/`p1a` (pass 1 YOY/adult), etc.

The app extracts the JSON with a regex rather than executing the JS.

---

## Color Scale

Dot color and size on the map both encode density. Color uses a log-scale HSL gradient:

```
red (0) → yellow → green → blue → violet (high)
hsl(t × 270, 90%, 52%)   where t = log(1 + val) / log(1 + maxVal)
```

Log scale is used because trout densities are heavily right-skewed — a linear scale would wash out most streams at the low end. `maxVal` is set to `highThresh × 2` per metric.

Dot radius scales linearly with density, clamped between 4–14px.

---

## Metrics

| Metric | Field | High threshold | Notes |
|--------|-------|---------------|-------|
| fish/100m² | `avg_density_per_100m2` | 15 | Standard area-based electrofishing density |
| fish/km | `avg_linear_per_km` | 300 | Linear density for streams where width wasn't measured |

The selected metric controls the map colors, legend, table density column, and sort default.

---

## Estimated Densities

Some records have `density_estimated: true`, meaning density was derived from fish counts and assumed/estimated reach dimensions rather than directly measured. These display with a `~` suffix in the density column (e.g. `8.20~`) and a footnote below the table.

---

## Dependencies

```
streamlit       — UI framework and server
folium          — Leaflet.js map wrapper
streamlit-folium — Embeds Folium maps inside Streamlit
pandas          — Data loading and filtering
```
