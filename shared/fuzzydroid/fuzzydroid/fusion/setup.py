"""Orchestrator for the /fusion:setup command.

Runs the 9-step flow described in the design spec:
  1. Detect platform (abort on Linux).
  2. Check for uv (abort with instructions if missing).
  3. Ensure shared venv exists.
  4. Editable-install shared/fuzzydroid into the venv.
  5. Resolve Fusion AddIns directory.
  6. Symlink the add-in into AddIns.
  7. Write state file.
  8. Print manual Fusion-UI-click instructions.
  9. Offer to run doctor.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from fuzzydroid.common import config as fd_config
from fuzzydroid.common import platform as fd_platform
from fuzzydroid.common import symlink as fd_symlink
from fuzzydroid.common import venv as fd_venv
from fuzzydroid.common.logbook import Logger

__all__ = [
    "SetupResult",
    "PLUGIN_NAME",
    "PLUGIN_VERSION",
    "PYTHON_VERSION",
    "compute_repo_root",
    "run_setup",
    "main",
]


@dataclass
class SetupResult:
    ok: bool
    message: str
    state_path: Optional[Path] = None


PLUGIN_NAME = "fusion"
PLUGIN_VERSION = "0.1.0"
PYTHON_VERSION = "3.11"


def compute_repo_root(plugin_root: Path) -> Path:
    """Given plugins/<name>/, return the repo root (two levels up)."""
    return Path(plugin_root).parent.parent


def run_setup(
    plugin_root: Path,
    repo_root: Optional[Path] = None,
    log: Optional[Logger] = None,
) -> SetupResult:
    """Run the full setup flow. Returns a SetupResult with ok=True on success."""
    log = log or Logger(PLUGIN_NAME)
    plugin_root = Path(plugin_root)
    repo_root = Path(repo_root) if repo_root else compute_repo_root(plugin_root)

    # Step 1: Detect platform
    try:
        os_name = fd_platform.detect_os()
    except fd_platform.UnsupportedPlatformError as e:
        msg = f"Unsupported platform: {e}"
        log.error(msg)
        return SetupResult(ok=False, message=msg)

    if os_name == "linux":
        msg = (
            "Linux is not supported in fusion v0. "
            "Please open an issue at https://github.com/aldrininbaraj/fuzzydroid/issues"
        )
        log.error(msg)
        return SetupResult(ok=False, message=msg)

    log.info(f"Platform: {os_name}")

    # Step 2: Check for uv
    if not fd_venv.is_uv_available():
        msg = (
            "uv is not installed. Install it first:\n"
            "  macOS: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            "  Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
            "Then re-run /fusion:setup."
        )
        log.error("uv not found")
        print(msg)
        return SetupResult(ok=False, message="uv not installed")

    log.success("uv is available")

    # Step 3: Ensure shared venv exists
    venv_path = fd_platform.shared_venv_path()
    try:
        fd_venv.ensure_venv(venv_path, python_version=PYTHON_VERSION)
    except fd_venv.VenvError as e:
        log.error(f"Failed to create shared venv: {e}")
        return SetupResult(ok=False, message=str(e))
    log.success(f"Shared venv at {venv_path}")

    # Step 4: Editable install
    shared_package = repo_root / "shared" / "fuzzydroid"
    try:
        fd_venv.install_editable(venv_path, shared_package)
    except fd_venv.VenvError as e:
        log.error(f"Editable install failed: {e}")
        return SetupResult(ok=False, message=str(e))
    log.success(f"Installed {shared_package.name} editable into venv")

    # Step 5: Resolve Fusion AddIns dir
    try:
        addins_dir = fd_platform.fusion_addins_dir()
    except fd_platform.UnsupportedPlatformError as e:
        log.error(str(e))
        return SetupResult(ok=False, message=str(e))

    if not addins_dir.parent.exists():
        msg = (
            f"Fusion 360 Add-Ins directory parent does not exist: {addins_dir.parent}\n"
            "Is Autodesk Fusion 360 installed? Install it first, then re-run /fusion:setup."
        )
        log.error("Fusion 360 not detected")
        print(msg)
        return SetupResult(ok=False, message="Fusion 360 not installed")

    addins_dir.mkdir(parents=True, exist_ok=True)

    # Step 6: Symlink the add-in
    source = plugin_root / "addin" / "fusion_bridge"
    target = addins_dir / "fusion_bridge"
    try:
        backup = fd_symlink.create_directory_symlink(source, target)
    except (FileNotFoundError, NotADirectoryError, fd_symlink.SymlinkError) as e:
        log.error(f"Symlink failed: {e}")
        return SetupResult(ok=False, message=str(e))

    if backup:
        log.warning(f"Existing add-in backed up to {backup}")
    log.success(f"Linked add-in: {target} -> {source}")

    # Step 7: Write state file
    pyproject_path = shared_package / "pyproject.toml"
    state = {
        "venv_path": str(venv_path),
        "addin_symlink_path": str(target),
        "plugin_version": PLUGIN_VERSION,
        "pyproject_hash": fd_config.hash_pyproject(pyproject_path),
        "install_timestamp": datetime.now().isoformat(timespec="seconds"),
        "python_version": PYTHON_VERSION,
    }
    fd_config.save_state(PLUGIN_NAME, state)
    state_path = fd_platform.config_dir() / f"{PLUGIN_NAME}.toml"
    log.success(f"State file written: {state_path}")

    # Step 8: Print manual instructions
    print()
    print("=" * 60)
    print("ONE MANUAL STEP REMAINS:")
    print("=" * 60)
    print("1. Open Autodesk Fusion 360")
    print("2. Press Shift+S to open the Scripts and Add-Ins dialog")
    print("3. Click the 'Add-Ins' tab")
    print("4. Find 'fusion_bridge' in the list")
    print("5. Click 'Run' and check 'Run on Startup'")
    print()
    print("Then run /fusion:doctor to verify everything is working.")
    print("=" * 60)

    return SetupResult(ok=True, message="Setup complete", state_path=state_path)


def main() -> int:
    """Entry point for `python -m fuzzydroid.fusion.setup`."""
    import os
    plugin_root_str = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not plugin_root_str:
        print("CLAUDE_PLUGIN_ROOT is not set - run this via /fusion:setup, not directly.")
        return 1
    plugin_root = Path(plugin_root_str)
    result = run_setup(plugin_root=plugin_root)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
