"""Resolve install facts; never store an author's machine paths in the plugin."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fuzzydroid_kicad.platform import config_dir, default_venv_path, detect_os, venv_python


def runtime_dir() -> Path:
    """Private per-user endpoint directory, shared with the embedded bridge."""
    return config_dir() / "kicad-runtime"


def state_path() -> Path:
    return config_dir() / "kicad.toml"


def cli_path(explicit: str | None = None) -> Path:
    candidate = explicit or os.getenv("KICAD_CLI") or shutil.which("kicad-cli")
    if not candidate:
        try:
            candidate = read_state().get("kicad_cli")
        except (OSError, ValueError):
            pass
    if candidate:
        path = Path(candidate).expanduser().resolve()
        if path.is_file():
            return path
        raise FileNotFoundError(f"kicad-cli not found at {path}")
    platform = detect_os()
    if platform == "macos":
        choices = [Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")]
    elif platform == "windows":
        base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "KiCad"
        choices = sorted(base.glob("*/bin/kicad-cli.exe"), reverse=True)
    else:
        choices = [Path("/usr/bin/kicad-cli")]
    for path in choices:
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError("Install KiCad, put kicad-cli on PATH, or set KICAD_CLI")


def plugin_dir(major: int) -> Path:
    platform = detect_os()
    if platform == "macos":
        base = Path.home() / "Library/Preferences/kicad"
    elif platform == "windows":
        base = Path(os.environ["APPDATA"]) / "kicad"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "kicad"
    return base / f"{major}.0/scripting/plugins"


def python_path() -> Path:
    return venv_python(default_venv_path())


def read_state() -> dict:
    import tomllib

    return tomllib.loads(state_path().read_text(encoding="utf-8"))
