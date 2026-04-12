"""TCP Server command — starts a JSON TCP server on localhost:8765.

All commands are marshaled to Fusion's main UI thread via CustomEvent,
making it safe to call any Fusion API (including documents.open()).

Commands:
  {"cmd": "ping"}
  {"cmd": "get_document"}
  {"cmd": "list_projects"}
  {"cmd": "list_bodies"}
  {"cmd": "list_components"}
  {"cmd": "export_step", "path": "/tmp/out.step"}
  {"cmd": "export_stl", "path": "/tmp/out.stl"}
  {"cmd": "export_f3d", "path": "/tmp/out.f3d"}
  {"cmd": "open_file", "project": "...", "folders": [...], "file": "..."}
  {"cmd": "search_files", "term": "..."}
  {"cmd": "exec_python", "code": "...", "session_id": "...", "persistent": true}
  {"cmd": "get_bounding_box"}
  {"cmd": "get_timeline"}
  {"cmd": "api_call", "api_path": "rootComponent.sketches.add", "args": [...], "kwargs": {...}, "store_as": "name", "return_properties": [...]}
  {"cmd": "api_docs", "search_term": "...", "category": "class_name|member_name|description|all", "max_results": 5}
  {"cmd": "online_docs", "class_name": "...", "member_name": "..."}
  {"cmd": "clear_context"}
  {"cmd": "cache_files"}
  {"cmd": "search_cached", "term": "..."}
"""

import adsk.core
import adsk.fusion
import traceback
import json
import threading
import queue
import socket
import os
import sys
import io
import time
import inspect
import re
import urllib.request
import urllib.error
from pathlib import Path
from types import ModuleType, FunctionType

from ...lib import fusionAddInUtils as futil
from ... import config

# ── Constants ────────────────────────────────────────────────────────────────

CUSTOM_EVENT_ID = 'FusionBridgeRequestEvent'
TIMER_INTERVAL = 0.2  # 200ms backup timer

# Port range: try 8765-8775 (Chrome DevToolsActivePort pattern)
PORT_RANGE_START = 8765
PORT_RANGE_END = 8775
DISCOVERY_FILE_NAME = 'fusion_bridge.port'


# ── Port Discovery ────────────────────────────────────────────────────────────


def _get_discovery_file_path():
    """Return the path to the port discovery file.
    macOS: ~/.config/fuzzydroid/fusion_bridge.port
    Windows: %APPDATA%/fuzzydroid/fusion_bridge.port
    """
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:
        base = Path.home() / '.config'
    return base / 'fuzzydroid' / DISCOVERY_FILE_NAME


def _bind_with_fallback(server_socket, host='127.0.0.1'):
    """Try to bind to ports 8765-8775. Return the port that worked.
    Raises OSError if all ports are taken.
    """
    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        try:
            server_socket.bind((host, port))
            return port
        except OSError:
            continue
    raise OSError(f'All ports {PORT_RANGE_START}-{PORT_RANGE_END} are in use')


def _write_discovery_file(port):
    """Write the chosen port to the discovery file so clients can find us."""
    path = _get_discovery_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(port) + '\n')


def _cleanup_discovery_file():
    """Remove the discovery file on shutdown."""
    try:
        _get_discovery_file_path().unlink(missing_ok=True)
    except Exception:
        pass

# ── State ────────────────────────────────────────────────────────────────────

_BRIDGE_ENV_KEY = '_FUZZYDROID_BRIDGE_STARTED'
_stop_flag = False
_server_thread = None
_server_socket = None
_timer_thread = None
_custom_event = None
_event_handler = None
_work_queue = queue.Queue()

# Must hold references to prevent GC
_handlers = []

# Stored object context for api_call (persists across calls within a session)
_fusion_context = {}

# Persistent Python execution sessions
_python_sessions = {}


# ── Work Item ────────────────────────────────────────────────────────────────


class WorkItem:
    """A unit of work to be executed on the main thread."""
    __slots__ = ('data', 'result', 'done')

    def __init__(self, data):
        self.data = data
        self.result = None
        self.done = threading.Event()


# ── CustomEvent Handler (runs on main thread) ───────────────────────────────


