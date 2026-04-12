---
description: Execute arbitrary Python inside Fusion 360's runtime. Pipe code via stdin.
allowed-tools: [Bash]
---

# /fusion:exec

Execute Python code inside Fusion 360's Python runtime. Useful for one-off inspections,
screenshots, or operations not covered by a dedicated slash command.

## Usage

Pipe the Python code to the CLI's stdin via `exec -`:

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

printf 'import adsk.core
app = adsk.core.Application.get()
print(app.activeDocument.name)' \
  | "$VENV_PYTHON" -m fuzzydroid.fusion.cli --json exec -
```

## Hard rules for code you send

1. **Import `adsk.core`, `adsk.fusion`, or `adsk.cam` at the top.** These modules are
   only available inside Fusion's runtime - the bridge marshals them in for you.
2. **Use `app.activeDocument`, not `documents.open()` from a background thread.** The
   bridge runs on a TCP worker thread and auto-marshals API calls to the main UI thread,
   but operations that must occur after a UI context switch (like opening a file) are
   already wrapped by the higher-level commands - do not reinvent them.
3. **Print results to stdout.** The CLI captures stdout and returns it in the JSON
   response. Do not write to files unless the task is explicitly "write a file".
4. **For screenshots, use `app.activeViewport.saveAsImageFile(path, w, h)`** - never
   Peekaboo or macos-control. Example:

   ```python
   import adsk.core
   app = adsk.core.Application.get()
   app.activeViewport.saveAsImageFile("/tmp/fusion_viewport.png", 1920, 1080)
   print("saved")
   ```
