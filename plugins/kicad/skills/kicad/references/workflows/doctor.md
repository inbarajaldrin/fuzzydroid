# kicad doctor

```bash
uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/scripts/run.py" --json doctor
```

Present the returned checks as a short table, separating install-artifact health
from IPC and native runtime availability. A closed editor is not a corrupt
installation. A native source/hash mismatch needs an editor restart; dependency
or editable-root drift requires the setup workflow. Read
`<plugin-root>/skills/kicad/references/workflows/setup.md` and follow it yourself when that repair is
needed; do not ask the user to invoke a separate skill.

If the launcher refuses to start because setup state or its recorded environment
is missing, run the diagnostic from this checkout through the bootstrap path:

```bash
uv run --python 3.11 --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_kicad" \
  fzd-kicad --json doctor
```

Read `data.checks[*].ok` to assess health. The outer `ok` means the diagnostic
completed; it can be true while individual checks fail. Resolve those failures
or explain the specific required manual step before resuming the original task.

Multiple live processes require an explicit `--instance <pid>` for native calls.
Report the currently tested platform and version; do not call untested platforms
qualified.
