---
name: fusion
description: Control Autodesk Fusion 360 from natural language — search projects, open files, inspect designs, export STEP/STL/URDF/F3D, generate CAD geometry from descriptions, view URDFs in a browser, and convert a flattened STEP into a rigged ROS package. Routes user intent to the cli-anything-fusion CLI over a TCP bridge. Triggers on Fusion 360, CAD automation, parametric design, "open in Fusion", "export STEP/STL/URDF", "design a cup/bracket/enclosure", URDF export, ROS package generation, fusion2urdf, CAD-to-URDF, robot rigging, Autodesk Fusion API.
---

# Fusion 360 Automation

Drives Autodesk Fusion 360 via a TCP bridge add-in (`localhost:8765`) and a Python
CLI (`cli-anything-fusion`) installed in the shared fuzzydroid venv. **You** (the
agent) own the workflow — the user expresses intent in natural language; you route
to the right CLI command, invoke it via `Bash`, and interpret the response.

The only user-facing slash commands are `/fusion:setup` (one-time install) and
`/fusion:doctor` (health check). Everything else is agent-driven — the user can
also explicitly route an intent through this plugin by invoking the skill
directly, e.g. `/fusion:fusion <what they want to do>`.

## Prerequisites (verify once per session)

1. `~/.config/fuzzydroid/fusion.toml` exists → plugin is installed. Otherwise tell
   the user to run `/fusion:setup`.
2. Fusion 360 is running with the `fusion_bridge` add-in loaded. Verify with:
   ```bash
   ~/.local/share/fuzzydroid/venv/bin/cli-anything-fusion --json ping
   ```
   If the response is `{"status":"ok","message":"pong",...}` → green light.
   If connection refused → tell user to open Fusion (`Shift+S → Add-Ins → Run
   fusion_bridge`) or run `/fusion:doctor` for a full diagnostic.

## Hard rules (non-negotiable)

1. **Always `--json ping` before assuming the bridge is alive.** Cheap, decisive.
2. **Never call the Fusion API from a background thread.** The bridge marshals to
   the main UI thread for you — go through the CLI, not around it.
3. **Always pass `--json`** when calling the CLI as an agent. The human-readable
   mode is for terminals.
4. **Default export path is `./outputs/`** in the current working directory.
   Never `/tmp/` unless the user explicitly asks.
5. **Screenshots use the Fusion API** (`activeViewport.saveAsImageFile`) — the
   bridge is the authoritative path.
6. **For any failure mode**, the diagnostic is `/fusion:doctor`. Don't try to
   restart anything manually.

## Routing user intent to CLI calls

The CLI binary lives at `~/.local/share/fuzzydroid/venv/bin/cli-anything-fusion`.
Common intent → command mappings:

| User says | You run |
|---|---|
| "is Fusion alive / connected?" | `cli-anything-fusion --json ping` |
| "list my projects" | `cli-anything-fusion --json project list` |
| "find the SCARA arm" | `cli-anything-fusion --json project find --term "scara"` |
| "open the SCARA arm" | First `project find`, present candidates if ambiguous, then `project open --project ... --file ...` |
| "what's in this design?" | `cli-anything-fusion --json design info` |
| "list the bodies / components / timeline" | `cli-anything-fusion --json design {bodies\|components\|timeline}` |
| "what's the bounding box?" | `cli-anything-fusion --json design bbox` (reports cm) |
| "export as STEP / STL / F3D" | `cli-anything-fusion --json export {step\|stl\|f3d} --path ./outputs/<name>.<ext>` |
| "export as URDF" | `cli-anything-fusion --json export urdf --path ./outputs/<name>_urdf` (see `references/cad-to-urdf.md` for design prerequisites) |
| "convert to USD" | Two steps — export STL, then `python3 plugins/fusion/scripts/export_usd.py <stl> <usd>` |
| "screenshot the viewport" | `exec` with `app.activeViewport.saveAsImageFile(path, 1920, 1080)` |
| "run this Python in Fusion" | `printf '<code>' \| cli-anything-fusion --json exec -` |

Full command reference: `references/cli-commands.md`.

## High-leverage workflows

### View a URDF in the browser

When the user has a ROS-style URDF package (any directory with `urdf/` and
`meshes/`) and wants to see it:

```bash
python3 plugins/fusion/viewer/urdf/serve_urdf.py <pkg_dir> --port 8090
# Add --host 0.0.0.0 to expose on Tailscale / LAN
```

Auto-detects URDFs, generates an interactive viewer with joint sliders. Details:
`references/urdf-viewer.md`.

### Export a Fusion design to a complete ROS 2 URDF package

`cli-anything-fusion export urdf` wraps `scripts/export_urdf.py`. **Requires the
Fusion design to follow the script's conventions** — a `base_link` component,
clean component identifiers, Fusion joints. Full prerequisites and the underlying
formulas: `references/cad-to-urdf.md`.

