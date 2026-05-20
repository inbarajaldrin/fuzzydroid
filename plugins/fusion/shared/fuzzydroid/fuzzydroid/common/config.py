"""TOML state file I/O for fuzzydroid plugins.

Reads with stdlib `tomllib` (Python 3.11+). Writes with a minimal flat-table
serializer since stdlib has no TOML writer. State files are flat dicts of
string/int/bool/float values — no nested tables — which keeps the writer trivial.
Strings are emitted as TOML basic strings (double-quoted) with spec-compliant
escape sequences, so any string value (including paths with apostrophes,
embedded quotes, or newlines) round-trips correctly.
"""
from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path
from typing import Any, Optional

from fuzzydroid.common import platform as _platform

__all__ = [
    "load_state",
    "save_state",
    "hash_pyproject",
]


def _state_file(plugin_name: str) -> Path:
    return _platform.config_dir() / f"{plugin_name}.toml"


def load_state(plugin_name: str) -> Optional[dict[str, Any]]:
    """Load a plugin's state file. Returns None if the file does not exist."""
    path = _state_file(plugin_name)
    if not path.exists():
        return None
    with path.open("rb") as f:
        return tomllib.load(f)


def save_state(plugin_name: str, state: dict[str, Any]) -> None:
    """Write a plugin's state file atomically. Creates the config dir if missing."""
    path = _state_file(plugin_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for key, value in state.items():
        lines.append(f"{key} = {_toml_value(value)}")
    content = "\n".join(lines) + "\n"

    tmp = path.parent / f"{path.name}.tmp"
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _toml_value(value: Any) -> str:
    """Serialize a Python value to a TOML scalar literal.

    Strings are emitted as TOML basic strings (double-quoted) with proper escape
    sequences per the TOML 1.0 spec. This handles apostrophes, backslashes, quotes,
    and control characters correctly without the fragility of literal strings.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # TOML basic-string escape sequences per spec
        escaped = (
            value
            .replace("\\", "\\\\")  # backslash first, before other escapes
            .replace('"', '\\"')
            .replace("\b", "\\b")
            .replace("\t", "\\t")
            .replace("\n", "\\n")
            .replace("\f", "\\f")
            .replace("\r", "\\r")
        )
        return f'"{escaped}"'
    raise TypeError(f"Unsupported value type for TOML: {type(value).__name__}")


def hash_pyproject(pyproject_path: Path) -> str:
    """Return the SHA-256 hex digest of a pyproject.toml file."""
    pyproject_path = Path(pyproject_path)
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found: {pyproject_path}")
    h = hashlib.sha256()
    h.update(pyproject_path.read_bytes())
    return h.hexdigest()
