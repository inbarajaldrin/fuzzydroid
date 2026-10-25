# isaaclab setup

Set up Isaac Lab for this machine and record the result in
`~/.config/fuzzydroid/isaaclab.toml`.

## Binding principles

- **Strict delegation.** The install itself follows the LIVE official docs at
  https://isaac-sim.github.io/IsaacLab (pip installation page) — fetch them at
  execution time, follow them exactly, never work from memory. Upstream doc
  problems get fixed upstream, not compensated for here.
- **Never assume `env_isaaclab`.** That is the docs' example venv name.
  Detect what actually exists and record it.
- Isaac Lab runs on Linux (and Windows per NVIDIA's support matrix) — on
  macOS, stop with a friendly pointer: the Mac's role is the viewer
  (`/isaacsim:isaacsim (setup workflow)` macOS branch).

## Flow

### 1. Detect first

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaaclab" \
    python -m fuzzydroid_isaaclab.detect --json
```

Finds pip venvs actually containing the `isaaclab` dist and IsaacLab source
checkouts (`isaaclab.sh` + `source/isaaclab`). Use `--scan-dir <dir>` for
unusual locations. **Present the inventory, state the recommendation (newest
pip > source), and ask the user to confirm** or request a fresh install.

### 2. Fresh install (only if none exists or the user asks)

Fetch and follow the official installation docs LIVE:
https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/pip_installation.html
Ask the user pip-vs-source first; after installing, re-run detect so the new
install is discovered and classified like any other.

### 3. omni-kit-mcp checkout (for bridge launches)

Bridge+livestream launches need a local omni-kit-mcp checkout (its `exts/`
folder is passed to `--kit_args`). If one is not already on this box:

```bash
git clone https://github.com/inbarajaldrin/omni-kit-mcp.git
```

The repo is public (https://github.com/inbarajaldrin/omni-kit-mcp); if the box
is offline or already has a checkout, record that local path instead.

### 4. Record

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaaclab" \
    python -m fuzzydroid_isaaclab.setup \
    --variant <pip|source> \
    --lab-root <venv-dir|checkout-dir> \
    --lab-version <isaaclab version from detect> \
    --isaac-version <isaacsim version from detect, if present> \
    --omni-kit-mcp <checkout path from step 3>
```

The recorder validates paths, warns if the venv's `activate` carries the
static-TLS blanket guard (a hazard that breaks Lab standalone runs — see the
bridge-launch reference), and writes the state file.

### 5. Hand the user the launch shape

Read `<plugin-root>/skills/isaaclab/references/bridge-launch.md` before composing
the bridge and livestream launch. Run [doctor](doctor.md) to verify setup, then
resume the original request.
