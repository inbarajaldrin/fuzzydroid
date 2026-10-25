"""Recorder for /isaaclab:setup — non-interactive by design.

The setup COMMAND owns the interactive flow (delegating the install itself to
the official live docs at https://isaac-sim.github.io/IsaacLab, running
detect.py, and asking the user to confirm). This module validates the
confirmed answers and records them in ~/.config/fuzzydroid/isaaclab.toml.

It also enforces the per-profile guard rule at record time: if the chosen
venv's activate script exports the GLIBC static-TLS tunable, that is a
recorded hazard (it breaks PhysX GPU init in Lab standalone runs) — setup
warns loudly and doctor keeps flagging it until it is removed.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from fuzzydroid_isaaclab import PLUGIN_NAME, PLUGIN_VERSION, PYTHON_VERSION
from fuzzydroid_isaaclab import _common as c

STATIC_TLS_MARKER = "optional_static_tls"


def _abs_verbatim(p: str) -> Path:
    """Absolute + normalized WITHOUT resolving symlinks. Recorded paths keep
    their given identity — a venv python's identity IS its venv path;
    resolving it to the interpreter's real file loses the venv's
    site-packages. Symlink resolution is for classification only."""
    return Path(os.path.abspath(os.path.expanduser(p)))


def activate_has_static_tls(venv: Path) -> bool:
    """True if the venv's activate script exports the static-TLS tunable —
    the exact blanket-guard mistake that produces the Lab reset() hang."""
    activate = venv / "bin" / "activate"
    try:
        return STATIC_TLS_MARKER in activate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=("pip", "source"))
    parser.add_argument("--lab-root", required=True,
                        help="venv dir (pip) or IsaacLab checkout dir (source)")
    parser.add_argument("--lab-python", help="python of the Lab venv (pip variant)")
    parser.add_argument("--lab-version", help="isaaclab dist version")
    parser.add_argument("--isaac-version", help="isaacsim dist version in the same env, if any")
    parser.add_argument("--omni-kit-mcp", help="path to the omni-kit-mcp checkout on this box (for bridge launches)")
    parser.add_argument("--mcp-port", type=int, default=9010,
                        help="OMNI_KIT_MCP_PORT for Lab runs — deliberately NOT 9009 so a "
                             "full Isaac Sim app's bridge on the same box never collides")
    args = parser.parse_args()

    os_name = c.detect_os()
    if os_name == "macos":
        raise SystemExit("Isaac Lab does not run on macOS — set up the Linux box, and use the "
                         "isaacsim plugin's macOS branch for the viewer.")

    if not c.is_uv_available():
        print("uv is not installed. Install it first:\n"
              "  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
              "Then re-run /isaaclab:setup.")
        return 1

    plugin_root = (os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT"))
    if not plugin_root:
        print("CLAUDE_PLUGIN_ROOT is not set — run this via /isaaclab:setup, not directly.")
        return 1
    package_path = Path(plugin_root) / "lib" / "fuzzydroid_isaaclab"

    # ── validate EVERYTHING first — a failed invocation must leave no side
    # effects (no venv created, no state written)
    facts: dict = {}
    lab_root = _abs_verbatim(args.lab_root)
    if not lab_root.is_dir():
        raise SystemExit(f"--lab-root does not exist: {lab_root}")
    if args.variant == "source" and not (lab_root / "isaaclab.sh").exists():
        raise SystemExit(f"{lab_root} does not look like an IsaacLab checkout (no isaaclab.sh)")
    if args.lab_python:
        lp = _abs_verbatim(args.lab_python)
        if not lp.exists():
            raise SystemExit(f"--lab-python does not exist: {lp}")
        facts["lab_python"] = str(lp)
    elif args.variant == "pip":
        default_py = c.venv_python(lab_root)
        if not default_py.exists():
            raise SystemExit(f"no python at {default_py} — pass --lab-python explicitly")
        facts["lab_python"] = str(default_py)
    if args.lab_version:
        facts["lab_version"] = args.lab_version
    if args.isaac_version:
        facts["isaac_version"] = args.isaac_version
    if args.omni_kit_mcp:
        okm = _abs_verbatim(args.omni_kit_mcp)
        if not (okm / "exts").is_dir():
            raise SystemExit(f"{okm} does not look like an omni-kit-mcp checkout (no exts/)")
        facts["omni_kit_mcp"] = str(okm)

    # ── side effects, only now
    venv_path = c.plugin_venv_path(PLUGIN_NAME)
    c.ensure_venv(venv_path, PYTHON_VERSION)
    c.install_editable(venv_path, package_path)
    print(f"plugin venv ready: {venv_path}")

    state: dict = {
        "venv_path": str(venv_path),
        "plugin_version": PLUGIN_VERSION,
        "pyproject_hash": c.hash_file(package_path / "pyproject.toml"),
        "install_timestamp": c.now_iso(),
        "python_version": PYTHON_VERSION,
        "os": os_name,
        "variant": args.variant,
        "lab_root": str(lab_root),
        "mcp_port": args.mcp_port,
        **facts,
    }

    # per-profile guard rule enforcement (record-time warning; doctor re-checks)
    if args.variant == "pip" and activate_has_static_tls(lab_root):
        print()
        print("⚠️  HAZARD: this venv's bin/activate exports the GLIBC static-TLS tunable "
              f"({STATIC_TLS_MARKER}). That blanket guard BREAKS Isaac Lab standalone runs "
              "(PhysX GPU dispatcher pthread_create fails; reset() hangs forever). "
              "Remove it from activate — guards belong in per-profile launchers "
              "(isaac-ctl full-app profile) only.")
        print()

    c.save_state(PLUGIN_NAME, state)
    print(f"state written: {c.state_file(PLUGIN_NAME)}")
    print("run /isaaclab:doctor to verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
