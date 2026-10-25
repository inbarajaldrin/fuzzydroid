"""Bridge client for communicating with the Fusion 360 add-in.

The fusion_bridge add-in runs a small JSON server inside Fusion 360:
  - macOS/Linux: Unix domain socket at ~/.config/fuzzydroid/fusion_bridge.sock
    (no TCP port to fight over).
  - Windows: TCP on 127.0.0.1, ports 8765-8775 (first free one wins).

On startup the add-in writes a JSON discovery file at
config_dir/fusion_bridge.json describing the live endpoint:
    {"transport": "uds", "path": "...", "pid": 123}
    {"transport": "tcp", "host": "127.0.0.1", "port": 8766, "pid": 123}

This client resolves the endpoint in priority order (env overrides, discovery
file, default UDS path, TCP port scan), and VERIFIES every candidate with a
signed ping before trusting it — a stale discovery file or a foreign process
squatting the port is skipped, not mistaken for the bridge.

Protocol: newline-delimited JSON.
    Send: {"cmd": "ping"}\n
    Recv: {"status": "ok", "message": "pong", "bridge": "fusion_bridge", "pid": 12345}\n
"""

import json
import os
import socket
from pathlib import Path
from typing import Any, Optional

TCP_PORT_RANGE = range(8765, 8776)
VERIFY_TIMEOUT = 2  # seconds; endpoint probes must fail fast


# ── Endpoint resolution ──────────────────────────────────────────────────────

def _config_dir() -> Path:
    from fuzzydroid_fusion import _common
    return _common.config_dir()


def _default_uds_path() -> Path:
    return _config_dir() / "fusion_bridge.sock"


def _discovery_file() -> Path:
    return _config_dir() / "fusion_bridge.json"


def _is_bridge_response(data: bytes) -> bool:
    """True if `data` is a fusion_bridge ping response (not a foreign service)."""
    try:
        obj = json.loads(data.decode("utf-8").strip())
    except Exception:
        return False
    return isinstance(obj, dict) and obj.get("bridge") == "fusion_bridge"


def _probe(endpoint: dict) -> bool:
    """Send a verification ping to a candidate endpoint. Fast, short timeout."""
    try:
        sock = _open_socket(endpoint, timeout=VERIFY_TIMEOUT)
    except OSError:
        return False
    try:
        sock.sendall(b'{"cmd":"ping"}\n')
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        return _is_bridge_response(buf)
    except OSError:
        return False
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _candidates() -> list[dict]:
    """Yield endpoint candidates in priority order (unverified)."""
    out: list[dict] = []

    # 1. Explicit env overrides — trusted as stated, still verified below
    env_sock = os.environ.get("FUSION_BRIDGE_SOCKET")
    if env_sock:
        out.append({"transport": "uds", "path": env_sock})
    env_port = os.environ.get("FUSION_BRIDGE_PORT")
    if env_port:
        out.append({
            "transport": "tcp",
            "host": os.environ.get("FUSION_BRIDGE_HOST", "127.0.0.1"),
            "port": int(env_port),
        })

    # 2. JSON discovery file written by the add-in
    try:
        df = _discovery_file()
        if df.exists():
            info = json.loads(df.read_text())
            if info.get("transport") in ("uds", "tcp"):
                out.append(info)
    except Exception:
        pass

    # 3. Default UDS path (macOS/Linux)
    if os.name != "nt":
        p = _default_uds_path()
        if p.exists():
            out.append({"transport": "uds", "path": str(p)})

    # 4. TCP port range scan (Windows, or stale-discovery recovery)
    for port in TCP_PORT_RANGE:
        out.append({"transport": "tcp", "host": "127.0.0.1", "port": port})

    return out


def resolve_endpoint(verify: bool = True) -> Optional[dict]:
    """Return the first live, verified bridge endpoint, or None.

    With verify=False, returns the top-priority candidate without probing
    (used only for composing error messages).
    """
    cands = _candidates()
    if not verify:
        return cands[0] if cands else None
    seen = set()
    for ep in cands:
        key = (ep.get("transport"), ep.get("path"), ep.get("host"), ep.get("port"))
        if key in seen:
            continue
        seen.add(key)
        if _probe(ep):
            return ep
    return None


def describe_endpoint(ep: Optional[dict]) -> str:
    if not ep:
        return "no live endpoint"
    if ep.get("transport") == "uds":
        return f"uds:{ep.get('path')}"
    return f"tcp:{ep.get('host', '127.0.0.1')}:{ep.get('port')}"


def _open_socket(endpoint: dict, timeout: float) -> socket.socket:
    if endpoint["transport"] == "uds":
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(endpoint["path"])
        return sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((endpoint.get("host", "127.0.0.1"), endpoint["port"]))
    return sock


def _get_timeout() -> int:
    return int(os.environ.get("FUSION_BRIDGE_TIMEOUT", "300"))


# ── Low-level transport ──────────────────────────────────────────────────────

