---
name: fusion
description: Main entry point for Autodesk Fusion 360 work. Route natural-language requests to setup, diagnostics, CAD creation, assembly, joint rigging, printable threads, control palettes, animation, and STEP/STL/URDF export. Select and load the needed workflows automatically; users do not need to name specialist skills. Use for Fusion 360, CAD automation, parametric design, robot rigging, assembly, CAD-to-URDF, or Autodesk Fusion API work.
---

## Agent host compatibility

This skill works in Claude Code and Codex. Resolve symlinks on this file; the
plugin root is three parent directories above this `SKILL.md`. Use that absolute
root for `plugins/<plugin>/...` examples, regardless of the working directory.
When `CLAUDE_PLUGIN_ROOT` is unavailable, pass the resolved root under that name
to commands that use it. Use the host's equivalent tools for `Bash`, `Read`,
`WebFetch` and user questions. In Codex, `$plugin:skill` invokes the sibling skill
named by a `/plugin:skill` reference. Read sibling `SKILL.md` files directly when
needed; do not assume another host's slash commands exist.

# Fusion 360 Automation

Drives Autodesk Fusion 360 via a bridge add-in (Unix socket on macOS, TCP
127.0.0.1:8765-8775 on Windows; endpoint auto-discovered) and a Python
CLI (`fzd-fusion`) installed in the plugin venv. **You** (the
agent) own the workflow — the user expresses intent in natural language; you route
to the right CLI command, invoke it via `Bash`, and interpret the response.

Users can describe their goal in normal language. For explicit routing, the
entry point is `/fusion:fusion` in Claude Code or `$fusion:fusion` in Codex.
Specialist skills are optional direct entry points; the user never needs to
invoke them separately to complete a request through this router.

## Route internally and complete the request

Resolve the plugin root from this file. For the relevant workflow, read the
`SKILL.md` listed below from that root and follow it in the current task. These
are instruction files to load, not commands to hand back to the user. Use the
host's skill loader when available, or read the files with its file tools.

| User goal | Load from the plugin root |
|---|---|
| Install or repair missing setup | `skills/setup/SKILL.md` |
| Diagnose connectivity or installation health | `skills/doctor/SKILL.md` |
| Mate parts, derive frames, or verify seating | `skills/assemble/SKILL.md` |
| Author or repair drivable joints and mechanism coupling | `skills/rig-joints/SKILL.md` |
| Export rigged CAD to a ROS description or view a URDF | `skills/cad-to-urdf/SKILL.md` |
| Create modeled printable threads or verify threaded seating | `skills/printable-threads/SKILL.md` |
| Build a docked interactive control panel and agent API | `skills/create-palette/SKILL.md` |
| Render Fusion animation frames or videos | `skills/animation/SKILL.md` |

For simple searches, inspection, file opening, and ordinary exports, use the
CLI routes below. Load specialist instructions before their operations, and
combine them when the goal spans workflows. For example, "rig this gripper
and export a URDF" requires joint-authoring guidance followed by CAD-to-URDF
guidance, with verification between stages. Keep the same source model, units,
frame convention, and output destination across the workflow.

Do not stop after naming a specialist or ask the user to invoke another skill.
Ask only for missing project facts or decisions the workflow actually needs.
Apply the same internal routing to setup and diagnostics. If a requested
downstream stage needs another plugin, load its skill when available; report
the missing dependency when it is unavailable rather than inventing its tools.

## Prerequisites (verify once per session)

1. `~/.config/fuzzydroid/fusion.toml` exists → plugin is installed. Otherwise
   load `skills/setup/SKILL.md` and follow the setup workflow.
2. Fusion 360 is running with the `fusion_bridge` add-in loaded. Verify with:
   ```bash
   ~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json ping
   ```
   If the response is `{"status":"ok","message":"pong",...}` → green light.
   If connection refused → tell user to open Fusion (`Shift+S → Add-Ins → Run
   fusion_bridge`), and load `skills/doctor/SKILL.md` for a full diagnostic.

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

The CLI binary lives at `~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion`.
Common intent → command mappings:

