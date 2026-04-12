"""Platform detection and cross-platform path resolution for fuzzydroid plugins.

All OS-specific path logic lives in this module. Other modules should never
call `platform.system()` directly — they should use the helpers here.
"""
from __future__ import annotations

import os
import platform as _platform
from pathlib import Path
from typing import Literal

__all__ = [
    "OS",
    "UnsupportedPlatformError",
    "detect_os",
    "shared_venv_path",
    "config_dir",
    "fusion_addins_dir",
    "venv_python",
]

OS = Literal["macos", "windows", "linux"]


class UnsupportedPlatformError(RuntimeError):
    """Raised when running on a platform fuzzydroid does not support."""


def detect_os() -> OS:
    """Return 'macos', 'windows', or 'linux'. Raises on anything else."""
    system = _platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    if system == "Linux":
        return "linux"
    raise UnsupportedPlatformError(f"Unsupported platform: {system}")


def _home() -> Path:
    """Return the current user's home directory."""
    return Path.home()


def shared_venv_path() -> Path:
    """Return the absolute path to the shared fuzzydroid venv for this user.

    macOS: ~/.local/share/fuzzydroid/venv
    Windows: %LOCALAPPDATA%\\fuzzydroid\\venv
    Linux: ~/.local/share/fuzzydroid/venv (same as macOS convention)
    """
    os_name = detect_os()
    if os_name == "windows":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            raise RuntimeError("LOCALAPPDATA environment variable is not set")
        return Path(local_appdata) / "fuzzydroid" / "venv"
    return _home() / ".local" / "share" / "fuzzydroid" / "venv"


def config_dir() -> Path:
    """Return the absolute path to the fuzzydroid config directory for this user.

    macOS: ~/.config/fuzzydroid
    Windows: %APPDATA%\\fuzzydroid
    Linux: ~/.config/fuzzydroid
    """
    os_name = detect_os()
    if os_name == "windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA environment variable is not set")
        return Path(appdata) / "fuzzydroid"
    return _home() / ".config" / "fuzzydroid"


def fusion_addins_dir() -> Path:
    """Return the absolute path to Fusion 360's Add-Ins directory.

    macOS: ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns
    Windows: %APPDATA%\\Autodesk\\Autodesk Fusion 360\\API\\AddIns
    """
    os_name = detect_os()
    if os_name == "windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA environment variable is not set")
        return (
            Path(appdata)
            / "Autodesk"
            / "Autodesk Fusion 360"
            / "API"
            / "AddIns"
        )
    if os_name == "macos":
        return (
            _home()
            / "Library"
            / "Application Support"
            / "Autodesk"
            / "Autodesk Fusion 360"
            / "API"
            / "AddIns"
        )
    raise UnsupportedPlatformError(
        "Fusion 360 is not supported on Linux — no Add-Ins directory convention"
    )


def venv_python(venv: Path) -> Path:
    """Return the path to the python binary inside a venv, per OS convention."""
    os_name = detect_os()
    if os_name == "windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"
