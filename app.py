import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as qo
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & CUSTOM STYLING (CURVED BORDERS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="E-Bike Battery Analytics Tracking",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS injection to give container cards and metrics a curved edge
st.markdown("""
<style>
.stApp { background-color: #cbd5e1 !important; }

section[data-testid="stSidebar"] { background-color: #64748b !important; }

/* "Dashboard Controls" markdown heading */
section[data-testid="stSidebar"] h3 {
    font-size: 24px !important;
    font-weight: 700 !important;
    /* color: #fef3c7 !important;*/
}

/* "Select Trip Time Frame" slider label */
section[data-testid="stSidebar"] .stSelectSlider label,
section[data-testid="stSidebar"] .stSlider label {
    font-size: 25px !important;
    font-weight: 600 !important;
    /*color: #fef3c7 !important;*/
}

div[data-testid="stMetric"] {
    background-color: #64748b !important;
    padding: 24px !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}

div[data-testid="stMetric"] label,
div[data-testid="stMetricValue"] { color: #ffffff !important; }

/* REMOVED: div[data-testid="stContainer"] — unreliable, now using inline HTML cards */

h1 { color: #1e293b !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. AUTHENTICATION (Query Parameter or Token Entry)
# -----------------------------------------------------------------------------
# def check_password():
#     if st.query_params.get("auth") == "evanalytics":
#         return True
        
#     st.title("🔒 Authorized Access Only")
#     user_password = st.text_input("Enter access token:", type="password")
#     if user_password == "evanalytics":
#         return True
#     elif user_password != "":
#         st.error("😕 Token incorrect.")
    
#     st.info("💡 Hint: Append `?auth=evanalytics` to the URL link for automatic access bypass.")
#     return False

# if not check_password():
#     st.stop()

# -----------------------------------------------------------------------------
# 3. LOCAL DATA LOADING PIPELINE
# -----------------------------------------------------------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# FILE_PATH = os.path.join("./ev-battery-storage/processed-files", "CadenceTest_processed.parquet")
# Fixed — works both locally and on Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "ev-battery-storage", "processed-files", "CadenceTest_processed.parquet")
# FILE_PATH = os.path.join("processed-files", "CadenceTest_processed.parquet")

@st.cache_data(ttl=60)
def load_local_data(path):
    if not os.path.exists(path):
        st.error(f"❌ Could not find file at {path}. Check your current directory context.")
        st.stop()
        
    df = pd.read_parquet(path, engine='pyarrow')
    df['Timestamp'] = pd.to_datetime(df['Time'], format='%H:%M:%S', errors='coerce')
    
    # Calculate a simple State of Charge (SoC) estimation based on voltage boundaries
    # df['SoC'] = ((df['Voltage'] - 34.0) / (42.0 - 34.0)) * 100
    # df['SoC'] = np.clip(df['SoC'], 0, 100)
    return df

df_raw = load_local_data(FILE_PATH)

# Define a reusable helper to open/close a styled card
import streamlit.components.v1 as components
import plotly.io as pio

def render_card(title: str, fig, height: int = 400, include_plotlyjs="cdn"):
    # Lock the figure height internally so it owns its own space
    fig.update_layout(height=height)
    
    chart_html = pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"displayModeBar": False}
    )
    
    TITLE_HEIGHT = 56   # h3 line height + margin-bottom
    PADDING      = 48   # 24px top + 24px bottom padding
    BORDER_PX    = 3    # border breathing room
    iframe_height = height + TITLE_HEIGHT + PADDING + BORDER_PX
    
    card = f"""
    <html>
    <head>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: transparent; overflow: hidden; }}
        .card {{
            background-color: #64748b;
            padding: 24px;
            border-radius: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            font-family: Inter, sans-serif;
            width: 100%;
        }}
        h3 {{
            color: #ffffff;
            font-weight: 600;
            font-size: 20px;
            margin-bottom: 12px;
        }}
        .chart-wrap {{
            height: {height}px;
            width: 100%;
        }}
        .chart-wrap > div {{
            height: 100% !important;
        }}
    </style>
    </head>
    <body>
        <div class="card">
            <h3>{title}</h3>
            <div class="chart-wrap">
                {chart_html}
            </div>
        </div>
    </body>
    </html>
    """
    components.html(card, height=iframe_height, scrolling=False)

# -----------------------------------------------------------------------------
# 4. SIDEBAR CONFIGURATION (Left Side)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Dashboard Controls")

    # Build 5-minute snapped boundaries
    import pandas as pd

    raw_min = df_raw["Timestamp"].min()
    raw_max = df_raw["Timestamp"].max()

    # Floor start to nearest 5-min, ceil end to nearest 5-min
    snapped_min = raw_min.floor("5min")
    snapped_max = raw_max.ceil("5min")

    # Generate every 5-minute mark between start and end
    time_marks = pd.date_range(start=snapped_min, end=snapped_max, freq="5min")

    # Convert to plain time objects for the slider
    time_options = [t.time() for t in time_marks]

    # Slider now steps only across 5-min ticks
    time_range = st.select_slider(
        "Select Trip Time Frame",
        options=time_options,
        value=(time_options[0], time_options[-1]),
        format_func=lambda t: t.strftime("%H:%M")  # display as HH:MM
    )

    if st.button("🔄 Refresh Local Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    # st.caption("🔒 Access Profile: **evanalytics**")

# Filter: keep rows whose HH:MM falls in selected set
# Convert selected "HH:MM" strings back to time objects for filtering
df = df_raw[
    (df_raw["Timestamp"].dt.time >= time_range[0]) &
    (df_raw["Timestamp"].dt.time <= time_range[1])
].copy()

if df.empty:
    st.warning("⚠️ No data available for the selected time points.")
    st.stop()

# -----------------------------------------------------------------------------
# 5. MAIN SCREEN LAYOUT
# -----------------------------------------------------------------------------
st.title("E-Bike Battery Analytics Tracking")
st.markdown("<br>", unsafe_allow_html=True)

# --- TOP ROW: STATISTIC CARDS (Native styling catches the CSS modifications) ---
col1, col2, col3 = st.columns(3)

total_dist_km = df["DistanceMeters"].max() / 1000
current_speed_kmh = df["Speed"].iloc[-1]
current_temp_c = df["Temp"].iloc[-1]

with col1:
    with st.container():
        st.metric(label="Total Distance Covered", value=f"{total_dist_km:.2f} km")
with col2:
    with st.container():
        st.metric(label="Current Speed", value=f"{current_speed_kmh:.1f} km/h")
with col3:
    with st.container():
        st.metric(label="Current Battery Temp", value=f"{current_temp_c:.1f} °C")

st.markdown("<br>", unsafe_allow_html=True)

# Shared transparent layout variable dictionary to remove Plotly backgrounds
plotly_transparent_layout = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=20, t=20, b=40),
    font=dict(
        color="#e2e8f0",
        family="Inter, sans-serif",
        size=16        # ← global base font size for all text
    ),
    legend=dict(
        font=dict(
            color="#e2e8f0",
            size=15,   # ← legend text size
        )
    ),
    # Axis titles (x/y labels)
    xaxis=dict(
        title_font=dict(size=16, color="#e2e8f0"),
        tickfont=dict(size=15, color="#e2e8f0", family="Inter, sans-serif"),
    ),
    yaxis=dict(
        title_font=dict(size=16, color="#e2e8f0"),
        tickfont=dict(size=15, color="#e2e8f0", family="Inter, sans-serif"),
    ),
)

# --- MIDDLE ROW: MAP & PERFORMANCE (3:1 Ratio) ---
mid_col1, mid_col2 = st.columns([3, 1])

with mid_col1:
    # Injecting the HTML card wrapper manually around our chart block
    # st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    # with st.container():
    # st.markdown("### 📍 GPS Route & Altitude Map")
    # card("📍 GPS Route & Altitude Map")
    fig_map = px.scatter_mapbox(
        df, 
        lat="LatitudeDegrees", 
        lon="LongitudeDegrees", 
        color="AltitudeMeters",
        size_max=12, 
        zoom=14,
        color_continuous_scale="Viridis",
        mapbox_style="carto-positron"
    )
    fig_map.update_layout(**plotly_transparent_layout)
    fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0)) # Stretch map to full card edges
    # st.plotly_chart(fig_map, use_container_width=True, config={'displayModeBar': False})
    render_card("📍 GPS Route & Altitude Map", fig_map, height=420)
    # st.markdown('</div>', unsafe_allow_html=True)

with mid_col2:
    # st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    # with st.container():
    # st.markdown("### 🚴 Cadence vs Speed")
    # card("🚴 Cadence vs Speed")
    fig_perf = px.scatter(
        df, 
        x="Cadence", 
        y="Speed", 
        color="Current",
        color_continuous_scale="Plasma"
    )
    fig_perf.update_layout(**plotly_transparent_layout)
    fig_perf.update_xaxes(showgrid=True, gridcolor="#edf2f7", linecolor="#cbd5e0")
    fig_perf.update_yaxes(showgrid=True, gridcolor="#edf2f7", linecolor="#cbd5e0")
    # st.plotly_chart(fig_perf, use_container_width=True, config={'displayModeBar': False})
    render_card("🚴 Cadence vs Speed", fig_perf, height=420)
    # card_end()
    # st.markdown('</div>', unsafe_allow_html=True)

# --- BOTTOM ROW: ADVANCED BATTERY ANALYTICS (1:1 Ratio) ---
bot_col1, bot_col2 = st.columns(2)

with bot_col1:
    # st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    # with st.container():
    # card("📊 SoC Usage Distribution & Mean Temperature")
    # st.markdown("### 📊 SoC Usage Distribution & Mean Temperature")
    
    bin_edges = list(range(0, 101, 10))
    bin_labels = [f"{bin_edges[i]}-{bin_edges[i+1]}%" for i in range(len(bin_edges)-1)]
    
    df['SoC_Bin'] = pd.cut(df['SoC'], bins=bin_edges, labels=bin_labels)
    bin_counts = df['SoC_Bin'].value_counts().sort_index().reset_index()
    bin_counts.columns = ['SoC Range', 'Sample Count']
    
    bin_temp = df.groupby('SoC_Bin', observed=False)['Temp'].mean().reset_index()
    
    fig_soc_dist = make_subplots(specs=[[{"secondary_y": True}]])
    fig_soc_dist.add_trace(
        qo.Bar(x=bin_counts['SoC Range'], y=bin_counts['Sample Count'], name="Samples Spent", marker_color='#3182ce', opacity=0.85),
        secondary_y=False
    )
    fig_soc_dist.add_trace(
        qo.Scatter(x=bin_temp['SoC_Bin'], y=bin_temp['Temp'], name="Avg Temp (°C)", mode='lines+markers', line=dict(color='#e53e3e', width=3)),
        secondary_y=True
    )
    
    fig_soc_dist.update_layout(**plotly_transparent_layout)
    fig_soc_dist.update_xaxes(linecolor="#cbd5e0")
    fig_soc_dist.update_yaxes(title_text="Count of Logs", secondary_y=False, showgrid=True, gridcolor="#edf2f7", linecolor="#cbd5e0")
    fig_soc_dist.update_yaxes(title_text="Temperature (°C)", secondary_y=True, showgrid=False, linecolor="#cbd5e0")
    # st.plotly_chart(fig_soc_dist, use_container_width=True, config={'displayModeBar': False})
    # card_end()
    render_card("📊 SoC Usage Distribution & Mean Temperature", fig_soc_dist, height=380)
    # st.markdown('</div>', unsafe_allow_html=True)

with bot_col2:
    # st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    # with st.container():
    # st.markdown("### 📈 SoC Estimation Timeline & Thermal Density")
    # card("📈 SoC Estimation Timeline & Thermal Density")
    fig_soc_time = qo.Figure()
    fig_soc_time.add_trace(qo.Scatter(
        x=df['Timestamp'], 
        y=df['SoC'],
        mode='lines',
        name='Estimated SoC %',
        line=dict(width=3, color='#38a169')
    ))
    
    fig_soc_time.add_trace(qo.Scatter(
        x=df['Timestamp'],
        y=df['SoC'],
        mode='markers',
        marker=dict(
            size=5,
            color=df['Temp'],
            colorscale='YlOrRd',
            showscale=True,
            colorbar=dict(title="Temp °C", thickness=12, len=0.8)
        ),
        name='Thermal Heatmap'
    ))
    
    fig_soc_time.update_layout(**plotly_transparent_layout)
    fig_soc_time.update_xaxes(showgrid=True, gridcolor="#edf2f7", linecolor="#cbd5e0")
    fig_soc_time.update_yaxes(title_text="Battery Capacity Remaining (%)", showgrid=True, gridcolor="#edf2f7", linecolor="#cbd5e0")
    # st.plotly_chart(fig_soc_time, use_container_width=True, config={'displayModeBar': False})
    # card_end()
    render_card("📈 SoC Estimation Timeline & Thermal Density", fig_soc_time, height=380)
    # st.markdown('</div>', unsafe_allow_html=True)
