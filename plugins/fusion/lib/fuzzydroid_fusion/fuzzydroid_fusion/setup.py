"""Orchestrator for the fusion setup workflow command.

Runs the 9-step flow:
  1. Detect platform (abort on Linux).
  2. Check for uv (abort with instructions if missing).
  3. Ensure the fusion plugin venv exists (one venv per plugin).
  4. Editable-install lib/fuzzydroid_fusion into the venv.
  5. Resolve Fusion AddIns directory.
  6. Symlink the add-in into AddIns.
  7. Write state file.
  8. Print manual Fusion-UI-click instructions.
  9. Offer to run doctor.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fuzzydroid_fusion import _common
from fuzzydroid_fusion import _symlink
from fuzzydroid_fusion._logbook import Logger

__all__ = [
    "SetupResult",
    "PLUGIN_NAME",
    "PLUGIN_VERSION",
    "PYTHON_VERSION",
    "fusion_addins_dir",
    "run_setup",
    "main",
]


@dataclass
class SetupResult:
    ok: bool
    message: str
    state_path: Optional[Path] = None


PLUGIN_NAME = "fusion"
PLUGIN_VERSION = "0.2.0"
PYTHON_VERSION = "3.11"


def fusion_addins_dir() -> Path:
    """Return the absolute path to Fusion 360's Add-Ins directory.

    macOS: ~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns
    Windows: %APPDATA%\\Autodesk\\Autodesk Fusion 360\\API\\AddIns
    """
    os_name = _common.detect_os()
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
            Path.home()
            / "Library"
            / "Application Support"
            / "Autodesk"
            / "Autodesk Fusion 360"
            / "API"
            / "AddIns"
        )
    raise _common.UnsupportedPlatformError(
        "Fusion 360 is not supported on Linux — no Add-Ins directory convention"
    )


def run_setup(
    plugin_root: Path,
    log: Optional[Logger] = None,
) -> SetupResult:
    """Run the full setup flow. Returns a SetupResult with ok=True on success.

    plugin_root is the directory of the plugin (CLAUDE_PLUGIN_ROOT). The bundled
    Python package is at plugin_root/lib/fuzzydroid_fusion, identical for dev and
    marketplace installs.
    """
    log = log or Logger(PLUGIN_NAME)
    plugin_root = Path(plugin_root)

    # Step 1: Detect platform
    try:
        os_name = _common.detect_os()
    except _common.UnsupportedPlatformError as e:
        msg = f"Unsupported platform: {e}"
        log.error(msg)
        return SetupResult(ok=False, message=msg)

    if os_name == "linux":
        msg = (
            "Linux is not supported in fusion v0. "
            "Please open an issue at https://github.com/inbarajaldrin/fuzzydroid/issues"
        )
        log.error(msg)
        return SetupResult(ok=False, message=msg)

    log.info(f"Platform: {os_name}")

    # Step 2: Check for uv
    if not _common.is_uv_available():
        msg = (
            "uv is not installed. Install it first:\n"
            "  macOS: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            "  Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
            "Then re-run fusion setup workflow."
        )
        log.error("uv not found")
        print(msg)
        return SetupResult(ok=False, message="uv not installed")

    log.success("uv is available")

    # Step 3: Ensure the plugin venv exists (one venv per plugin)
    venv_path = _common.plugin_venv_path(PLUGIN_NAME)
    try:
        _common.ensure_venv(venv_path, python_version=PYTHON_VERSION)
    except _common.VenvError as e:
        log.error(f"Failed to create plugin venv: {e}")
        return SetupResult(ok=False, message=str(e))
    log.success(f"Plugin venv at {venv_path}")

    # Step 4: Editable install
    package_dir = plugin_root / "lib" / "fuzzydroid_fusion"
    try:
        _common.install_editable(venv_path, package_dir)
    except _common.VenvError as e:
        log.error(f"Editable install failed: {e}")
        return SetupResult(ok=False, message=str(e))
    log.success(f"Installed {package_dir.name} editable into venv")

    # Step 5: Resolve Fusion AddIns dir
    try:
        addins_dir = fusion_addins_dir()
    except _common.UnsupportedPlatformError as e:
        log.error(str(e))
        return SetupResult(ok=False, message=str(e))

    if not addins_dir.parent.exists():
        msg = (
            f"Fusion 360 Add-Ins directory parent does not exist: {addins_dir.parent}\n"
            "Is Autodesk Fusion 360 installed? Install it first, then re-run fusion setup workflow."
        )
        log.error("Fusion 360 not detected")
        print(msg)
        return SetupResult(ok=False, message="Fusion 360 not installed")

    addins_dir.mkdir(parents=True, exist_ok=True)

    # Step 6: Symlink the add-in
    source = plugin_root / "addin" / "fusion_bridge"
    target = addins_dir / "fusion_bridge"
    try:
        backup = _symlink.create_directory_symlink(source, target)
    except (FileNotFoundError, NotADirectoryError, _symlink.SymlinkError) as e:
        log.error(f"Symlink failed: {e}")
        return SetupResult(ok=False, message=str(e))

    if backup:
        log.warning(f"Existing add-in backed up to {backup}")
    log.success(f"Linked add-in: {target} -> {source}")

    # Step 7: Write state file
    pyproject_path = package_dir / "pyproject.toml"
    state = {
        "venv_path": str(venv_path),
        "addin_symlink_path": str(target),
        "plugin_version": PLUGIN_VERSION,
        "pyproject_hash": _common.hash_file(pyproject_path),
        "install_timestamp": _common.now_iso(),
        "python_version": PYTHON_VERSION,
    }
    _common.save_state(PLUGIN_NAME, state)
    state_path = _common.state_file(PLUGIN_NAME)
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
    print("Then run fusion doctor workflow to verify everything is working.")
    print("=" * 60)

    return SetupResult(ok=True, message="Setup complete", state_path=state_path)


def main() -> int:
    """Entry point for `python -m fuzzydroid_fusion.setup`."""
    plugin_root_str = (os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT"))
    if not plugin_root_str:
        print("CLAUDE_PLUGIN_ROOT is not set - run this via fusion setup workflow, not directly.")
        return 1
    plugin_root = Path(plugin_root_str)
    result = run_setup(plugin_root=plugin_root)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
