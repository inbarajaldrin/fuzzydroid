#!/usr/bin/env python3
"""Generate Codex metadata and command skills from the Claude plugin sources.

Run with --check in CI; without arguments, update generated files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_DESCRIPTIONS = {
    "lerobot": "Fetch live HuggingFace LeRobot documentation for robot hardware, teleoperation, datasets, calibration, imitation learning, and policies such as ACT, SmolVLA, Pi0, Diffusion and HIL-SERL.",
    "mujoco": "Fetch live MuJoCo ecosystem documentation for MJCF, Python/C APIs, MJX, MJWarp, Menagerie, Playground, MPC and dm_control. Use for simulation, contact dynamics, actuators, rendering and MuJoCo troubleshooting.",
    "nvidia": "Fetch live NVIDIA robotics and Physical-AI documentation. Route questions about Isaac Sim, Isaac Lab, Isaac ROS, GR00T, Cosmos, Warp, Omniverse, OpenUSD, Replicator, NGC containers and NVIDIA developer forums.",
}


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
        for command in sorted((plugin / "commands").glob("*.md")):
            # RoboDocs keeps its detailed workflows in commands/ too.
            description = (
                f"Run the {entry['name']} {command.stem} workflow. "
                f"Use when the user asks for {entry['name']} {command.stem}."
            )
            if entry["name"] == "robodocs":
                description = DOC_DESCRIPTIONS[command.stem]
            files[plugin / "skills" / command.stem / "SKILL.md"] = (
                "---\n"
                f"name: {command.stem}\n"
                f"description: {description}\n"
                "---\n\n"
                f"# {entry['name']} {command.stem}\n\n"
                "Resolve symlinks on this file. The plugin root is three parent\n"
                "directories above this `SKILL.md` (`<plugin>/skills/<skill>/SKILL.md`).\n"
                "Use that absolute root in every command; pass it as\n"
                "`CLAUDE_PLUGIN_ROOT` to child processes that use that variable.\n\n"
                f"Read `<plugin-root>/commands/{command.name}` and follow its workflow.\n"
                "Resolve its relative references from the paths it specifies.\n"
                "Use the current host's shell, file, web and user-input tools for\n"
                "`Bash`, `Read`, `WebFetch` and `AskUserQuestion` respectively.\n"
                "In Codex, invoke sibling skills with `$plugin:skill`; slash-command\n"
                "names in the workflow refer to the equivalent bundled skills.\n"
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
    print(
        f"Plugin metadata and command skills are in sync ({len(generated_files())} files)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
