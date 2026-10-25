# fusion

Control Autodesk Fusion 360 from Claude Code or Codex — search projects, open files,
export STEP/STL/URDF, view models, and run Python scripts inside Fusion's runtime.

Bundled inside the [fuzzydroid](https://github.com/inbarajaldrin/fuzzydroid) marketplace.

## Skills

| Skill | Purpose |
|---|---|
| `fusion:setup` | Creates the per-plugin venv, installs the Python package, links the add-in, and records setup state. |
| `fusion:doctor` | Verifies state, venv, add-in link, dependency drift, and the live bridge endpoint. |
| `fusion:fusion` | Top-level routing skill — auto-triggers on Fusion / CAD / URDF / STEP / STL queries. |
| `fusion:assemble` | Assemble parts from measured CAD features and verify seating. |
| `fusion:rig-joints` | Rig serial arms, grippers, and chains with drivable joints. |
| `fusion:cad-to-urdf` | Export and verify a rigged design as a ROS 2 description package. |
| `fusion:create-palette` | Build a docked control panel with matching agent API access. |
| `fusion:animation` | Render animation frames and videos inside Fusion. |
| `fusion:printable-threads` | Author and validate native printable screw threads, derived seated targets, and production export gates. |

## Install

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
/plugin install fusion@fuzzydroid
/fusion:setup
```

In Codex CLI:

```bash
codex plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
codex plugin add fusion@fuzzydroid
```

Start a new session and invoke `$fusion:setup`, then `$fusion:doctor`.
After setup, describe the CAD task in normal language, or explicitly start with
`$fusion:fusion` in Codex or `/fusion:fusion` in Claude Code. The Fusion router
loads the appropriate assembly, rigging, export, threading, palette, or animation
instructions itself. You do not need to invoke each specialist skill.

For example, `$fusion:fusion rig this gripper and export a URDF` routes through
joint authoring and CAD-to-URDF export in the same task. The other listed skills
remain available as optional direct entry points.

Then enable the bridge add-in inside Fusion:

1. Open Fusion 360
2. Press **Shift+S** to open the Scripts and Add-Ins dialog
3. Switch to the **Add-Ins** tab
4. Select `fusion_bridge`, then click **Run** and check **Run on Startup**

Verify everything is wired up:

```
/fusion:doctor
```

You should see the state file, venv, add-in symlink, and bridge ping all green.

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
managed by `/fusion:setup` and verified by `/fusion:doctor`.

Skills bundle general methods, API references, and reusable tools. Keep personal
walkthroughs, model-specific scripts, CAD exports, and session records in the
user's project or reference archive.

## License

Apache-2.0 — see [fuzzydroid root LICENSE](../../LICENSE) and [NOTICES.md](../../NOTICES.md).
