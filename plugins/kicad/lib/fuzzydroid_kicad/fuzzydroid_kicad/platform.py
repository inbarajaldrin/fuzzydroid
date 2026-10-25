"""Platform paths for KiCad; kept separate from other plugins' Python packages."""

from __future__ import annotations

import os
import platform
from pathlib import Path


def detect_os() -> str:
    names = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}
    try:
        return names[platform.system()]
    except KeyError as error:
        raise RuntimeError("Unsupported platform: " + platform.system()) from error


def config_dir() -> Path:
    if detect_os() == "windows":
        if "APPDATA" not in os.environ:
            raise RuntimeError("APPDATA is not set")
        return Path(os.environ["APPDATA"]) / "fuzzydroid"
    return Path.home() / ".config/fuzzydroid"


def shared_venv_path() -> Path:
    if detect_os() == "windows":
        if "LOCALAPPDATA" not in os.environ:
            raise RuntimeError("LOCALAPPDATA is not set")
        return Path(os.environ["LOCALAPPDATA"]) / "fuzzydroid/venv"
    return Path.home() / ".local/share/fuzzydroid/venv"


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if detect_os() == "windows" else "bin/python")
