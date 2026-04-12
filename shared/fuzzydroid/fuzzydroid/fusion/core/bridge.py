"""TCP bridge client for communicating with the Fusion 360 add-in.

The fusion_bridge add-in runs a TCP server inside Fusion 360 on localhost:8765.
This module provides the low-level send_command() function and all high-level
wrappers that correspond to bridge commands.

Protocol: newline-delimited JSON over TCP.
    Send: {"cmd": "ping"}\n
    Recv: {"status": "ok", "message": "pong", "pid": 12345}\n
"""

import json
import os
import socket
from typing import Any, Optional


# ── Configuration ────────────────────────────────────────────────────────────

def _get_host() -> str:
    return os.environ.get("FUSION_BRIDGE_HOST", "127.0.0.1")


def _get_port() -> int:
    """Resolve the bridge port. Priority:
    1. FUSION_BRIDGE_PORT env var (explicit override)
    2. Discovery file at config_dir/fusion_bridge.port (written by bridge on startup)
    3. Default 8765 (backward compat fallback)
    """
    env_port = os.environ.get("FUSION_BRIDGE_PORT")
    if env_port:
        return int(env_port)

    # Try discovery file
    try:
        from fuzzydroid.common import platform as fd_platform

        discovery = fd_platform.config_dir() / "fusion_bridge.port"
        if discovery.exists():
            port_str = discovery.read_text().strip()
            if port_str.isdigit():
                return int(port_str)
    except Exception:
        pass

    return 8765  # backward compat default


def _get_timeout() -> int:
    return int(os.environ.get("FUSION_BRIDGE_TIMEOUT", "300"))


# ── Low-level transport ──────────────────────────────────────────────────────

def send_command(cmd_dict: dict) -> dict:
    """Send a JSON command to the Fusion bridge and return the parsed response.

    Opens a new TCP connection per call (short-lived, matches bridge protocol).

    Args:
        cmd_dict: Command payload — must contain a "cmd" key.

    Returns:
        dict with at minimum a "status" key ("ok" or "error").
    """
    host = _get_host()
    port = _get_port()
    timeout = _get_timeout()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
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
    except ConnectionRefusedError:
        return {
            "status": "error",
            "message": (
                f"Fusion bridge not running on {host}:{port}. "
                "Load the fusion_bridge add-in in Fusion 360 first "
                "(Shift+S → Add-Ins → browse to fusion_bridge folder → Run)."
            ),
        }
    except socket.timeout:
        return {
            "status": "error",
            "message": (
                f"Fusion bridge timed out after {timeout}s. Cloud operations "
                "(search, open) can be slow — try increasing FUSION_BRIDGE_TIMEOUT."
            ),
        }
    except Exception as e:
        return {"status": "error", "message": f"Connection error: {e}"}
    finally:
        sock.close()


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
