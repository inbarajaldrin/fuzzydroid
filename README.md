# fuzzydroid

An AI agent plugin marketplace for robotics developers using Claude Code or Codex.

## Plugins

| Plugin | Description |
|---|---|
| [`fusion`](plugins/fusion/) | Control Autodesk Fusion 360—search projects, open files, export STEP/STL/URDF, and run Python scripts inside Fusion. |
| [`kicad`](plugins/kicad/) | Control the running KiCad PCB Editor—inspect and edit boards, load footprints and 3D models, and export designs. |
| [`robodocs`](plugins/robodocs/) | Live-fetched docs for the robotics stack — LeRobot, MuJoCo, and the NVIDIA Physical-AI suite (Isaac, GR00T, Cosmos, Warp, Omniverse, OpenUSD) |
| [`isaacsim`](plugins/isaacsim/) | NVIDIA Isaac Sim setup + health — detects existing installs, registers the omni.kit.mcp bridge, persistent ROS 2 bridge enable, native Isaac Viewer on macOS |
| [`isaaclab`](plugins/isaaclab/) | Isaac Lab setup, health, and project scaffolding — pinned-template projects with bridge+livestream launch support |

## Install

In Claude Code:

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
```

Then install the plugins you want:

```
/plugin install fusion@fuzzydroid
/plugin install kicad@fuzzydroid
/plugin install robodocs@fuzzydroid
/plugin install isaacsim@fuzzydroid
/plugin install isaaclab@fuzzydroid
```

In Codex CLI:

```bash
codex plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
codex plugin add fusion@fuzzydroid
codex plugin add kicad@fuzzydroid
codex plugin add robodocs@fuzzydroid
codex plugin add isaacsim@fuzzydroid
codex plugin add isaaclab@fuzzydroid
```

Install the plugins you need, then start a new session in Claude Code or Codex
and describe your task. Your agent handles setup and diagnostics as needed.
RoboDocs needs no local setup.

Each plugin exposes one main skill that loads its internal workflows as needed.

## Requirements

- Claude Code or a Codex client with plugin support

Plugin-specific requirements live in each plugin's README:

- [`fusion`](plugins/fusion/README.md) — Fusion 360, `uv`, macOS/Windows
- [`kicad`](plugins/kicad/README.md) — KiCad 10, `uv`; macOS qualified, live Windows validation pending
- [`robodocs`](plugins/robodocs/README.md) — none
- [`isaacsim`](plugins/isaacsim/README.md) — `uv`; Linux (sim box) or macOS (viewer box)
- [`isaaclab`](plugins/isaaclab/README.md) — `uv`; Linux (Isaac Lab does not run on macOS)

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICES.md](NOTICES.md).

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) and [docs/CONVENTIONS.md](docs/CONVENTIONS.md).
