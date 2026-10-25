"""Read-only diagnostics with artifact drift and per-backend evidence."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path

from . import __version__, client, ipc
from .paths import read_state, state_path
from .setup import digest


def diagnose() -> dict:
    checks = []

    def check(name, function):
        try:
            evidence = function()
            checks.append(
                {
                    "name": name,
                    "ok": True,
                    "evidence": json.loads(json.dumps(evidence, default=ipc.encode)),
                }
            )
        except Exception as error:  # noqa: BLE001 - tool/diagnostic boundary
            checks.append({"name": name, "ok": False, "error": str(error)})

    state = {}

    def state_check():
        state.update(read_state())
        return str(state_path())

    check("state", state_check)
    if state:

        def artifacts():
            root = Path(state["plugin_root"])
            if state["plugin_version"] != __version__:
                raise ValueError("Plugin version changed; rerun setup")
            if digest(root / "lib/fuzzydroid_kicad/pyproject.toml") != state["pyproject_hash"]:
                raise ValueError("Dependency drift; rerun setup")
            if not Path(state["kicad_cli"]).is_file():
                raise ValueError("KiCad executable moved; rerun setup")
            if (
                state["native_enabled"]
                and digest(Path(state["loader_path"])) != state["loader_hash"]
            ):
                raise ValueError("Native loader missing or changed; rerun setup")
            distribution = importlib.metadata.distribution("fuzzydroid-kicad")
            direct_url = distribution.read_text("direct_url.json") or ""
            import json
            from urllib.parse import urlparse
            from urllib.request import url2pathname

            installed = Path(url2pathname(urlparse(json.loads(direct_url)["url"]).path)).resolve()
            if installed != (root / "lib/fuzzydroid_kicad").resolve():
                raise ValueError("Editable install points to another plugin checkout; rerun setup")
            return {"version": __version__, "python": sys.executable}

        check("artifacts", artifacts)
    check("ipc", ipc.inspect_board)

    def native():
        instances = client.discover()
        if not instances:
            raise ValueError("No live embedded bridge; restart KiCad 10 PCB Editor after setup")
        if state:
            expected = str(
                (
                    Path(state["plugin_root"]) / "lib/fuzzydroid_kicad/fuzzydroid_kicad/bridge.py"
                ).resolve()
            )
            for entry in instances:
                from .bridge import runtime_digest

                if entry["source"] != expected or entry["source_hash"] != runtime_digest():
                    raise ValueError("Native process serves stale bridge code; restart PCB Editor")
        return [
            {"pid": e["pid"], "version": e["version"], "status": e["status"]} for e in instances
        ]

    check("native", native)
    return {
        "checks": checks,
        "qualified_platform": "macOS / KiCad 10.0.7",
        "note": "Windows paths and protocol have unit coverage; live Windows validation is pending.",
    }
