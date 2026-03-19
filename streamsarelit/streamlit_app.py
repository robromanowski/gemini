"""
Trout Stream Data Explorer — Streamlit Edition
Southern Appalachian streams
"""

import json, math, re
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Trout Stream Data Explorer",
    page_icon="🎣",
    layout="wide",
)

# ── Load data ─────────────────────────────────────────────────
@st.cache_data
def load_data():
    with open("data/master_trout_density.json") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)
    # Fix numeric columns
    for col in ["avg_density_per_100m2", "best_site_density", "peak_sample_density",
                "avg_fish_per_sample", "num_samples", "years_sampled",
                "first_year", "last_year", "latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

@st.cache_data
def load_samples():
    with open("data/sa_samples_data.js") as f:
        content = f.read()
    match = re.search(r"=\s*(\{.*\})\s*;?\s*$", content, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return {}

df_all = load_data()
samples_all = load_samples()

# ── Color helpers ─────────────────────────────────────────────
def density_color(val, max_val=30):
    if val is None or math.isnan(val):
        return "#888"
    t = min(1.0, math.log1p(val) / math.log1p(max(max_val, 0.01)))
    hue = round(t * 270)
    return f"hsl({hue},90%,52%)"

def hsl_to_hex(h, s, l):
    """Convert HSL (0-360, 0-100, 0-100) to hex color."""
    s /= 100; l /= 100
    c = (1 - abs(2*l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c/2
    if h < 60:   r,g,b = c,x,0
    elif h < 120: r,g,b = x,c,0
    elif h < 180: r,g,b = 0,c,x
    elif h < 240: r,g,b = 0,x,c
    elif h < 300: r,g,b = x,0,c
    else:         r,g,b = c,0,x
    return "#{:02x}{:02x}{:02x}".format(int((r+m)*255), int((g+m)*255), int((b+m)*255))

def density_color_hex(val, max_val=30):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "#888"
    t = min(1.0, math.log1p(val) / math.log1p(max(max_val, 0.01)))
    hue = round(t * 270)
    return hsl_to_hex(hue, 90, 52)

# ── Metric config ─────────────────────────────────────────────
METRIC_OPTIONS = {
    "fish/100m² (area density)": {
        "field": "avg_density_per_100m2",
        "peak_field": "peak_sample_density",
        "label": "fish/100m²",
        "high_thresh": 15,
        "factor": 1,
    },
    "fish/km (linear density)": {
        "field": "avg_linear_per_km",
        "peak_field": "avg_linear_per_km",
        "label": "fish/km",
        "high_thresh": 300,
        "factor": 1,
    },
}

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.title("🎣 Filters")

metric_label = st.sidebar.selectbox("Density metric", list(METRIC_OPTIONS.keys()))
mc = METRIC_OPTIONS[metric_label]
metric_field = mc["field"]

# Species
all_species = sorted({sp.strip() for row in df_all["species"].dropna()
                      for sp in str(row).split(",")})
species_filter = st.sidebar.multiselect("Species", all_species, default=[])

# State
all_states = sorted(df_all["state"].dropna().unique())
state_filter = st.sidebar.multiselect("State", all_states, default=[])

# Region
all_regions = sorted(df_all["region"].dropna().unique())
region_filter = st.sidebar.multiselect("Region", all_regions, default=[])

# Density range
if metric_field in df_all.columns:
    col_max = float(df_all[metric_field].dropna().max()) if not df_all[metric_field].dropna().empty else 100.0
else:
    col_max = 100.0
density_range = st.sidebar.slider(
    f"Min density ({mc['label']})",
    min_value=0.0,
    max_value=round(col_max, 1),
    value=0.0,
    step=0.5,
)

# Min samples
min_samples = st.sidebar.number_input("Min samples", min_value=0, value=0, step=1)

# Sort
sort_options = {
    f"Avg {mc['label']}": metric_field,
    "Avg fish/sample": "avg_fish_per_sample",
    "# Samples": "num_samples",
    "Stream name": "stream_name",
}
sort_label = st.sidebar.selectbox("Sort by", list(sort_options.keys()))
sort_field = sort_options[sort_label]

# ── Filter data ───────────────────────────────────────────────
df = df_all.copy()

if species_filter:
    df = df[df["species"].apply(lambda s: any(sp in str(s) for sp in species_filter))]

if state_filter:
    df = df[df["state"].isin(state_filter)]

if region_filter:
    df = df[df["region"].isin(region_filter)]

if metric_field in df.columns:
    df = df[df[metric_field].fillna(0) >= density_range]

df = df[df["num_samples"].fillna(0) >= min_samples]

# Sort
if sort_field in df.columns:
    ascending = sort_field == "stream_name"
    df = df.sort_values(sort_field, ascending=ascending, na_position="last").reset_index(drop=True)
df.insert(0, "Rank", df.index + 1)

# ── Header ────────────────────────────────────────────────────
st.title("🎣 Trout Stream Data Explorer")
st.caption("Southern Appalachians · electrofishing survey data")
st.subheader(f"{len(df)} streams")

# ── Map ───────────────────────────────────────────────────────
max_val = mc["high_thresh"] * 2
df_mapped = df[df["latitude"].notna() & df["longitude"].notna()]

m = folium.Map(
    location=[35.5, -83.0],
    zoom_start=7,
    tiles="CartoDB dark_matter",
)

for _, row in df_mapped.iterrows():
    val = row.get(metric_field)
    color = density_color_hex(val if pd.notna(val) else None, max_val)
    val_display = f"{val * mc['factor']:.2f}" if pd.notna(val) else "N/A"
    est_tag = " (~est)" if row.get("density_estimated") else ""

    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=max(4, min(14, (val or 0) / max(max_val / 14, 0.01))),
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.75,
        weight=1,
        popup=folium.Popup(
            f"<b>#{row['Rank']} {row['stream_name']}</b><br>"
            f"{mc['label']}: {val_display}{est_tag}<br>"
            f"Species: {row.get('species', 'N/A')}",
            max_width=260,
        ),
        tooltip=f"#{row['Rank']} {row['stream_name']}",
    ).add_to(m)

# Legend HTML overlay
legend_steps = 5
legend_html = '<div style="background:rgba(20,20,20,0.85);padding:8px 12px;border-radius:6px;color:#eee;font-size:11px;">'
legend_html += f'<div style="margin-bottom:4px;font-weight:600">{mc["label"]}</div>'
legend_html += '<div style="display:flex;height:12px;width:160px;border-radius:3px;overflow:hidden">'
for i in range(20):
    t = i / 19
    hue = round(t * 270)
    legend_html += f'<div style="flex:1;background:hsl({hue},90%,52%)"></div>'
legend_html += '</div><div style="display:flex;justify-content:space-between;width:160px;margin-top:3px">'
for i in range(legend_steps):
    t = i / (legend_steps - 1)
    tick_val = math.exp(t * math.log1p(max_val)) - 1
    legend_html += f'<span>{tick_val * mc["factor"]:.0f}</span>'
legend_html += '</div></div>'

m.get_root().html.add_child(folium.Element(
    f'<div style="position:fixed;bottom:30px;right:10px;z-index:1000">{legend_html}</div>'
))

map_col, table_col = st.columns([2, 3])

with map_col:
    st_folium(m, width=None, height=520, returned_objects=[])

# ── Table ─────────────────────────────────────────────────────
with table_col:

    display_cols = {
        "Rank": "Rank",
        "stream_name": "Stream",
        "state": "State",
        "region": "Region",
        "species": "Species",
        metric_field: mc["label"],
        "avg_fish_per_sample": "Avg fish/sample",
        "num_samples": "Samples",
        "years_sampled": "Years",
        "last_year": "Last yr",
    }
    # Only keep cols that exist
    disp = {k: v for k, v in display_cols.items() if k in df.columns or k == "Rank"}
    df_disp = df[[c for c in disp.keys() if c in df.columns]].rename(columns=disp)

    # Round numeric display; append ~ for estimated values
    if mc["label"] in df_disp.columns:
        estimated = df["density_estimated"].fillna(False).astype(bool).values
        df_disp[mc["label"]] = [
            (f"{x * mc['factor']:.2f}~" if est else f"{x * mc['factor']:.2f}") if pd.notna(x) else "—"
            for x, est in zip(df_disp[mc["label"]], estimated)
        ]
    if "Avg fish/sample" in df_disp.columns:
        df_disp["Avg fish/sample"] = df_disp["Avg fish/sample"].apply(
            lambda x: f"{x:.1f}" if pd.notna(x) else "—"
        )

    selected = st.dataframe(
        df_disp,
        use_container_width=True,
        height=520,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    st.caption("~ estimated density")

# ── Detail panel ──────────────────────────────────────────────
selected_rows = selected.get("selection", {}).get("rows", [])
if selected_rows:
    row_idx = selected_rows[0]
    row = df.iloc[row_idx]
    stream_name = row["stream_name"]

    st.divider()
    st.subheader(f"📍 {stream_name}")

    d1, d2, d3, d4 = st.columns(4)
    val = row.get(metric_field)
    d1.metric(mc["label"], f"{val * mc['factor']:.2f}" if pd.notna(val) else "N/A")
    d2.metric("Avg fish/sample", f"{row['avg_fish_per_sample']:.1f}" if pd.notna(row.get('avg_fish_per_sample')) else "N/A")
    d3.metric("Samples", int(row["num_samples"]) if pd.notna(row.get("num_samples")) else "N/A")
    d4.metric("Last surveyed", int(row["last_year"]) if pd.notna(row.get("last_year")) else "N/A")

    st.caption(f"**Species:** {row.get('species', 'N/A')}  ·  **Region:** {row.get('region', '')}  ·  **State:** {row.get('state', '')}")
    if row.get("notes"):
        with st.expander("Notes"):
            st.write(row["notes"])

    # Sample visits
    stream_samples = samples_all.get(stream_name, [])
    if stream_samples:
        st.markdown("**Survey visits**")
        sdf = pd.DataFrame(stream_samples)
        col_map = {
            "date": "Date", "year": "Year", "fish": "Fish",
            "density": "Density/100m²", "length_m": "Length (m)",
            "width_m": "Width (m)", "passes": "Passes",
            "yoy": "YOY", "adult": "Adult", "src": "Source",
        }
        sdf = sdf[[c for c in col_map if c in sdf.columns]].rename(columns=col_map)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
    else:
        st.info("No individual sample visits available for this stream.")
