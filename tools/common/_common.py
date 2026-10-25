"""Small vendored helpers used by setup / doctor plumbing in every fuzzydroid plugin.

CANONICAL MASTER: tools/common/_common.py at the marketplace repo root.
Each plugin vendors a byte-identical copy at plugins/<name>/lib/<pkg>/_common.py,
because a marketplace install ships only that plugin's subtree — there is no
shared install unit at runtime. `tools/check_common_sync.py` verifies the copies
match the master; edit the master first, then re-vendor.

If/when the fleet outgrows vendoring, extract this file as a published
`fuzzydroid-common` package and replace the vendored copies with
`from fuzzydroid_common import ...` imports.
"""
from __future__ import annotations

import hashlib
import os
import platform as _platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ─── platform ──────────────────────────────────────────────────────────────

class UnsupportedPlatformError(RuntimeError):
    pass


def detect_os() -> str:
    system = _platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Linux":
        return "linux"
    if system == "Windows":
        return "windows"
    raise UnsupportedPlatformError(f"Unsupported platform: {system}")


def _home() -> Path:
    return Path.home()


def config_dir() -> Path:
    os_name = detect_os()
    if os_name == "windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("APPDATA not set")
        return Path(appdata) / "fuzzydroid"
    return _home() / ".config" / "fuzzydroid"


def plugin_venv_path(plugin_name: str) -> Path:
    """One venv per plugin to keep dep sets isolated.

    Lives at ~/.local/share/fuzzydroid/<plugin>/venv (Linux/Mac) or
    %LOCALAPPDATA%\\fuzzydroid\\<plugin>\\venv (Windows).
    """
    os_name = detect_os()
    if os_name == "windows":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            raise RuntimeError("LOCALAPPDATA not set")
        return Path(local_appdata) / "fuzzydroid" / plugin_name / "venv"
    return _home() / ".local" / "share" / "fuzzydroid" / plugin_name / "venv"


def venv_python(venv: Path) -> Path:
    os_name = detect_os()
    if os_name == "windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


# ─── venv (uv-backed) ──────────────────────────────────────────────────────

class VenvError(RuntimeError):
    pass


def is_uv_available() -> bool:
    return shutil.which("uv") is not None


def ensure_venv(venv_path: Path, python_version: str = "3.11") -> None:
    venv_path = Path(venv_path)
    if venv_python(venv_path).exists():
        return
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["uv", "venv", str(venv_path), "--python", python_version],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise VenvError(f"uv venv failed: {result.stderr.strip()}")


def install_editable(venv_path: Path, package_path: Path) -> None:
    py = venv_python(venv_path)
    result = subprocess.run(
        ["uv", "pip", "install", "--python", str(py), "-e", str(package_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise VenvError(f"uv pip install -e failed: {result.stderr.strip()}")


# ─── state (TOML I/O — same shape as fusion) ───────────────────────────────

def state_file(plugin_name: str) -> Path:
    return config_dir() / f"{plugin_name}.toml"


def _toml_reader():
    """stdlib tomllib (3.11+), else tomli, else a friendly exit — never a
    bare ModuleNotFoundError traceback on an old system python."""
    try:
        import tomllib
        return tomllib
    except ImportError:
        try:
            import tomli
            return tomli
        except ImportError:
            raise SystemExit(
                "this tooling needs Python 3.11+ (tomllib). Run it via the plugin's "
                "slash commands (/setup, /doctor), which use "
                "`uv run --python 3.11` — not the system python."
            ) from None


def load_state(plugin_name: str) -> Optional[dict[str, Any]]:
    tomllib = _toml_reader()
    path = state_file(plugin_name)
    if not path.exists():
        return None
    with path.open("rb") as f:
        return tomllib.load(f)


def save_state(plugin_name: str, state: dict[str, Any]) -> None:
    path = state_file(plugin_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k} = {_toml_value(v)}" for k, v in state.items()]
    content = "\n".join(lines) + "\n"
    tmp = path.parent / f"{path.name}.tmp"
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = (value
                   .replace("\\", "\\\\")
                   .replace('"', '\\"')
                   .replace("\b", "\\b")
                   .replace("\t", "\\t")
                   .replace("\n", "\\n")
                   .replace("\f", "\\f")
                   .replace("\r", "\\r"))
        return f'"{escaped}"'
    raise TypeError(f"Unsupported TOML value type: {type(value).__name__}")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ─── version ordering ──────────────────────────────────────────────────────

def version_key(version: str) -> tuple:
    """Sortable key for dotted version strings; non-numeric parts sort low."""
    parts = []
    for piece in version.replace("-", ".").split("."):
        parts.append(int(piece) if piece.isdigit() else -1)
    return tuple(parts)
