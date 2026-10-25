# Robot Jog

A browser control panel that drives the **active Fusion 360 design live** through
the `fusion_bridge` add-in: joint sliders, named poses, analytic IK for UR arms,
and gripper open/close buttons. Docks as a palette inside Fusion — the same URL
also works in any external browser.

```
Palette (embedded Chromium) ──fetch──▶ serve_jog.py ──JSON──▶ fusion_bridge (in Fusion)
        http://127.0.0.1:8093                exec_python         main-thread joint writes
```

No `adsk.fusionSendData` plumbing: the palette page is a plain web app; all
Fusion access goes through the bridge socket, marshaled to the main UI thread.

## Quick start

```bash
python3 serve_jog.py            # serves :8093 AND opens the docked palette in Fusion
python3 serve_jog.py --no-palette --browser   # external browser only
```

Open a rigged design in Fusion, hit **Rescan** in the panel.

## Architecture: one palette, many robots

Palettes are global Fusion UI — they are NOT per-document. Robot-specificity
lives in **profiles** (`profiles/*.json` bundled, `~/.config/fuzzydroid/jog_profiles/*.json`
user overrides by name). At scan time each profile is matched against the active
doc's joint names; every matching profile renders one UI section. An assembly
doc (arm + gripper) matches two profiles → two sections, no code merging.
Unmatched revolute/slider joints always get generic sliders.

See `profiles/README.md` for the schema.

## Pieces

| File | Role |
|---|---|
| `serve_jog.py` | stdlib HTTP server: UI + `/api/state`, `/api/set`, `/api/pose`, `/api/ik`, `/api/gripper`, `/api/open-palette` |
| `ui/index.html` | the palette page (vanilla JS, coalesced one-in-flight sender) |
| `bridge_client.py` | discovery-file + socket client for fusion_bridge |
| `fusion_ops.py` | the Python snippets executed inside Fusion (scan / set / open palette) |
| `ik_ur.py` | analytic FK/IK for UR3e/5e/10e/16e (self-test: `python3 ik_ur.py`) |
| `profiles/` | robot registrations |

## Conventions & gotchas

- **Units**: Fusion revolute values are radians, slider values cm. The API layer
  speaks degrees/mm; profiles map model-side angles to Fusion via
  `fusion = sign * model + offset`.
- **IK frame**: poses are the **flange in the DH base frame** (matches UR
  controller/URDF joint angles). All 8 closed-form branches are computed, each
  verified against FK, nearest-to-current applied.
- **Referenced components**: joints inside externally-linked components are
  driven via `createForAssemblyContext` proxies found by the scan.
- **Busy Fusion**: a modal dialog or long operation blocks the bridge's main
  thread — the panel shows the scan error; close the dialog and Rescan.
- The Fusion palette is created by `ui.palettes.add` pointing at this server;
  stop the server and the palette shows a connection error until restarted
  (Rescan after restarting).
