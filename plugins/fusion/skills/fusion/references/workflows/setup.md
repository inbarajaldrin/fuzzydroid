# fusion setup

Run the fuzzydroid fusion plugin one-time setup.

## What this does

1. Verifies platform (macOS or Windows only - Linux is not supported in v0).
2. Verifies `uv` is installed.
3. Creates `~/.local/share/fuzzydroid/fusion/venv` (or `%LOCALAPPDATA%\fuzzydroid\fusion\venv`) if missing.
4. Editable-installs the bundled `lib/fuzzydroid_fusion/` into the venv.
5. Symlinks `addin/fusion_bridge/` into Fusion 360's AddIns directory.
6. Writes state to `~/.config/fuzzydroid/fusion.toml`.
7. Prints the one manual Fusion UI step.
8. Runs the doctor workflow after required manual steps are complete.

## Execute

Run this via the Bash tool:

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_fusion" \
    python -m fuzzydroid_fusion.setup
```

If `uv` is not installed, the command prints install instructions and exits cleanly.
Do not try to work around this - tell the user to install `uv` and re-run.

## After it completes

Remind the user of the one manual step that cannot be automated:

1. Open Autodesk Fusion 360.
2. Press **Shift+S** to open the Scripts and Add-Ins dialog.
3. Click the **Add-Ins** tab.
4. Find `fusion_bridge` in the list.
5. Click **Run** and check **Run on Startup**.

Once the manual step is complete, read [doctor](doctor.md), verify the
whole chain, and resume the original request.
