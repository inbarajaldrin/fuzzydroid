"""Pre-existing Isaac Sim install detection — the ladder, strongest first.

    1. running process
    2. PATH entries (symlinks resolved; shell-wrapper launchers REFUSED as
       installs — they are classified `launcher` and never recommended)
    3. pip venvs containing the `isaacsim` package
    4. ~/.local/share/ov/pkg binaries
    5. source checkouts

Pre-existing installs are the norm on robotics workstations; a fresh install
is the fallback, not the default. This module only *finds and classifies* —
it never installs, never edits config, and never asks questions. The setup
command presents the inventory, recommends (running > newest pip > newest
binary), and the user confirms before anything is recorded.

Output: human-readable markdown table by default, `--json` for the agent.
Machine facts discovered here go into the state file via setup.py, never
into plugin content.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from fuzzydroid_isaacsim._common import detect_os, version_key

# Candidate roots for the pip-venv rung. Doc-example names (env_isaacsim,
# env_isaaclab) are NVIDIA's published examples, not assumptions — every hit
# is verified by the presence of an isaacsim dist before it is reported.
_VENV_ROOT_GLOBS = [
    "env_*",
    "venvs/*",
    ".venvs/*",
    "miniconda3/envs/*",
    "anaconda3/envs/*",
    "micromamba/envs/*",
]

_SHELL_SHEBANGS = ("sh", "bash", "zsh", "dash", "ksh")

# argv[0] basenames that ARE an Isaac/Kit entrypoint. Substring-anywhere
# matching is deliberately not used: watchdog scripts, telemetry helpers,
# tmux/editor sessions and greps all mention isaac paths in their cmdline
# without being the sim.
_ENTRYPOINT_EXES = {"isaacsim", "isaac-sim.sh", "isaac-sim.streaming.sh", "kit"}


def _is_isaac_entrypoint(cmdline: str) -> bool:
    """True only if the process actually IS a Kit/Isaac entrypoint:
    argv[0] is an isaacsim/kit binary, or a python running the isaacsim
    console script / module / a script from inside an isaacsim install."""
    argv = cmdline.split()
    if not argv:
        return False
    exe = Path(argv[0]).name
    if exe in _ENTRYPOINT_EXES:
        return True
    if not exe.startswith("python"):
        return False
    prev = ""
    for arg in argv[1:]:
        if prev == "-m":
            return arg.split(".")[0] == "isaacsim"
        if arg.startswith("-"):
            prev = arg
            continue
        # first positional arg = the script being run
        return (Path(arg).name == "isaacsim"
                or "site-packages/isaacsim/" in arg)
    return False


def detect_running() -> list[dict[str, Any]]:
    """Rung 1: live Isaac Sim processes (strongest evidence)."""
    hits: list[dict[str, Any]] = []
    try:
        out = subprocess.run(
            ["ps", "-eo", "pid=,args="], capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception:
        return hits
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        pid, _, args = line.partition(" ")
        # skip our own tooling (this scan, doctor, uv shims)
        if "fuzzydroid" in args:
            continue
        if _is_isaac_entrypoint(args.strip()):
            hits.append({"kind": "running", "pid": int(pid), "cmdline": args.strip()[:400]})
    return hits


def classify_path_entries() -> list[dict[str, Any]]:
    """Rung 2: PATH entries, symlinks resolved, wrapper scripts refused.

    A pip console script (python shebang inside a venv) is evidence of a pip
    install and points at its venv. A shell-script wrapper (bash shebang) is a
    LAUNCHER, not an install — reported so the user sees it, but classified
    `launcher` and never eligible as the recorded install.
    """
    results: list[dict[str, Any]] = []
    for name in ("isaacsim", "isaac-sim"):
        found = shutil.which(name)
        if not found:
            continue
        real = Path(found).resolve()
        entry: dict[str, Any] = {"kind": "path", "name": name, "path": found, "resolved": str(real)}
        try:
            first = real.open("rb").readline().decode("utf-8", "replace").strip()
        except Exception:
            first = ""
        if first.startswith("#!"):
            interp = first[2:].strip()
            interp_base = Path(interp.split()[-1]).name  # handles '#!/usr/bin/env bash'
            if interp_base in _SHELL_SHEBANGS:
                entry["classification"] = "launcher"
                entry["note"] = ("shell-wrapper script — a launcher, NOT an install; "
                                 "refused as an install candidate")
            elif "python" in interp_base:
                venv = Path(interp.split()[0]).parent.parent
                entry["classification"] = "pip-console-script"
                entry["venv_hint"] = str(venv)
            else:
                entry["classification"] = "unknown-script"
        else:
            entry["classification"] = "binary"
        results.append(entry)
    return results


def _dist_version(venv: Path, dist_prefix: str) -> Optional[str]:
    """Fast presence check from dist-info directory names. Can be WRONG about
    the version when stale dist-infos linger (editable/upgrade leftovers) —
    use _dist_version_via_python for the authoritative number."""
    for sp in venv.glob("lib/python3.*/site-packages"):
        for info in sp.glob(f"{dist_prefix}-*.dist-info"):
            m = re.match(rf"{re.escape(dist_prefix)}-(.+)\.dist-info", info.name)
            if m:
                return m.group(1)
    return None


def _dist_version_via_python(python: Path, dist: str) -> Optional[str]:
    """Authoritative version: ask the venv's own interpreter. importlib.metadata
    resolves exactly what `import` would see, so stale dist-info dirs on disk
    can't lie to it."""
    try:
        out = subprocess.run(
            [str(python), "-c",
             f"from importlib.metadata import version; print(version('{dist}'))"],
            capture_output=True, text=True, timeout=15)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _has_dist(venv: Path, dist_prefix: str) -> bool:
    return _dist_version(venv, dist_prefix) is not None


