---
description: Diagnose KiCad installation state, dependency drift, IPC, and the embedded bridge without changing them.
allowed-tools: [Bash, Read]
---

# /kicad:doctor

```bash
uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/scripts/run.py" --json doctor
```

Present the returned checks as a short table, separating install-artifact health
from IPC and native runtime availability. A closed editor is not a corrupt
installation. A native source/hash mismatch needs an editor restart; dependency
or editable-root drift needs `/kicad:setup`. Multiple live processes require an
explicit `--instance <pid>` for native calls. Report the currently tested platform
and version; do not call untested platforms qualified.
