"""Health check for the fusion doctor workflow command.

Verifies every component from fusion setup workflow is still healthy and prints a
markdown table. Exit 0 on all-pass, 1 otherwise.

The bridge check reuses core.bridge's endpoint resolution (env overrides,
JSON discovery file, default Unix socket, TCP port scan) with a short probe
timeout, so a hung or unreachable bridge fails fast (well under the 300s
command timeout) instead of letting the caller block.
"""
from __future__ import annotations

import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fuzzydroid_fusion import _common
from fuzzydroid_fusion._logbook import Logger
from fuzzydroid_fusion.core import bridge as _bridge

__all__ = [
    "CheckResult",
    "PLUGIN_NAME",
    "check_state_file",
    "check_venv",
    "check_addin_symlink",
    "check_pyproject_drift",
    "check_editable_install_target",
    "check_bridge_ping",
    "run_doctor",
    "main",
]

PLUGIN_NAME = "fusion"


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str


def _safe_load_state() -> tuple[Optional[dict], Optional[str]]:
    """Load state with TOMLDecodeError handling.

    Returns (state, error_message). On success: (dict, None). On missing
    file: (None, None). On corrupt file: (None, message).
    """
    try:
        state = _common.load_state(PLUGIN_NAME)
    except tomllib.TOMLDecodeError as e:
        return None, f"corrupt state file: {e}"
    return state, None


def check_state_file() -> CheckResult:
    state, err = _safe_load_state()
    if err:
        return CheckResult(name="state file", ok=False, message=err)
    if state is None:
        return CheckResult(
            name="state file",
            ok=False,
            message="not found - run fusion setup workflow",
        )
    return CheckResult(
        name="state file",
        ok=True,
        message=f"version {state.get('plugin_version', '?')}",
    )


def check_venv(state: dict) -> CheckResult:
    venv_path_str = state.get("venv_path")
    if not venv_path_str:
        return CheckResult("venv", False, "state file missing venv_path")
    venv_path = Path(venv_path_str)
    python_bin = _common.venv_python(venv_path)
    if not python_bin.exists():
        return CheckResult("venv", False, f"python not found at {python_bin}")
    return CheckResult("venv", True, str(venv_path))


def check_addin_symlink(state: dict) -> CheckResult:
    link_str = state.get("addin_symlink_path")
    if not link_str:
        return CheckResult("addin symlink", False, "state file missing addin_symlink_path")
    link = Path(link_str)
    if not link.exists():
        return CheckResult("addin symlink", False, f"missing: {link}")
    if not link.is_symlink():
        return CheckResult(
            "addin symlink",
            False,
            f"exists but is not a symlink: {link} - re-run fusion setup workflow",
        )
    return CheckResult("addin symlink", True, str(link))


def check_pyproject_drift(state: dict, pyproject_path: Path) -> CheckResult:
    stored = state.get("pyproject_hash")
    if not stored:
        return CheckResult("pyproject.toml", False, "state file missing pyproject_hash")
    if not pyproject_path.exists():
        return CheckResult(
            "pyproject.toml",
            False,
            f"plugin's pyproject.toml not found at {pyproject_path}",
        )
    current = _common.hash_file(pyproject_path)
    if current != stored:
        return CheckResult(
            "pyproject.toml",
            False,
            "dependencies changed since last setup - re-run fusion setup workflow",
        )
    return CheckResult("pyproject.toml", True, "no drift")


