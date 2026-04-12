---
name: fusion
description: Control Autodesk Fusion 360 from Claude Code. Use this skill when the user asks to search Fusion projects, open a file in Fusion, export a design as STEP/STL/URDF/USD/F3D, list bodies or components, get the bounding box, inspect the timeline, or run Python inside Fusion's runtime. Also triggers on CAD automation, 3D model export, "open in Fusion", "export STEP", URDF export, robotics CAD, fusion2urdf, Autodesk Fusion API.
---

# Fusion 360 Automation

Drives Autodesk Fusion 360 via a TCP bridge add-in exposing the full Fusion Python API on
`localhost:8765`. All commands go through the `cli-anything-fusion` CLI, which is installed
into the shared fuzzydroid venv by `/fusion:setup`.

## Prerequisites

- `/fusion:setup` must have been run successfully.
- Fusion 360 must be running with the `fusion_bridge` add-in loaded (one-time click in
  Shift+S → Add-Ins → Run on Startup).
- Always start with `/fusion:ping` to confirm the bridge is alive before running anything else.

## Core commands

Run slash commands directly — they wrap the CLI in the shared venv. If you need to invoke
the CLI yourself from Bash, its path is stored in `~/.config/fuzzydroid/fusion.toml` under
`venv_path` (append `/bin/cli-anything-fusion`, or `\Scripts\cli-anything-fusion.exe` on
Windows).

| Command | What it does |
|---|---|
| `/fusion:ping` | Check the bridge TCP is responding. |
| `/fusion:open --project "P" --file "F"` | Open a file by project + folder path. |
| `/fusion:export step --path ./outputs/out.step` | Export the active design. Formats: `step`, `stl`, `urdf`, `usd`, `f3d`. |
| `/fusion:exec` | Pipe Python into the CLI to run code inside Fusion's runtime. |
| `/fusion:doctor` | Health check — run this if anything seems off. |

## Hard rules

1. **Always ping first** before assuming the bridge is alive. If it fails, tell the user
   to open Fusion 360 and load the `fusion_bridge` add-in via Shift+S.
2. **Never modify designs from background threads.** The bridge already marshals API calls
   to Fusion's main UI thread via CustomEvent — use the CLI, do not go around it.
3. **Save exports to `./outputs/`** in the current project, not `/tmp`, unless the user
   explicitly asks otherwise.
4. **Screenshots go through the Fusion API** (`activeViewport.saveAsImageFile`), not
   Peekaboo or macos-control. See `plugins/fusion/scripts/` for templates.
5. **If the bridge is unreachable**, the diagnostic is `/fusion:doctor` — do not try to
   restart anything manually.

## Common patterns

Open a file and list its bodies:

```bash
cli-anything-fusion --json project open --project "SO-ARM101" --file "arm_base"
cli-anything-fusion --json design bodies
```

Export the active design as STEP:

```bash
cli-anything-fusion --json export step --path ./outputs/arm_base.step
```

Run multi-line Python inside Fusion:

```bash
printf 'import adsk.core\napp = adsk.core.Application.get()\nprint(app.activeDocument.name)' \
  | cli-anything-fusion --json exec -
```

Capture a viewport screenshot, then read it:

```bash
printf 'import adsk.core
app = adsk.core.Application.get()
app.activeViewport.saveAsImageFile("/tmp/fusion_viewport.png", 1920, 1080)
print("ok")' | cli-anything-fusion --json exec -
```

Then use the Read tool on `/tmp/fusion_viewport.png`.

## Bundled scripts

`plugins/fusion/scripts/` ships runnable Python scripts:

| Script | Purpose |
|---|---|
| `search_all_projects.py` | Scan all Fusion projects and folders |
| `open_file.py` | Open a file by project/folder path |
| `export_step.py` | Export the active design as STEP |
| `export_urdf.py` | Export a robot as a full ROS2 URDF package (multi-component design) |
| `export_single_urdf.py` | Export a single-link URDF |
| `export_multi_link_urdf.py` | Export a multi-link URDF |
| `create_container_with_cap.py` | Parametric container + cap example |

Invoke a bundled script via the CLI:

```bash
printf "exec(open('plugins/fusion/scripts/export_step.py').read())" \
  | cli-anything-fusion --json exec -
```

## When things break

1. `/fusion:doctor` — the first move for any failure.
2. If doctor says "dependencies changed since last setup", re-run `/fusion:setup`.
3. If doctor says "bridge not reachable" but Fusion is open, the add-in isn't loaded —
   Shift+S → Add-Ins → click Run on `fusion_bridge` (and check Run on Startup).
4. If doctor says "addin symlink missing", Fusion may have been reinstalled; re-run
   `/fusion:setup`.
5. For anything else, file an issue at https://github.com/inbarajaldrin/fuzzydroid/issues.
