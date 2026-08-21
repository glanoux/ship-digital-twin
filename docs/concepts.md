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
| **Consumers** | Whoever/whatever uses the twin: dashboards, alerts, optimizers, control systems. | `viz/dashboard.py` — a Streamlit dashboard. Later: a fuel-optimization module in the same `model/` layer. |

The key architectural idea: **consumers never talk to the physical asset
directly, and the twin never talks to the physical asset directly either —
everything flows through the ingestion layer.** That's what lets you swap
the simulator for a real ship later without touching the dashboard.

## Fidelity levels (how "smart" a twin is)

- **Descriptive** — mirrors current state. "Here's the ship's speed right
  now." (What `get_latest()` gives you.)
- **Predictive** — uses a model (physics-based or ML) to forecast forward.
  "At this fuel-consumption rate, you have 340 nm of range left." (What
  `ShipTwin.snapshot()` starts doing with `fuel_range_nm` / `eta_next_wp_hours`.)
  This is also where the *fuel/performance* phase of this project fits: a
  model comparing actual fuel burn against an expected baseline to flag
  hull fouling, engine degradation, or weather impact.
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

1. ~~Training/visualization twin~~ (this phase): simulate a ship, sync its
   state, visualize it live.
2. **Fuel & performance**: add a baseline "expected fuel consumption" model
   (e.g. from calm-water speed/power curves) and have the twin compare
   actual vs. expected — this is a real use case (hull fouling detection,
   route efficiency) and demonstrates the "predictive" fidelity level.
