# Contributing to fuzzydroid

## Development setup

```bash
git clone https://github.com/inbarajaldrin/fuzzydroid.git
cd fuzzydroid
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e plugins/fusion/shared/fuzzydroid
uv pip install --python .venv/bin/python pytest pytest-cov
```

Run the full test suite:

```bash
.venv/bin/python -m pytest plugins/fusion/shared/fuzzydroid/tests -v
```

## Adding a plugin

See `docs/CONVENTIONS.md` — specifically the bootstrap checklist at the bottom.

## Code style

- Python 3.11+, use stdlib `tomllib` (no `tomli` dep).
- Format with `ruff format`, lint with `ruff check`.
- Type hints on public functions.
- Tests required for every new module in `plugins/<plugin>/shared/fuzzydroid/fuzzydroid/common/` and `plugins/<plugin>/shared/fuzzydroid/fuzzydroid/<plugin>/`.

## Testing on Windows

Most fuzzydroid developers use macOS. When modifying cross-platform code (anything in `fuzzydroid.common.platform`, `symlink`, or `venv`), test on a Windows 10+ machine before merging. If you can't, mark the PR `needs-windows-test` and ask someone else to verify.

## License

By contributing, you agree that your contributions will be licensed under Apache-2.0.
