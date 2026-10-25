"""Verify endpoint ownership without loading the proprietary Autodesk runtime."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def addin(monkeypatch):
    adsk = ModuleType("adsk")
    adsk.core = ModuleType("adsk.core")
    adsk.core.CustomEventHandler = object
    adsk.fusion = ModuleType("adsk.fusion")
    for name, module in {
        "adsk": adsk,
        "adsk.core": adsk.core,
        "adsk.fusion": adsk.fusion,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    for name in (
        "test_addin",
        "test_addin.lib",
        "test_addin.lib.fusionAddInUtils",
        "test_addin.config",
    ):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    source = (
        Path(__file__).resolve().parents[3]
        / "addin/fusion_bridge/commands/tcpServer/entry.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_addin.commands.tcpServer.entry", source
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("owner", ["current", "another", "corrupt"])
def test_cleanup_preserves_another_instances_endpoint(
    tmp_path, monkeypatch, addin, owner
):
    monkeypatch.setattr(addin, "_config_dir", lambda: tmp_path)
    discovery = tmp_path / "fusion_bridge.json"
    socket = tmp_path / "fusion_bridge.sock"
    socket.touch()
    discovery.write_text(
        "corrupt"
        if owner == "corrupt"
        else json.dumps({"pid": os.getpid() if owner == "current" else -1})
    )
    addin._cleanup_discovery_files()
    assert discovery.exists() is (owner != "current")
    assert socket.exists() is (owner != "current")
