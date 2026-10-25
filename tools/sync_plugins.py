#!/usr/bin/env python3
"""Generate Codex metadata from the Claude plugin manifests.

Run with --check in CI; without arguments, update generated files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generated_files() -> dict[Path, str]:
    catalog = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    marketplace = {
        "name": catalog["name"],
        "interface": {"displayName": "fuzzydroid"},
        "plugins": [],
    }
    files = {}
    for entry in catalog["plugins"]:
        plugin = ROOT / entry["source"]
        manifest = json.loads((plugin / ".claude-plugin/plugin.json").read_text())
        manifest.pop("$schema", None)
        manifest["skills"] = "./skills/"
        manifest["interface"] = {
            "displayName": {
                "fusion": "Fusion 360",
                "isaacsim": "Isaac Sim",
                "isaaclab": "Isaac Lab",
                "robodocs": "RoboDocs",
                "kicad": "KiCad",
            }[entry["name"]],
            "shortDescription": manifest["description"]
            .split(" - ")[0]
            .split("—")[0]
            .strip()[:100],
            "developerName": manifest["author"]["name"],
            "category": "Developer Tools",
        }
        if (plugin / ".mcp.json").exists():
            manifest["mcpServers"] = "./.mcp.json"
        files[plugin / ".codex-plugin/plugin.json"] = (
            json.dumps(manifest, indent=2) + "\n"
        )
        marketplace["plugins"].append(
            {
                "name": entry["name"],
                "source": {"source": "local", "path": entry["source"]},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
                "category": "Developer Tools",
            }
        )
    files[ROOT / ".agents/plugins/marketplace.json"] = (
        json.dumps(marketplace, indent=2) + "\n"
    )
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for path, content in generated_files().items():
        if path.exists() and path.read_text() == content:
            continue
        stale.append(str(path.relative_to(ROOT)))
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if args.check and stale:
        print("Generated plugin files are stale; run python3 tools/sync_plugins.py:")
        print("\n".join(stale))
        return 1
    print(f"Plugin metadata is in sync ({len(generated_files())} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
