# Robot Jog — drive the active design's joints from a palette / API

Interactive control panel for any RIGGED Fusion design: joint sliders, named
poses, analytic IK for UR arms (UR3e/5e/10e/16e), and gripper open/close.
Docks as a palette INSIDE Fusion and is simultaneously a normal web page and a
JSON API for agents. Lives in `plugins/fusion/jog/` (own README there).

Robot jog is the reference implementation of the palette pattern. To scaffold a
NEW panel for some other Fusion process, use `workflows/create-palette/workflow.md`.

## When to use

User says any of:
- "move the joints / jog the robot / pose the arm in Fusion"
- "open the robot control palette"
- "enter an IK point and see the robot move"
- "open/close the gripper in the assembly"
- an agent needs to set a Fusion joint pose programmatically (use the HTTP API)

## Quick usage

```bash
python3 plugins/fusion/jog/serve_jog.py             # :8093 + docked palette in Fusion
python3 plugins/fusion/jog/serve_jog.py --no-palette --browser   # browser only
```

Open a rigged design, hit **Rescan** in the panel. Stop: `lsof -ti tcp:8093 | xargs kill`.

## Agent API (same server)

```bash
curl -s http://127.0.0.1:8093/api/state                       # doc, sections, joints, FK
curl -s -X POST http://127.0.0.1:8093/api/set -H 'Content-Type: application/json' \
  -d '{"sets":[{"profile":"ur5e","id":"elbow_joint","value":45}]}'          # degrees
curl -s -X POST http://127.0.0.1:8093/api/pose    -d '{"profile":"ur5e","pose":"home"}'
curl -s -X POST http://127.0.0.1:8093/api/ik      -d '{"profile":"ur5e","xyz_mm":[-500,-133,400],"rpy_deg":[180,0,90]}'
curl -s -X POST http://127.0.0.1:8093/api/gripper -d '{"profile":"onrobot_rg2","action":"open"}'  # or close / width+width_mm
curl -s -N http://127.0.0.1:8093/api/events                   # SSE: sync after every change
```

Generic joints (no profile): `{"sets":[{"token":"<from /api/state>","kind":"revolute","value":30}]}`
(degrees for revolute, mm for slider).

## Architecture (why it's shaped this way)

- Palette = embedded Chromium pointed at `http://127.0.0.1:8093/` via
  `ui.palettes.add` — NO `adsk.fusionSendData` plumbing. All Fusion access goes
  through the fusion_bridge socket (`exec_python`, main-thread marshaled).
- Palettes are GLOBAL Fusion UI, not per-document → robot-specificity lives in
  **profiles** (`jog/profiles/*.json` bundled, `~/.config/fuzzydroid/jog_profiles/`
  user overrides). A profile matches by joint-name fragments in the active doc;
  each match renders one UI section. Assembly = arm + gripper sections, no code.
  Schema: `jog/profiles/README.md`.
- Live sync: server broadcasts SSE after every mutation + polls Fusion (~4s)
  for manual drags, so palette/browser/agent views never go stale.
- IK: closed-form UR solution in `jog/ik_ur.py` (self-test `python3 ik_ur.py`),
  poses are the flange in the DH base frame; nearest-to-current branch applied.

## Gotchas

- Fusion revolute values are radians, sliders cm — the HTTP API speaks deg/mm.
- A modal dialog / busy Fusion blocks the bridge main thread → scan times out;
  close the dialog, hit Rescan. (Bridge ping still succeeds — that's the tell.)
- Joint moves are transient until the doc is saved. Do NOT save source docs.
- Joints inside externally-referenced components are driven via
  `createForAssemblyContext` proxies — the scan handles this; don't drive natives.
