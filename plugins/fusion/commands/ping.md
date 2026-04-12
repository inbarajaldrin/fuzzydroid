---
description: Check if the Fusion 360 bridge add-in is reachable on localhost:8765.
allowed-tools: [Bash]
---

# /fusion:ping

Quick connectivity check for the fuzzydroid fusion bridge.

## Execute

```bash
VENV_PYTHON=$(python3 -c "
import tomllib, os, sys
from pathlib import Path

if os.name == 'nt':
    cfg = Path(os.environ['APPDATA']) / 'fuzzydroid' / 'fusion.toml'
else:
    cfg = Path.home() / '.config' / 'fuzzydroid' / 'fusion.toml'

if not cfg.exists():
    sys.exit(1)

state = tomllib.loads(cfg.read_text())
venv = Path(state['venv_path'])
py = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
print(py)
")

if [ -z "$VENV_PYTHON" ]; then
    echo "fusion plugin is not set up - run /fusion:setup first"
    exit 1
fi

"$VENV_PYTHON" -m fuzzydroid.fusion.cli --json ping
```

## Expected output

JSON like `{"status":"ok","message":"pong"}`.

If the command errors with connection refused, Fusion 360 isn't running or the
`fusion_bridge` add-in isn't loaded. Tell the user and point them at `/fusion:doctor`
for a full diagnostic.