def send_command(cmd_dict: dict) -> dict:
    """Send a JSON command to the Fusion bridge and return the parsed response.

    Opens a new connection per call (short-lived, matches bridge protocol).
    Resolves + verifies the endpoint on every call, so a bridge that moved
    (Fusion restarted, port changed) is found again without client restarts.

    Args:
        cmd_dict: Command payload — must contain a "cmd" key.

    Returns:
        dict with at minimum a "status" key ("ok" or "error").
    """
    endpoint = resolve_endpoint()
    if endpoint is None:
        return {
            "status": "error",
            "message": (
                "Fusion bridge not reachable (checked env overrides, discovery "
                "file, default socket, and TCP ports 8765-8775). "
                "Load the fusion_bridge add-in in Fusion 360 first "
                "(Shift+S -> Add-Ins -> fusion_bridge -> Run)."
            ),
        }

    timeout = _get_timeout()
    try:
        sock = _open_socket(endpoint, timeout=timeout)
    except OSError as e:
        return {"status": "error", "message": f"Connection error ({describe_endpoint(endpoint)}): {e}"}
    try:
        payload = json.dumps(cmd_dict) + "\n"
        sock.sendall(payload.encode("utf-8"))
        buf = b""
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break
        return json.loads(buf.decode("utf-8").strip())
    except socket.timeout:
        return {
            "status": "error",
            "message": (
                f"Fusion bridge timed out after {timeout}s. Cloud operations "
                "(search, open) can be slow — try increasing FUSION_BRIDGE_TIMEOUT."
            ),
        }
    except Exception as e:
        return {"status": "error", "message": f"Connection error ({describe_endpoint(endpoint)}): {e}"}
    finally:
        try:
            sock.close()
        except OSError:
            pass


# ── High-level commands ──────────────────────────────────────────────────────

def ping() -> dict:
    """Check bridge connectivity."""
    return send_command({"cmd": "ping"})


def get_document() -> dict:
    """Get info about the active document."""
    return send_command({"cmd": "get_document"})


def list_projects() -> dict:
    """List all projects in the data hub."""
    return send_command({"cmd": "list_projects"})


def list_bodies() -> dict:
    """List bodies in the active design's root component."""
    return send_command({"cmd": "list_bodies"})


def list_components() -> dict:
    """List component occurrences in the active design."""
    return send_command({"cmd": "list_components"})


def get_bounding_box() -> dict:
    """Get axis-aligned bounding box (min/max XYZ in cm)."""
    return send_command({"cmd": "get_bounding_box"})


def get_timeline() -> dict:
    """Get the design timeline (feature history)."""
    return send_command({"cmd": "get_timeline"})


def open_file(project: str, file: str, folders: Optional[list[str]] = None) -> dict:
    """Open a file from the Fusion data hub.

    Args:
        project: Project name (e.g., 'Default Project').
        file: File name (e.g., 'allen_key').
        folders: Optional subfolder path list.
    """
    cmd: dict[str, Any] = {"cmd": "open_file", "project": project, "file": file}
    if folders:
        cmd["folders"] = folders
    return send_command(cmd)


def search_files(term: str) -> dict:
    """Search files across all projects (cloud, slow 30-60s)."""
    return send_command({"cmd": "search_files", "term": term})


def cache_files() -> dict:
    """Build local file index by scanning all projects (takes 1-3 min)."""
    return send_command({"cmd": "cache_files"})


def search_cached(term: str) -> dict:
    """Search the local file cache (instant, requires cache_files first)."""
    return send_command({"cmd": "search_cached", "term": term})


def export(fmt: str, path: Optional[str] = None) -> dict:
    """Export the active design.

    Args:
        fmt: Export format — 'step', 'stl', or 'f3d'.
        path: Output file path (auto-generated if None).
    """
    cmd: dict[str, Any] = {"cmd": f"export_{fmt}"}
    if path:
        cmd["path"] = path
    return send_command(cmd)


def api_call(
    api_path: str,
    args: Optional[list] = None,
    kwargs: Optional[dict] = None,
    store_as: Optional[str] = None,
    return_properties: Optional[list[str]] = None,
) -> dict:
    """Call any Fusion API method/property via dotted path.

    Args:
        api_path: Dotted path (e.g., 'rootComponent.bRepBodies.count').
        args: Positional arguments.
        kwargs: Keyword arguments.
        store_as: Name to store result for later $name references.
        return_properties: Properties to extract from the result.
    """
    cmd: dict[str, Any] = {"cmd": "api_call", "api_path": api_path}
    if args:
        cmd["args"] = args
    if kwargs:
        cmd["kwargs"] = kwargs
    if store_as:
        cmd["store_as"] = store_as
    if return_properties:
        cmd["return_properties"] = return_properties
    return send_command(cmd)


def api_docs(search_term: str, category: str = "class_name", max_results: int = 5) -> dict:
    """Search Fusion API docs via runtime introspection."""
    return send_command({
        "cmd": "api_docs",
        "search_term": search_term,
        "category": category,
        "max_results": max_results,
    })


def online_docs(class_name: str, member_name: Optional[str] = None) -> dict:
    """Fetch Autodesk online API documentation."""
    cmd: dict[str, Any] = {"cmd": "online_docs", "class_name": class_name}
    if member_name:
        cmd["member_name"] = member_name
    return send_command(cmd)


def clear_context() -> dict:
    """Clear stored API object references."""
    return send_command({"cmd": "clear_context"})


def exec_python(
    code: str,
    session_id: Optional[str] = None,
    persistent: bool = False,
) -> dict:
    """Execute Python code inside Fusion 360's runtime.

    Args:
        code: Python source code to execute.
        session_id: Session ID for persistent variable scope.
        persistent: Whether to keep variables for future calls.
    """
    cmd: dict[str, Any] = {"cmd": "exec_python", "code": code}
    if session_id:
        cmd["session_id"] = session_id
        cmd["persistent"] = persistent
    return send_command(cmd)
