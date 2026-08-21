"""
Stands in for the real ship. In a production digital twin this file would
not exist -- its job (producing timestamped sensor readings) would be done
by actual hardware: GPS, engine ECU, fuel flow meter, etc. Everything
downstream (ingestion, twin, dashboard) can't tell the difference between
this simulator and a real vessel, which is the point: the twin is built
against a data contract, not against "real vs. simulated".

Model: way-point navigation across a fixed route, first-order inertia on
speed/heading, a cubic speed->fuel-consumption curve (roughly physical --
power required scales with speed^3 for a displacement hull), and Gaussian
sensor noise. Time is accelerated (TIME_ACCEL_S) so a voyage that would
take hours plays out in minutes on the dashboard.
"""

import argparse
import math
import time

import numpy as np

from ingestion.store import init_db, insert_telemetry, get_latest

# --- Route: Le Havre -> off Le Havre -> off Isle of Wight -> Southampton ---
WAYPOINTS = [
    (49.4938, 0.1077),    # Le Havre (port, refuels here)
    (49.6800, -0.4000),
    (50.5500, -1.1000),
    (50.9097, -1.4044),   # Southampton (port, refuels here)
]
PORT_INDICES = {0, len(WAYPOINTS) - 1}

CRUISE_SPEED_KN = 18.0
MAX_TURN_RATE_DEG_PER_SIMHOUR = 900.0   # how fast heading can change
SPEED_INERTIA_PER_SIMHOUR = 6.0         # how fast speed approaches target
WAYPOINT_ARRIVAL_NM = 1.0

FUEL_CAPACITY_L = 20_000.0
FUEL_K = 0.55  # fuel_rate_lph = FUEL_K * speed_knots^3

TIME_ACCEL_S = 60.0  # sim-seconds simulated per real second (1 real min = 1 sim hour)


def haversine_nm(lat1, lon1, lat2, lon2):
    r_nm = 3440.065
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r_nm * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlmb = math.radians(lon2 - lon1)
    x = math.sin(dlmb) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlmb)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def move_nm(lat, lon, heading_deg, dist_nm):
    dlat = (dist_nm / 60.0) * math.cos(math.radians(heading_deg))
    dlon = (dist_nm / 60.0) * math.sin(math.radians(heading_deg)) / math.cos(math.radians(lat))
    return lat + dlat, lon + dlon


def angle_diff(target, current):
    d = (target - current + 180) % 360 - 180
    return d


class ShipState:
    def __init__(self):
        self.lat, self.lon = WAYPOINTS[0]
        self.heading = bearing_deg(*WAYPOINTS[0], *WAYPOINTS[1])
        self.speed = 0.0
        self.rpm = 0.0
        self.fuel_level = FUEL_CAPACITY_L
        self.engine_temp = 20.0
        self.waypoint_idx = 0
        self.direction = 1  # ping-pong through WAYPOINTS
        self.sim_time_s = 0.0

    def target_waypoint(self):
        return WAYPOINTS[self.waypoint_idx + self.direction]

    def step(self, dt_sim_s: float, rng: np.random.Generator):
        dt_h = dt_sim_s / 3600.0
        self.sim_time_s += dt_sim_s

        tgt_lat, tgt_lon = self.target_waypoint()
        dist_to_wp = haversine_nm(self.lat, self.lon, tgt_lat, tgt_lon)

        if dist_to_wp < WAYPOINT_ARRIVAL_NM:
            self.waypoint_idx += self.direction
            if self.waypoint_idx in PORT_INDICES:
                self.fuel_level = FUEL_CAPACITY_L  # refuel in port
            if self.waypoint_idx == 0 or self.waypoint_idx == len(WAYPOINTS) - 1:
                self.direction *= -1
            tgt_lat, tgt_lon = self.target_waypoint()

        target_heading = bearing_deg(self.lat, self.lon, tgt_lat, tgt_lon)
        max_turn = MAX_TURN_RATE_DEG_PER_SIMHOUR * dt_h
        turn = np.clip(angle_diff(target_heading, self.heading), -max_turn, max_turn)
        self.heading = (self.heading + turn) % 360

        turn_severity = min(abs(turn) / max(max_turn, 1e-6), 1.0)
        target_speed = CRUISE_SPEED_KN * (1.0 - 0.5 * turn_severity)
        speed_step = SPEED_INERTIA_PER_SIMHOUR * dt_h
        self.speed += np.clip(target_speed - self.speed, -speed_step, speed_step)
        self.speed = max(self.speed, 0.0)

        dist_travelled = self.speed * dt_h
        self.lat, self.lon = move_nm(self.lat, self.lon, self.heading, dist_travelled)

        base_rpm = 90.0 * self.speed + 20.0
        self.rpm = max(0.0, base_rpm + rng.normal(0, 15))

        fuel_rate = FUEL_K * (self.speed ** 3) + rng.normal(0, 3)
        fuel_rate = max(fuel_rate, 0.0)
        self.fuel_level = max(0.0, self.fuel_level - fuel_rate * dt_h)

        target_temp = 80.0 + 0.3 * self.speed
        self.engine_temp += (target_temp - self.engine_temp) * min(1.0, 2.0 * dt_h) + rng.normal(0, 0.5)

        return {
            "sim_time_s": self.sim_time_s,
            "wall_time": time.time(),
            "lat": self.lat + rng.normal(0, 0.0003),
            "lon": self.lon + rng.normal(0, 0.0003),
            "heading_deg": self.heading,
            "speed_knots": self.speed,
            "rpm": self.rpm,
            "fuel_level_l": self.fuel_level,
            "fuel_rate_lph": fuel_rate,
            "engine_temp_c": self.engine_temp,
            "waypoint_idx": self.waypoint_idx,
        }


def run(hz: float, reset: bool, duration_s: float | None, seed: int | None):
    init_db(reset=reset)
    rng = np.random.default_rng(seed)
    ship = ShipState()

    if not reset:
        latest = get_latest(1)
        if latest:
            row = latest[0]
            ship.lat, ship.lon = row["lat"], row["lon"]
            ship.heading = row["heading_deg"]
            ship.speed = row["speed_knots"]
            ship.fuel_level = row["fuel_level_l"]
            ship.engine_temp = row["engine_temp_c"]
            ship.waypoint_idx = row["waypoint_idx"]
            ship.sim_time_s = row["sim_time_s"]

    tick_period = 1.0 / hz
    started = time.time()
    print(f"Simulator running: {hz} tick/s, {TIME_ACCEL_S}x time acceleration. Ctrl-C to stop.")
    try:
        while True:
            row = ship.step(TIME_ACCEL_S * tick_period, rng)
            insert_telemetry(row)
            if duration_s is not None and time.time() - started >= duration_s:
                break
            time.sleep(tick_period)
    except KeyboardInterrupt:
        print("Simulator stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ship telemetry simulator")
    parser.add_argument("--hz", type=float, default=1.0, help="Ticks per second")
    parser.add_argument("--reset", action="store_true", help="Reset the DB before starting")
    parser.add_argument("--duration", type=float, default=None, help="Stop after N real seconds")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    run(hz=args.hz, reset=args.reset, duration_s=args.duration, seed=args.seed)
