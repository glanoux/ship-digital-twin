"""
HTTP bridge onto the twin, for consumers that aren't Python and don't share
memory with this process -- Unity, a browser, curl. viz/dashboard.py reads
model.twin.ShipTwin directly because it *is* Python in the same run; this
API exists because Unity isn't. Same twin, same model/twin.py underneath --
this is just a second, network-reachable door into it.

Run with: uvicorn api.server:app --port 8000
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from model.twin import ShipTwin

app = FastAPI(title="Ship Digital Twin API")

# Not required for the Unity Editor (UnityWebRequest isn't browser-sandboxed),
# but keeps this API usable from a browser-based client too (e.g. a WebGL build).
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

twin = ShipTwin()


class Snapshot(BaseModel):
    lat: float
    lon: float
    heading_deg: float
    speed_knots: float
    rpm: float
    fuel_level_l: float
    fuel_rate_lph: float
    fuel_pct: float
    engine_temp_c: float
    waypoint_idx: int
    distance_to_next_wp_nm: float
    eta_next_wp_hours: float
    fuel_range_nm: float
    avg_fuel_rate_lph: float
    sim_time_s: float
    fouling_pct: float


class TelemetryPoint(BaseModel):
    sim_time_s: float
    lat: float
    lon: float
    heading_deg: float
    speed_knots: float
    fuel_rate_lph: float


@app.get("/twin/snapshot", response_model=Snapshot)
def get_snapshot():
    snap = twin.snapshot()
    if snap is None:
        return Snapshot(
            lat=0, lon=0, heading_deg=0, speed_knots=0, rpm=0, fuel_level_l=0,
            fuel_rate_lph=0, fuel_pct=0, engine_temp_c=0, waypoint_idx=0,
            distance_to_next_wp_nm=0, eta_next_wp_hours=0, fuel_range_nm=0,
            avg_fuel_rate_lph=0, sim_time_s=0, fouling_pct=0,
        )
    return Snapshot(
        lat=snap.lat, lon=snap.lon, heading_deg=snap.heading_deg,
        speed_knots=snap.speed_knots, rpm=snap.rpm, fuel_level_l=snap.fuel_level_l,
        fuel_rate_lph=snap.fuel_rate_lph, fuel_pct=snap.fuel_pct,
        engine_temp_c=snap.engine_temp_c, waypoint_idx=snap.waypoint_idx,
        distance_to_next_wp_nm=snap.distance_to_next_wp_nm,
        eta_next_wp_hours=snap.eta_next_wp_hours or 0.0,
        fuel_range_nm=snap.fuel_range_nm or 0.0,
        avg_fuel_rate_lph=snap.avg_fuel_rate_lph or 0.0,
        sim_time_s=snap.sim_time_s, fouling_pct=snap.fouling_pct,
    )


@app.get("/twin/track", response_model=list[TelemetryPoint])
def get_track(limit: int = 500):
    hist = twin.track(limit=limit)
    return [
        TelemetryPoint(
            sim_time_s=h["sim_time_s"], lat=h["lat"], lon=h["lon"],
            heading_deg=h["heading_deg"], speed_knots=h["speed_knots"],
            fuel_rate_lph=h["fuel_rate_lph"],
        )
        for h in hist
    ]
