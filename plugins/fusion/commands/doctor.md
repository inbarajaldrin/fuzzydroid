---
description: Health check for the fusion plugin - verifies state file, venv, add-in symlink, pyproject hash drift, and bridge TCP ping. Prints a markdown table.
allowed-tools: [Bash, Read]
---

# /fusion:doctor

Diagnose the state of the fusion plugin install.

## What this checks

| Check | Pass condition |
|---|---|
| state file | `~/.config/fuzzydroid/fusion.toml` exists and parses as valid TOML |
| venv | Python binary at the state file's `venv_path` exists |
| addin symlink | Path at the state file's `addin_symlink_path` is a live symlink |
| pyproject.toml | Current hash matches the state file's `pyproject_hash` |
| bridge TCP | `localhost:8765` responds to a ping in under 2 seconds |

## Execute

Run this via the Bash tool:

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/../../shared/fuzzydroid" \
    python -m fuzzydroid.fusion.doctor
```

Exit code `0` if all checks pass, `1` otherwise. The command always finishes in a few
seconds even when the bridge is unreachable - the TCP probe has a 2-second timeout.

## Reading the output

Read the printed markdown table carefully and act on any failing row:

- **state file missing** -> run `/fusion:setup`.
- **state file corrupt / invalid TOML** -> delete `~/.config/fuzzydroid/fusion.toml` and
  run `/fusion:setup`.
- **venv missing / python not found** -> run `/fusion:setup`.
- **addin symlink missing** -> run `/fusion:setup`. If it was working before, Fusion 360
  may have been reinstalled.
- **pyproject.toml drift** -> dependencies changed since last setup; run `/fusion:setup`
  again to refresh the editable install.
- **bridge TCP not reachable** -> open Fusion 360 and confirm the `fusion_bridge` add-in
  is loaded (Shift+S -> Add-Ins tab -> Run `fusion_bridge`).
