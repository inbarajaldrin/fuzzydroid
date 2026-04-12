---
description: Open a Fusion 360 file by project and folder path.
argument-hint: --project "Project Name" --file "file_name" [--folder "Subfolder"]
allowed-tools: [Bash]
---

# /fusion:open

Open a file in Fusion 360 by project and folder path.

## Arguments

- `--project "NAME"` - project name (required)
- `--file "NAME"` - file name within the project (required)
- `--folder "PATH"` - optional folder path inside the project

## Execute

Resolve the venv python using the snippet from `/fusion:ping`, then:

```bash
VENV_PYTHON=$(python3 -c "
import tomllib, os, sys
from pathlib import Path
cfg = (Path(os.environ['APPDATA']) / 'fuzzydroid' / 'fusion.toml') if os.name == 'nt' \
      else Path.home() / '.config' / 'fuzzydroid' / 'fusion.toml'
if not cfg.exists():
    sys.exit(1)
state = tomllib.loads(cfg.read_text())
venv = Path(state['venv_path'])
print(venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
")

if [ -z "$VENV_PYTHON" ]; then
    echo "fusion plugin is not set up - run /fusion:setup first"
    exit 1
fi

"$VENV_PYTHON" -m fuzzydroid.fusion.cli --json project open $ARGUMENTS
```

## Disambiguation

If the user's request is ambiguous about which file to open, first run the cached search
to present candidates, and confirm with the user before opening:

```bash
"$VENV_PYTHON" -m fuzzydroid.fusion.cli --json project find --term "<partial name>"
```
