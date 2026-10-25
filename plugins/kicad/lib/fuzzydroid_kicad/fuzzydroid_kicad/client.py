"""Reference native client. Never retry a request after an unknown write outcome."""

from __future__ import annotations

import json
import socket

from .paths import runtime_dir


class BridgeError(RuntimeError):
    def __init__(self, response):
        self.response = response
        super().__init__(response.get("error", "Bridge request failed"))


def call_endpoint(endpoint: dict, tool: str, params: dict | None = None) -> object:
    request = {"token": endpoint["token"], "tool": tool, "params": params or {}}
    raw = json.dumps(request, allow_nan=False).encode() + b"\n"
    if len(raw) > 1024 * 1024:
        raise ValueError("Request exceeds 1 MiB")
    try:
        with socket.create_connection(("127.0.0.1", endpoint["port"]), timeout=3) as connection:
            connection.settimeout(30)
            connection.sendall(raw)
            response = json.loads(connection.makefile("rb").readline())
    except (OSError, ValueError) as error:
        raise BridgeError(
            {
                "error": f"Transport failed: {error}",
                "retry_safe": False,
                "note": "Inspect application state before retrying a write.",
            }
        ) from error
    if not response.get("ok"):
        raise BridgeError(response)
    return response["data"]


def discover() -> list[dict]:
    instances = []
    for path in sorted(runtime_dir().glob("*.json")):
        try:
            endpoint = json.loads(path.read_text(encoding="utf-8"))
            status = call_endpoint(endpoint, "native.ping")
            if status["pid"] == endpoint["pid"]:
                instances.append(dict(endpoint, status=status))
        except (OSError, ValueError, KeyError, BridgeError):
            continue
    return instances


def resolve(instance: int | None = None) -> dict:
    instances = discover()
    if instance is not None:
        instances = [entry for entry in instances if entry["pid"] == instance]
    if len(instances) != 1:
        choices = [{"pid": item["pid"], "board": item["status"].get("board")} for item in instances]
        raise BridgeError(
            {"error": "Select one live native instance with --instance", "instances": choices}
        )
    return instances[0]


def call(tool: str, params: dict | None = None, instance: int | None = None) -> object:
    return call_endpoint(resolve(instance), tool, params)
