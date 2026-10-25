"""Unified tool surface: official IPC provider plus the live native registry."""

from __future__ import annotations

import json
import threading

from . import client
from .registry import Registry


class Service:
    def __init__(self, instance: int | None = None):
        self.instance = instance
        self._dispatch_lock = threading.RLock()
        self.registry = Registry()
        from . import ipc

        def install(name, description, handler, properties=None, required=(), mutates=False):
            def wrapped(**params):
                return json.loads(json.dumps(handler(**params), default=ipc.encode))

            self.registry.tool(name, description, properties, required, mutates)(wrapped)

        board = {"board": {"type": "string"}}
        install("ipc.ping", "Ping official KiCad IPC.", ipc.ping)
        install(
            "ipc.inspect",
            "Inspect live PCB footprints, tracks, nets and selection.",
            ipc.inspect_board,
        )
        install(
            "ipc.move",
            "Move a footprint with one undo step; attached tracks are not rerouted.",
            lambda reference, x_mm, y_mm, board, angle_deg=None: ipc.move_footprint(
                reference, x_mm, y_mm, board, angle_deg
            ),
            dict(
                board,
                reference={"type": "string"},
                x_mm={"type": "number"},
                y_mm={"type": "number"},
                angle_deg={"type": "number"},
            ),
            ["reference", "x_mm", "y_mm", "board"],
            True,
        )
        install(
            "ipc.python",
            "Run local Python with IPC objects; mutate groups writes and rolls back on error.",
            lambda code, board, mutate=False, message="Agent edit": ipc.execute_python(
                code, board, mutate, message
            ),
            dict(
                board,
                code={"type": "string"},
                mutate={"type": "boolean"},
                message={"type": "string"},
            ),
            ["board", "code"],
            True,
        )
        install(
            "ipc.save",
            "Save the expected active PCB.",
            lambda board: ipc.save_board(board),
            board,
            ["board"],
            True,
        )
        install(
            "ipc.export",
            "Render, export STEP, or generic DRC from a fresh live snapshot.",
            lambda kind, output, board: ipc.snapshot_job(kind, output, board),
            dict(
                board,
                kind={"type": "string", "enum": ["render", "step", "drc"]},
                output={"type": "string"},
            ),
            ["board", "kind", "output"],
            True,
        )
        install(
            "bridge.instances",
            "Discover native processes; does not return authentication tokens.",
            lambda: [
                {"pid": e["pid"], "version": e["version"], "status": e["status"]}
                for e in client.discover()
            ],
        )

    def catalog(self) -> list[dict]:
        tools = self.registry.catalog()
        instances = client.discover()
        if self.instance is not None:
            instances = [entry for entry in instances if entry["pid"] == self.instance]
        if len(instances) == 1:
            tools.extend(client.call_endpoint(instances[0], "native.tools"))
        return tools

    def call(self, tool: str, params: dict | None = None) -> object:
        with self._dispatch_lock:
            return self._call(tool, params)

    def _call(self, tool: str, params: dict | None = None) -> object:
        if tool.startswith("native."):
            return client.call(tool, params, self.instance)
        # Project namespaces are discovered on the native provider too.
        if not any(entry["name"] == tool for entry in self.registry.catalog()):
            return client.call(tool, params, self.instance)
        return self.registry.dispatch(tool, params)
