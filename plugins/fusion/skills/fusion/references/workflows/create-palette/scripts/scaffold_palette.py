#!/usr/bin/env python3
"""Scaffold a new Fusion 360 palette control panel.

Stamps a self-contained, immediately runnable panel following the fuzzydroid
palette pattern (see the create-palette skill): a stdlib HTTP server that
serves an embedded-browser palette INSIDE Fusion and drives the Fusion API
live through the fusion_bridge add-in, with an op registry ("register once —
UI button + agent JSON API + SSE live sync all come from the same entry").

Usage:
    python3 scaffold_palette.py my_panel --title "My Panel" --port 8094 \
        [--dest /path/to/parent-dir]

Creates:
    <dest>/<name>/
        panel.py        # single-file server: bridge client + op registry + SSE
        ui/index.html   # palette page: auto-renders one card per op
        README.md

Then: `python3 <name>/panel.py` opens the docked palette in Fusion.
Add ops in panel.py with @op(...); the UI picks them up on reload.
"""

import argparse
import re
import sys
from pathlib import Path

PANEL_TEMPLATE = '''#!/usr/bin/env python3
"""%(title)s — a Fusion 360 palette control panel (fuzzydroid palette pattern).

    python3 panel.py [--port %(port)d] [--no-palette] [--browser]

Register ops with @op(...) below. Every op automatically becomes:
  - a card with a Run button in the palette UI,
  - an agent-callable endpoint: POST /api/run {"op": "<name>", "params": {...}},
  - a broadcast source: its return dict is pushed to all pages over SSE.
Ops run Fusion code via exec_py()/exec_json() — marshaled to Fusion's MAIN
thread by the fusion_bridge add-in (Fusion API is not thread-safe).
Units inside Fusion: lengths cm, angles radians.
"""

import argparse
import json
import os
import queue
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── fusion_bridge client (endpoint discovery + newline-JSON over UDS/TCP) ────

def _discovery():
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming")) \\
        if os.name == "nt" else Path.home() / ".config"
    path = base / "fuzzydroid" / "fusion_bridge.json"
    if not path.exists():
        raise ConnectionError(f"bridge discovery file missing: {path} — "
                              f"is the fusion_bridge add-in running in Fusion?")
    return json.loads(path.read_text())


def bridge_request(payload, timeout=60.0):
    info = _discovery()
    if info.get("transport") == "tcp":
        s = socket.create_connection((info["host"], info["port"]), timeout=timeout)
    else:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(info["path"])
    try:
        s.sendall((json.dumps(payload) + "\\n").encode())
        buf = b""
        while b"\\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                raise ConnectionError("bridge closed connection")
            buf += chunk
        return json.loads(buf.split(b"\\n", 1)[0])
    finally:
        s.close()


def exec_py(code, timeout=60.0):
    """Run Python inside Fusion (main thread). Returns captured stdout."""
    r = bridge_request({"cmd": "exec_python", "code": code}, timeout)
    if r.get("status") != "ok":
        raise RuntimeError(r.get("message", str(r)))
    out = r.get("output", "")
    if out.startswith("ERROR:"):
        raise RuntimeError(out)
    return out


def exec_json(code, timeout=60.0):
    """exec_py + parse the LAST stdout line as JSON (code must print it)."""
    out = exec_py(code, timeout).strip()
    if not out:
        raise RuntimeError("fusion code printed nothing")
    return json.loads(out.splitlines()[-1])


# ── op registry: register once → UI card + agent API + SSE broadcast ─────────

OPS = {}


def op(name, description, params=None):
    """params: optional {name: {"type": ..., "default": ...}} hint for the UI."""
    def deco(fn):
        OPS[name] = {"fn": fn, "description": description, "params": params or {}}
        return fn
    return deco


# ═══════════════ YOUR OPS — replace/extend these ═══════════════

@op("doc_info", "Read the active document's name and object counts")
def doc_info():
    return exec_json(r"""
import adsk.core, adsk.fusion, json
app = adsk.core.Application.get()
doc = app.activeDocument
design = adsk.fusion.Design.cast(app.activeProduct)
print(json.dumps({
    "doc": doc.name if doc else None,
    "bodies": design.rootComponent.bRepBodies.count if design else 0,
    "occurrences": design.rootComponent.allOccurrences.count if design else 0,
    "joints": design.rootComponent.joints.count if design else 0,
}))
""")


@op("fit_view", "Fit the viewport to the model")
def fit_view():
    exec_py("adsk.core.Application.get().activeViewport.fit()")
    return {"ok": True}

# ═══════════════════════════════════════════════════════════════


# ── live sync (SSE) ──────────────────────────────────────────────────────────

_SUBS, _SUBS_LOCK = [], threading.Lock()
_BRIDGE_LOCK = threading.Lock()   # serialize bridge traffic


def broadcast(obj):
    with _SUBS_LOCK:
        for q in _SUBS:
            try:
                q.put_nowait(obj)
            except queue.Full:
                pass


# ── HTTP layer ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            html = (HERE / "ui" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif path == "/api/ops":
            self._json({"status": "ok", "title": %(title)r, "ops": {
                k: {"description": v["description"], "params": v["params"]}
                for k, v in OPS.items()}})
        elif path == "/api/events":
            self._sse()
        else:
            self._json({"status": "error", "message": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or b"{}")
        if self.path != "/api/run":
            self._json({"status": "error", "message": "not found"}, 404)
            return
        name = data.get("op")
        if name not in OPS:
            self._json({"status": "error", "message": f"unknown op: {name}"}, 400)
            return
        try:
            with _BRIDGE_LOCK:
                result = OPS[name]["fn"](**data.get("params", {}))
            broadcast({"type": "op_result", "op": name, "result": result})
            self._json({"status": "ok", "result": result})
        except Exception as e:
            self._json({"status": "error", "message": str(e)}, 500)

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        q = queue.Queue(maxsize=64)
        with _SUBS_LOCK:
            _SUBS.append(q)
        try:
            while True:
                try:
                    item = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": keepalive\\n\\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(f"data: {json.dumps(item)}\\n\\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _SUBS_LOCK:
                if q in _SUBS:
                    _SUBS.remove(q)


PALETTE_CODE = r"""
import adsk.core, json
ui = adsk.core.Application.get().userInterface
pid = %(palette_id)r
p = ui.palettes.itemById(pid)
if p: p.deleteMe()
p = ui.palettes.add(pid, %(title)r, %%(url)r, True, True, True, 380, 560)
p.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
print(json.dumps({"palette": pid}))
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=%(port)d)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-palette", action="store_true")
    ap.add_argument("--browser", action="store_true")
    args = ap.parse_args()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"%(title)s serving on {url}  ops: {list(OPS)}")

    if not args.no_palette:
        def open_pal():
            try:
                exec_json(PALETTE_CODE %% {"url": url})
                print("palette opened inside Fusion (docked right)")
            except Exception as e:
                print(f"could not open palette ({e}) — open {url} in a browser")
        threading.Thread(target=open_pal, daemon=True).start()
    if args.browser:
        webbrowser.open(url)

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
'''

