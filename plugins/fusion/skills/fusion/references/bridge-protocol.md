# Fusion Bridge — TCP Wire Protocol

Reference for the TCP protocol between the CLI and the `fusion_bridge` add-in.
Agents normally never see this layer — they call the CLI, which serialises to JSON
and sends here. Documented for: low-level debugging, writing custom clients, and
understanding why certain failures look the way they do.

## Architecture

```
CLI (Python)
  │
  ▼
TCP socket :8765  (newline-delimited JSON, one command per connection)
  │
  ▼
fusion_bridge add-in  (runs inside Fusion 360 on the main UI thread via CustomEvent)
  │
  ▼
Fusion 360 API  (adsk.core, adsk.fusion, adsk.cam)
```

The CLI never imports the Fusion API directly. Every operation is one JSON line
sent over TCP. The bridge marshals all API calls onto Fusion's main UI thread
(threading directly into the Fusion API crashes the process).

## Connection lifecycle

One command per TCP connection:

1. CLI opens a socket to `127.0.0.1:8765`.
2. CLI sends one JSON object on one line, terminated by `\n`.
3. Bridge enqueues the command via `app.fireCustomEvent`.
4. Bridge handler runs on the main UI thread, executes the command, writes the
   response to the socket.
5. CLI reads one JSON line.
6. CLI closes the socket.

No streaming, no keepalive, no pipelining. Each call is a fresh connection.

## Request format

```json
{"cmd": "<command_name>", "key1": "value1", "key2": ...}
```

## Response format

```json
{"status": "ok", "data": ...}
{"status": "error", "message": "<description>"}
```

The `status` field is always present. Other top-level fields depend on the command.

## Supported commands (19)

### Connectivity

| Command | Payload | Returns |
|---|---|---|
| `ping` | `{}` | `{"status": "ok", "message": "pong", "pid": <fusion_pid>}` |

### Project / file operations

| Command | Payload | Description |
|---|---|---|
| `list_projects` | `{}` | All projects in the active Fusion data hub |
| `open_file` | `{"project": "...", "file": "...", "folders": [...]}` | Open a file (folders = list, may be empty) |
| `search_files` | `{"term": "..."}` | Live search across all projects (slow) |
| `cache_files` | `{}` | Build a local index of every project file |
| `search_cached` | `{"term": "..."}` | Search the cached index (instant) |

### Design inspection

| Command | Payload | Returns |
|---|---|---|
| `get_document` | `{}` | `{name, path, units, isSaved}` for the active doc |
| `list_bodies` | `{}` | All BRep bodies in the active design |
| `list_components` | `{}` | All component occurrences |
| `get_bounding_box` | `{}` | `{min: [x,y,z], max: [x,y,z]}` in **cm** |
| `get_timeline` | `{}` | The design's feature history |

### Export

| Command | Payload | Description |
|---|---|---|
| `export_step` | `{"path": "..."}` | Export active design as STEP |
| `export_stl` | `{"path": "..."}` | Export active design as STL — **mm units** |
| `export_f3d` | `{"path": "..."}` | Export as F3D archive |

URDF and USD are not single bridge commands — they're orchestrated client-side by
the CLI, which runs `scripts/export_urdf.py` (URDF) or `scripts/export_usd.py`
(USD) via `exec_python`.

### Generic API

| Command | Payload | Notes |
|---|---|---|
| `api_call` | `{"api_path": "...", "args": [...], "kwargs": {...}, "store_as": "...", "return_properties": [...]}` | Call any Fusion API method by dotted path |
| `api_docs` | `{"search_term": "...", "category": "<class>", "max_results": 5}` | Search bundled API docstrings |
| `online_docs` | `{"class_name": "...", "member_name": "..."}` | Return the Autodesk online docs URL |
| `exec_python` | `{"code": "...", "session_id": "...", "persistent": false}` | Execute arbitrary Python in Fusion's runtime |
| `clear_context` | `{}` | Drop all `store_as` references |

`store_as` lets you chain calls without re-resolving objects:

```json
{"cmd": "api_call", "api_path": "rootComponent.sketches.add",
 "args": ["rootComponent.xYConstructionPlane"], "store_as": "sketch1"}
{"cmd": "api_call", "api_path": "sketch1.sketchCurves.sketchLines.addByTwoPoints",
 "args": [[0,0,0], [1,0,0]]}
```

## Error handling

All errors arrive as `{"status": "error", "message": "..."}`. Common shapes:

- **Connection refused** — Fusion isn't running, or the `fusion_bridge` add-in
  isn't loaded. Tell the user; point them at `/fusion:doctor`.
- **`{"status": "error", "message": "No active document"}`** — they need to open
  a file first.
- **`{"status": "error", "message": "Command 'X' not recognised"}`** — typo in
  the JSON `cmd` field, or the bridge add-in is older than the CLI.
- Python exceptions raised inside `exec_python` come back as
  `{"status": "error", "message": str(exc), "traceback": "..."}`.

## Environment variables

| Variable | Default | Used by |
|---|---|---|
| `FUSION_BRIDGE_HOST` | `127.0.0.1` | CLI |
| `FUSION_BRIDGE_PORT` | `8765` | CLI |
| `FUSION_BRIDGE_TIMEOUT` | `120` (seconds) | CLI |
| `CLAUDE_PLUGIN_ROOT` | (unset) | CLI's URDF export to locate `scripts/export_urdf.py` |

## Add-in location

The bridge add-in lives at `plugins/fusion/addin/fusion_bridge/` and is symlinked
into Fusion's AddIns directory by `/fusion:setup`:

- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/fusion_bridge`
- Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\fusion_bridge`

The user enables it once via **Shift+S → Add-Ins → fusion_bridge → Run** (with
**Run on Startup** ticked). After that, subsequent Fusion launches auto-load the
bridge.
