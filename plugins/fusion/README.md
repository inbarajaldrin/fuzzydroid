# fusion

Control Autodesk Fusion 360 from Claude Code or Codex — search projects, open files,
export STEP/STL/URDF, view models, and run Python scripts inside Fusion's runtime.

Bundled inside the [fuzzydroid](https://github.com/inbarajaldrin/fuzzydroid) marketplace.

## Main skill

Use `/fusion:fusion` in Claude Code or `$fusion:fusion` in Codex, or describe
the CAD task in normal language. The agent loads the internal workflows it needs:

| Workflow | Purpose |
|---|---|
| Setup and doctor | Install the runtime and add-in; verify installation and bridge health. |
| Assembly | Mate parts from measured CAD features and verify seating. |
| Joint rigging | Rig serial arms, grippers, and chains with drivable joints. |
| CAD-to-URDF | Export and verify a ROS 2 description package. |
| Control palettes | Build docked controls with matching agent API access. |
| Animation | Render animation frames and videos inside Fusion. |
| Printable threads | Author native modeled threads and validate seating and production exports. |

## Install

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
/plugin install fusion@fuzzydroid
```

In Codex CLI:

```bash
codex plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
codex plugin add fusion@fuzzydroid
```

Start a new session and describe your task. The main skill handles setup and
diagnostics as needed. For example, “rig this gripper and export a URDF” combines
joint authoring and export within the same task.

When setup prompts for the manual application step, enable the bridge:

1. Open Fusion 360
2. Press **Shift+S** to open the Scripts and Add-Ins dialog
3. Switch to the **Add-Ins** tab
4. Select `fusion_bridge`, then click **Run** and check **Run on Startup**

The agent then runs doctor to verify state, the venv, add-in link, and live bridge.

## Requirements

- macOS or Windows 10+ (Linux not supported in v0 — Fusion 360 has no Linux build)
- [`uv`](https://docs.astral.sh/uv/) — Python package manager. Install with:
  - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Autodesk Fusion 360 installed and signed in

## Architecture

The plugin runs a Python bridge inside Fusion 360 (`fusion_bridge` add-in)
that listens on a Unix socket (macOS) or TCP 127.0.0.1:8765-8775 (Windows). Agent skills shell out to a CLI which
sends newline-delimited JSON requests to the bridge — the bridge then drives Fusion's API
in-process and returns results.

```
Claude Code / Codex ──(CLI)──▶ Bridge add-in ──▶ Fusion API
                            ◀──(JSON over UDS/TCP)──
```

State (paths, venv location, hash of `pyproject.toml`) lives in a state file
managed by the setup workflow and verified by doctor.

Skills bundle general methods, API references, and reusable tools. Keep personal
walkthroughs, model-specific scripts, CAD exports, and session records in the
user's project or reference archive.

## License

Apache-2.0 — see [fuzzydroid root LICENSE](../../LICENSE) and [NOTICES.md](../../NOTICES.md).
