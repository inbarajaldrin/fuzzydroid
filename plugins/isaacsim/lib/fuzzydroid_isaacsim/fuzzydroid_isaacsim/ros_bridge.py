"""Persistent isaacsim.ros2.bridge enable in Kit's user.config.json.

ROS is a persistent setup step, NOT a per-launch flag. Mechanism (the same
one omni-kit-mcp's scripts/install.py uses for omni.kit.mcp — the scriptable
equivalent of the Extensions window's AUTOLOAD checkbox):

  - the ext id goes into /persistent/app/exts/enabled as the VERSIONED id
    (e.g. isaacsim.ros2.bridge-4.9.3); an unversioned id silently does nothing
  - the version is READ from the install's bundled extension.toml, never guessed
  - the config file is backed up first, the edit is idempotent, and stale
    isaacsim.ros2.bridge-* variants from older versions are collapsed

Which user.config.json gets edited is a machine fact: a box can have many Kit
app-data dirs, so the caller passes the path explicitly and setup RECORDS it
in the state file. Env guards do NOT belong here — ld.so consumes them before
the process starts, so they are per-profile launcher business (isaac-ctl),
never Kit config and never blanket venv/env files.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Any, Optional

BRIDGE_EXT = "isaacsim.ros2.bridge"


def find_bridge_ext_toml(install_root: Path) -> Optional[Path]:
    """Locate the bundled isaacsim.ros2.bridge extension.toml under an install.

    Works for pip installs (site-packages/isaacsim/exts*) and binary installs
    (<pkg>/exts). install_root is the venv dir for pip, the pkg dir for binary.
    """
    for pattern in (
        f"lib/python3.*/site-packages/isaacsim/exts*/{BRIDGE_EXT}*/config/extension.toml",
        f"exts*/{BRIDGE_EXT}*/config/extension.toml",
        f"extscache/{BRIDGE_EXT}*/config/extension.toml",
    ):
        hits = sorted(install_root.glob(pattern))
        if hits:
            return hits[0]
    return None


def read_ext_version(ext_toml: Path) -> str:
    """First standalone `version = "..."` line of [package] — same rule
    omni-kit-mcp's install.py uses."""
    for line in ext_toml.read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*version\s*=\s*"([^"]+)"', line)
        if m:
            return m.group(1)
    raise ValueError(f"no version line in {ext_toml}")


def _idx_dict_values(d: Any) -> list:
    """user.config serializes lists as {'0': v, '1': v}. Return the value list."""
    if isinstance(d, list):
        return list(d)
    if not isinstance(d, dict):
        return []
    return [d[k] for k in sorted(d, key=lambda x: int(x) if x.isdigit() else 0)]


def _to_idx_dict(values: list) -> dict:
    return {str(i): v for i, v in enumerate(values)}


def enable_bridge(kit_config: Path, install_root: Path, dry_run: bool = False) -> str:
    """Idempotently add the versioned bridge id to /persistent/app/exts/enabled.

    Returns the versioned ext id that is now (or already was) enabled.
    """
    ext_toml = find_bridge_ext_toml(install_root)
    if ext_toml is None:
        raise FileNotFoundError(
            f"{BRIDGE_EXT} extension.toml not found under {install_root} — "
            "is this really an Isaac Sim install with the ROS 2 bridge bundled?"
        )
    versioned = f"{BRIDGE_EXT}-{read_ext_version(ext_toml)}"

    cfg = json.loads(kit_config.read_text(encoding="utf-8"))
    persistent = cfg.setdefault("persistent", {})
    app = persistent.setdefault("app", {})
    exts = app.setdefault("exts", {})
    enabled = _idx_dict_values(exts.get("enabled"))

    # collapse stale versioned variants, then add the current one
    kept = [e for e in enabled if not str(e).startswith(f"{BRIDGE_EXT}-")]
    if kept + [versioned] == enabled:
        return versioned  # already exactly right — nothing to write
    kept.append(versioned)
    exts["enabled"] = _to_idx_dict(kept)

    if not dry_run:
        backup = kit_config.with_name(
            f"{kit_config.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(kit_config, backup)
        kit_config.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    return versioned


def bridge_enabled_id(kit_config: Path) -> Optional[str]:
    """Return the versioned bridge id currently enabled, or None (doctor)."""
    try:
        cfg = json.loads(kit_config.read_text(encoding="utf-8"))
    except Exception:
        return None
    enabled = _idx_dict_values(
        cfg.get("persistent", {}).get("app", {}).get("exts", {}).get("enabled"))
    for e in enabled:
        if str(e).startswith(f"{BRIDGE_EXT}-") or str(e) == BRIDGE_EXT:
            return str(e)
    return None