| User says | You run |
|---|---|
| "is Fusion alive / connected?" | `fzd-fusion --json ping` |
| "list my projects" | `fzd-fusion --json project list` |
| "find the SCARA arm" | `fzd-fusion --json project find --term "scara"` |
| "open the SCARA arm" | First `project find`, present candidates if ambiguous, then `project open --project ... --file ...` |
| "what's in this design?" | `fzd-fusion --json design info` |
| "list the bodies / components / timeline" | `fzd-fusion --json design {bodies\|components\|timeline}` |
| "what's the bounding box?" | `fzd-fusion --json design bbox` (reports cm) |
| "export as STEP / STL / F3D" | `fzd-fusion --json export {step\|stl\|f3d} --path ./outputs/<name>.<ext>` |
| "export as URDF" | `fzd-fusion --json export urdf --path ./outputs/<name>_urdf` (design prerequisites + the full workflow: `/fusion:cad-to-urdf`) |
| "convert to USD" | Two steps — export STL, then `python3 plugins/fusion/scripts/export_usd.py <stl> <usd>` |
| "import an STL / OBJ mesh" | Write `/tmp/fusion_import_mesh.json` (units + meshes[file,name,xyz_m,rpy]), then exec `scripts/import_mesh.py`. Imports + places meshes with correct units; manipulate like any body. Use for RIGID parts. |
| "import a URDF / robot into Fusion" | Write `/tmp/fusion_import_urdf.json` (urdf path), then exec `scripts/import_urdf.py`. For ARTICULATED inputs (real joint tree). Mesh-only bags of parts → use import_mesh instead. |
| "screenshot the viewport" | `exec` with `app.activeViewport.saveAsImageFile(path, 1920, 1080)` |
| "run this Python in Fusion" | `printf '<code>' \| fzd-fusion --json exec -` |

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
`/fusion:cad-to-urdf` `references/urdf-viewer.md`.

### Assemble parts clean-room (feature-derived mates)

When the user wants to assemble/mate parts (gripper on robot, adapter on flange),
verify a seat/clocking, or rebuild a suspect assembly: use `/fusion:assemble` —
frames from B-Rep features + datasheet, placement by derived matrices in a fresh
live-linked doc, proof by boolean-overlap + signed point checks.

### Jog a rigged design's joints (palette inside Fusion + agent API)

When the user wants to move joints, enter an IK target, or open/close a gripper
on the ACTIVE rigged design (not an exported URDF):

```bash
python3 plugins/fusion/jog/serve_jog.py   # serves :8093 AND docks a palette in Fusion
```

Robot-specific UI comes from `jog/profiles/*.json` (UR5e + RG2 bundled; assembly
docs match multiple profiles → merged sections). Agents drive the same server via
JSON endpoints. Details: `references/robot-jog.md`.

### Export a Fusion design to a complete ROS 2 URDF package

`fzd-fusion export urdf` wraps `scripts/export_urdf.py`. **Requires the
Fusion design to follow the script's conventions** — a `base_link` component,
clean component identifiers, Fusion joints. Full prerequisites and the underlying
formulas: `/fusion:cad-to-urdf` (`references/exporter-recipe.md`).

### Generate parametric CAD from a description

When the user says "design a 60×60×50 mm container with a 5 mm dome cap" or
similar, follow the recipe in `references/cad-generation.md`. Summary:

1. Write a parametric script to `/tmp/f360_design.py` with a `CONFIG` dict for
   every tunable dimension.
2. Execute via `printf 'exec(open("/tmp/f360_design.py").read())' | fzd-fusion --json exec -`.
3. Capture a viewport screenshot and present it.
4. Iterate by editing CONFIG values; re-run.

### Rig a flattened STEP file into a URDF

When upstream CAD ships as a single STEP with no assembly tree (hundreds of
`Body1`, `Body2`, ... bodies in one component — AgileX Bunker Mini is the canonical
case), `export_urdf.py` doesn't apply directly. Follow the multi-step recipe in
`/fusion:cad-to-urdf` (`references/export-flavors.md`, Flavour B): import STEP → cluster
bodies by spatial signature → export per-link STLs → merge with `trimesh` → hand-write the URDF.

### Capture a viewport screenshot

