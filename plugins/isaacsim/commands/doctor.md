---
description: Health check for the isaacsim plugin — state-file-driven rows (components setup didn't install read N/A, never FAIL), recorded install artifacts, persistent ROS 2 bridge ext, omni.kit.mcp list_tools probe (discovery-first via the reference client), bridge bind host, isaac-ctl status, viewer app + remote-operate client on macOS. Prints a markdown table.
allowed-tools: [Bash, Read]
---

# /isaacsim:doctor

Diagnose the isaacsim plugin install on this machine.

## Execute

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaacsim" \
    python -m fuzzydroid_isaacsim.doctor
```

Exit code `0` when every recorded component is healthy, `1` otherwise. It
always finishes in seconds — the bridge probe has a 2-second timeout.

## Row semantics (important)

Rows are **driven by the state file**: a component the setup did not
install/record reads `N/A — not installed`, never ❌. A box without
isaac-ctl, without ROS, or without a viewer is a normal box. Liveness probes
(bridge port, isaac-ctl status) print ⚠️ rather than ❌ — a stopped sim is a
normal state and does not fail the check.

| row | pass condition |
|---|---|
| state file | `~/.config/fuzzydroid/isaacsim.toml` exists and parses |
| plugin venv | python exists at the recorded `venv_path` |
| pyproject drift | bundled `pyproject.toml` hash matches the recorded hash |
| install variant / isaac root / binary / venv python | the recorded artifacts still exist |
| kit user.config.json | the recorded config file still exists |
| ROS 2 bridge ext | the recorded versioned `isaacsim.ros2.bridge-<ver>` id is in the persistent enabled list |
| omni-kit-mcp checkout | the recorded `omni_kit_mcp` path still contains `exts/omni.kit.mcp` (N/A when not recorded) |
| bind host | the recorded `bind_host` (loopback vs a tailnet IP that exposes `run_python`); ⚠️ + reachability shown when bound remotely, N/A when unrecorded (localhost default) |
| bridge list_tools | a `list_tools` round-trip via omni-kit-mcp's reference client — `PYTHONPATH=<omni_kit_mcp> python -m kit_mcp.client`, **auto-discovering a lone bridge** (recorded `mcp_port` pinned only if discovery is ambiguous); ⚠️ when the sim isn't running; raw-socket fallback when `omni_kit_mcp` is unrecorded |
| isaac-ctl | recorded path exists; `isaac-ctl status` runs |
| viewer app (macOS) | recorded `Isaac Viewer.app` bundle is intact |
| operate client (macOS) | recorded `operate_client` (kit_mcp `client.py` used to drive `sim_box_host`) still exists (N/A when not set up) |

## Acting on failures

- **state file missing** → run `/isaacsim:setup`.
- **plugin venv / pyproject drift** → re-run `/isaacsim:setup` (refreshes the editable install).
- **recorded install artifacts gone** → the Isaac install moved or was removed; re-run `/isaacsim:setup` to re-detect and re-record.
- **ROS 2 bridge ext missing/drifted** → re-run the ROS step of `/isaacsim:setup`.
- **bridge list_tools ⚠️ while the sim IS running** → the bridge ext isn't registered in that Kit app's config; re-run omni-kit-mcp's `scripts/install.py` (check `--config` against the recorded `kit_config`).
