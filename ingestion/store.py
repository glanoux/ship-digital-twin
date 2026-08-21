"""
Ingestion / sync layer.

This is the "wire" between the physical asset (here, the simulated ship)
and its digital twin: the simulator writes telemetry ticks in, and the
twin/dashboard read the latest state and history out. In a real system
this module would be replaced by something like an MQTT subscriber, a
Kafka consumer, or a REST endpoint receiving sensor payloads -- but the
role is the same: turn raw incoming readings into a queryable time series.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "twin.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_time_s REAL NOT NULL,
    wall_time REAL NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    heading_deg REAL NOT NULL,
    speed_knots REAL NOT NULL,
    rpm REAL NOT NULL,
    fuel_level_l REAL NOT NULL,
    fuel_rate_lph REAL NOT NULL,
    engine_temp_c REAL NOT NULL,
    waypoint_idx INTEGER NOT NULL
);
"""


@contextmanager
def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db(reset: bool = False) -> None:
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    with _connect() as conn:
        conn.execute(SCHEMA)
        conn.commit()


def insert_telemetry(row: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO telemetry (
                sim_time_s, wall_time, lat, lon, heading_deg, speed_knots,
                rpm, fuel_level_l, fuel_rate_lph, engine_temp_c, waypoint_idx
            ) VALUES (:sim_time_s, :wall_time, :lat, :lon, :heading_deg, :speed_knots,
                      :rpm, :fuel_level_l, :fuel_rate_lph, :engine_temp_c, :waypoint_idx)
            """,
            row,
        )
        conn.commit()


def get_latest(n: int = 1):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (n,)
        )
        rows = [dict(r) for r in cur.fetchall()]
    return rows[::-1]  # chronological order


def get_history(limit: int = 5000):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = [dict(r) for r in cur.fetchall()]
    return rows[::-1]
