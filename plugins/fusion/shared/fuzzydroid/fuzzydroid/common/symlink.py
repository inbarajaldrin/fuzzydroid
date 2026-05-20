"""Cross-platform directory symlink / junction helper.

On macOS / Linux: uses `os.symlink` directly.
On Windows: uses `mklink /J` to create a directory junction (no admin required).

If the target path already exists as a real directory (not a symlink or junction),
it is backed up to `<target>.bak-<timestamp>` before the symlink is created.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from fuzzydroid.common.platform import detect_os

__all__ = [
    "SymlinkError",
    "create_directory_symlink",
]


class SymlinkError(RuntimeError):
    """Raised when symlink / junction creation fails."""


def create_directory_symlink(source: Path, target: Path) -> Optional[Path]:
    """Create `target` as a symlink (or junction on Windows) pointing at `source`.

    If `target` already exists as a real directory, it is renamed to
    `<target>.bak-<YYYYMMDD-HHMMSS>` before the symlink is created. The backup
    path is returned so callers can report it or offer recovery.

    Recovery: if a crash occurs between the backup rename and the symlink
    creation, the original directory is intact under the backup name. Rename
    it back manually or re-run setup.

    Returns the backup path if an existing non-symlink target was backed up,
    otherwise None.

    Raises:
        FileNotFoundError: if `source` does not exist
        NotADirectoryError: if `source` is not a directory
        SymlinkError: if creation fails or the post-creation check fails
    """
    source = Path(source)
    target = Path(target)

    if not source.exists():
        raise FileNotFoundError(f"Source does not exist: {source}")
    if not source.is_dir():
        raise NotADirectoryError(f"Source is not a directory: {source}")

    backup: Optional[Path] = None

    # Use os.path.lexists so we detect symlinks (even broken ones) without
    # following them, and without touching Path.exists (which tests may patch).
    target_str = os.fspath(target)
    if os.path.lexists(target_str):
        if os.path.islink(target_str):
            # Existing symlink/junction — safe to remove and replace
            os.unlink(target_str)
        else:
            # Real directory — back it up
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = target.with_name(f"{target.name}.bak-{timestamp}")
            target.rename(backup)

    target.parent.mkdir(parents=True, exist_ok=True)

    os_name = detect_os()
    if os_name == "windows":
        _create_windows_junction(source, target)
    else:
        # target_is_directory is a no-op on POSIX; kept for clarity
        os.symlink(source, target, target_is_directory=True)

    if not (target.exists() and target.is_symlink()):
        raise SymlinkError(
            f"Symlink creation appeared to succeed but target is not a symlink: {target}"
        )

    return backup


def _create_windows_junction(source: Path, target: Path) -> None:
    """Invoke `mklink /J <target> <source>` on Windows (no admin needed)."""
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(target), str(source)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SymlinkError(
            f"mklink /J failed (exit {result.returncode}): {result.stderr.strip()}"
        )
