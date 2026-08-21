"""
The digital twin itself.

Note what this class does NOT do: it doesn't generate telemetry (that's
simulation/ship_simulator.py acting as the "real" ship) and it doesn't
persist anything (that's ingestion/store.py). Its job is the thing that
actually makes something a *twin* rather than just a data feed: it holds
a virtual representation of the ship's state and derives things the raw
sensors never told you directly -- estimated range, ETA, trend -- by
combining current readings with a model of how the ship behaves.
"""

from dataclasses import dataclass

from ingestion.store import get_latest, get_history
from simulation.ship_simulator import WAYPOINTS, haversine_nm


@dataclass
class TwinSnapshot:
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
    next_waypoint: tuple
    distance_to_next_wp_nm: float
    eta_next_wp_hours: float | None
    fuel_range_nm: float | None
    avg_fuel_rate_lph: float | None
    sim_time_s: float


class ShipTwin:
    """Virtual counterpart of the ship: current state + derived estimates."""

    FUEL_CAPACITY_L = 20_000.0

    def snapshot(self, history_window: int = 60) -> TwinSnapshot | None:
        latest = get_latest(1)
        if not latest:
            return None
        row = latest[0]

        wp_idx = row["waypoint_idx"]
        direction = 1 if wp_idx == 0 else (-1 if wp_idx == len(WAYPOINTS) - 1 else None)
        next_idx = wp_idx + direction if direction is not None else wp_idx
        next_idx = max(0, min(len(WAYPOINTS) - 1, next_idx))
        next_wp = WAYPOINTS[next_idx]

        dist_nm = haversine_nm(row["lat"], row["lon"], *next_wp)
        eta_h = dist_nm / row["speed_knots"] if row["speed_knots"] > 0.1 else None

        hist = get_history(limit=history_window)
        rates = [h["fuel_rate_lph"] for h in hist if h["fuel_rate_lph"] is not None]
        avg_rate = sum(rates) / len(rates) if rates else None
        fuel_range = (
            row["fuel_level_l"] / avg_rate * row["speed_knots"]
            if avg_rate and avg_rate > 0.1 and row["speed_knots"] > 0.1
            else None
        )

        return TwinSnapshot(
            lat=row["lat"],
            lon=row["lon"],
            heading_deg=row["heading_deg"],
            speed_knots=row["speed_knots"],
            rpm=row["rpm"],
            fuel_level_l=row["fuel_level_l"],
            fuel_rate_lph=row["fuel_rate_lph"],
            fuel_pct=100.0 * row["fuel_level_l"] / self.FUEL_CAPACITY_L,
            engine_temp_c=row["engine_temp_c"],
            waypoint_idx=wp_idx,
            next_waypoint=next_wp,
            distance_to_next_wp_nm=dist_nm,
            eta_next_wp_hours=eta_h,
            fuel_range_nm=fuel_range,
            avg_fuel_rate_lph=avg_rate,
            sim_time_s=row["sim_time_s"],
        )

    def track(self, limit: int = 2000):
        """Full recent history, e.g. for plotting the ship's path."""
        return get_history(limit=limit)