def find_pip_venvs(extra_dirs: list[str]) -> list[dict[str, Any]]:
    """Rung 3: venvs that actually contain the `isaacsim` package."""
    candidates: set[Path] = set()
    home = Path.home()
    for pattern in _VENV_ROOT_GLOBS:
        candidates.update(home.glob(pattern))
    if os.environ.get("VIRTUAL_ENV"):
        candidates.add(Path(os.environ["VIRTUAL_ENV"]))
    for entry in classify_path_entries():
        if entry.get("venv_hint"):
            candidates.add(Path(entry["venv_hint"]))
    for extra in extra_dirs:
        p = Path(extra).expanduser()
        if p.is_dir():
            # accept both "this IS a venv" and "this contains venvs"
            candidates.add(p)
            candidates.update(c for c in p.iterdir() if c.is_dir())

    results = []
    for venv in sorted(candidates):
        py = venv / ("Scripts/python.exe" if detect_os() == "windows" else "bin/python")
        if not py.exists():
            continue
        version = _dist_version(venv, "isaacsim")
        if not version:
            continue
        # dist-info names found the candidate; the venv's python is authoritative
        # for versions AND presence (stale dist-infos from upgrades can disagree)
        isaac_probe = _dist_version_via_python(py, "isaacsim")
        if isaac_probe:  # interpreter answered — trust it for the lab check too
            has_lab = _dist_version_via_python(py, "isaaclab") is not None
        else:            # interpreter unusable — fall back to dist-info names
            has_lab = _has_dist(venv, "isaaclab")
        entry = {
            "kind": "pip",
            "variant": "pip-lab" if has_lab else "pip-standalone",
            "venv": str(venv),
            "isaac_version": isaac_probe or version,
            "python": str(py),
        }
        launcher = venv / "bin" / "isaacsim"
        if launcher.exists():
            entry["isaac_bin"] = str(launcher)
        results.append(entry)
    return results


def find_binary_installs() -> list[dict[str, Any]]:
    """Rung 4: Omniverse-launcher / standalone binary installs (no venv)."""
    results = []
    pkg_root = Path.home() / ".local" / "share" / "ov" / "pkg"
    if not pkg_root.is_dir():
        return results
    for d in sorted(pkg_root.iterdir()):
        if not d.is_dir() or "isaac" not in d.name.lower():
            continue
        m = re.search(r"(\d+(?:\.\d+)+)", d.name)
        version = m.group(1) if m else "unknown"
        entry: dict[str, Any] = {"kind": "binary", "variant": "binary",
                                 "path": str(d), "isaac_version": version}
        for launcher in ("isaac-sim.sh", "isaac-sim.streaming.sh", "runapp.sh"):
            if (d / launcher).exists():
                entry["isaac_bin"] = str(d / launcher)
                break
        results.append(entry)
    return results


