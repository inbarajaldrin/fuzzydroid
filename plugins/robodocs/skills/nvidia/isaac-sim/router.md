# Isaac Sim Docs

Reliable live access to NVIDIA Isaac Sim documentation at `https://docs.isaacsim.omniverse.nvidia.com/latest/`.

## When to use this sub-skill

Trigger on: NVIDIA Isaac Sim, robotics simulation, `SimulationApp` Python boilerplate, URDF / MJCF / USD robot import, Isaac Sim sensors (RTX-based cameras, stereo, depth, IMU, contact, lidar, force sensors), Isaac Sim controllers (differential, holonomic, Franka / UR / cuRobo motion planning, Lula, RMPflow), `isaacsim.*` Python modules (`isaacsim.core`, `isaacsim.sensors.camera`, `isaacsim.sensors.physics`, `isaacsim.robot`, `isaacsim.robot.manipulators`, `isaacsim.robot.wheeled_robots`, `isaacsim.replicator` Isaac-wrapped SDG, `isaacsim.ros2.bridge`, `isaacsim.storage`), Cortex decider networks, cuMotion motion planning in Sim, Nova Carter / Nova Orin / Jetson-in-sim, **physics and collision authoring** (contactOffset / restOffset / SDF mesh / PhysX schema / `UsdPhysics` / `PhysxSchema` / articulation stability), standalone Python vs Script Editor vs Extension workflow, Isaac Sim installation (workstation / container / pip / cloud), or the NGC `nvcr.io/nvidia/isaac-sim` image. Also triggers on adjacent uses — Isaac Lab training envs are built on Isaac Sim; Isaac ROS uses Isaac Sim for sim-to-real; Replicator synthetic data runs inside Isaac Sim via the `isaacsim.replicator` wrapper.

## Why this skill exists

Isaac Sim is the NVIDIA robotics simulator — SimulationApp standalone Python, URDF/MJCF/USD robot import, RTX-accelerated sensors, controllers, and Isaac-specific wrappers around Replicator / OmniGraph / USD. The API namespace changed in 4.x → 5.x (`omni.isaac.*` → `isaacsim.*`), and many older examples online reference the old names. Training-data memory is unreliable; the live docs are the only source of truth for current APIs, boilerplate, and supported sensors.

## The retrieval rule

Pattern D — **plain HTML, WebFetch the URL directly.** The site is Sphinx-rendered and server-delivers full body content on every page. **The `.md` suffix does NOT work here** — unlike the sibling `docs.omniverse.nvidia.com`, Isaac Sim's subdomain returns 404 for `.html.md`.

| HTML URL | Fetch URL |
|---|---|
| `https://docs.isaacsim.omniverse.nvidia.com/latest/index.html` | same |
| `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_workstation.html` | same |
| `https://docs.isaacsim.omniverse.nvidia.com/latest/python_scripting/manual_standalone_python.html` | same |
| `https://docs.isaacsim.omniverse.nvidia.com/latest/reference_python_api.html` | same |

## HTML exceptions

- **`objects.inv` and `searchindex.js` exist** (200 OK) — Sphinx's intersphinx inventory. Useful for symbol-to-URL lookup but not directly readable via WebFetch. Treat as a discovery tool for the URL-construction rule.
- **Version pinning** — URLs live under `/latest/` (redirects to current), `/5.0.0/`, `/5.1.0/` (pinned), `/6.0.0/` (early preview). Default `/latest/`; pin when the user asks for specific version behavior.
- **`/py/` API pages don't exist as `.html.md`** — the Python API is embedded inline in Sphinx pages under `/latest/reference_python_api.html` and per-module sub-pages.

## Workflow

1. Classify — installation / getting-started, Python-scripting (Standalone vs Script Editor vs Extension), robot import (URDF / MJCF / USD), sensors, controllers, motion planning (cuMotion / Lula / RMPflow), synthetic data (isaacsim.replicator wrapper), ROS 2 bridge, Isaac Lab integration, digital twin, or API reference.
2. Look up in `shared/live-sources.md`. For specific Python APIs in `isaacsim.*`, start at `reference_python_api.html` and drill in.
3. `WebFetch` the HTML URL directly.
4. If the user asks about RL training — route to `isaac-lab` skill.
5. If the user asks about on-robot ROS 2 deploy — route to `isaac-ros` skill.
6. If the user asks about raw Replicator (non-robot) — route to `omniverse-replicator` skill.
7. Cite the HTML URL back.

## Reference files

- `shared/live-sources.md` — curated entry points across Installation · Quick Start · Python Scripting · Robot Simulation (robots, sensors, controllers, cuMotion) · Synthetic Data (Isaac wrapper) · ROS 2 Bridge · Isaac Lab Integration · Cortex · Digital Twin · API Reference · GUI / Tools · Assets.
- `shared/retrieval-rule.md` — Pattern D rule, verification date, version strategy.

## Common pitfalls

- **API namespace changed in 4.x → 5.x.** Old: `omni.isaac.core.*` / `omni.isaac.sensor.*`. New: `isaacsim.core.*` / `isaacsim.sensors.*`. Confirm which the user's docs/tutorials reference and translate if needed.
- **`SimulationApp` MUST be constructed before most imports.** Standalone Python scripts need `SimulationApp(CONFIG)` on the first meaningful line — then import the rest. Calling `isaacsim.core` before `SimulationApp` silently fails.
- **Standalone vs Script Editor vs Extension are three different execution contexts.** Same APIs, different import / lifecycle rules. Check `python_scripting/manual_standalone_python.html` for the right pattern.
- **Sensors come in two flavors.** RTX-based (high-fidelity, ray-traced camera / lidar) vs physics-based (contact, IMU, force). Don't conflate — check the sensor docs.
- **URDF import has known quirks.** Joint frames, mesh paths, collision approximations differ subtly from other simulators. Pull the URDF importer docs before debugging a failed import.
- **`isaacsim.replicator` ≠ `omni.replicator.core`.** The former is the Isaac-wrapped SDG (adds robot-specific writers, sensor-aware annotators); the latter is the raw Omniverse Replicator. Route accordingly.
- **ROS 2 bridge config is version-tied.** Different ROS 2 distributions (Humble, Jazzy) have different Isaac Sim setup steps. Check `ros_tutorials/` pages for the current mapping.
- **`.md` suffix does not work on this site.** Unlike `docs.omniverse.nvidia.com`, `docs.isaacsim.omniverse.nvidia.com` requires plain HTML fetches.
