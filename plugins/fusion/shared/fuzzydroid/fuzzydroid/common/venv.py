"""uv-based venv management for fuzzydroid plugins.

Wraps `uv venv` and `uv pip install -e` so that every plugin's /setup command
shares the same logic for ensuring the shared venv exists and has the plugin's
code installed editable.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from fuzzydroid.common.platform import venv_python

__all__ = [
    "VenvError",
    "is_uv_available",
    "ensure_venv",
    "install_editable",
]


class VenvError(RuntimeError):
    """Raised when venv creation or editable install fails."""


def is_uv_available() -> bool:
    """Return True if `uv` is on PATH."""
    return shutil.which("uv") is not None


def ensure_venv(venv_path: Path, python_version: str = "3.11") -> None:
    """Create the venv at `venv_path` with the given Python version if it does not already exist.

    Raises VenvError if `uv venv` fails.
    """
    venv_path = Path(venv_path)
    python_bin = venv_python(venv_path)
    if python_bin.exists():
        # Venv already present
        return

    venv_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["uv", "venv", str(venv_path), "--python", python_version],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise VenvError(
            f"uv venv failed (exit {result.returncode}): {result.stderr.strip()}"
        )


def install_editable(venv_path: Path, package_path: Path) -> None:
    """Install `package_path` into `venv_path` as an editable package via uv pip install -e.

    Raises VenvError if the install fails.
    """
    venv_path = Path(venv_path)
    package_path = Path(package_path)
    python_bin = venv_python(venv_path)

    result = subprocess.run(
        [
            "uv", "pip", "install",
            "--python", str(python_bin),
            "-e", str(package_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise VenvError(
            f"uv pip install -e failed (exit {result.returncode}): {result.stderr.strip()}"
        )
