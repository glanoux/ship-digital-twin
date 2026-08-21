# Ship Digital Twin

A digital twin of a ship: a virtual model kept in sync with the real (or simulated) vessel to monitor, analyze, and predict its behavior.

Built as a learning project — see [`docs/concepts.md`](docs/concepts.md) for what a digital twin actually is and how the pieces below map to that theory.

## Status

Phase 1 done: a simulated ship, synced live into a twin, visualized on a dashboard. Phase 2 (fuel & performance modeling) is next.

## Project structure

```
data/            SQLite store (twin.db) holding the telemetry time series
ingestion/       Sync layer: writes/reads telemetry (ingestion/store.py)
model/           The twin itself: state + derived estimates (model/twin.py)
simulation/      Stands in for the real ship (simulation/ship_simulator.py)
viz/             Live dashboard (viz/dashboard.py)
docs/            concepts.md — digital twin theory mapped to this code
```

## Getting started

Install dependencies:

```
pip install -r requirements.txt
```

Run the simulator (in one terminal) — this plays the role of the real ship's sensors:

```
python -m simulation.ship_simulator --reset
```

Run the dashboard (in another terminal):

```
streamlit run viz/dashboard.py
```

Then open http://localhost:8501. The ship runs a Le Havre <-> Southampton route on
accelerated time (1 real minute ≈ 1 sim hour), refueling each time it reaches a port.

## Possible components (future work)

- **Fuel & performance**: compare actual vs. expected fuel consumption to flag
  hull fouling / route inefficiency (next phase — see `docs/concepts.md`)
- **Real data source**: swap the simulator for live sensor feed (AIS, engine
  telemetry, IMU, GPS) without changing ingestion/model/viz
- **Prescriptive twin**: recommend or send speed/route adjustments back to the ship
