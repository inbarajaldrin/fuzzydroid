"""Unit tests for the parts with real logic: state round-trip, wrapper
refusal, the ROS bridge config edit (idempotency + stale-variant collapse),
and detect's recommendation ordering."""
import json
from pathlib import Path

import pytest

from fuzzydroid_isaacsim import _common as c
from fuzzydroid_isaacsim import detect, doctor, ros_bridge


def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "config_dir", lambda: tmp_path)
    state = {"variant": "pip-lab", "mcp_port": 9009, "ros_enabled": True,
             "isaac_root": str(tmp_path / "it's a \"path\"")}
    c.save_state("isaacsim", state)
    assert c.load_state("isaacsim") == state


def test_version_key_ordering():
    assert c.version_key("5.0.0") > c.version_key("4.2.0")
    assert c.version_key("4.10.1") > c.version_key("4.2.0")


def test_recommend_prefers_newest_pip_over_binary():
    inv = {
        "running": [],
        "pip": [
            {"kind": "pip", "variant": "pip-lab", "venv": "/v/a", "isaac_version": "4.5.0"},
            {"kind": "pip", "variant": "pip-standalone", "venv": "/v/b", "isaac_version": "5.0.0"},
        ],
        "binary": [{"kind": "binary", "variant": "binary", "path": "/p", "isaac_version": "5.1.0"}],
    }
    rec = detect.recommend(inv)
    assert rec["venv"] == "/v/b"
    assert rec["reason"] == "newest pip install"


def test_recommend_running_matches_candidate():
    inv = {
        "running": [{"kind": "running", "pid": 1, "cmdline": "/v/a/bin/python -m isaacsim"}],
        "pip": [
            {"kind": "pip", "variant": "pip-lab", "venv": "/v/a", "isaac_version": "4.5.0"},
            {"kind": "pip", "variant": "pip-standalone", "venv": "/v/b", "isaac_version": "5.0.0"},
        ],
        "binary": [],
    }
    rec = detect.recommend(inv)
    assert rec["venv"] == "/v/a"
    assert "running" in rec["reason"]


def test_entrypoint_matcher_true_positives():
    assert detect._is_isaac_entrypoint("/home/u/env_isaaclab/bin/python3 /home/u/env_isaaclab/bin/isaacsim")
    assert detect._is_isaac_entrypoint("/home/u/.local/share/ov/pkg/isaac-sim-4.2.0/kit/kit --exec foo")
    assert detect._is_isaac_entrypoint("bash /home/u/pkg/isaac-sim.sh --no-window") is False  # argv[0] is bash
    assert detect._is_isaac_entrypoint("/home/u/pkg/isaac-sim.sh --no-window")
    assert detect._is_isaac_entrypoint("python3 -m isaacsim.exp.full")
    assert detect._is_isaac_entrypoint(
        "python3 /v/lib/python3.11/site-packages/isaacsim/somescript.py")


def test_entrypoint_matcher_rejects_bystanders():
    # the three real false positives from the a4500 verification run
    assert not detect._is_isaac_entrypoint(
        "bash /home/u/Documents/isaac-sim-mcp/scripts/ursim_watchdog.sh")
    assert not detect._is_isaac_entrypoint(
        "/home/u/env_isaaclab/lib/python3.11/site-packages/isaacsim/extscache/omni.telemetry.transmitter")
    assert not detect._is_isaac_entrypoint(
        "tmux new-session -d -s jr exec bash -lc 'cd ~/Documents/isaac-sim-mcp && claude'")
    # plus greps / editors that merely mention isaac paths
    assert not detect._is_isaac_entrypoint("grep -r isaacsim /home/u/notes")
    assert not detect._is_isaac_entrypoint("python3 train.py --task Isaac-Cartpole-v0")


def _make_ext(root: Path, version: str) -> None:
    cfg = root / "exts" / "isaacsim.ros2.bridge" / "config"
    cfg.mkdir(parents=True)
    (cfg / "extension.toml").write_text(f'[package]\nversion = "{version}"\n')


def _make_kit_config(path: Path, enabled: list) -> None:
    path.write_text(json.dumps(
        {"persistent": {"app": {"exts": {"enabled": {str(i): v for i, v in enumerate(enabled)}}}}}))


def test_enable_bridge_versioned_and_idempotent(tmp_path):
    install = tmp_path / "install"
    _make_ext(install, "4.9.3")
    kit = tmp_path / "user.config.json"
    _make_kit_config(kit, ["omni.kit.mcp-1.0.0"])

    versioned = ros_bridge.enable_bridge(kit, install)
    assert versioned == "isaacsim.ros2.bridge-4.9.3"
    assert ros_bridge.bridge_enabled_id(kit) == versioned
    backups_after_first = list(tmp_path.glob("user.config.json.bak-*"))
    assert len(backups_after_first) == 1

    # second run: no new write, no new backup
    ros_bridge.enable_bridge(kit, install)
    assert list(tmp_path.glob("user.config.json.bak-*")) == backups_after_first
    # other entries preserved
    cfg = json.loads(kit.read_text())
    values = list(cfg["persistent"]["app"]["exts"]["enabled"].values())
    assert "omni.kit.mcp-1.0.0" in values


