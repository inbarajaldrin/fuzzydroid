# kicad setup

Use the plugin root supplied by the host. Run:

```bash
uv run --python 3.11 --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_kicad" \
  fzd-kicad --json setup --plugin-root "${CLAUDE_PLUGIN_ROOT}"
```

Setup detects KiCad through PATH, `KICAD_CLI`, or platform install locations. It
creates/reuses the per-plugin fuzzydroid venv, installs the package, builds the pinned
official stable Python bindings for KiCad 10, writes a user-level plugin loader,
and records `kicad.toml`. It does not modify the KiCad application bundle or silently
restart an editor. Existing unrelated loader files are preserved.

For a nonstandard installation add `--kicad-cli <path>` and/or `--plugin-dir <path>`.
The embedded backend is qualified for KiCad 10. For KiCad 9/11 use `--no-native`;
their IPC behavior still needs version-specific validation.

When setup succeeds, explain any required manual step: restart PCB Editor when
the open work can be saved and enable the official API under Preferences >
Plugins. Preserve open work rather than restarting silently. Once those steps
are complete, read `<plugin-root>/skills/kicad/references/workflows/doctor.md` and run its workflow
yourself. The user does not need to invoke another skill. Resume the original
request after the required checks pass. Explain specific failed prerequisites
from the returned JSON; don't substitute an author's paths or reinstall KiCad
automatically.
