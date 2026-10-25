"""Pre-existing Isaac Lab install detection.

Isaac Lab comes in two variants:
  - pip: a venv containing the `isaaclab` package (the official docs' example
    venv name is `env_isaaclab`, but that is an EXAMPLE — every candidate is
    verified by the presence of the dist, never by name)
  - source: an IsaacLab checkout (marked by `isaaclab.sh` + `source/isaaclab`)

Recommendation: newest pip > source. This module only finds and classifies;
setup records what the user confirms.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from fuzzydroid_isaaclab._common import detect_os, version_key

_VENV_ROOT_GLOBS = [
    "env_*",
    "venvs/*",
    ".venvs/*",
    "miniconda3/envs/*",
    "anaconda3/envs/*",
    "micromamba/envs/*",
]


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
    """Version per the interpreter's dist metadata (no package import)."""
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


def _import_probe(python: Path, module: str) -> Optional[dict[str, Any]]:
    """Authoritative version AND origin: actually import the module under the
    venv's interpreter. This is the only probe that sees shadowing — e.g. a
    source checkout on the import path (editable .pth) hiding the venv's pip
    dist, where dist metadata and reality disagree."""
    code = (
        "import json\n"
        f"import {module} as m\n"
        "print(json.dumps({'version': getattr(m, '__version__', None),"
        " 'file': getattr(m, '__file__', None)}))\n"
    )
    try:
        out = subprocess.run([str(python), "-c", code],
                             capture_output=True, text=True, timeout=60)
        if out.returncode == 0 and out.stdout.strip():
            return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        pass
    return None


def find_pip_venvs(extra_dirs: list[str]) -> list[dict[str, Any]]:
    candidates: set[Path] = set()
    home = Path.home()
    for pattern in _VENV_ROOT_GLOBS:
        candidates.update(home.glob(pattern))
    if os.environ.get("VIRTUAL_ENV"):
        candidates.add(Path(os.environ["VIRTUAL_ENV"]))
    for extra in extra_dirs:
        p = Path(extra).expanduser()
        if p.is_dir():
            candidates.add(p)
            candidates.update(c for c in p.iterdir() if c.is_dir())

    results = []
    for venv in sorted(candidates):
        py = venv / ("Scripts/python.exe" if detect_os() == "windows" else "bin/python")
        if not py.exists():
            continue
        lab_version = _dist_version(venv, "isaaclab")
        if not lab_version:
            continue
        # dist-info names found the candidate; the actual import under the
        # venv's python is authoritative for version AND origin (a source
        # checkout on the import path can shadow the pip dist entirely)
        probe = _import_probe(py, "isaaclab") or {}
        entry = {
            "kind": "pip",
            "variant": "pip",
            "venv": str(venv),
            "lab_version": (probe.get("version")
                            or _dist_version_via_python(py, "isaaclab")
                            or lab_version),
            "isaac_version": (_dist_version_via_python(py, "isaacsim")
                              or _dist_version(venv, "isaacsim")),
            "python": str(py),
        }
        origin = probe.get("file")
        if origin and str(venv) not in origin:
            entry["note"] = (f"import resolves OUTSIDE the venv: {origin} — "
                             "a source checkout shadows the pip dist")
        results.append(entry)
    return results


def find_source_checkouts(extra_dirs: list[str]) -> list[dict[str, Any]]:
    results = []
    candidates: set[Path] = set()
    home = Path.home()
    for name in ("IsaacLab", "isaaclab", "isaac-lab"):
        candidates.add(home / name)
        candidates.add(home / "Documents" / name)
    for extra in extra_dirs:
        p = Path(extra).expanduser()
        if p.is_dir():
            candidates.add(p)
            candidates.update(c for c in p.iterdir() if c.is_dir())
    for d in sorted(candidates):
        if d.is_dir() and (d / "isaaclab.sh").exists() and (d / "source" / "isaaclab").is_dir():
            results.append({"kind": "source", "variant": "source", "path": str(d)})
    return results


def recommend(inventory: dict[str, Any]) -> Optional[dict[str, Any]]:
    if inventory["pip"]:
        best = max(inventory["pip"], key=lambda e: version_key(e["lab_version"]))
        return {**best, "reason": "newest pip install"}
    if inventory["source"]:
        return {**inventory["source"][0], "reason": "source checkout (only candidate kind found)"}
    return None


def build_inventory(extra_dirs: list[str]) -> dict[str, Any]:
    inventory = {
        "os": detect_os(),
        "pip": find_pip_venvs(extra_dirs),
        "source": find_source_checkouts(extra_dirs),
    }
    inventory["recommendation"] = recommend(inventory)
    return inventory


def print_markdown(inv: dict[str, Any]) -> None:
    print("| kind | where | isaaclab | isaacsim | note |")
    print("|---|---|---|---|---|")
    rows = 0
    for e in inv["pip"]:
        print(f"| pip | `{e['venv']}` | {e['lab_version']} | {e['isaac_version'] or '—'} | {e.get('note', '')} |")
        rows += 1
    for e in inv["source"]:
        print(f"| source | `{e['path']}` | — | — | `isaaclab.sh` checkout |")
        rows += 1
    if rows == 0:
        print("| — | no Isaac Lab installs found | — | — | fresh install needed |")
    print()
    rec = inv["recommendation"]
    if rec:
        where = rec.get("venv") or rec.get("path")
        print(f"Recommended: **{rec['variant']}** at `{where}` ({rec['reason']})")
    else:
        print("Recommended: none — delegate a fresh install to the official live docs "
              "(https://isaac-sim.github.io/IsaacLab).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--scan-dir", action="append", default=[],
                        help="extra directory to scan for venvs / checkouts (repeatable)")
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
