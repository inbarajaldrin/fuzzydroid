---
description: Health check for the isaaclab plugin - state-file-driven rows (components setup didn't record read N/A, never FAIL), isaaclab dist probe via the recorded python, omni-kit-mcp checkout, and the static-TLS guard-rule scan. Prints a markdown table.
allowed-tools: [Bash, Read]
---

# /isaaclab:doctor

Diagnose the isaaclab plugin install on this machine.

## Execute

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaaclab" \
    python -m fuzzydroid_isaaclab.doctor
```

Exit code `0` when every recorded component is healthy, `1` otherwise.

## Row semantics

Rows are **driven by the state file** — a component the setup did not record
reads `N/A`, never ❌. One exception, deliberately: the **static-TLS guard
rule** row FAILS if the Lab venv's `activate` exports the
`glibc.rtld.optional_static_tls` tunable, even though setup never puts it
there — its presence breaks every Lab standalone run on this box (PhysX GPU
dispatcher thread can't start; reset() hangs forever).

| row | pass condition |
|---|---|
| state file | `~/.config/fuzzydroid/isaaclab.toml` exists and parses |
| plugin venv / pyproject drift | recorded plugin venv healthy, bundled deps unchanged |
| lab root | the recorded venv/checkout still exists |
| isaaclab dist | `import isaaclab` succeeds under the recorded `lab_python` — shows the runtime version + an inline note when the import resolves outside the venv (source checkout shadowing the pip dist); falls back to dist metadata (⚠️) when import fails |
| static-TLS guard rule | no blanket tunable export in the venv `activate` |
| omni-kit-mcp checkout | recorded path still contains `exts/omni.kit.mcp` |
| mcp port | recorded (informational — only live during a run) |

## Acting on failures

- **state file missing** → run `/isaaclab:setup`.
- **lab root / isaaclab dist gone** → the env was moved or rebuilt; re-run `/isaaclab:setup` to re-detect and re-record.
- **static-TLS guard rule ❌** → edit the venv's `bin/activate` and remove the `GLIBC_TUNABLES`/`optional_static_tls` export. Guards belong in per-profile launchers (isaac-ctl full-app profile), never blanket env files.
- **omni-kit-mcp checkout ❌/N/A** → re-run step 3 of `/isaaclab:setup`.
