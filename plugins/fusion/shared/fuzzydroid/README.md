# fuzzydroid (shared Python package)

This is the monorepo-internal pip package that ships shared Python code for all fuzzydroid Claude Code plugins. It is installed editable by each plugin's `/setup` command into a user-level shared venv.

## Layout

```
fuzzydroid/
├── common/              # cross-plugin: platform detection, venv mgmt, symlink, config, logging
├── fusion/              # fusion plugin (Fusion 360 CLI + setup/doctor)
├── urdf/                # (future) urdf plugin
└── ...
```

## Editable install (for development)

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e .
uv pip install --python .venv/bin/python pytest
.venv/bin/python -m pytest tests -v
```

## Why shared?

Every fuzzydroid plugin will want: platform detection, venv management, symlink creation, TOML state file I/O, and a shared log format. Putting these in a single package means one implementation, one test suite, atomic refactors when conventions evolve.
