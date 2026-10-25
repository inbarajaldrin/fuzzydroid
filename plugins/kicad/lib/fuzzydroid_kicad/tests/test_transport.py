import json
import threading
from types import SimpleNamespace

import pytest

from fuzzydroid_kicad import bridge, client


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(bridge, "runtime_dir", lambda: tmp_path)
    monkeypatch.setattr(client, "runtime_dir", lambda: tmp_path)
    pcb = SimpleNamespace(GetBoard=lambda: None, GetBuildVersion=lambda: "10.0.7")
    wx = SimpleNamespace(CallAfter=lambda callback: callback(), IsMainThread=lambda: True)
    instance = bridge.Bridge(pcb, wx)
    yield instance
    instance.close()


def test_authenticated_transport_discovery_and_dynamic_tools(server):
    endpoint = json.loads(server.descriptor.read_text())
    instances = client.discover()
    assert len(instances) == 1
    assert instances[0]["pid"] == endpoint["pid"]
    server.registry.tool("project.answer", "Dynamic project tool")(lambda: {"answer": 42})
    assert client.call_endpoint(endpoint, "project.answer") == {"answer": 42}
    assert "project.answer" in {
        entry["name"] for entry in client.call_endpoint(endpoint, "native.tools")
    }


def test_bad_token_is_rejected_before_dispatch(server):
    endpoint = json.loads(server.descriptor.read_text())
    endpoint["token"] = "wrong"
    server.registry.tool("probe.never", "Must not execute")(
        lambda: pytest.fail("Unauthorized dispatch")
    )
    with pytest.raises(client.BridgeError, match="token"):
        client.call_endpoint(endpoint, "probe.never")


def test_queued_write_is_cancelled_when_main_thread_deadline_expires(server, monkeypatch):
    monkeypatch.setattr(bridge, "MAIN_THREAD_TIMEOUT", 0.01)
    queued = []
    server.wx.CallAfter = queued.append
    changed = []
    server.registry.tool("probe.write", "Write", mutates=True)(lambda: changed.append(True))
    endpoint = json.loads(server.descriptor.read_text())
    with pytest.raises(client.BridgeError) as error:
        client.call_endpoint(endpoint, "probe.write")
    assert error.value.response["retry_safe"] is True
    assert error.value.response["execution_started"] is False
    queued[0]()
    assert changed == []


def test_started_write_timeout_is_reported_as_uncertain(server, monkeypatch):
    monkeypatch.setattr(bridge, "MAIN_THREAD_TIMEOUT", 0.01)
    release = threading.Event()
    server.wx.CallAfter = lambda callback: threading.Thread(target=callback, daemon=True).start()
    server.registry.tool("probe.slow", "Slow", mutates=True)(lambda: release.wait(1))
    endpoint = json.loads(server.descriptor.read_text())
    try:
        with pytest.raises(client.BridgeError) as error:
            client.call_endpoint(endpoint, "probe.slow")
        assert error.value.response["execution_started"] is True
        assert error.value.response["retry_safe"] is False
    finally:
        release.set()


def test_ambiguity_never_picks_an_arbitrary_process(monkeypatch):
    monkeypatch.setattr(
        client,
        "discover",
        lambda: [{"pid": 1, "status": {"board": "a"}}, {"pid": 2, "status": {"board": "b"}}],
    )
    with pytest.raises(client.BridgeError):
        client.resolve()
    assert client.resolve(2)["pid"] == 2
