---
description: Scaffold a new Isaac Lab extension project - clones isaac-sim/IsaacLabExtensionTemplate at a pinned commit, follows the template's own README for renaming, and drops in omni-kit-mcp's bridge launch example fetched from its repo at invocation time (never vendored).
allowed-tools: [Bash, Read, WebFetch, AskUserQuestion]
---

# /isaaclab:new-project

Scaffold a new Isaac Lab extension project with bridge+livestream launch
support.

## Prerequisite

`~/.config/fuzzydroid/isaaclab.toml` must exist (run `/isaaclab:setup`
first). Read it — `lab_python`, `omni_kit_mcp`, and `mcp_port` feed the
launch instructions at the end.

## Flow

### 1. Ask

Ask the user for the project name and the destination directory. Never pick
a location yourself.

### 2. Clone the template at the pinned commit

The upstream template repo has **no release tags** (only `main`), so the pin
is a commit SHA. The pinned commit lives in the bundled package
(`fuzzydroid_isaaclab.TEMPLATE_PINNED_COMMIT`) so it is versioned with the
plugin — read it:

```bash
uv run --python 3.11 \
  --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaaclab" \
  python -c "import fuzzydroid_isaaclab as m; print(m.TEMPLATE_REPO); print(m.TEMPLATE_PINNED_COMMIT)"
```

```bash
git clone <TEMPLATE_REPO> <dest>
git -C <dest> checkout <TEMPLATE_PINNED_COMMIT>
```

### 3. Follow the template's OWN README

Read `<dest>/README.md` and follow its rename/setup instructions (it owns
how the extension gets renamed and installed into the Lab env — do not
improvise or substitute remembered steps). Install the extension into the
Lab env recorded in the state file, not into a doc-example venv name.

### 4. Drop in the bridge launch example — fetched at invocation time

Never vendor a copy of this file in the plugin; always take it from the
omni-kit-mcp repo so it tracks that repo's protocol:

```bash
# preferred: the checkout recorded in the state file (omni_kit_mcp)
cp <omni_kit_mcp>/examples/isaaclab_bridge_launch.py <dest>/scripts/

# if no checkout is recorded, clone fresh (repo is public):
git clone https://github.com/inbarajaldrin/omni-kit-mcp.git
# (offline? use the operator's existing local checkout path instead)
```

### 5. Print the launch shape

Show the user the canonical bridge+livestream launch from
`skills/isaaclab/references/bridge-launch.md`, with the placeholders filled
from the state file (`lab_python`, `omni_kit_mcp`, `mcp_port`) and the box's
current IP. Remind them of the guard rule: no static-TLS tunable for Lab
standalone runs.
