# fuzzydroid-fusion (plugin Python package)

The fusion plugin's Python code: the `fzd-fusion` CLI, the bridge client that
talks to the `fusion_bridge` add-in inside Fusion 360, and the `../../skills/fusion/references/workflows/setup.md` /
`../../skills/fusion/references/workflows/doctor.md` plumbing.

Installed editable by `../../skills/fusion/references/workflows/setup.md` into the plugin's own venv at
`~/.local/share/fuzzydroid/fusion/venv` (Windows:
`%LOCALAPPDATA%\fuzzydroid\fusion\venv`). Each fuzzydroid plugin owns its venv —
there is no shared install unit, so one plugin's dependencies or reinstalls can
never break another's.

## Layout

```
fuzzydroid_fusion/
├── _common.py       # vendored fleet plumbing (master: tools/common/_common.py)
├── _symlink.py      # cross-platform dir symlink/junction (add-in install)
├── _logbook.py      # prefixed logger for setup/doctor output
├── cli.py           # fzd-fusion CLI (click)
├── setup.py         # ../../skills/fusion/references/workflows/setup.md orchestrator
├── doctor.py        # ../../skills/fusion/references/workflows/doctor.md health checks
├── core/
│   ├── bridge.py    # endpoint discovery + JSON protocol client (UDS/TCP)
│   └── session.py   # CLI session state (undo/redo, history)
└── utils/
    └── repl_skin.py # REPL terminal skin
```

`_common.py` is a byte-identical vendored copy of `tools/common/_common.py` at
the repo root — edit the master, re-vendor, and let `tools/check_common_sync.py`
verify. Everything else in this package is fusion-specific.

## Editable install (for development)

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e .
uv pip install --python .venv/bin/python pytest
.venv/bin/python -m pytest tests -v
```

## CLI

The console script is `fzd-fusion`. Run `fzd-fusion --help`, or bare
`fzd-fusion` for the interactive REPL.
