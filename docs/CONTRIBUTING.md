# Contributing to fuzzydroid

## Development setup

```bash
git clone https://github.com/inbarajaldrin/fuzzydroid.git
cd fuzzydroid
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e plugins/fusion/lib/fuzzydroid_fusion
uv pip install --python .venv/bin/python pytest pytest-cov
```

Run the Fusion test suite:

```bash
.venv/bin/python -m pytest plugins/fusion/lib/fuzzydroid_fusion/tests -v
```

Run each other Python plugin's tests from its package directory:

```bash
cd plugins/kicad/lib/fuzzydroid_kicad  # or isaacsim / isaaclab's lib/<package>
uv run --python 3.11 --extra dev python -m pytest -q
```

From the repository root, validate release packaging:

```bash
python3 tools/sync_plugins.py --check
python3 tools/check_plugins.py
python3 tools/check_common_sync.py
git diff --check
```

With Codex installed, `python3 tools/check_plugins.py --codex` also loads the
repo catalog, skills, and MCP declarations through the actual Codex parser.
This read-only check does not install plugins or edit Codex settings.

After changing a Claude plugin manifest, marketplace entry, or command, run
`python3 tools/sync_plugins.py` to refresh the Codex manifests, catalog, and
command skills. Keep generated files in the same commit as their sources.
Personal tutorials, their CAD exports, and timestamped backups belong in a user's
project or reference archive. Skills retain general methods and reusable tools;
do not bundle personal session histories. Live Fusion, KiCad, and NVIDIA
application tests require their respective applications and are separate from
these unit checks.

## Adding a plugin

See `docs/CONVENTIONS.md` — specifically the bootstrap checklist at the bottom.

## Code style

- Python 3.11+, use stdlib `tomllib` (no `tomli` dep).
- Format with `ruff format`, lint with `ruff check`.
- Type hints on public functions.
- Tests required for every new module in `plugins/<plugin>/lib/fuzzydroid_<plugin>/fuzzydroid_<plugin>/`. If you touch the vendored `_common.py`, edit the master at `tools/common/_common.py` and re-vendor (`tools/check_common_sync.py` must pass).

## Testing on Windows

Most fuzzydroid developers use macOS. When modifying cross-platform code (the vendored `_common.py` or fusion's `_symlink.py`), test on a Windows 10+ machine before merging. If you can't, mark the PR `needs-windows-test` and ask someone else to verify.

## License

By contributing, you agree that your contributions will be licensed under Apache-2.0.
