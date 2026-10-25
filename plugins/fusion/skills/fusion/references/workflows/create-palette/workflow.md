> Internal workflow loaded by the main skill. The plugin root comes from
> that skill. Resolve this workflow's `references/`, `scripts/`, and
> `evals/` paths relative to this directory.

# Fusion Palette — build a control panel for any Fusion process

One pattern, any process: a **stdlib HTTP server** serves a web page; Fusion
shows that page as a **docked palette** (`ui.palettes.add` → embedded Chromium);
every operation goes `page → fetch → server → fusion_bridge socket →
exec_python on Fusion's MAIN thread`. Humans click, agents POST, both hit the
same entrance. Reference implementation: `plugins/fusion/jog/` (robot jog).

## Quick start — scaffold a new panel

```bash
python3 skills/fusion/references/workflows/create-palette/scripts/scaffold_palette.py export_dashboard \
    --title "Export Dashboard" --port 8094 --dest /path/to/parent
python3 /path/to/parent/export_dashboard/panel.py     # serves + docks palette
```

The scaffold is immediately runnable: two example ops (`doc_info`, `fit_view`),
a generic card UI that auto-renders every op, SSE wiring, and an embedded
bridge client. Verify with `curl -s localhost:8094/api/ops`.

## Workflow for a real panel

1. **Scaffold** (above). Pick a free port — 8090 urdf-viewer, 8093 robot-jog
   are taken by convention.
2. **Write ops** in `panel.py` with `@op("name", "description", params)`.
   Each op body calls `exec_py(code)` / `exec_json(code)` — Python that runs
   inside Fusion. Print ONE json line from Fusion code; return payload dicts.
3. **Test headless first**: `python3 panel.py --no-palette`, then curl
   `/api/run` with each op. Only then open the palette.
4. **Grow the UI** in `ui/index.html` — replace generic cards with purpose-built
   widgets (sliders, tables), but keep the iron rule: every widget action calls
   `/api/run` (or a dedicated endpoint on the server) — never duplicate logic
   client-side, so agents and humans stay on one code path.
5. **Live sync**: server-side, call `broadcast({...})` after any state change;
   page-side, extend `applySync`. For state changed inside Fusion itself
   (user drags/edits), add a poll loop like robot-jog's (`serve_jog.py::_poll_loop`).

## Iron rules (violating these is how panels rot)

- Fusion API calls ONLY inside `exec_py` payloads (main-thread marshaled).
  Never import `adsk` in the server.
- Fusion units: lengths **cm**, angles **radians**. Convert at the API boundary,
  speak mm/deg to humans.
- **Read back after write** — near limits Fusion's solver clamps or reverts;
  report what Fusion actually did, not what you asked (see jog's SET_CODE).
- Serialize bridge traffic (one lock) — the bridge queues to one main thread;
  parallel calls just interleave confusingly.
- Palettes are GLOBAL Fusion UI, not per-document. If the panel must adapt to
  the active doc, scan it (like robot-jog's profiles) rather than forking panels.
- Never save the user's document from a panel op unless explicitly asked.

## Deep dives

- `references/architecture.md` — the full pattern: palette lifecycle, bridge
  contract, SSE, error modes (busy Fusion, crash recovery), when to add
  registration/profiles, and how robot-jog applies all of it.
- Working examples: `plugins/fusion/jog/` (device-registry panel with IK),
  the scaffold output (op-registry panel).