class BridgeEventHandler(adsk.core.CustomEventHandler):
    """Handles the custom event on Fusion's main UI thread."""
    def __init__(self):
        super().__init__()

    def notify(self, args):
        """Drain the work queue — this runs on the MAIN THREAD."""
        _drain_queue()


def _drain_queue():
    """Process all pending work items. Must only be called from main thread."""
    while True:
        try:
            item = _work_queue.get_nowait()
        except queue.Empty:
            break
        try:
            item.result = _handle_command(item.data)
        except Exception as e:
            item.result = {
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc(),
            }
        finally:
            item.done.set()


# ── Dispatch (called from TCP background thread) ────────────────────────────


def _dispatch_to_main_thread(data, timeout=300):
    """Queue a command for main-thread execution. Blocks until done."""
    # Fast path: ping doesn't need main thread
    cmd = data.get('cmd', '')
    if cmd == 'ping':
        return {'status': 'ok', 'message': 'pong', 'pid': os.getpid()}

    item = WorkItem(data)
    _work_queue.put(item)

    # Poke the main thread
    try:
        app = adsk.core.Application.get()
        app.fireCustomEvent(CUSTOM_EVENT_ID, '')
    except Exception:
        pass  # backup timer will pick it up

    if not item.done.wait(timeout=timeout):
        return {'status': 'error', 'message': f'Timed out after {timeout}s waiting for main thread'}

    return item.result


# ── Backup Timer ─────────────────────────────────────────────────────────────


def _timer_loop():
    """Fire custom event every 200ms if work is pending. Guards against dropped events."""
    while not _stop_flag:
        time.sleep(TIMER_INTERVAL)
        if not _work_queue.empty():
            try:
                app = adsk.core.Application.get()
                app.fireCustomEvent(CUSTOM_EVENT_ID, '')
            except Exception:
                pass


# ── Entry Points ─────────────────────────────────────────────────────────────


def start():
    """Called when the add-in starts (MAIN THREAD). Registers event + launches TCP server."""
    global _stop_flag, _server_thread, _timer_thread, _custom_event, _event_handler

    if os.environ.get(_BRIDGE_ENV_KEY):
        if config.DEBUG:
            futil.log('Fusion Bridge: already running, skipping duplicate start()')
        return
    os.environ[_BRIDGE_ENV_KEY] = '1'

    _stop_flag = False

    # Register CustomEvent on the MAIN THREAD — this is critical
    app = adsk.core.Application.get()
    _custom_event = app.registerCustomEvent(CUSTOM_EVENT_ID)
    _event_handler = BridgeEventHandler()
    _custom_event.add(_event_handler)
    _handlers.append(_event_handler)  # prevent GC

    # Start backup timer thread
    _timer_thread = threading.Thread(target=_timer_loop, daemon=True)
    _timer_thread.start()

    # Start TCP server thread
    _server_thread = threading.Thread(target=_tcp_server, daemon=True)
    _server_thread.start()

    futil.log(f'Fusion Bridge: TCP server starting (port range {PORT_RANGE_START}-{PORT_RANGE_END})', force_console=True)


def stop():
    """Called when the add-in stops. Shuts down everything."""
    global _stop_flag, _server_socket, _custom_event, _event_handler

    os.environ.pop(_BRIDGE_ENV_KEY, None)
    _stop_flag = True

    # Unregister custom event
    if _custom_event:
        try:
            if _event_handler:
                _custom_event.remove(_event_handler)
            app = adsk.core.Application.get()
            app.unregisterCustomEvent(CUSTOM_EVENT_ID)
        except:
            pass
        _custom_event = None
        _event_handler = None

    _handlers.clear()

    # Close server socket
    if _server_socket:
        try:
            _server_socket.close()
        except:
            pass

    # Remove discovery file
    _cleanup_discovery_file()

    futil.log('Fusion Bridge: TCP server stopped')


# ── TCP Server ───────────────────────────────────────────────────────────────


