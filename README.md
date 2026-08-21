# Ship Digital Twin

A digital twin of a ship: a virtual model kept in sync with the real (or simulated) vessel to monitor, analyze, and predict its behavior.

Built as a learning project — see [`docs/concepts.md`](docs/concepts.md) for what a digital twin actually is and how the pieces below map to that theory.

## Status

Phase 1 & 2 done: a simulated ship synced live into a twin, visualized on a
dashboard, with a predictive fuel-performance panel (hull fouling detection
from telemetry alone). Phase 3 in progress: a 3D Unity viewer as a second,
independent consumer of the same twin, talking to it over HTTP.

## Project structure

```
data/            SQLite store (twin.db) holding the telemetry time series
ingestion/       Sync layer: writes/reads telemetry (ingestion/store.py)
model/           The twin: state + estimates (twin.py), predictive fuel model (performance.py)
simulation/      Stands in for the real ship (simulation/ship_simulator.py)
api/             HTTP bridge onto the twin, for non-Python consumers (api/server.py)
viz/             Live dashboard (viz/dashboard.py)
unity/           3D viewer: C# scripts + setup guide (unity/README.md) -- project itself isn't checked in
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

To also drive a 3D view in Unity, additionally run the bridge API:

```
uvicorn api.server:app --port 8000
```

then follow [`unity/README.md`](unity/README.md) to set up the Unity side.

## Possible components (future work)

- **Prescriptive twin**: use `model/performance.py`'s deviation estimate to
  recommend an action (e.g. speed adjustment to hold range margin) instead of
  just reporting status — see `docs/concepts.md`
- **Real data source**: swap the simulator for live sensor feed (AIS, engine
  telemetry, IMU, GPS) without changing ingestion/model/viz
