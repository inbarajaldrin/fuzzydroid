"""Tests for fuzzydroid_fusion.core.bridge endpoint resolution and verification."""
import json
from unittest.mock import patch

import pytest

from fuzzydroid_fusion.core import bridge


class TestIsBridgeResponse:
    @pytest.mark.parametrize("data", [b"[]", b"null", b"42", b'"hello"'])
    def test_other_json_types_are_rejected(self, data):
        assert bridge._is_bridge_response(data) is False

    def test_new_bridge_signature_accepted(self):
        data = json.dumps({"status": "ok", "bridge": "fusion_bridge", "pid": 1}).encode()
        assert bridge._is_bridge_response(data) is True

    def test_unsigned_pong_rejected(self):
        """Only responses carrying the bridge signature are trusted."""
        data = json.dumps({"status": "ok", "message": "pong", "pid": 1}).encode()
        assert bridge._is_bridge_response(data) is False

    def test_foreign_service_rejected(self):
        data = b'{"jsonrpc": "2.0", "result": "something else"}\n'
        assert bridge._is_bridge_response(data) is False

    def test_non_json_rejected(self):
        assert bridge._is_bridge_response(b"HTTP/1.1 400 Bad Request\r\n") is False

    def test_empty_rejected(self):
        assert bridge._is_bridge_response(b"") is False


class TestCandidates:
    def test_env_socket_is_first_priority(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FUSION_BRIDGE_SOCKET", "/tmp/custom.sock")
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        cands = bridge._candidates()
        assert cands[0] == {"transport": "uds", "path": "/tmp/custom.sock"}

    def test_env_port_beats_discovery_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.setenv("FUSION_BRIDGE_PORT", "9001")
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        (tmp_path / "fusion_bridge.json").write_text(
            json.dumps({"transport": "tcp", "host": "127.0.0.1", "port": 8770})
        )
        cands = bridge._candidates()
        assert cands[0]["port"] == 9001
        assert any(c.get("port") == 8770 for c in cands[1:])

    def test_discovery_json_parsed(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        (tmp_path / "fusion_bridge.json").write_text(
            json.dumps({"transport": "uds", "path": str(tmp_path / "b.sock"), "pid": 42})
        )
        cands = bridge._candidates()
        assert cands[0]["transport"] == "uds"
        assert cands[0]["pid"] == 42

    def test_legacy_port_file_still_read(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        (tmp_path / "fusion_bridge.port").write_text("8771\n")
        cands = bridge._candidates()
        assert any(
            c.get("transport") == "tcp" and c.get("port") == 8771 for c in cands
        )

    def test_tcp_range_scan_is_last_resort(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        cands = bridge._candidates()
        ports = [c.get("port") for c in cands if c.get("transport") == "tcp"]
        for p in range(8765, 8776):
            assert p in ports

    def test_corrupt_discovery_file_skipped(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        (tmp_path / "fusion_bridge.json").write_text("{not json!!!")
        cands = bridge._candidates()  # must not raise
        assert isinstance(cands, list)


class TestResolveEndpoint:
    def test_returns_first_verified_candidate(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        good = {"transport": "tcp", "host": "127.0.0.1", "port": 8767}
        (tmp_path / "fusion_bridge.json").write_text(json.dumps(good))

        def fake_probe(ep):
            return ep.get("port") == 8767

        with patch.object(bridge, "_probe", side_effect=fake_probe):
            ep = bridge.resolve_endpoint()
        assert ep is not None and ep["port"] == 8767

    def test_stale_discovery_falls_through_to_scan(self, tmp_path, monkeypatch):
        """A discovery file pointing at a dead/foreign port must not win —
        resolution should keep scanning and find the real bridge."""
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        (tmp_path / "fusion_bridge.json").write_text(
            json.dumps({"transport": "tcp", "host": "127.0.0.1", "port": 8765})
        )

        def fake_probe(ep):
            return ep.get("port") == 8772  # the real bridge is elsewhere

        with patch.object(bridge, "_probe", side_effect=fake_probe):
            ep = bridge.resolve_endpoint()
        assert ep is not None and ep["port"] == 8772

    def test_nothing_alive_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        with patch.object(bridge, "_probe", return_value=False):
            assert bridge.resolve_endpoint() is None


class TestSendCommand:
    def test_no_endpoint_returns_error_dict(self, tmp_path, monkeypatch):
        monkeypatch.delenv("FUSION_BRIDGE_SOCKET", raising=False)
        monkeypatch.delenv("FUSION_BRIDGE_PORT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        with patch.object(bridge, "resolve_endpoint", return_value=None):
            result = bridge.send_command({"cmd": "ping"})
        assert result["status"] == "error"
        assert "not reachable" in result["message"]


class TestDescribeEndpoint:
    def test_uds(self):
        assert bridge.describe_endpoint(
            {"transport": "uds", "path": "/tmp/x.sock"}
        ) == "uds:/tmp/x.sock"

    def test_tcp(self):
        assert bridge.describe_endpoint(
            {"transport": "tcp", "host": "127.0.0.1", "port": 8765}
        ) == "tcp:127.0.0.1:8765"

    def test_none(self):
        assert bridge.describe_endpoint(None) == "no live endpoint"
