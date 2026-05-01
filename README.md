# fuzzydroid

An AI agent plugin marketplace for robotics developers.

## Plugins

| Plugin | Description |
|---|---|
| [`fusion`](plugins/fusion/) | Control Autodesk Fusion 360 — search, open, export STEP/STL/URDF, view models, run Python |
| [`robodocs`](plugins/robodocs/) | Live-fetched docs for the robotics stack — LeRobot + the NVIDIA Physical-AI suite (Isaac, GR00T, Cosmos, Warp, Omniverse, OpenUSD) |

## Install

In Claude Code:

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
```

Then install the plugins you want:

```
/plugin install fusion@fuzzydroid       # see plugins/fusion/README.md for setup
/plugin install robodocs@fuzzydroid     # robotics documentation skills
```

## Requirements

- Claude Code

Plugin-specific requirements live in each plugin's README:

- [`fusion`](plugins/fusion/README.md) — Fusion 360, `uv`, macOS/Windows
- [`robodocs`](plugins/robodocs/README.md) — none

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICES.md](NOTICES.md).

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) and [docs/CONVENTIONS.md](docs/CONVENTIONS.md).
