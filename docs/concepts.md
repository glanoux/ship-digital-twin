# What is a digital twin?

A digital twin is a **virtual representation of a physical thing that stays
in sync with it over time via data**, and can be queried/analyzed/simulated
without touching the real thing. Three properties separate it from "just a
dashboard" or "just a simulation":

1. **It's tied to a specific real (or intended-to-be-real) asset** — not a
   generic model, but *this* ship.
2. **It updates from live data** — the twin's state reflects the asset's
   actual condition, not a one-time snapshot.
3. **It can answer questions the raw sensors can't** — by combining current
   readings with a model of how the asset behaves, it derives things like
   remaining range, time-to-failure, or expected fuel cost.

## The four pieces, and where they live in this repo

| Concept | Role | This repo |
|---|---|---|
| **Physical asset** | The real thing being twinned. Produces raw sensor data. | `simulation/ship_simulator.py` — simulates a ship instead of using a real one, so we can build everything else without hardware. |
| **Ingestion / sync layer** | Gets raw readings from the asset into a form the twin can use. In production: MQTT, Kafka, a REST API, OPC-UA, etc. | `ingestion/store.py` — a SQLite table the simulator writes into and everything else reads from. |
| **Twin (the virtual model)** | Holds current + historical state, and *derives* things: predictions, estimates, anomaly flags. This is the part that makes it a twin and not just a data feed. | `model/twin.py` — `ShipTwin` computes fuel range, ETA, etc. from raw telemetry + simple physics assumptions. |
| **Consumers** | Whoever/whatever uses the twin: dashboards, alerts, optimizers, control systems. | `viz/dashboard.py` — a Streamlit dashboard, including the fuel-performance panel below. |

The key architectural idea: **consumers never talk to the physical asset
directly, and the twin never talks to the physical asset directly either —
everything flows through the ingestion layer.** That's what lets you swap
the simulator for a real ship later without touching the dashboard.

## Fidelity levels (how "smart" a twin is)

- **Descriptive** — mirrors current state. "Here's the ship's speed right
  now." (What `get_latest()` gives you.)
- **Predictive** — uses a model (physics-based or ML) to forecast forward, or
  to surface a hidden condition the raw sensors don't report. Two examples
  in this repo:
  - `ShipTwin.snapshot()`'s `fuel_range_nm` / `eta_next_wp_hours` — forecasts
    forward from current state.
  - `model/performance.py` — compares actual fuel burn against `BASELINE_FUEL_K`,
    the ship's as-built calm-water curve. The simulator models hull fouling as
    a slow, *unmeasured* real-world effect (`FOULING_GROWTH_PCT_PER_SIMHOUR`
    in `ship_simulator.py`) that raises actual fuel burn above the baseline
    over time. `performance.py` never reads that hidden state — it only sees
    telemetry (speed, actual fuel rate) — and still recovers the trend from
    the actual-vs-expected gap. That's the general shape of predictive
    maintenance: infer a condition nothing measures directly, from things
    that are measured. The dashboard shows both the twin's estimate and the
    simulation's ground truth side by side so you can see the inference working.
- **Prescriptive** — recommends or takes action. "Reduce speed to 14 kn to
  make port with fuel margin" or, further still, sends that command back to
  the real ship. Not implemented here, but it's the natural next step after
  predictive: a feedback loop from the twin back to the asset.

## Why simulate the ship instead of using real data?

Real ship telemetry needs hardware access, sensor protocols, and possibly
maritime data agreements. Simulating it first means you can build and test
the ingestion → twin → visualization pipeline immediately, and the
*interface* between the simulator and the ingestion layer (a dict of named
telemetry fields) is the same shape that real sensor data would arrive in.
Later, swapping in real data means replacing `ship_simulator.py`'s writer —
nothing downstream changes.

## Where this project goes next

1. ~~Training/visualization twin~~: simulate a ship, sync its state, visualize it live.
2. ~~Fuel & performance~~: baseline "expected fuel consumption" model, twin
   compares actual vs. expected to flag hull fouling — demonstrates the
   "predictive" fidelity level.
3. **Prescriptive**: use the performance model to recommend an action (e.g.
   "reduce speed to hold the same range margin given current fouling") rather
   than just reporting a status.
