# fusion

Control Autodesk Fusion 360 from Claude Code — search projects, open files,
export STEP/STL/URDF, view models, and run Python scripts inside Fusion's runtime.

Bundled inside the [fuzzydroid](https://github.com/inbarajaldrin/fuzzydroid) marketplace.

## Skills

| Skill | Purpose |
|---|---|
| `fusion:setup` | One-time install — creates the shared venv, installs the Python code editable, symlinks the Fusion add-in, writes the state file. Idempotent. |
| `fusion:doctor` | Health check — verifies state file, venv, add-in symlink, pyproject hash drift, bridge TCP ping. |
| `fusion:ping` | Check if the Fusion 360 bridge add-in is reachable on `localhost:8765`. |
| `fusion:open` | Open a Fusion 360 file by project and folder path. |
| `fusion:export` | Export the active design as STEP, STL, URDF, USD, or F3D. |
| `fusion:exec` | Execute arbitrary Python inside Fusion 360's runtime (pipe code via stdin). |
| `fusion:design` | Generate or modify CAD geometry from natural language descriptions or reference images — writes parametric Python and iterates from visual feedback. |
| `fusion:fusion` | Top-level routing skill — auto-triggers on Fusion / CAD / URDF / STEP / STL queries. |

## Install

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
/plugin install fusion@fuzzydroid
/fusion:setup
```

Then enable the bridge add-in inside Fusion:

1. Open Fusion 360
2. Press **Shift+S** to open the Scripts and Add-Ins dialog
3. Switch to the **Add-Ins** tab
4. Select `fusion_bridge`, then click **Run** and check **Run on Startup**

Verify everything is wired up:

```
/fusion:doctor
```

You should see the state file, venv, add-in symlink, and bridge TCP ping all green.

## Requirements

- macOS or Windows 10+ (Linux not supported in v0 — Fusion 360 has no Linux build)
- [`uv`](https://docs.astral.sh/uv/) — Python package manager. Install with:
  - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Autodesk Fusion 360 installed and signed in

## Architecture

The plugin runs a Python bridge inside Fusion 360 (`fusion_bridge` add-in)
that listens on `localhost:8765`. Claude Code skills shell out to a CLI which
sends JSON-RPC requests to the bridge — the bridge then drives Fusion's API
in-process and returns results.

```
Claude Code  ──(CLI)──▶  Bridge add-in (in Fusion 360)  ──▶  Fusion API
                  ◀──(JSON-RPC over TCP)──
```

State (paths, venv location, hash of `pyproject.toml`) lives in a state file
managed by `/fusion:setup` and verified by `/fusion:doctor`.

## License

Apache-2.0 — see [fuzzydroid root LICENSE](../../LICENSE) and [NOTICES.md](../../NOTICES.md).