UI_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>%(title)s</title>
<style>
  :root { --bg:#1b1d1f; --panel:#26292c; --panel2:#2e3236; --line:#3a3f44;
          --text:#e8eaec; --dim:#9aa1a8; --accent:#4da3ff; --ok:#43c56f; --err:#e5604c; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font:13px/1.45 -apple-system,"Segoe UI",Roboto,sans-serif; }
  header { display:flex; align-items:center; gap:8px; padding:10px 12px;
           border-bottom:1px solid var(--line); position:sticky; top:0; background:var(--bg); }
  h1 { font-size:14px; margin:0; font-weight:600; }
  .card { margin:10px; background:var(--panel); border:1px solid var(--line);
          border-radius:10px; padding:10px 12px; }
  .card h2 { font-size:12px; margin:0 0 4px; color:var(--accent); }
  .card p { margin:0 0 8px; color:var(--dim); font-size:11px; }
  button { background:var(--accent); color:#08111c; border:none; border-radius:6px;
           padding:6px 14px; cursor:pointer; font-size:12px; font-weight:600; }
  textarea { width:100%%; background:var(--panel2); color:var(--text); border:1px solid var(--line);
             border-radius:6px; font:11px ui-monospace,Menlo,monospace; padding:6px; margin-bottom:8px; }
  pre { background:var(--panel2); border:1px solid var(--line); border-radius:6px; padding:8px;
        font-size:11px; white-space:pre-wrap; margin:8px 0 0; max-height:180px; overflow:auto; }
  #status { position:sticky; bottom:0; padding:7px 12px; font-size:11px; color:var(--dim);
            background:var(--bg); border-top:1px solid var(--line); }
  .ok { color:var(--ok); } .err { color:var(--err); }
