"""Dependency-free tool contract shared by native transport, panel, CLI and MCP."""

from __future__ import annotations

import json
import re


class Registry:
    def __init__(self, reserved_namespaces=()):
        self._tools = {}
        self._reserved_namespaces = set(reserved_namespaces)

    def tool(self, name, description, properties=None, required=(), mutates=False):
        if name.split(".")[0] in self._reserved_namespaces:
            raise ValueError("Reserved provider namespace: " + name)
        if (
            not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", name)
            or "__" in name
            or len(name.replace(".", "__")) > 64
        ):
            raise ValueError("Tool names must be namespaced, for example board.inspect")

        def register(handler):
            if name in self._tools:
                raise ValueError("Duplicate tool: " + name)
            self._tools[name] = {
                "handler": handler,
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": properties or {},
                    "required": list(required),
                    "additionalProperties": False,
                },
                "mutates": mutates,
            }
            return handler

        return register

    def catalog(self):
        return [
            {k: v for k, v in entry.items() if k != "handler"}
            for _, entry in sorted(self._tools.items())
        ]

    def unregister(self, name):
        """Remove a registered tool; callers refresh their catalogs afterward."""
        if name not in self._tools:
            raise ValueError("Unknown tool: " + name)
        del self._tools[name]

    def dispatch(self, name, params=None):
        if name not in self._tools:
            raise ValueError("Unknown tool: " + name)
        entry = self._tools[name]
        params = {} if params is None else params
        if not isinstance(params, dict):
            raise TypeError("Tool parameters must be an object")
        schema = entry["inputSchema"]
        unknown = set(params) - set(schema["properties"])
        missing = set(schema["required"]) - set(params)
        if unknown or missing:
            raise ValueError(
                f"Invalid parameters; unknown={sorted(unknown)}, missing={sorted(missing)}"
            )
        types = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        for key, value in params.items():
            spec = schema["properties"][key]
            kind = spec.get("type")
            if kind in types and (
                not isinstance(value, types[kind])
                or (kind in ("number", "integer") and isinstance(value, bool))
            ):
                raise TypeError(f"{key} must be {kind}")
            if "enum" in spec and value not in spec["enum"]:
                raise ValueError(f"{key} must be one of {spec['enum']}")
        result = entry["handler"](**params)
        json.dumps(result, allow_nan=False)
        return result
