# Qualification

## Automated checks

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e 'lib/fuzzydroid_kicad[dev]'
.venv/bin/ruff check .
.venv/bin/python -m pytest lib/fuzzydroid_kicad/tests -q
```

The default suite tests registry validation, dynamic catalog behavior, token
authentication, ambiguous process selection, queued cancellation, uncertain
started-write timeouts, setup idempotence, preservation of unrelated files,
archive traversal rejection, dependency drift and JSON CLI errors. Live edits
are skipped unless the target is explicitly selected.

## Live PCB test

Use a saved LED demo board containing R1, with the plugin loaded and the API
enabled. Set `FZD_KICAD_LIVE_BOARD` to its absolute path. Optionally set
`FZD_KICAD_TEST_LIBRARY` to the installed `LED_THT.pretty` directory to qualify
real library loading too. Run:

```bash
.venv/bin/python -m pytest lib/fuzzydroid_kicad/tests/test_live.py -q
```

The external test environment must have the matching stable Python bindings from
setup for KiCad 10.0.7. The test moves/restores R1, forces an IPC rollback, rejects
a wrong board path, adds/removes a real library LED, and checks the entire board
snapshot matches its starting state. It registers a temporary project tool,
executes it from the native panel and MCP, and unregisters it. It renders a fresh
live snapshot to a temporary PNG. The panel and MCP results must agree.

These are actual application tests, not mock evidence. The test intentionally
does not save probe mutations. Save the restored board and run final project DRC
after qualification if the app's modified flag changed.

## Live fabrication and Fusion handoff

Run the README handoff command with both applications connected and a fresh
output directory. The qualified LED demo passes ERC, DRC and schematic parity,
exports seven Gerber layers and six plated holes, and imports all three part
models into Fusion. The imported outline measures 35 × 25 mm; finished PCB stack
geometry measures 1.61 mm versus nominal 1.6 mm, within the recorded 0.05 mm CAD
exchange tolerance. The core alone measures 1.51 mm, so the STEP preset includes
copper, pads and solder mask. Local STEP, F3D, application previews and the
hash-linked receipt are retained. Unit tests check that failed ERC/DRC blocks
fabrication, existing exports are preserved, and multilayer boards cannot use
the two-layer preset.

## Release gates

- Live macOS KiCad 10.0.7 qualification and package installation.
- Plugin/skill manifest validation and a scan for machine-specific paths.
- Install the built wheel in a clean environment and invoke the installed CLI.
- Confirm Fusion imports/settings remain intact.
- Live Windows KiCad 10 qualification remains required before claiming a fully
  qualified cross-platform release; use a draft PR marked `needs-windows-test`.
- No complete schematic or arbitrary-GUI coverage claim.

The platform setup conventions predate Fusion's independent Python distribution.
This plugin follows the current Fusion packaging approach (`lib/<distribution>`)
to avoid shared Python namespace collisions while retaining the shared venv and
per-plugin TOML state conventions.
