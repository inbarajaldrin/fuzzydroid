---
name: kicad
description: Inspect and edit a live KiCad PCB, load component footprints and 3D models, control native viewer menus, render and export boards. Uses the fuzzydroid KiCad CLI/MCP with official IPC and an embedded main-thread bridge. Use for KiCad automation or /kicad:kicad.
---

# KiCad automation

Drive the installed `fzd-kicad` CLI or the equivalent MCP tools. Setup and health
commands are `/kicad:setup` and `/kicad:doctor`; ordinary requests are agent-driven.
For another agent host, resolve the plugin root from the real path of this
`SKILL.md` (three parent directories). Substitute that root in examples when
`CLAUDE_PLUGIN_ROOT` is unavailable.

## Connect before editing

Use MCP `bridge__instances` and `ipc__inspect`, or the CLI launcher:

```bash
uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/scripts/run.py" --json tools
```

The launcher reads the installed shared venv from `kicad.toml`; don't assume an
author's machine path. `tools` returns current names and JSON input schemas.
Native tools are discovered from the running bridge, including registered project
tools. Names are dotted in CLI (`native.inspect`) and double-underscored in MCP
(`native__inspect`). Refresh the client's tool list after new registrations.

Read the active board path from inspection and supply it as `board` on edits.
Multiple native processes require `--instance <pid>`. Official IPC uses
`KICAD_API_SOCKET` to select a non-default IPC endpoint. Never guess a board.

## Pick the control path explicitly

| Need | Tool/provider |
|---|---|
| Inspect existing footprints, tracks and nets | `ipc.inspect` |
| Move/rotate footprints with undo | `ipc.move` |
| Edit other exposed IPC items | `ipc.python` with `mutate=true` |
| Save the live board | `ipc.save` |
| Load a library footprint with its package model | `native.footprint_add` |
| Native windows, menus and 3D viewer commands | `native.windows`, `native.menus`, `native.menu_invoke` |
| Run Python inside KiCad | `native.python` |
| Show the shared native tool panel | `native.panel_show` |
| Render or export STEP from current live state | `ipc.export` |

Use IPC for supported edits: mutation scripts form one undo group and roll back
on error. Native Python runs in KiCad's main thread with `pcbnew`, `wx`, `board`
and `registry`; it has broader access and **no automatic undo/rollback**. Native
and IPC Python are execution interfaces for trusted local operator code, not
sandboxes. Don't retry a timed-out write automatically; inspect the outcome.

## Invoke and verify

Use the discovered schema with `call <tool> --params-file <file>`; `-` reads JSON
from stdin. Do not interpolate JSON or Python into shell commands. Python scripts
can instead be passed by filename:

```text
fzd-kicad --json exec script.py --board /absolute/board.kicad_pcb --mutate
fzd-kicad --json exec script.py --board /absolute/board.kicad_pcb --backend native
```

IPC Python receives `kicad`, `board`, `Vector2`, `Angle`, `Path` and `result`.
Set `result` for structured output; `print()` becomes `stdout`. The IPC runner
owns the commit: do not nest commits or save inside a mutation script.

Inspect before edits and read back afterward. Moving a footprint doesn't reroute
its tracks. Newly loaded footprints need pad-net assignments. Verify LED polarity,
package dimensions, connectivity and models. Save finished work and run KiCad's
checks. Snapshot DRC is generic; use the saved original project for custom rules.

Native menu commands resolve labels and owning menus dynamically. Never hardcode
numeric IDs from another run. A handled event is not proof of the resulting UI
state: read back windows or capture the actual render.

## Extend and troubleshoot

The native panel's buttons and native MCP/CLI calls use the same registry.
Project tools register through the public contract described in
[references/architecture.md](references/architecture.md). New capabilities should
be small composable tools, not duplicated UI-only handlers.

Run doctor on connection, decoding, stale-source or installation failures.
Detailed version boundaries, setup behavior and the tested workflow are in
[references/compatibility.md](references/compatibility.md).

Do not describe this as complete KiCad control. The qualified embedded backend
uses KiCad 10's legacy bindings; live schematic editing and arbitrary C++ internals
are not established. Don't overwrite an open board file behind the editor.