```bash
printf 'import adsk.core
app = adsk.core.Application.get()
app.activeViewport.saveAsImageFile("/tmp/fusion_viewport.png", 1920, 1080)
print("ok")' \
  | fzd-fusion --json exec -
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
| CLI source | `lib/fuzzydroid_fusion/fuzzydroid_fusion/cli.py` | Every command |
| Bridge add-in | `addin/fusion_bridge/` | Runs inside Fusion |
| Scripts | `scripts/` (export_urdf, export_usd, import_mesh, import_urdf, search_all_projects, etc.) | Run via `exec` |
| URDF viewer | `viewer/urdf/serve_urdf.py` + `viewer/urdf/viewer/` | Browser-side rendering |
| References | `skills/fusion/references/` | What you're reading now |

## When things break

1. **Bridge unreachable** — `/fusion:doctor`. Tells you exactly which check failed.
2. **`doctor` says "addin symlink missing"** — Fusion was reinstalled. Re-run `/fusion:setup`.
3. **`doctor` says "pyproject drift"** — dependencies changed since setup. Re-run `/fusion:setup`.
4. **`doctor` says "editable install: venv bound to … but plugin_root expects …"** — the venv's editable install is pointing at an old cache directory (typically after `claude plugin marketplace remove + add` swapped the source). Re-run `/fusion:setup` to rebind the venv to the current `${CLAUDE_PLUGIN_ROOT}`.
5. **CLI says "fusion plugin is not set up"** — `/fusion:setup` was never run, or `fusion.toml` was deleted.
6. **`exec_python` returns a traceback** — read it, fix the script, re-execute. Common Fusion errors: shell compute failure (use cut-extrude fallback), feature validation (reorder operations), profile not found (sketch isn't closed).
7. **Anything else** — `https://github.com/inbarajaldrin/fuzzydroid/issues`.

## References (load on demand)

- `references/cad-to-urdf.md`, `references/urdf-viewer.md` — thin pointer stubs; the
  full CAD→URDF workflow (exporter recipe, export flavours, package split, coupling
  measurement, verification) and the browser viewer reference now live in the standalone
  `/fusion:cad-to-urdf` skill.
- `references/cli-commands.md` — Every CLI subcommand with example invocations.
- `references/bridge-protocol.md` — bridge wire format (UDS/TCP) and the 19 bridge commands.
  Only needed when debugging at the protocol layer.
- `references/cad-generation.md` — Recipe for natural-language → parametric
  Python → Fusion design generation. Includes the geometry-technique selection
  table and shell-fallback pattern.

## Related skills (route here for specialized workflows)

This plugin is multi-skill. Route to the right sibling when the task is more than a
one-shot CLI call:

- `/fusion:cad-to-urdf` — turn rigged CAD into a ROS 2 URDF description package: the
  exporter recipe, export flavours, the Robotiq-precedent package split, coupling
  measurement (boolean overlap, the 18.10 mm standoff), FK/mesh-identity verification,
  and the browser viewer.
- `/fusion:rig-joints` — author drivable joints on a CAD assembly (the Ten Laws), with
  mechanism routes for serial arms, 4-bar/parallelogram grippers, and drag chains.
  Its bundled mechanism references and script skeletons provide the reusable methods.
- `/fusion:create-palette` — scaffold an interactive control panel (docked palette +
  HTTP/JSON API) for any Fusion process; robot jog (`references/robot-jog.md`) is the
  reference implementation.
- `/fusion:animation` — render assembly-sequence / turntable / exploded videos as
  ray-traced frames from a Fusion design, stitched to MP4.
- `/fusion:printable-threads` — author modeled printable threads, reproduce a
  BOSL2-compatible fit contract, derive seated screw poses, and validate exact
  target clearance before STEP/STL export.

Cross-plugin (the USD / Isaac Sim half of the pipeline):

- `/isaacsim:urdf-to-usd` — import a URDF into Isaac Sim as a driven PhysX articulation.
- `/isaacsim:animation` — author USD scene assembly-sequence animation (distinct from
  `/fusion:animation`, which ray-traces frames inside Fusion).
- `/isaacsim:add-physics` — author Isaac Sim collision approximations for CAD parts.
- `/isaacsim:create-extension` — build an Isaac Sim tool/extension package.