### Generate parametric CAD from a description

When the user says "design a 60×60×50 mm container with a 5 mm dome cap" or
similar, follow the recipe in `references/cad-generation.md`. Summary:

1. Write a parametric script to `/tmp/f360_design.py` with a `CONFIG` dict for
   every tunable dimension.
2. Execute via `printf 'exec(open("/tmp/f360_design.py").read())' | cli-anything-fusion --json exec -`.
3. Capture a viewport screenshot and present it.
4. Iterate by editing CONFIG values; re-run.

### Rig a flattened STEP file into a URDF

When upstream CAD ships as a single STEP with no assembly tree (hundreds of
`Body1`, `Body2`, ... bodies in one component — AgileX Bunker Mini is the canonical
case), `export_urdf.py` doesn't apply directly. Follow the multi-step recipe in
`references/cad-to-urdf.md` (Flavour B): import STEP → cluster bodies by spatial
signature → export per-link STLs → merge with `trimesh` → hand-write the URDF.

### Capture a viewport screenshot

```bash
printf 'import adsk.core
app = adsk.core.Application.get()
app.activeViewport.saveAsImageFile("/tmp/fusion_viewport.png", 1920, 1080)
print("ok")' \
  | cli-anything-fusion --json exec -
```

Then `Read /tmp/fusion_viewport.png`.

## Unit conventions

The single most common source of "the export is 100× wrong" bugs:

| Source | Unit | Convert to URDF metres by |
|---|---|---|
| `body.boundingBox` from Fusion Python API | **cm** | × `0.01` |
| `body.physicalProperties.volume` | **cm³** | × `1e-6` for m³ |
| Inertia from `getXYZMomentsOfInertia()` | **kg·cm²** | × `1e-6` for kg·m² |
| **STL files exported by `exportManager`** | **mm** | × `0.001` |
| **STEP files from external suppliers** | mm (by convention) | × `0.001` |

Pick metres at every boundary and convert immediately. Do not let cm/mm/m mix
inside any computation.

## Bundled assets

| Asset | Location | Used by |
|---|---|---|
| CLI source | `shared/fuzzydroid/fuzzydroid/fusion/cli.py` | Every command |
| Bridge add-in | `addin/fusion_bridge/` | Runs inside Fusion |
| Scripts | `scripts/` (export_urdf, export_usd, search_all_projects, etc.) | Run via `exec` |
| URDF viewer | `viewer/urdf/serve_urdf.py` + `viewer/urdf/viewer/` | Browser-side rendering |
| References | `skills/fusion/references/` | What you're reading now |

## When things break

1. **Bridge unreachable** — `/fusion:doctor`. Tells you exactly which check failed.
2. **`doctor` says "addin symlink missing"** — Fusion was reinstalled. Re-run `/fusion:setup`.
3. **`doctor` says "pyproject drift"** — dependencies changed since setup. Re-run `/fusion:setup`.
4. **`doctor` says "editable install: venv bound to … but plugin_root expects …"** — the venv's editable install is pointing at an old cache directory (typically after `claude plugin marketplace remove + add` swapped the source). Re-run `/fusion:setup` to rebind the venv to the current `${CLAUDE_PLUGIN_ROOT}`.
5. **CLI says "fusion plugin is not set up"** — `/fusion:setup` was never run, or `fusion.toml` was deleted.
6. **`exec_python` returns a traceback** — read it, fix the script, re-execute. Common Fusion errors: shell compute failure (use cut-extrude fallback), feature validation (reorder operations), profile not found (sketch isn't closed).
7. **After `claude plugin marketplace remove + add` (swapping local-dev ↔ github)** — always re-run `/fusion:setup` to rebind the venv's editable install to the new cache. The pyproject hash may match across both caches (no drift reported) but the venv stays bound to the OLD physical path; a future `claude plugin prune` would silently break the CLI.
8. **Anything else** — `https://github.com/inbarajaldrin/fuzzydroid/issues`.

## References (load on demand)

- `references/cad-to-urdf.md` — The full CAD→URDF workflow including the
  `export_urdf.py` conventions, key formulas, the flattened-STEP recipe, and
  every gotcha that has bitten this skill in production.
- `references/urdf-viewer.md` — `serve_urdf.py` flags, Tailscale exposure,
  two-instance setup, `package://` resolution.
- `references/cli-commands.md` — Every CLI subcommand with example invocations.
- `references/bridge-protocol.md` — TCP wire format and the 19 bridge commands.
  Only needed when debugging at the protocol layer.
- `references/cad-generation.md` — Recipe for natural-language → parametric
  Python → Fusion design generation. Includes the geometry-technique selection
  table and shell-fallback pattern.