def check_editable_install_target(state: dict, plugin_root: Path) -> CheckResult:
    """Verify the venv's editable install of fuzzydroid-fusion points at the current plugin_root.

    Catches the stale-link bug: after `claude plugin marketplace remove + add`,
    the venv's editable install can still point at the old cache directory while
    pyproject.toml content is identical. The drift check passes but the running
    install is bound to a directory whose lifetime is no longer guaranteed
    (a future `claude plugin prune` would break the CLI).

    Reads pip's direct_url.json — the canonical record of every editable install's
    source path.
    """
    venv_path_str = state.get("venv_path")
    if not venv_path_str:
        return CheckResult("editable install", False, "state file missing venv_path")
    venv_path = Path(venv_path_str)

    site_packages_candidates = list(venv_path.glob("lib/python*/site-packages"))
    if not site_packages_candidates:
        return CheckResult(
            "editable install", False, f"no site-packages under {venv_path}"
        )
    site_packages = site_packages_candidates[0]

    dist_info_candidates = list(site_packages.glob("fuzzydroid_fusion-*.dist-info"))
    if not dist_info_candidates:
        return CheckResult(
            "editable install",
            False,
            "fuzzydroid-fusion not installed in venv - run fusion setup workflow",
        )

    direct_url = dist_info_candidates[0] / "direct_url.json"
    if not direct_url.exists():
        return CheckResult(
            "editable install",
            False,
            "no direct_url.json in dist-info - run fusion setup workflow",
        )

    try:
        data = json.loads(direct_url.read_text())
    except Exception as e:
        return CheckResult("editable install", False, f"direct_url.json unreadable: {e}")

    url = data.get("url", "")
    if not url.startswith("file://"):
        return CheckResult(
            "editable install", False, f"unsupported url scheme: {url}"
        )
    try:
        # direct_url.json percent-encodes the path (e.g. spaces as %20) —
        # decode before comparing filesystem paths.
        from urllib.parse import unquote
        target = Path(unquote(url[len("file://"):])).resolve()
        expected = (plugin_root / "lib" / "fuzzydroid_fusion").resolve()
    except OSError as e:
        return CheckResult("editable install", False, f"path resolution failed: {e}")

    if target != expected:
        return CheckResult(
            "editable install",
            False,
            f"venv bound to {target} but plugin_root expects {expected} - run fusion setup workflow",
        )
    return CheckResult("editable install", True, "bound to current plugin cache")


def check_bridge_ping() -> CheckResult:
    """Probe for a live bridge endpoint with short-timeout verification pings.

    Resolution (env overrides -> discovery file -> default socket -> TCP scan)
    and verification both live in core.bridge, so doctor reports exactly what
    the CLI would use.
    """
    endpoint = _bridge.resolve_endpoint()
    if endpoint is None:
        return CheckResult(
            "bridge",
            False,
            "no live endpoint (checked discovery file, default socket, TCP "
            "8765-8775) - is Fusion running with the bridge loaded?",
        )
    return CheckResult(
        "bridge",
        True,
        f"responding at {_bridge.describe_endpoint(endpoint)}",
    )


def run_doctor(plugin_root: Optional[Path] = None) -> int:
    """Run all checks, print a markdown table, return exit code.

    plugin_root is the directory of the plugin (CLAUDE_PLUGIN_ROOT). The bundled
    pyproject.toml lives at plugin_root/lib/fuzzydroid_fusion/pyproject.toml.
    """
    log = Logger(PLUGIN_NAME)

    state_check = check_state_file()
    checks = [state_check]

    state, _ = _safe_load_state()
    state = state or {}

    if state_check.ok:
        checks.append(check_venv(state))
        checks.append(check_addin_symlink(state))
        if plugin_root:
            pyproject = plugin_root / "lib" / "fuzzydroid_fusion" / "pyproject.toml"
            checks.append(check_pyproject_drift(state, pyproject))
            checks.append(check_editable_install_target(state, plugin_root))
        checks.append(check_bridge_ping())

    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for c in checks:
        icon = "✅" if c.ok else "❌"
        print(f"| {c.name} | {icon} | {c.message} |")

    all_ok = all(c.ok for c in checks)
    if not all_ok:
        log.error("One or more checks failed")
    return 0 if all_ok else 1


def main() -> int:
    import os
    plugin_root_str = (os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT"))
    plugin_root = Path(plugin_root_str) if plugin_root_str else None
    return run_doctor(plugin_root=plugin_root)


if __name__ == "__main__":
    sys.exit(main())
