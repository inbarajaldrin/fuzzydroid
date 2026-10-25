"""Recorder for /isaacsim:setup — non-interactive by design.

The setup COMMAND (commands/setup.md) owns the interactive flow: it delegates
the install itself to live upstream docs (NVIDIA / isaac-viewer-macos /
omni-kit-mcp), runs detect.py, presents the inventory, and asks the user the
ask-once questions. This module is the final, idempotent step: it validates
the confirmed answers, optionally performs the persistent ROS bridge enable,
and records EVERYTHING in ~/.config/fuzzydroid/isaacsim.toml.

ROS env values fall in exactly three classes (spec section D):
  1. auto-detect, silent      → ROS_DISTRO (from /opt/ros, else Ubuntu-release
                                map); lib paths are DERIVED at runtime from
                                recorded facts, never stored as literals
  2. ask-once-with-defaults   → RMW_IMPLEMENTATION (rmw_cyclonedds_cpp),
                                ROS_DOMAIN_ID (0), ROS_LOCALHOST_ONLY (1) —
                                the command asks, this module records
  3. computed                 → everything else; never asked, never stored

No personal paths, box names, or site facts appear in plugin code — machine
facts live only in the state file this module writes.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from fuzzydroid_isaacsim import PLUGIN_NAME, PLUGIN_VERSION, PYTHON_VERSION
from fuzzydroid_isaacsim import _common as c
from fuzzydroid_isaacsim import ros_bridge

VARIANTS = ("pip-standalone", "pip-lab", "binary", "source", "viewer")

# Ubuntu LTS → ROS 2 distro map, used only when /opt/ros is empty.
_UBUNTU_ROS_MAP = {"22.04": "humble", "24.04": "jazzy"}
# newest-first preference when several distros are installed
_ROS_DISTRO_ORDER = ("rolling", "kilted", "jazzy", "iron", "humble")


def autodetect_ros_distro() -> Optional[str]:
    """Class-1 value: /opt/ros presence wins; else the Ubuntu-release map."""
    opt_ros = Path("/opt/ros")
    if opt_ros.is_dir():
        present = {d.name for d in opt_ros.iterdir() if d.is_dir()}
        for distro in _ROS_DISTRO_ORDER:
            if distro in present:
                return distro
        if present:
            return sorted(present)[-1]
    try:
        os_release = Path("/etc/os-release").read_text(encoding="utf-8")
    except OSError:
        return None
    version_id = None
    for line in os_release.splitlines():
        if line.startswith("VERSION_ID="):
            version_id = line.split("=", 1)[1].strip().strip('"')
    return _UBUNTU_ROS_MAP.get(version_id or "")


def _abs_verbatim(p: str) -> Path:
    """Absolute + normalized WITHOUT resolving symlinks. Recorded paths keep
    their given identity — a venv python's identity IS its venv path;
    resolving it to the interpreter's real file loses the venv's
    site-packages. Symlink resolution is for classification only
    (refuse_wrapper resolves internally, and records nothing)."""
    return Path(os.path.abspath(os.path.expanduser(p)))


def refuse_wrapper(path: Path) -> None:
    """Wrapper shell scripts are launchers, not installs — refuse to record them."""
    real = path.resolve()
    try:
        first = real.open("rb").readline().decode("utf-8", "replace").strip()
    except OSError:
        return
    if first.startswith("#!"):
        interp = Path(first[2:].strip().split()[-1]).name
        if interp in ("sh", "bash", "zsh", "dash", "ksh") and real.suffix != ".sh":
            # .sh launchers inside a binary install tree (isaac-sim.sh) are the
            # install's own entry points; a bare wrapper elsewhere is not.
            raise SystemExit(
                f"REFUSED: {path} resolves to a shell wrapper script ({real}). "
                "That is a launcher, not an install. Record the underlying "
                "install (pip venv / binary dir) instead."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=VARIANTS)
    parser.add_argument("--isaac-bin", help="launch entry point (venv bin/isaacsim, isaac-sim.sh, ...)")
    parser.add_argument("--isaac-python", help="python of the Isaac venv (pip variants only)")
    parser.add_argument("--isaac-root", help="install root: venv dir (pip), pkg dir (binary), checkout (source)")
    parser.add_argument("--isaac-version", help="Isaac Sim version of the chosen install")
    parser.add_argument("--kit-config", help="the user.config.json that setup/omni-kit-mcp edited (recorded fact)")
    parser.add_argument("--mcp-port", type=int, default=9009, help="omni.kit.mcp bridge port")
    parser.add_argument("--omni-kit-mcp", help="path to the omni-kit-mcp checkout on this box (for bridge scripting + the doctor probe's reference client)")
    parser.add_argument("--isaac-ctl", help="path to isaac-ctl if installed on this box")
    parser.add_argument("--bind-host", help="Linux: bridge bind address recorded for remote access "
                        "(localhost is the default; a tailnet IP exposes run_python — trusted networks only)")
    parser.add_argument("--viewer-app", help="macOS: path to the installed Isaac Viewer.app")
    parser.add_argument("--operate-client", help="macOS: path where kit_mcp's client.py was dropped to drive a remote sim")
    parser.add_argument("--sim-box-host", help="macOS: hostname / tailnet name of the Linux sim box this Mac operates")
    parser.add_argument("--sim-box-port", type=int, help="macOS: pinned bridge port on the sim box (optional; omit to auto-discover via --list-bridges)")
    parser.add_argument("--ros", action="store_true", help="record ROS config + persistently enable the ROS 2 bridge ext")
    parser.add_argument("--ros-distro", help="override class-1 autodetection")
    parser.add_argument("--rmw", default="rmw_cyclonedds_cpp", help="ask-once value, recorded")
    parser.add_argument("--ros-domain-id", type=int, default=0, help="ask-once value, recorded")
    parser.add_argument("--ros-localhost-only", type=int, default=1, choices=(0, 1), help="ask-once value, recorded")
    args = parser.parse_args()

    os_name = c.detect_os()
    if args.variant == "viewer" and os_name != "macos":
        raise SystemExit("--variant viewer is the macOS branch; this box is " + os_name)
    if args.variant != "viewer" and os_name == "macos":
        raise SystemExit("Isaac Sim does not run on macOS — the macOS branch installs the viewer (--variant viewer)")

    if not c.is_uv_available():
        print("uv is not installed. Install it first:\n"
              "  curl -LsSf https://astral.sh/uv/install.sh | sh\n"
              "Then re-run /isaacsim:setup.")
        return 1

    plugin_root = (os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT"))
    if not plugin_root:
        print("CLAUDE_PLUGIN_ROOT is not set — run this via /isaacsim:setup, not directly.")
        return 1
    package_path = Path(plugin_root) / "lib" / "fuzzydroid_isaacsim"

    # ── validate EVERYTHING first — a failed invocation must leave no side
    # effects (no venv created, no config edited, no state written)
    facts: dict = {}
    isaac_root: Path | None = None
    if args.variant == "viewer":
        viewer = Path(args.viewer_app or "/Applications/Isaac Viewer.app")
        if not viewer.exists():
            raise SystemExit(
                f"viewer app not found at {viewer} — install it first by following "
                "the isaac-viewer-macos README, then re-run with --viewer-app.")
        facts["viewer_app"] = str(viewer)
        # optional: this Mac also DRIVES a remote sim via a local reference client
        if args.operate_client:
            oc = _abs_verbatim(args.operate_client)
            if not oc.is_file():
                raise SystemExit(
                    f"--operate-client not found: {oc} — copy omni-kit-mcp/kit_mcp/client.py "
                    "there first (it is a single stdlib-only file).")
            facts["operate_client"] = str(oc)
        if args.sim_box_host:
            facts["sim_box_host"] = args.sim_box_host
        if args.sim_box_port:
            facts["sim_box_port"] = args.sim_box_port
    else:
        if not args.isaac_root:
            raise SystemExit("--isaac-root is required for sim variants (venv dir / pkg dir / checkout)")
        isaac_root = _abs_verbatim(args.isaac_root)
        if not isaac_root.is_dir():
            raise SystemExit(f"--isaac-root does not exist: {isaac_root}")
        facts["isaac_root"] = str(isaac_root)
        if args.isaac_bin:
            isaac_bin = _abs_verbatim(args.isaac_bin)
            if not isaac_bin.exists():
                raise SystemExit(f"--isaac-bin does not exist: {isaac_bin}")
            refuse_wrapper(isaac_bin)
            facts["isaac_bin"] = str(isaac_bin)
        if args.isaac_python:
            ipy = _abs_verbatim(args.isaac_python)
            if not ipy.exists():
                raise SystemExit(f"--isaac-python does not exist: {ipy}")
            facts["isaac_python"] = str(ipy)
        if args.isaac_version:
            facts["isaac_version"] = args.isaac_version
        if args.omni_kit_mcp:
            okm = _abs_verbatim(args.omni_kit_mcp)
            if not (okm / "exts").is_dir():
                raise SystemExit(f"{okm} does not look like an omni-kit-mcp checkout (no exts/)")
            facts["omni_kit_mcp"] = str(okm)
        if args.bind_host:
            facts["bind_host"] = args.bind_host
        if args.kit_config:
            kit_config = Path(args.kit_config).expanduser()
            if not kit_config.is_file():
                raise SystemExit(f"--kit-config does not exist: {kit_config}")
            facts["kit_config"] = str(kit_config)
        if args.isaac_ctl:
            ctl = Path(args.isaac_ctl).expanduser()
            if ctl.exists():
                facts["isaac_ctl"] = str(ctl)
        if args.ros:
            distro = args.ros_distro or autodetect_ros_distro()
            if not distro:
                raise SystemExit(
                    "could not autodetect ROS_DISTRO (no /opt/ros, unmapped OS release) — "
                    "pass --ros-distro explicitly.")
            if "kit_config" not in facts:
                raise SystemExit("--ros needs --kit-config (which user.config.json to edit is a recorded fact)")
            facts["ros_enabled"] = True
            facts["ros_distro"] = distro                       # class 1, recorded fact
            facts["rmw_implementation"] = args.rmw             # class 2, ask-once
            facts["ros_domain_id"] = args.ros_domain_id        # class 2, ask-once
            facts["ros_localhost_only"] = args.ros_localhost_only  # class 2, ask-once

    # ── side effects, only now
    # plugin venv + editable install (conventions §3-4; hash gives doctor drift detection)
    venv_path = c.plugin_venv_path(PLUGIN_NAME)
    c.ensure_venv(venv_path, PYTHON_VERSION)
    c.install_editable(venv_path, package_path)
    print(f"plugin venv ready: {venv_path}")

    if facts.get("ros_enabled"):
        versioned = ros_bridge.enable_bridge(Path(facts["kit_config"]), isaac_root)
        facts["ros_bridge_ext"] = versioned
        print(f"ROS 2 bridge persistently enabled: {versioned} in {facts['kit_config']}")
        print("NOTE: env guards (GLIBC_TUNABLES static-TLS bump, nvjitlink preload) are "
              "PER-PROFILE launcher business (isaac-ctl full-app profile). They must NOT "
              "go in venv activate or blanket env files — the static-TLS tunable breaks "
              "PhysX GPU init in Isaac Lab standalone runs.")

    state: dict = {
        "venv_path": str(venv_path),
        "plugin_version": PLUGIN_VERSION,
        "pyproject_hash": c.hash_file(package_path / "pyproject.toml"),
        "install_timestamp": c.now_iso(),
        "python_version": PYTHON_VERSION,
        "os": os_name,
        "variant": args.variant,
        "mcp_port": args.mcp_port,
        **facts,
    }
    c.save_state(PLUGIN_NAME, state)
    print(f"state written: {c.state_file(PLUGIN_NAME)}")
    print("run /isaacsim:doctor to verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
