"""Stdlib launcher for the installed plugin venv, including stdio MCP mode."""

import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib/fuzzydroid_kicad"))
from fuzzydroid_kicad.paths import state_path

try:
    state = tomllib.loads(state_path().read_text())
    if Path(state["plugin_root"]).resolve() != ROOT:
        raise RuntimeError("Installation points to another plugin checkout")
    venv = Path(state["venv_path"])
    python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.is_file():
        raise RuntimeError("The configured Python environment is missing")
except (OSError, KeyError, ValueError, RuntimeError) as error:
    print(f"KiCad plugin is not set up: {error}. Run /kicad:setup.", file=sys.stderr)
    raise SystemExit(1)

os.execv(str(python), [str(python), "-m", "fuzzydroid_kicad.cli", *sys.argv[1:]])
