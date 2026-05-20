# cli-anything-fusion — Full CLI Surface

Every subcommand the agent can invoke via `Bash`. The CLI lives in the shared
venv (`~/.local/share/fuzzydroid/venv/bin/cli-anything-fusion`) and talks to
the `fusion_bridge` add-in on `localhost:8765`.

## Global flags

| Flag | Effect |
|---|---|
| `--json` | Machine-readable JSON output. **Always pass this when an agent is calling the CLI.** |
| `--host HOST` | Override bridge TCP host (default `127.0.0.1`). |
| `--port N` | Override bridge TCP port (default `8765`). |
| `--version` | Print CLI version and exit. |

Set via env instead: `FUSION_BRIDGE_HOST`, `FUSION_BRIDGE_PORT`,
`FUSION_BRIDGE_TIMEOUT` (default 120 s).

## Connectivity

```bash
cli-anything-fusion --json ping
```

Returns `{"status": "ok", "message": "pong", "pid": <fusion_pid>}`. If the
bridge is unreachable, you get a structured error pointing at `/fusion:doctor`.

**Always ping first** when a session opens — it's the cheapest "is Fusion alive"
check.

## Project / file operations

```bash
# List all projects in the active Fusion data hub
cli-anything-fusion --json project list

# Build the local file cache (slow — minutes; do once per session)
cli-anything-fusion --json project cache

# Search the cached index (instant)
cli-anything-fusion --json project find --term "scara"

# Live search the Fusion cloud (slow — 30–60 s)
cli-anything-fusion --json project search --term "scara"

# Open a file. Required: --project, --file. Optional: --folder (repeat for nested)
cli-anything-fusion --json project open \
  --project "SO-ARM101" --file "arm_base"

cli-anything-fusion --json project open \
  --project "Default Project" --file "base3" \
  --folder "UR5" --folder "FMB"
```

When the user's request is ambiguous ("open the scara"), run `project find` first,
present candidates, and confirm before opening.

## Design inspection

```bash
cli-anything-fusion --json design info         # document name, body/component counts, units
cli-anything-fusion --json design bodies       # list all bodies, with names + body counts
cli-anything-fusion --json design components   # list component occurrences
cli-anything-fusion --json design bbox         # bounding box (min/max XYZ in cm)
cli-anything-fusion --json design timeline     # feature history
```

All return JSON; `bbox` reports cm (Fusion's internal unit) — multiply by 0.01 for
metres.

## Export

```bash
cli-anything-fusion --json export step --path ./outputs/out.step
cli-anything-fusion --json export stl  --path ./outputs/out.stl
cli-anything-fusion --json export f3d  --path ./outputs/out.f3d

cli-anything-fusion --json export urdf \
  --path ./outputs/scara_urdf \
  --pkg-name scara_description \
  --robot-name scara_arm
```

- `step` / `stl` / `f3d` are first-class bridge commands.
- `urdf` runs `plugins/fusion/scripts/export_urdf.py` inside Fusion via the bridge's
  `exec_python`. Requires the design to follow the conventions in
  `references/cad-to-urdf.md`.
- USD is a separate post-process: `cli-anything-fusion export stl` → run
  `plugins/fusion/scripts/export_usd.py <stl> <usd>` standalone.

If `--path` is omitted, output goes to `./outputs/<active_doc_name>.<ext>` — never
`/tmp/` (one of the hard rules).

## Execute Python inside Fusion

```bash
# One-liner
cli-anything-fusion --json exec --code "import adsk.core; print(adsk.core.Application.get().activeDocument.name)"

# Multi-line via stdin
printf 'import adsk.core
app = adsk.core.Application.get()
print(app.activeDocument.name)' \
  | cli-anything-fusion --json exec -

# Persistent session — variables survive between calls
cli-anything-fusion --json exec --code "x = 42" --session-id work --persistent
cli-anything-fusion --json exec --code "print(x)" --session-id work --persistent
```

Hard rules for code sent via `exec`:

1. Import `adsk.core`, `adsk.fusion`, `adsk.cam` at the top — they only exist inside
   Fusion's Python runtime.
2. Print results to stdout — the CLI captures stdout and returns it in the JSON
   response. Don't write to files unless the task explicitly says so.
3. For screenshots, use `app.activeViewport.saveAsImageFile(path, w, h)` — never
   Peekaboo or macos-control.
4. Never spawn background threads. The bridge marshals to the Fusion main UI
   thread; threading from your Python code bypasses that and crashes Fusion.

## Run a bundled script

```bash
printf "exec(open('plugins/fusion/scripts/export_step.py').read())" \
  | cli-anything-fusion --json exec -
```

Bundled scripts (in `plugins/fusion/scripts/`):

| Script | Purpose |
|---|---|
| `search_all_projects.py` | Scan all projects/folders in Fusion |
| `open_file.py` | Open a file by project/folder path |
| `export_step.py` | Export active design as STEP |
| `export_urdf.py` | Full ROS 2 URDF package export — see `references/cad-to-urdf.md` |
| `export_single_urdf.py` | Single-link URDF |
| `export_multi_link_urdf.py` | Multi-link URDF |
| `export_usd.py` | STL → USD post-processor (standalone, uses `pxr`, not Fusion API) |
| `create_container_with_cap.py` | Parametric container + cap example |

The first 6 expect to run inside Fusion's runtime (`exec(open(...).read())` via
the bridge). `export_usd.py` is standalone.

## Generic API access

For Fusion API calls the CLI doesn't wrap explicitly:

```bash
cli-anything-fusion --json api call --path "design.rootComponent.bRepBodies.count"

# Store a reference for chained calls
cli-anything-fusion --json api call \
  --path "rootComponent.sketches.add" \
  --args '["rootComponent.xYConstructionPlane"]' \
  --store-as sketch1

# Search the Fusion API docs
cli-anything-fusion --json api docs --search "ExtrudeFeatures"

# Get the online docs URL
cli-anything-fusion --json api online --class "Sketch" --member "profiles"

# Clear stored references
cli-anything-fusion --json api clear
```

## Interactive REPL (non-agent use)

```bash
cli-anything-fusion           # default behaviour with no subcommand
cli-anything-fusion repl      # explicit REPL
```

Agents should not use the REPL — every call should be a discrete one-shot for
auditability.

## Resolving the venv-bound CLI from a slash command

Slash commands (`commands/setup.md`, `commands/doctor.md`) need to find the
venv's Python at runtime. The canonical snippet:

```bash
VENV_PYTHON=$(python3 -c "
import tomllib, os, sys
from pathlib import Path
cfg = (Path(os.environ['APPDATA']) / 'fuzzydroid' / 'fusion.toml') if os.name == 'nt' \
      else Path.home() / '.config' / 'fuzzydroid' / 'fusion.toml'
if not cfg.exists():
    sys.exit(1)
state = tomllib.loads(cfg.read_text())
venv = Path(state['venv_path'])
print(venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
")

if [ -z "$VENV_PYTHON" ]; then
    echo "fusion plugin is not set up - run /fusion:setup first"
    exit 1
fi

"$VENV_PYTHON" -m fuzzydroid.fusion.cli --json <subcommand>
```

For ad-hoc invocations from the agent's Bash tool, the binary is at
`~/.local/share/fuzzydroid/venv/bin/cli-anything-fusion` (macOS) or
`%LOCALAPPDATA%\fuzzydroid\venv\Scripts\cli-anything-fusion.exe` (Windows).
The agent can use that path directly without the TOML lookup.
