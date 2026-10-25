# The Fusion palette pattern — full architecture

```
┌────────────────────────── Fusion 360 process ─────────────────────────┐
│  fusion_bridge add-in                    Palette (ui.palettes.add)    │
│  UDS ~/.config/fuzzydroid/…sock ◀─┐      = embedded Chromium showing  │
│  exec_python → MAIN thread        │      http://127.0.0.1:<port>/     │
└───────────────────────────────────┼──────────────▲────────────────────┘
                                    │              │ fetch / SSE
                              JSON lines           │
                                    │              │
                        ┌───────────┴──────────────┴───────┐
                        │  panel server (stdlib http)      │◀── agents (curl/POST)
                        │  ops / endpoints / broadcast     │◀── external browsers
                        └──────────────────────────────────┘
```

Why this shape (vs `adsk.fusionSendData` palette↔add-in events): the page is a
plain web app — no Fusion-side JS bus, works in external browsers and over
Tailscale, agents get the same API for free, and the server restarts without
touching Fusion.

## Bridge contract (what the server may send)

Newline-delimited JSON to the socket advertised in
`~/.config/fuzzydroid/fusion_bridge.json` (UDS on macOS, TCP 8765-8775 on
Windows). The two commands panels need:

- `{"cmd": "exec_python", "code": "..."}` → `{"status": "ok", "output": "<stdout>"}`.
  Code runs on Fusion's MAIN thread (CustomEvent marshaling — the Fusion API is
  not thread-safe). Convention: code prints exactly one JSON line; client
  parses the LAST stdout line (`exec_json`). Errors come back as stdout
  starting `ERROR:` — raise, don't parse.
- `{"cmd": "ping"}` — fast path, does NOT touch the main thread. Ping success
  + exec timeout = Fusion has a modal dialog up or is mid-solve. Surface that
  hint to the user; don't retry-hammer.

One connection per request is fine; hold a server-side lock so bridge traffic
serializes (the bridge queues to one thread anyway).

## Palette lifecycle

Create/replace (via exec_json, from the server at startup):

```python
p = ui.palettes.itemById(pid)
if p: p.deleteMe()
p = ui.palettes.add(pid, title, url, True, True, True, width, height)
p.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
```

- IDs: `fzd<CamelName>`. Recreating with the same id after `deleteMe()` is the
  reliable "reload" — palettes keep no state, the page is the state.
- Palettes are **global UI**: they survive document switches and show whatever
  the URL serves. Panels that must track the active doc re-scan on demand
  (Rescan button) — see robot-jog's profile matching.
- Server restart ⇒ the palette shows a connection error until recreated; the
  server reopens it at startup, so "restart server" is the full recovery story.
- Fusion crash ⇒ bridge socket dies (connection refused, stale discovery
  file). Recovery: relaunch Fusion (`open -a "Autodesk Fusion"`), wait for
  ping (add-in autoloads), reopen the doc (`open_file` bridge cmd), restart
  the panel server.

## Live sync (SSE)

- `GET /api/events` — `text/event-stream`; one `queue.Queue` per subscriber,
  15 s keepalive comments, drop subscriber on write failure.
- Server broadcasts after EVERY mutation it performs → palette, external
  tabs, and agent-driven changes all converge. Client applies a broadcast
  only to widgets the user isn't actively dragging (skip keys with pending
  sends).
- Changes made INSIDE Fusion (user drags a joint, edits a param) are invisible
  to the server — add a poll loop that re-reads known state when idle
  (`lock.acquire(blocking=False)`; skip the tick if a mutation is in flight)
  and broadcasts on change. 4 s is a good period.
- Client sends coalesce: one request in flight, latest value per key wins
  (see jog `ui/index.html::pump`).

## Write-then-read-back

Fusion's assembly solver may CLAMP a requested joint/param value near limits,
or revert the whole solve if a big jump lands on an infeasible configuration
(observed on RG2: jump to the exact CAD limit reverted; stepwise approach
clamped). Therefore every write op reads the post-solve value in the SAME
exec payload and returns it; the server records and broadcasts the ACTUAL
value. Never trust the request.

## When to add a registration layer

The scaffold's op registry (`@op`) covers process panels: each op = button +
endpoint. When a panel must adapt to *what's in the document* (robots, fixture
families, part libraries), add data-driven registration like robot-jog's
`profiles/*.json`: match rules against the scanned doc, render one section per
match, keep user overrides in `~/.config/fuzzydroid/<panel>_profiles/`. Code
stays generic; new hardware is a JSON file.

## Port conventions

| Port | Owner |
|---|---|
| 8090 | urdf viewer (`viewer/urdf/serve_urdf.py`) |
| 8091-2 | urdf viewer extra instances |
| 8093 | robot jog (`jog/serve_jog.py`) |
| 8094+ | scaffolded panels |

## Checklist for shipping a panel

- [ ] Ops tested headless (`--no-palette` + curl) before palette work
- [ ] All writes read back actuals; errors list surfaced in UI status
- [ ] Bridge lock around every bridge call; deg/mm at the API boundary
- [ ] SSE broadcast after each mutation; poll loop if in-Fusion edits matter
- [ ] Busy-Fusion error message tells the user to close the dialog and retry
- [ ] No document saves; no Fusion API imports server-side
- [ ] README in the panel dir; port noted in the table above