def _tcp_server():
    """Run TCP server in a background thread."""
    global _stop_flag, _server_socket

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.settimeout(1.0)
    _server_socket = srv

    try:
        port = _bind_with_fallback(srv, config.HOST)
        srv.listen(5)
        _write_discovery_file(port)
        futil.log(f'Fusion Bridge: listening on {config.HOST}:{port}', force_console=True)
    except Exception as e:
        futil.log(f'Fusion Bridge: failed to bind — {e}', adsk.core.LogLevels.ErrorLogLevel, force_console=True)
        return

    while not _stop_flag:
        try:
            conn, addr = srv.accept()
            t = threading.Thread(target=_handle_client, args=(conn, addr), daemon=True)
            t.start()
        except socket.timeout:
            continue
        except Exception:
            if not _stop_flag:
                pass

    srv.close()


def _handle_client(conn, addr):
    """Handle a single TCP client connection."""
    try:
        buffer = ''
        while not _stop_flag:
            data = conn.recv(8192)
            if not data:
                break
            buffer += data.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    cmd_data = json.loads(line)
                except json.JSONDecodeError as e:
                    response = {'status': 'error', 'message': f'Invalid JSON: {e}'}
                    conn.sendall((json.dumps(response) + '\n').encode('utf-8'))
                    continue

                # Dispatch to main thread (blocks until done)
                result = _dispatch_to_main_thread(cmd_data)
                conn.sendall((json.dumps(result) + '\n').encode('utf-8'))
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except:
            pass


# ── Command Router (runs on MAIN THREAD via CustomEvent) ────────────────────