def find_source_checkouts(extra_dirs: list[str]) -> list[dict[str, Any]]:
    """Rung 5: source checkouts (best-effort — pass --scan-dir for yours)."""
    results = []
    candidates: set[Path] = set()
    home = Path.home()
    for name in ("IsaacSim", "isaac-sim", "isaacsim"):
        candidates.add(home / name)
        candidates.add(home / "Documents" / name)
    for extra in extra_dirs:
        p = Path(extra).expanduser()
        if p.is_dir():
            candidates.add(p)
            candidates.update(c for c in p.iterdir() if c.is_dir())
    for d in sorted(candidates):
        if not d.is_dir():
            continue
        if "isaac" not in d.name.lower():
            continue
        if any((d / marker).exists() for marker in ("repo.sh", "build.sh", "SConstruct")):
            results.append({"kind": "source", "variant": "source", "path": str(d)})
    return results


def recommend(inventory: dict[str, Any]) -> Optional[dict[str, Any]]:
    """running > newest pip > newest binary (source is never auto-recommended)."""
    if inventory["running"]:
        # A running process is the strongest evidence, but the *recorded*
        # install must still be one of the concrete candidates below; prefer
        # the pip/binary entry whose path appears in the running cmdline.
        cmdlines = " ".join(p["cmdline"] for p in inventory["running"])
        for entry in inventory["pip"] + inventory["binary"]:
            root = entry.get("venv") or entry.get("path", "")
            if root and root in cmdlines:
                return {**entry, "reason": "matches the currently running Isaac Sim process"}
    if inventory["pip"]:
        best = max(inventory["pip"], key=lambda e: version_key(e["isaac_version"]))
        return {**best, "reason": "newest pip install"}
    if inventory["binary"]:
        with_bin = [e for e in inventory["binary"] if e.get("isaac_bin")]
        pool = with_bin or inventory["binary"]
        best = max(pool, key=lambda e: version_key(e["isaac_version"]))
        return {**best, "reason": "newest binary install"}
    return None


def build_inventory(extra_dirs: list[str]) -> dict[str, Any]:
    inventory = {
        "os": detect_os(),
        "running": detect_running(),
        "path": classify_path_entries(),
        "pip": find_pip_venvs(extra_dirs),
        "binary": find_binary_installs(),
        "source": find_source_checkouts(extra_dirs),
    }
    inventory["recommendation"] = recommend(inventory)
    return inventory


def print_markdown(inv: dict[str, Any]) -> None:
    print("| rung | what | where | version | note |")
    print("|---|---|---|---|---|")
    rows = 0
    for p in inv["running"]:
        print(f"| running | pid {p['pid']} | `{p['cmdline'][:80]}` | — | live process |")
        rows += 1
    for e in inv["path"]:
        note = e.get("note", e["classification"])
        print(f"| PATH | `{e['name']}` | `{e['resolved']}` | — | {note} |")
        rows += 1
    for e in inv["pip"]:
        print(f"| pip | {e['variant']} | `{e['venv']}` | {e['isaac_version']} | |")
        rows += 1
    for e in inv["binary"]:
        launch = f"launcher: `{e['isaac_bin']}`" if e.get("isaac_bin") else "no launcher found"
        print(f"| binary | {e['variant']} | `{e['path']}` | {e['isaac_version']} | {launch} |")
        rows += 1
    for e in inv["source"]:
        print(f"| source | checkout | `{e['path']}` | — | best-effort match |")
        rows += 1
    if rows == 0:
        print("| — | no Isaac Sim installs found | — | — | fresh install needed |")
    print()
    rec = inv["recommendation"]
    if rec:
        where = rec.get("venv") or rec.get("path")
        print(f"Recommended: **{rec['variant']}** at `{where}` ({rec['reason']})")
    else:
        print("Recommended: none — no eligible pre-existing install; "
              "delegate a fresh install to NVIDIA's live docs.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON for the agent")
    parser.add_argument("--scan-dir", action="append", default=[],
                        help="extra directory to scan for venvs / source checkouts (repeatable)")
    args = parser.parse_args()
    inv = build_inventory(args.scan_dir)
    if args.json:
        json.dump(inv, sys.stdout, indent=2)
        print()
    else:
        print_markdown(inv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
