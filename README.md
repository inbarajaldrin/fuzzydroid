# fuzzydroid

An AI agent plugin marketplace for robotics developers.

## Plugins

| Plugin | Description |
|---|---|
| [`fusion`](plugins/fusion/) | Control Autodesk Fusion 360 — search, open, export STEP/STL/URDF, view models, run Python |

## Install

In Claude Code:

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
/plugin install fusion@fuzzydroid
/fusion:setup
```

Then open Fusion 360 → Shift+S → Add-Ins → click "Run" + "Run on Startup" on `fusion_bridge`.

Verify: `/fusion:doctor`

## Requirements

- macOS or Windows 10+ (Linux not supported in v0)
- [`uv`](https://docs.astral.sh/uv/) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS/Linux, or `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` on Windows
- Autodesk Fusion 360 installed (for the `fusion` plugin)

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICES.md](NOTICES.md).

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) and [docs/CONVENTIONS.md](docs/CONVENTIONS.md).
