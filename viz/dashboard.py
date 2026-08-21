"""
Live view onto the digital twin.

This is the layer a human actually looks at. It doesn't talk to the
simulator directly -- it only ever reads through model.twin.ShipTwin,
which is the point: visualization is a consumer of the twin's state,
not a special case. Swap the simulator for a real ship feed and this
file would not need to change.

Run with: streamlit run viz/dashboard.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from model.twin import ShipTwin
from simulation.ship_simulator import WAYPOINTS

st.set_page_config(page_title="Ship Digital Twin", layout="wide")

twin = ShipTwin()

st.title("🚢 Ship Digital Twin")
st.caption(
    "Simulated vessel (simulation/ship_simulator.py) -> SQLite (ingestion/store.py) "
    "-> twin state (model/twin.py) -> this dashboard. See docs/concepts.md."
)

if twin.snapshot() is None:
    st.warning(
        "No telemetry yet. Start the simulator:\n\n"
        "`python -m simulation.ship_simulator --reset`"
    )
    st.stop()


def make_gauge(value, title, max_val, suffix=""):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title},
            number={"suffix": suffix},
            gauge={"axis": {"range": [0, max_val]}},
        )
    )
    fig.update_layout(
        height=220, margin=dict(l=20, r=20, t=40, b=10),
        transition=dict(duration=400, easing="cubic-in-out"),
    )
    return fig


def make_map(track_df, snap):
    # Scattergeo is SVG-rendered (no WebGL, no external tile requests) --
    # more robust than a WebGL basemap for a small local demo, and works offline.
    wp_lat = [w[0] for w in WAYPOINTS]
    wp_lon = [w[1] for w in WAYPOINTS]

    lat_pad, lon_pad = 0.5, 0.8
    lat_range = [min(wp_lat) - lat_pad, max(wp_lat) + lat_pad]
    lon_range = [min(wp_lon) - lon_pad, max(wp_lon) + lon_pad]

    fig = go.Figure()
    fig.add_trace(
        go.Scattergeo(
            lat=track_df["lat"], lon=track_df["lon"],
            mode="lines", line=dict(width=2, color="royalblue"),
            name="track",
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lat=wp_lat, lon=wp_lon,
            mode="markers+text", marker=dict(size=8, color="gray"),
            text=["Le Havre", "WP1", "WP2", "Southampton"],
            textposition="top right", name="waypoints",
        )
    )
    fig.add_trace(
        go.Scattergeo(
            lat=[snap.lat], lon=[snap.lon],
            mode="markers", marker=dict(size=14, color="red", symbol="triangle-up"),
            name="ship",
        )
    )
    fig.update_layout(
        geo=dict(
            resolution=50,
            showland=True, landcolor="rgb(60, 58, 50)",
            showocean=True, oceancolor="rgb(20, 40, 60)",
            showcountries=True, countrycolor="rgb(90, 90, 90)",
            coastlinecolor="rgb(120, 120, 120)",
            lataxis_range=lat_range, lonaxis_range=lon_range,
            projection_type="mercator",
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=520,
        showlegend=False,
        transition=dict(duration=400, easing="cubic-in-out"),
    )
    return fig


@st.fragment(run_every="2s")
def live_view():
    snap = twin.snapshot()
    if snap is None:
        st.stop()
    hist = twin.track(limit=2000)
    df = pd.DataFrame(hist)
    df["sim_hours"] = df["sim_time_s"] / 3600.0

    col_map, col_gauges = st.columns([2, 1])

    with col_map:
        st.plotly_chart(make_map(df, snap), use_container_width=True, key="map_chart")

    with col_gauges:
        g1, g2 = st.columns(2)
        g1.plotly_chart(make_gauge(snap.speed_knots, "Speed", 25, " kn"), use_container_width=True, key="gauge_speed")
        g2.plotly_chart(make_gauge(snap.rpm, "RPM", 2200), use_container_width=True, key="gauge_rpm")
        g3, g4 = st.columns(2)
        g3.plotly_chart(make_gauge(snap.fuel_pct, "Fuel", 100, " %"), use_container_width=True, key="gauge_fuel")
        g4.plotly_chart(make_gauge(snap.engine_temp_c, "Engine temp", 120, " °C"), use_container_width=True, key="gauge_engine_temp")

    st.subheader("Twin-derived estimates")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Heading", f"{snap.heading_deg:.0f}°")
    m2.metric("Distance to next waypoint", f"{snap.distance_to_next_wp_nm:.1f} nm")
    m3.metric("ETA next waypoint", f"{snap.eta_next_wp_hours:.1f} h" if snap.eta_next_wp_hours else "—")
    m4.metric("Estimated range on remaining fuel", f"{snap.fuel_range_nm:.0f} nm" if snap.fuel_range_nm else "—")

    st.subheader("History")
    c1, c2 = st.columns(2)
    c1.line_chart(df.set_index("sim_hours")[["speed_knots"]])
    c2.line_chart(df.set_index("sim_hours")[["fuel_level_l"]])


live_view()

with st.sidebar:
    st.header("About")
    st.write(
        "This dashboard is the *view* on a digital twin. The twin's state "
        "lives in `ingestion/store.py` (SQLite) and is derived/interpreted "
        "in `model/twin.py`. The simulator in `simulation/ship_simulator.py` "
        "plays the role of the real ship's sensors."
    )
    st.write("Read `docs/concepts.md` for how the pieces map to digital-twin theory.")
