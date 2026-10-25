---
name: kicad
description: Main entry point for KiCad work. Handle setup, diagnostics, live PCB inspection and editing, library footprints and 3D models, native viewer tools, rendering, fabrication exports, and Fusion handoff. Route requests to the needed workflow automatically so users do not need separate setup or doctor invocations. Uses the fuzzydroid CLI/MCP with official IPC and an embedded main-thread bridge.
---

## Agent host compatibility

This skill works in Claude Code and Codex. Resolve symlinks on this file; the
plugin root is three parent directories above this `SKILL.md`. Use that absolute
root for `plugins/<plugin>/...` examples, regardless of the working directory.
When `CLAUDE_PLUGIN_ROOT` is unavailable, pass the resolved root under that name
to commands that use it. Use the host's equivalent tools for `Bash`, `Read`,
`WebFetch` and user questions. In Codex, `$plugin:skill` invokes the sibling skill
named by a `/plugin:skill` reference. Read sibling `SKILL.md` files directly when
needed; do not assume another host's slash commands exist.

# KiCad automation

Drive the installed `fzd-kicad` CLI or equivalent MCP tools. Users describe the
goal in normal language; the explicit entry point is `/kicad:kicad` in Claude
Code or `$kicad:kicad` in Codex. Handle setup, health checks, editing, verification,
and exports within the same task. Separate setup and doctor skills remain
optional direct entry points, not required user handoffs.

## Route internally and establish readiness

Resolve the plugin root from this file and read the relevant workflow yourself.
Use the host's skill loader when available, or read the files with its file tools.
Do not stop after naming another skill or ask the user to invoke it.

| Situation or goal | Workflow to load |
|---|---|
| First use, missing state/venv, or launcher reports another checkout | `skills/setup/SKILL.md` from the plugin root |
| Diagnose installation, connectivity, decoding, dependency drift, or stale bridge code | `skills/doctor/SKILL.md` from the plugin root |
| Inspect or edit the active PCB, add footprints/models, or operate native tools | Discover schemas and use the control paths below |
| Render or export a live board snapshot | `ipc.export` using its discovered schema |
| Generate fabrication files or hand the PCB model to Fusion | `references/handoff.md` relative to this skill |
| Register project-specific native tools or panels | `references/architecture.md` relative to this skill |
| Determine supported platforms, versions, or schematic limitations | `references/compatibility.md` relative to this skill |

1. Check the per-platform `kicad.toml` state and the launcher. If setup is missing
   or bound to a different plugin root, follow the setup workflow before editing.
   Setup bootstraps through `uv`; it does not require the MCP server to start first.
2. Discover the live backends and inspect the board. If a required backend fails,
   run doctor and distinguish an installation problem from a closed editor,
   disabled API, ambiguous instance, or a bridge that needs an editor restart.
3. Read each diagnostic's `data.checks[*].ok`; the outer CLI `ok` indicates that
   the diagnostic ran, not that every health check passed. Apply the documented
   repair within the request and resume discovery once its prerequisites hold.
4. Ask only for missing project facts, an ambiguous board/instance, or a necessary
   manual application step. Preserve open work: do not silently restart KiCad,
   overwrite an unrelated loader, or reinstall the application.

When a task combines editing, export, and Fusion handoff, keep the same inspected
board path through every stage and read back each result before continuing.

## Connect before editing

Use MCP `bridge__instances` and `ipc__inspect`, or the CLI launcher:

```bash
uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/scripts/run.py" --json tools
```

The launcher reads the installed plugin venv from `kicad.toml`; don't assume an
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

For PCB fabrication exports and a mechanical import into Fusion, use the bounded
`handoff` CLI workflow described in [references/handoff.md](references/handoff.md).
It gates output on ERC/DRC/parity and writes a hash-linked validation receipt.

The native panel's buttons and native MCP/CLI calls use the same registry.
Project tools register through the public contract described in
[references/architecture.md](references/architecture.md). New capabilities should
be small composable tools, not duplicated UI-only handlers.

On connection, decoding, stale-source, or installation failures, load
`skills/doctor/SKILL.md` from the plugin root and follow it within the task.
Detailed version boundaries, setup behavior and the tested workflow are in
[references/compatibility.md](references/compatibility.md).

Do not describe this as complete KiCad control. The qualified embedded backend
uses KiCad 10's legacy bindings; live schematic editing and arbitrary C++ internals
are not established. Don't overwrite an open board file behind the editor.