</style>
</head>
<body>
<header><h1 id="title">%(title)s</h1></header>
<main id="main"></main>
<div id="status">connecting…</div>
<script>
'use strict';
const $ = id => document.getElementById(id);
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} :
    { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const j = await r.json();
  if (j.status === 'error') throw new Error(j.message);
  return j;
}
async function load() {
  const info = await api('/api/ops');
  $('title').textContent = info.title;
  const main = $('main');
  main.replaceChildren();
  for (const [name, meta] of Object.entries(info.ops)) {
    const card = document.createElement('div'); card.className = 'card';
    card.innerHTML = `<h2>${name}</h2><p>${meta.description}</p>`;
    let ta = null;
    if (Object.keys(meta.params).length) {
      ta = document.createElement('textarea'); ta.rows = 2;
      ta.value = JSON.stringify(Object.fromEntries(
        Object.entries(meta.params).map(([k, v]) => [k, v.default ?? null])));
      card.append(ta);
    }
    const btn = document.createElement('button'); btn.textContent = 'Run';
    const out = document.createElement('pre'); out.textContent = '';
    btn.onclick = async () => {
      try {
        $('status').textContent = name + ' running…';
        const params = ta ? JSON.parse(ta.value) : {};
        const r = await api('/api/run', { op: name, params });
        out.textContent = JSON.stringify(r.result, null, 2);
        $('status').innerHTML = '<span class="ok">idle</span>';
      } catch (e) {
        out.textContent = String(e.message || e);
        $('status').innerHTML = '<span class="err">' + (e.message || e) + '</span>';
      }
    };
    card.append(btn, out);
    main.append(card);
  }
  $('status').innerHTML = '<span class="ok">idle</span>';
}
/* Live sync: results of ops run by ANYONE (another page, an agent via the API)
   land here too. Extend applySync for your panel's widgets. */
function applySync(m) { $('status').textContent = 'update: ' + (m.op || m.type); }
new EventSource('/api/events').onmessage = e => { try { applySync(JSON.parse(e.data)); } catch(_){} };
load();
</script>
</body>
</html>
'''

README_TEMPLATE = '''# %(title)s

A Fusion 360 palette control panel (fuzzydroid palette pattern) scaffolded by
the `create-palette` skill.

```bash
python3 panel.py            # serves :%(port)d AND opens the docked palette in Fusion
python3 panel.py --no-palette --browser   # external browser only
```

- Add ops in `panel.py` with `@op("name", "description")` — each op instantly
  becomes a UI card, an agent endpoint (`POST /api/run {"op": ..., "params": ...}`),
  and an SSE broadcast source (`GET /api/events`).
- Ops call `exec_py()` / `exec_json()` to run code inside Fusion (main-thread
  marshaled by the fusion_bridge add-in). Fusion units: cm and radians.
- Replace `ui/index.html`'s generic card list with purpose-built widgets as the
  panel grows; keep all mutations flowing through `/api/run` so UI and agents
  stay on the same code path.

Stop: `lsof -ti tcp:%(port)d | xargs kill`
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('name', help='panel package name (snake_case)')
    ap.add_argument('--title', default=None, help='human title (default: from name)')
    ap.add_argument('--port', type=int, default=8094)
    ap.add_argument('--dest', default='.', help='parent directory (default: cwd)')
    args = ap.parse_args()

    if not re.fullmatch(r'[a-z][a-z0-9_]*', args.name):
        sys.exit('name must be snake_case (e.g. export_dashboard)')
    title = args.title or args.name.replace('_', ' ').title()
    palette_id = 'fzd' + ''.join(w.title() for w in args.name.split('_'))

    dest = Path(args.dest).resolve() / args.name
    if dest.exists():
        sys.exit(f'{dest} already exists — refusing to overwrite')
    (dest / 'ui').mkdir(parents=True)

    subs = {'title': title, 'port': args.port, 'palette_id': palette_id}
    (dest / 'panel.py').write_text(PANEL_TEMPLATE % subs)
    (dest / 'ui' / 'index.html').write_text(UI_TEMPLATE % subs)
    (dest / 'README.md').write_text(README_TEMPLATE % subs)

    print(f'scaffolded {dest}')
    print(f'  run:  python3 {dest / "panel.py"}')
    print(f'  then edit panel.py — add ops with @op(...)')


if __name__ == '__main__':
    main()