def test_enable_bridge_collapses_stale_variants(tmp_path):
    install = tmp_path / "install"
    _make_ext(install, "5.1.0")
    kit = tmp_path / "user.config.json"
    _make_kit_config(kit, ["isaacsim.ros2.bridge-4.9.3", "other.ext-1.0"])

    ros_bridge.enable_bridge(kit, install)
    cfg = json.loads(kit.read_text())
    values = list(cfg["persistent"]["app"]["exts"]["enabled"].values())
    assert values.count("isaacsim.ros2.bridge-5.1.0") == 1
    assert "isaacsim.ros2.bridge-4.9.3" not in values
    assert "other.ext-1.0" in values


def test_refuse_wrapper_script(tmp_path):
    from fuzzydroid_isaacsim.setup import refuse_wrapper
    wrapper = tmp_path / "isaacsim"
    wrapper.write_text("#!/usr/bin/env bash\nexec ~/my-streaming-wrapper \"$@\"\n")
    with pytest.raises(SystemExit, match="REFUSED"):
        refuse_wrapper(wrapper)


def test_dot_sh_launcher_inside_install_tree_allowed(tmp_path):
    from fuzzydroid_isaacsim.setup import refuse_wrapper
    launcher = tmp_path / "isaac-sim.sh"
    launcher.write_text("#!/bin/bash\nexec ./kit/kit \"$@\"\n")
    refuse_wrapper(launcher)  # must not raise


def test_pip_console_script_not_refused(tmp_path):
    from fuzzydroid_isaacsim.setup import refuse_wrapper
    script = tmp_path / "isaacsim"
    script.write_text("#!/home/user/env/bin/python\nimport isaacsim\n")
    refuse_wrapper(script)  # must not raise


# ── bridge probe via omni-kit-mcp's reference client CLI ──────────────────
# The doctor migrated its bridge probe from a hand-rolled socket to a
# subprocess call to `python -m kit_mcp.client`. The exit-code contract IS the
# probe result, so these tests plant a fake `kit_mcp` package on PYTHONPATH and
# assert the CLI's exit code and stderr are passed straight through.

def _fake_kit_mcp(root: Path, exit_code: int, stderr: str = "", stdout: str = "") -> None:
    """A stdlib-only stand-in for the reference client that emits a fixed
    exit code — the real client is stdlib-only too, so plumbing is identical."""
    pkg = root / "kit_mcp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "client.py").write_text(
        "import sys\n"
        f"sys.stdout.write({stdout!r})\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({exit_code})\n")


def test_probe_via_client_unreachable_passes_through_exit2(tmp_path):
    _fake_kit_mcp(tmp_path, 2, stderr="[Errno 111] Connection refused")
    rc, out, err = doctor.probe_via_client(tmp_path, 9009)
    assert rc == 2
    assert "Connection refused" in err


def test_probe_via_client_success_passes_through_exit0(tmp_path):
    _fake_kit_mcp(tmp_path, 0, stdout='{"tools": []}')
    rc, out, err = doctor.probe_via_client(tmp_path, 9009)
    assert rc == 0


def test_probe_via_client_bridge_error_passes_through_exit1(tmp_path):
    _fake_kit_mcp(tmp_path, 1, stderr="bridge said no")
    rc, out, err = doctor.probe_via_client(tmp_path, 9009)
    assert rc == 1
    assert "bridge said no" in err


def test_probe_via_client_missing_client_is_not_zero(tmp_path):
    # a checkout with no kit_mcp package must not read as a healthy bridge
    rc, out, err = doctor.probe_via_client(tmp_path, 9009)
    assert rc != 0


def test_oneline_is_table_safe():
    # newlines collapse, pipes are neutralized (they'd break the markdown row)
    assert doctor._oneline("a\nb  c") == "a b c"
    assert "|" not in doctor._oneline("x | y")
    assert len(doctor._oneline("z" * 500)) <= 200


# ── port discovery: the probe omits --port so a lone bridge auto-resolves ──
def _argv_asserting_kit_mcp(root: Path, must_have=(), must_lack=()) -> None:
    """Fake client that exits 0 only if the CLI argv contains all `must_have`
    tokens and none of `must_lack` — lets a test assert whether --port was passed."""
    pkg = root / "kit_mcp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "client.py").write_text(
        "import sys\n"
        f"mh = {list(must_have)!r}\n"
        f"ml = {list(must_lack)!r}\n"
        "a = sys.argv\n"
        "sys.exit(0 if all(x in a for x in mh) and all(x not in a for x in ml) else 3)\n")


def test_probe_discovery_omits_port(tmp_path):
    # no port arg → the client must be invoked WITHOUT --port (discovery mode)
    _argv_asserting_kit_mcp(tmp_path, must_lack=["--port"])
    rc, _, _ = doctor.probe_via_client(tmp_path)
    assert rc == 0


def test_probe_pinned_passes_port(tmp_path):
    # explicit port → the client must receive --port 9009 (disambiguation)
    _argv_asserting_kit_mcp(tmp_path, must_have=["--port", "9009"])
    rc, _, _ = doctor.probe_via_client(tmp_path, port=9009)
    assert rc == 0


def test_tcp_reachable_true_then_false():
    import socket as _socket
    srv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    host, port = srv.getsockname()
    try:
        assert doctor._tcp_reachable(host, port) is True
    finally:
        srv.close()
    # nothing listens on that port once closed → refused
    assert doctor._tcp_reachable("127.0.0.1", port) is False