def _handle_command(data):
    """Route a command dict to the appropriate handler. Runs on main thread."""
    cmd = data.get('cmd', '')
    try:
        if cmd == 'ping':
            return {'status': 'ok', 'message': 'pong', 'pid': os.getpid()}
        elif cmd == 'get_document':
            return _cmd_get_document()
        elif cmd == 'list_projects':
            return _cmd_list_projects()
        elif cmd == 'list_bodies':
            return _cmd_list_bodies()
        elif cmd == 'list_components':
            return _cmd_list_components()
        elif cmd == 'export_step':
            return _cmd_export(data, 'step')
        elif cmd == 'export_stl':
            return _cmd_export(data, 'stl')
        elif cmd == 'export_f3d':
            return _cmd_export(data, 'f3d')
        elif cmd == 'open_file':
            return _cmd_open_file(data)
        elif cmd == 'search_files':
            return _cmd_search_files(data)
        elif cmd == 'exec_python':
            return _cmd_exec_python(data)
        elif cmd == 'get_bounding_box':
            return _cmd_get_bounding_box()
        elif cmd == 'get_timeline':
            return _cmd_get_timeline()
        elif cmd == 'api_call':
            return _cmd_api_call(data)
        elif cmd == 'api_docs':
            return _cmd_api_docs(data)
        elif cmd == 'online_docs':
            return _cmd_online_docs(data)
        elif cmd == 'clear_context':
            return _cmd_clear_context()
        elif cmd == 'cache_files':
            return _cmd_cache_files()
        elif cmd == 'search_cached':
            return _cmd_search_cached(data)
        else:
            return {'status': 'error', 'message': f'Unknown command: {cmd}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()}


# ── Command Handlers (all run on MAIN THREAD) ───────────────────────────────


def _cmd_get_document():
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if not doc:
        return {'status': 'error', 'message': 'No active document'}
    design = adsk.fusion.Design.cast(app.activeProduct)
    return {
        'status': 'ok',
        'name': doc.name,
        'bodies': design.rootComponent.bRepBodies.count if design else 0,
        'components': design.rootComponent.allOccurrences.count if design else 0,
    }


def _cmd_list_projects():
    app = adsk.core.Application.get()
    projects = [p.name for p in app.data.dataProjects]
    return {'status': 'ok', 'projects': projects}


def _cmd_list_bodies():
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {'status': 'error', 'message': 'No active design'}
    bodies = [b.name for b in design.rootComponent.bRepBodies]
    return {'status': 'ok', 'bodies': bodies}


def _cmd_list_components():
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {'status': 'error', 'message': 'No active design'}
    comps = [occ.name for occ in design.rootComponent.allOccurrences]
    return {'status': 'ok', 'components': comps}


def _cmd_export(data, fmt):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {'status': 'error', 'message': 'No active design'}

    doc = app.activeDocument
    safe_name = doc.name.replace(' ', '_').replace('/', '_')
    path = os.path.abspath(data.get('path', f'/tmp/{safe_name}.{fmt}'))

    root = design.rootComponent
    mgr = design.exportManager

    if fmt == 'step':
        opts = mgr.createSTEPExportOptions(path, root)
    elif fmt == 'stl':
        opts = mgr.createSTLExportOptions(root)
        opts.filename = path
    elif fmt == 'f3d':
        opts = mgr.createFusionArchiveExportOptions(path)
    else:
        return {'status': 'error', 'message': f'Unknown format: {fmt}'}

    mgr.execute(opts)
    size = os.path.getsize(path) if os.path.exists(path) else -1
    return {'status': 'ok', 'path': path, 'size': size, 'document': doc.name}


def _cmd_open_file(data):
    app = adsk.core.Application.get()
    ui = app.userInterface

    # Terminate any active command first (prevents conflicts)
    if ui.activeCommand != 'SelectCommand':
        ui.commandDefinitions.itemById('SelectCommand').execute()

    project_name = data.get('project', 'Default Project')
    folders = data.get('folders', [])
    file_name = data.get('file', '')

    proj = None
    for p in app.data.dataProjects:
        if p.name == project_name:
            proj = p
            break
    if not proj:
        return {'status': 'error', 'message': f'Project not found: {project_name}'}

    folder = proj.rootFolder
    for fname in folders:
        found = None
        for f in folder.dataFolders:
            if f.name == fname:
                found = f
                break
        if not found:
            return {'status': 'error', 'message': f'Folder not found: {fname}'}
        folder = found

    target = None
    for d in folder.dataFiles:
        if d.name == file_name:
            target = d
            break
    if not target:
        return {'status': 'error', 'message': f'File not found: {file_name}'}

    doc = app.documents.open(target)
    return {'status': 'ok', 'opened': doc.name}


def _cmd_search_files(data):
    app = adsk.core.Application.get()
    term = data.get('term', '').lower()
    results = []

    def scan(folder, path=''):
        for f in folder.dataFiles:
            full = f'{path}/{f.name}'
            if term in f.name.lower():
                results.append(full)
        for sf in folder.dataFolders:
            scan(sf, f'{path}/{sf.name}')

    for p in app.data.dataProjects:
        try:
            scan(p.rootFolder, p.name)
        except:
            pass

    return {'status': 'ok', 'term': term, 'matches': results, 'count': len(results)}


def _cmd_exec_python(data):
    code = data.get('code', '')
    session_id = data.get('session_id', 'default')
    persistent = data.get('persistent', False)

    old_stdout = sys.stdout
    sys.stdout = capture = io.StringIO()
    try:
        exec_globals = {'adsk': adsk, '__builtins__': __builtins__}
        # Restore persistent session variables if requested
        if persistent and session_id in _python_sessions:
            exec_globals.update(_python_sessions[session_id])
        exec(code, exec_globals)
        result_val = capture.getvalue()
        # Save session state if persistent
        if persistent:
            saved = {}
            for k, v in exec_globals.items():
                if k.startswith('_') or k in ('adsk', '__builtins__'):
                    continue
                try:
                    json.dumps(v)  # only save JSON-serializable values
                    saved[k] = v
                except (TypeError, ValueError):
                    saved[k] = v  # keep non-serializable in memory too
            _python_sessions[session_id] = saved
    except Exception as e:
        result_val = f'ERROR: {e}\n{traceback.format_exc()}'
    finally:
        sys.stdout = old_stdout

    result = {'status': 'ok', 'output': result_val}
    if persistent:
        result['session_id'] = session_id
        result['session_vars'] = list(_python_sessions.get(session_id, {}).keys())
    return result


def _cmd_get_bounding_box():
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {'status': 'error', 'message': 'No active design'}
    bbox = design.rootComponent.boundingBox
    return {
        'status': 'ok',
        'min': {'x': bbox.minPoint.x, 'y': bbox.minPoint.y, 'z': bbox.minPoint.z},
        'max': {'x': bbox.maxPoint.x, 'y': bbox.maxPoint.y, 'z': bbox.maxPoint.z},
    }


def _cmd_get_timeline():
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return {'status': 'error', 'message': 'No active design'}
    tl = design.timeline
    items = []
    for i in range(tl.count):
        item = tl.item(i)
        items.append({'index': i, 'name': item.name if hasattr(item, 'name') else str(i)})
    return {'status': 'ok', 'count': tl.count, 'items': items}


# ── Generic API Call ─────────────────────────────────────────────────────────


def _resolve_api_path(path):
    """Resolve a dotted API path to an actual Fusion object/method.

    Supports:
      - "app", "ui", "design", "rootComponent" as shortcuts
      - "app.activeDocument.name" — navigate from Application.get()
      - "$sketch1.sketchCurves" — stored object references
      - "adsk.core.Point3D.create" — full module paths
    """
    if not path:
        raise ValueError('api_path is required')

    # Stored object reference ($name or $name.rest)
    if path.startswith('$'):
        parts = path[1:].split('.', 1)
        obj = _fusion_context.get(parts[0])
        if obj is None:
            raise ValueError(f"Stored object '{parts[0]}' not found. Available: {list(_fusion_context.keys())}")
        return _navigate_path(obj, parts[1]) if len(parts) > 1 else obj

    # Full module paths
    if path.startswith('adsk.core.'):
        return _navigate_path(adsk.core, path[10:])
    if path.startswith('adsk.fusion.'):
        return _navigate_path(adsk.fusion, path[12:])

    # Shortcut roots
    app = adsk.core.Application.get()
    shortcuts = {
        'app': app,
        'ui': app.userInterface,
        'design': app.activeProduct,
        'rootComponent': adsk.fusion.Design.cast(app.activeProduct).rootComponent if app.activeProduct else None,
    }

    # Exact shortcut
    if path in shortcuts:
        return shortcuts[path]

    # Shortcut prefix
    for prefix, root in shortcuts.items():
        if path.startswith(prefix + '.'):
            if root is None:
                raise ValueError(f"Cannot resolve '{prefix}' — no active product")
            return _navigate_path(root, path[len(prefix) + 1:])

    # Default: navigate from app
    return _navigate_path(app, path)


def _navigate_path(obj, path):
    """Walk a dotted attribute path from obj."""
    for part in path.split('.'):
        if not part:
            continue
        # Support collection indexing: bodies[0]
        if '[' in part:
            attr_name, idx_str = part.split('[', 1)
            idx = int(idx_str.rstrip(']'))
            obj = getattr(obj, attr_name)
            obj = obj.item(idx) if hasattr(obj, 'item') else obj[idx]
        else:
            obj = getattr(obj, part)
        if obj is None:
            raise ValueError(f"Path resolved to None at '{part}'")
    return obj


def _resolve_argument(arg):
    """Resolve an argument that might be a literal, an API path, or a constructor.

    - None/bool/int/float → pass through
    - str with '.' or '$' → try API path resolution, fall back to literal string
    - dict with "type" key → construct a Fusion object (Point3D, Vector3D, etc.)
    - list → recursively resolve each element
    """
    if arg is None or isinstance(arg, (bool, int, float)):
        return arg

    if isinstance(arg, str):
        if '.' in arg or arg.startswith('$') or arg in ('app', 'ui', 'design', 'rootComponent'):
            try:
                return _resolve_api_path(arg)
            except Exception:
                return arg  # literal string
        return arg

    if isinstance(arg, dict) and 'type' in arg:
        return _construct_object(arg)

    if isinstance(arg, list):
        return [_resolve_argument(item) for item in arg]

    return arg


def _construct_object(spec):
    """Construct a Fusion API object from a dict spec.

    Example: {"type": "Point3D", "x": 1, "y": 2, "z": 3}
             → adsk.core.Point3D.create(1, 2, 3)
    """
    obj_type = spec.get('type', '')
    cls = getattr(adsk.core, obj_type, None) or getattr(adsk.fusion, obj_type, None)
    if cls is None:
        raise ValueError(f"Unknown type: {obj_type}")

    params = {k: v for k, v in spec.items() if k != 'type'}

    if hasattr(cls, 'create'):
        if obj_type in ('Point3D', 'Vector3D'):
            return cls.create(params.get('x', 0), params.get('y', 0), params.get('z', 0))
        if obj_type == 'Point2D':
            return cls.create(params.get('x', 0), params.get('y', 0))
        if obj_type == 'ValueInput':
            if 'real' in params:
                return cls.createByReal(params['real'])
            return cls.createByString(params.get('string', params.get('value', '0')))
        return cls.create(**params)

    return cls(**params)


def _extract_result_info(result, properties=None):
    """Extract readable info from a Fusion API result object."""
    if result is None:
        return 'None'
    if isinstance(result, (str, int, float, bool)):
        return str(result)

    if properties:
        info = {}
        for prop in properties:
            try:
                val = getattr(result, prop, None)
                if hasattr(val, 'count'):
                    info[prop] = val.count
                elif hasattr(val, 'name'):
                    info[prop] = val.name
                else:
                    info[prop] = str(val) if val is not None else None
            except Exception:
                info[prop] = '<error>'
        return info

    # Default info
    try:
        if hasattr(result, 'name'):
            return f"{type(result).__name__}(name='{result.name}')"
        if hasattr(result, 'count'):
            return f"{type(result).__name__}(count={result.count})"
        if hasattr(result, 'objectType'):
            return str(result.objectType)
        return type(result).__name__
    except Exception:
        return type(result).__name__


def _cmd_api_call(data):
    """Generic API path resolver — call any Fusion 360 API method.

    Request format:
      {"cmd": "api_call",
       "api_path": "rootComponent.sketches.add",
       "args": ["rootComponent.xYConstructionPlane"],
       "kwargs": {},
       "store_as": "sketch1",
       "return_properties": ["name", "isVisible"]}
    """
    api_path = data.get('api_path', '')
    args = data.get('args', [])
    kwargs = data.get('kwargs', {})
    store_as = data.get('store_as')
    return_properties = data.get('return_properties', [])

    target = _resolve_api_path(api_path)
    resolved_args = [_resolve_argument(a) for a in args]
    resolved_kwargs = {k: _resolve_argument(v) for k, v in kwargs.items()}

    if callable(target):
        result = target(*resolved_args, **resolved_kwargs)
    else:
        result = target  # property access

    if store_as:
        _fusion_context[store_as] = result

    info = _extract_result_info(result, return_properties if return_properties else None)

    resp = {
        'status': 'ok',
        'result': info,
        'type': type(result).__name__ if result is not None else 'None',
    }
    if store_as:
        resp['stored_as'] = store_as
    resp['context_keys'] = list(_fusion_context.keys())
    return resp


def _cmd_clear_context():
    """Clear all stored objects from the api_call context."""
    count = len(_fusion_context)
    _fusion_context.clear()
    return {'status': 'ok', 'cleared': count}


# ── API Documentation (runtime introspection) ───────────────────────────────


def _cmd_api_docs(data):
    """Search the live Fusion 360 API via introspection.

    Request: {"cmd": "api_docs", "search_term": "Sketch", "category": "class_name", "max_results": 5}
    Categories: class_name, member_name, description, all
    """
    search_term = data.get('search_term', '')
    category = data.get('category', 'class_name')
    max_results = data.get('max_results', 5)

    if not search_term:
        return {'status': 'error', 'message': 'search_term is required'}

    search_lower = search_term.lower()
    if search_lower.startswith('adsk.'):
        search_lower = search_lower[5:]

    # Split namespace.class.member if dotted
    namespace_prefix = None
    if '.' in search_lower:
        parts = search_lower.split('.', 1)
        namespace_prefix = parts[0]
        search_lower = parts[1]
        if '.' in search_lower:
            parts2 = search_lower.split('.', 1)
            search_lower = parts2[1]  # member name portion

    if category != 'description':
        search_lower = search_lower.split()[0] if search_lower else ''

    exact = []
    partial = []

    def short_doc(member, name):
        doc = getattr(member, '__doc__', '') or ''
        first = doc[:doc.find('.')].strip() if '.' in doc else doc.strip()
        return {'name': name, 'doc': first[:200]}

    def class_info(cls, ns):
        doc = (cls.__doc__ or '')[:500]
        props = []
        funcs = []
        for mname, mobj in cls.__dict__.items():
            if mname.startswith('_') or mname in ('thisown', 'cast'):
                continue
            if isinstance(mobj, property):
                props.append(short_doc(mobj, mname))
            elif isinstance(mobj, FunctionType):
                funcs.append(short_doc(mobj, mname))
        result = {'type': 'class', 'name': cls.__name__, 'namespace': f'adsk.{ns}', 'doc': doc}
        if props:
            result['properties'] = props[:15]
        if funcs:
            result['functions'] = funcs[:15]
        return result

    def func_info(func, cls_name, ns):
        result = {'type': 'function', 'name': func.__name__, 'class': cls_name, 'namespace': f'adsk.{ns}'}
        doc = (func.__doc__ or '')[:500]
        if doc:
            result['doc'] = doc
        try:
            sig = str(inspect.signature(func))
            sig = sig.replace('(self, ', '(').replace('(self)', '()')
            result['signature'] = sig
        except Exception:
            pass
        return result

    def prop_info(prop, pname, cls_name, ns):
        result = {'type': 'property', 'name': pname, 'class': cls_name, 'namespace': f'adsk.{ns}'}
        doc = (prop.__doc__ or '')[:500]
        if doc:
            result['doc'] = doc
        if prop.fset is None:
            result['readonly'] = True
        return result

    import adsk as adsk_root
    for ns_name, ns_mod in adsk_root.__dict__.items():
        if ns_name.startswith('_') or not isinstance(ns_mod, ModuleType):
            continue
        if namespace_prefix and namespace_prefix != ns_name.lower():
            continue

        for cls_name, cls_obj in ns_mod.__dict__.items():
            if cls_name.startswith('_') or not isinstance(cls_obj, type):
                continue

            cls_lower = cls_name.lower()

            if category in ('class_name', 'all'):
                if search_lower == cls_lower:
                    exact.append(('class', ns_name, cls_obj, None))
                elif search_lower in cls_lower:
                    partial.append(('class', ns_name, cls_obj, None))

            if category in ('description', 'all'):
                if search_lower in (cls_obj.__doc__ or '').lower():
                    partial.append(('class', ns_name, cls_obj, None))

            if category in ('member_name', 'description', 'all'):
                for mname, mobj in cls_obj.__dict__.items():
                    if mname.startswith('_') or mname in ('thisown', 'cast'):
                        continue
                    if not isinstance(mobj, (property, FunctionType)):
                        continue
                    if category in ('member_name', 'all') and search_lower in mname.lower():
                        bucket = exact if search_lower == mname.lower() else partial
                        bucket.append(('member', ns_name, cls_obj, mobj))
                    if category in ('description', 'all') and search_lower in (mobj.__doc__ or '').lower():
                        partial.append(('member', ns_name, cls_obj, mobj))

            if len(exact) >= max_results:
                break
        if len(exact) >= max_results:
            break

    results = []
    for match_type, ns_name, cls_obj, member_obj in (exact + partial)[:max_results]:
        if match_type == 'class':
            results.append(class_info(cls_obj, ns_name))
        elif isinstance(member_obj, property):
            pname = next((n for n, m in cls_obj.__dict__.items() if m is member_obj), '?')
            results.append(prop_info(member_obj, pname, cls_obj.__name__, ns_name))
        elif isinstance(member_obj, FunctionType):
            results.append(func_info(member_obj, cls_obj.__name__, ns_name))

    if not results:
        return {'status': 'ok', 'results': [], 'message': f"No results for '{search_term}' in category '{category}'"}
    return {'status': 'ok', 'results': results}


# ── Online Documentation (Autodesk cloudhelp) ───────────────────────────────


def _cmd_online_docs(data):
    """Fetch rich API docs from Autodesk's cloudhelp pages.

    Request: {"cmd": "online_docs", "class_name": "ExtrudeFeatures", "member_name": "createInput"}
    """
    class_name = data.get('class_name', '')
    member_name = data.get('member_name', '')

    if not class_name:
        return {'status': 'error', 'message': 'class_name is required'}

    base_url = 'https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files'
    filename = f"{class_name}_{member_name}.htm" if member_name else f"{class_name}.htm"
    url = f"{base_url}/{filename}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'FusionBridge/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')

        result = {'url': url, 'class_name': class_name}
        if member_name:
            result['member_name'] = member_name

        # Description
        m = re.search(r'<h2[^>]*>\s*Description\s*</h2>\s*<p>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        if m:
            result['description'] = re.sub(r'<[^>]+>', '', m.group(1)).strip()

        # Parameters table
        m = re.search(r'<h2[^>]*>\s*Parameters\s*</h2>(.*?)<h2', html, re.DOTALL | re.IGNORECASE)
        if m:
            params = []
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', m.group(1), re.DOTALL)
            for row in rows[1:]:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 3:
                    params.append({
                        'name': re.sub(r'<[^>]+>', '', cells[0]).strip(),
                        'type': re.sub(r'<[^>]+>', '', cells[1]).strip(),
                        'description': re.sub(r'<[^>]+>', '', cells[2]).strip(),
                    })
            if params:
                result['parameters'] = params

        # Return value
        m = re.search(r'<h2[^>]*>\s*Return Value\s*</h2>(.*?)<h2', html, re.DOTALL | re.IGNORECASE)
        if m:
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', m.group(1), re.DOTALL)
            for row in rows[1:]:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 2:
                    result['return_type'] = re.sub(r'<[^>]+>', '', cells[0]).strip()
                    result['return_description'] = re.sub(r'<[^>]+>', '', cells[1]).strip()
                    break

        # Python syntax
        m = re.search(r'returnValue\s*=\s*\w+\.<strong>(\w+)</strong>\((.*?)\)', html)
        if m:
            result['syntax'] = f"{m.group(1)}({m.group(2)})"

        return {'status': 'ok', **result}

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {'status': 'error', 'message': f'Page not found: {url}', 'suggestion': 'Try different spelling or use api_docs for introspection'}
        return {'status': 'error', 'message': f'HTTP {e.code}: {e}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ── File Cache ───────────────────────────────────────────────────────────────

CACHE_PATH = '/tmp/f360_file_cache.json'


def _cmd_cache_files():
    """Scan all projects and folders, write a cache file for instant search later."""
    app = adsk.core.Application.get()
    entries = []
    project_count = 0
    folder_count = 0

    def scan(folder, project_name, path_parts):
        nonlocal folder_count
        folder_count += 1
        for f in folder.dataFiles:
            entries.append({
                'project': project_name,
                'folders': list(path_parts),
                'name': f.name,
                'path': '/'.join([project_name] + list(path_parts) + [f.name]),
                'id': f.id if hasattr(f, 'id') else None,
            })
        for sf in folder.dataFolders:
            scan(sf, project_name, path_parts + [sf.name])

    for p in app.data.dataProjects:
        project_count += 1
        try:
            scan(p.rootFolder, p.name, [])
        except Exception:
            pass

    import datetime
    cache = {
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'projects': project_count,
        'folders_scanned': folder_count,
        'file_count': len(entries),
        'files': entries,
    }

    with open(CACHE_PATH, 'w') as f:
        json.dump(cache, f)

    return {
        'status': 'ok',
        'projects': project_count,
        'folders_scanned': folder_count,
        'file_count': len(entries),
        'cache_path': CACHE_PATH,
    }


def _cmd_search_cached(data):
    """Search the file cache. Falls back to live scan if no cache exists."""
    term = data.get('term', '').lower()
    if not term:
        return {'status': 'error', 'message': 'term is required'}

    if not os.path.exists(CACHE_PATH):
        return {'status': 'error', 'message': 'No cache exists. Run cache_files first.', 'hint': 'Send {"cmd": "cache_files"} to build the index.'}

    with open(CACHE_PATH) as f:
        cache = json.load(f)

    matches = []
    for entry in cache.get('files', []):
        if term in entry['name'].lower():
            matches.append(entry)

    return {
        'status': 'ok',
        'term': term,
        'matches': matches,
        'count': len(matches),
        'cache_timestamp': cache.get('timestamp', '?'),
        'total_files_in_cache': cache.get('file_count', 0),
    }
