---
description: Install the KiCad CLI, configure the embedded bridge loader, and record portable setup state.
allowed-tools: [Bash, Read]
---

# /kicad:setup

Use the plugin root supplied by the host. Run:

```bash
uv run --python 3.11 --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_kicad" \
  fzd-kicad --json setup --plugin-root "${CLAUDE_PLUGIN_ROOT}"
```

Setup detects KiCad through PATH, `KICAD_CLI`, or platform install locations. It
creates/reuses the shared fuzzydroid venv, installs the package, builds the pinned
official stable Python bindings for KiCad 10, writes a user-level plugin loader,
and records `kicad.toml`. It does not modify the KiCad application bundle or silently
restart an editor. Existing unrelated loader files are preserved.

For a nonstandard installation add `--kicad-cli <path>` and/or `--plugin-dir <path>`.
The embedded backend is qualified for KiCad 10. For KiCad 9/11 use `--no-native`;
their IPC behavior still needs version-specific validation.

When setup succeeds, restart PCB Editor when the open work can be saved, enable
the official API under Preferences > Plugins, and run `/kicad:doctor`. Explain any
specific failed prerequisite from the returned JSON. Don't substitute an author's
paths or reinstall KiCad automatically.
