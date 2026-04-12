---
description: Export the active Fusion 360 design as STEP, STL, URDF, USD, or F3D.
argument-hint: <format> [--path PATH]
allowed-tools: [Bash]
---

# /fusion:export

Export the active Fusion 360 design.

## Arguments

- `<format>` - one of `step`, `stl`, `urdf`, `usd`, `f3d` (required, first positional).
- `--path PATH` - output path. Defaults to `./outputs/<active_doc_name>.<ext>`.

## Execute

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

# Ensure default output directory exists when caller did not pass --path
mkdir -p ./outputs

"$VENV_PYTHON" -m fuzzydroid.fusion.cli --json export $ARGUMENTS
```

## Notes

- If `--path` is not provided, default to writing into `./outputs/` in the current
  working directory (not `/tmp`), per the skill's hard rules.
- For URDF exports, the output is a **directory** (a ROS2 package), not a single file -
  adjust the default path accordingly when writing `--path`.
- Supported formats are locked to `step`, `stl`, `urdf`, `usd`, `f3d`. Anything else is
  rejected by the CLI.
