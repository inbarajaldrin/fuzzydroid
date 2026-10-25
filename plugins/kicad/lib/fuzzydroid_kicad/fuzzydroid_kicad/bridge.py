"""Embedded server: transport thread queues all app work onto wx's main thread."""

from __future__ import annotations

import atexit
import hashlib
import importlib
import json
import os
import secrets
import socket
import threading
from pathlib import Path

from . import __version__
from .paths import runtime_dir
from .registry import Registry

MAX_REQUEST = 1024 * 1024
MAIN_THREAD_TIMEOUT = 25
_server = None


def runtime_digest():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class Bridge:
    def __init__(self, pcbnew, wx):
        self.wx = wx
        self.registry = Registry(reserved_namespaces=("ipc", "bridge"))
        self.token = secrets.token_hex(32)
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(8)
        root = runtime_dir()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        self.descriptor = root / f"{os.getpid()}.json"
        descriptor = {
            "pid": os.getpid(),
            "port": self.listener.getsockname()[1],
            "token": self.token,
            "version": __version__,
            "source": str(Path(__file__).resolve()),
            "source_hash": runtime_digest(),
        }
        from .native import register

        register(self.registry, pcbnew, wx)
        self.registry.tool("native.tools", "Discover the current native tool registry.")(
            self.registry.catalog
        )
        # Project packages opt in explicitly and register against the same contract.
        for module in filter(None, os.getenv("FZD_KICAD_TOOL_MODULES", "").split(",")):
            importlib.import_module(module.strip()).register(self.registry)
        # Publish only after registration succeeds; never advertise a half-started server.
        fd = os.open(self.descriptor, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(descriptor, stream)
        atexit.register(self.close)
        threading.Thread(target=self.serve, name="FzdKiCadTransport", daemon=True).start()

    def close(self):
        self.listener.close()
        try:
            self.descriptor.unlink()
        except FileNotFoundError:
            pass

    def handle(self, connection):
        connection.settimeout(30)
        raw = connection.makefile("rb").readline(MAX_REQUEST + 1)
        if len(raw) > MAX_REQUEST or not raw.endswith(b"\n"):
            raise ValueError("Request is too large or incomplete")
        request = json.loads(raw)
        if not secrets.compare_digest(str(request.get("token", "")), self.token):
            raise ValueError("Invalid bridge token")
        done = threading.Event()
        lock = threading.Lock()
        state = {"started": False, "cancelled": False}
        response = {}

        def execute():
            with lock:
                if state["cancelled"]:
                    return
                state["started"] = True
            try:
                value = self.registry.dispatch(request["tool"], request.get("params", {}))
                response.update(ok=True, data=value)
            except BaseException as error:  # noqa: BLE001 - contain operator code inside KiCad
                response.update(ok=False, error=str(error), type=type(error).__name__)
            finally:
                done.set()

        self.wx.CallAfter(execute)
        if not done.wait(MAIN_THREAD_TIMEOUT):
            with lock:
                state["cancelled"] = True
                started = state["started"]
            return {
                "ok": False,
                "error": "Main-thread deadline exceeded",
                "execution_started": started,
                "retry_safe": not started,
            }
        return response

    def serve(self):
        while True:
            try:
                connection, _ = self.listener.accept()
            except OSError:
                return
            with connection:
                try:
                    response = self.handle(connection)
                except Exception as error:  # noqa: BLE001 - tool/diagnostic boundary
                    response = {"ok": False, "error": str(error)}
                try:
                    connection.sendall(json.dumps(response, allow_nan=False).encode() + b"\n")
                except OSError:
                    pass


def start():
    global _server
    if _server is not None:
        return _server
    import pcbnew
    import wx

    if int(pcbnew.GetBuildVersion().split(".")[0]) != 10:
        raise RuntimeError("The embedded backend is qualified for KiCad 10 only; use official IPC")
    _server = Bridge(pcbnew, wx)

    class PanelPlugin(pcbnew.ActionPlugin):
        def defaults(self):
            self.name = "fuzzydroid KiCad tools"
            self.category = "Automation"
            self.description = "Show the shared agent/tool registry"
            self.show_toolbar_button = False

        def Run(self):
            _server.registry.dispatch("native.panel_show")

    PanelPlugin().register()
    return _server
