# fuzzydroid

An AI agent plugin marketplace for robotics developers using Claude Code or Codex.

## Plugins

| Plugin | Description |
|---|---|
| [`fusion`](plugins/fusion/) | Control Autodesk Fusion 360—search projects, open files, export STEP/STL/URDF, and run Python scripts inside Fusion. |
| [`kicad`](plugins/kicad/) | Live KiCad PCB control, component models, fabrication exports, and Fusion handoff (preview) |
| [`robodocs`](plugins/robodocs/) | Live-fetched docs for the robotics stack — LeRobot + the NVIDIA Physical-AI suite (Isaac, GR00T, Cosmos, Warp, Omniverse, OpenUSD) |
| [`isaacsim`](plugins/isaacsim/) | NVIDIA Isaac Sim setup + health — detects existing installs, registers the omni.kit.mcp bridge, persistent ROS 2 bridge enable, native Isaac Viewer on macOS |
| [`isaaclab`](plugins/isaaclab/) | Isaac Lab setup, health, and project scaffolding — pinned-template projects with bridge+livestream launch support |

## Install

In Claude Code:

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
```

Then install the plugins you want:

```
/plugin install fusion@fuzzydroid       # see plugins/fusion/README.md for setup
/plugin install kicad@fuzzydroid        # then /kicad:setup
/plugin install robodocs@fuzzydroid     # robotics documentation skills
/plugin install isaacsim@fuzzydroid     # then /isaacsim:setup
/plugin install isaaclab@fuzzydroid     # then /isaaclab:setup
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

Install whichever plugins you need, then start a new session. Ask Codex to use
`$fusion:setup`, `$isaacsim:setup`, `$isaaclab:setup`, or `$kicad:setup`, followed
by the matching `$plugin:doctor`. RoboDocs needs no setup: invoke
`$robodocs:lerobot`, `$robodocs:mujoco`, or `$robodocs:nvidia`.

Each plugin bundles both host manifests and shares the same skills, scripts,
and Python package. See [docs/CONVENTIONS.md](docs/CONVENTIONS.md) for portability
and [the OpenAI plugin documentation](https://developers.openai.com/plugins/build/plugins)
for Codex marketplace support.

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
