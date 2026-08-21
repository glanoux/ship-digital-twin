# Unity viewer for the ship digital twin

A 3D consumer of the same twin the Streamlit dashboard uses, talking to it
over HTTP instead of in-process Python calls. See `docs/concepts.md` for why
that split exists.

## What's here vs. what you need to create

`Scripts/*.cs` are ready to use, but there's no `.unity` project checked in —
Unity project files are version/machine-specific and not something to
hand-author outside the Editor. You create the project via Unity Hub; these
scripts just drop in.

## Setup

1. **Install Unity Hub**, sign in (free Unity Personal account — see
   `docs/concepts.md` or just unity.com), install the latest LTS Editor
   version it recommends.

2. **Start the bridge API and simulator** (from the repo root, in separate
   terminals — the simulator may already be running from earlier phases):

   ```
   python -m simulation.ship_simulator --reset
   uvicorn api.server:app --port 8000
   ```

   Check it's alive: `curl http://localhost:8000/twin/snapshot` should
   return JSON.

3. **New Project** in Unity Hub: 3D (URP) template. Name it e.g.
   `ShipDigitalTwinUnity`, save it inside this `unity/` folder (so it lives
   alongside this README) or wherever you prefer.

4. In the Unity **Project** window, create `Assets/Scripts/`, then copy the
   four files from this repo's `unity/Scripts/` into it (drag-and-drop from
   your file manager, or copy on disk — either works, Unity will import them).

5. Build the scene:
   - **Ocean**: `GameObject > 3D Object > Plane`, scale it up (e.g. `50, 1, 50`
     in the Transform), position at origin. Give it a new Material with a
     blue-ish base color (`Assets > Create > Material`, drag onto the plane).
   - **Ship**: `GameObject > 3D Object > Cube`. Scale it to something
     ship-shaped, e.g. `(2, 1, 8)`. Add the `TwinClient` component to it
     (select the cube, `Add Component > Twin Client` in the Inspector).
     Defaults (Le Havre origin, 200 m/unit) match the current route —
     no need to change them to start.
   - **Camera**: select `Main Camera`, add the `CameraFollow` component,
     drag the ship cube into its `Target` field.
   - **HUD** (optional): add an empty GameObject, add the `TwinHud`
     component, drag the ship cube (which holds `TwinClient`) into its
     `Client` field.

6. Press **Play**. The cube should glide along the Le Havre <-> Southampton
   route and turn to match heading, driven by the same telemetry the
   Streamlit dashboard shows. The `TwinHud` overlay shows live values in the
   corner if you added it.

## If it doesn't move

- Confirm `curl http://localhost:8000/twin/snapshot` returns data *before*
  pressing Play — `TwinClient` logs a warning to the Console if requests fail.
- Check the `TwinClient` component's `Api Url` field matches the port
  `uvicorn` is actually running on.
- The ship only moves once the simulator has written at least one row —
  if you just ran `--reset`, give it a couple of seconds.

## Where this could go next

- Replace the placeholder cube with an actual ship model (free assets exist
  on the Unity Asset Store) — cosmetic, doesn't change any of the twin logic.
- Color the ship or trigger a particle effect based on `fouling_pct` /
  performance status from the API, tying the 3D view back to the predictive
  layer in `model/performance.py`.
- A proper ocean shader instead of a flat plane (Unity's URP has water
  samples) — purely visual, same architecture.
