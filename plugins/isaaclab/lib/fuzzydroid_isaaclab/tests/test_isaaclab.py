"""Unit tests: state round-trip, detect recommendation, static-TLS hazard scan."""
from pathlib import Path

from fuzzydroid_isaaclab import _common as c
from fuzzydroid_isaaclab import detect
from fuzzydroid_isaaclab.setup import activate_has_static_tls


def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "config_dir", lambda: tmp_path)
    state = {"variant": "pip", "lab_root": "/some/venv", "mcp_port": 9010}
    c.save_state("isaaclab", state)
    assert c.load_state("isaaclab") == state


def test_recommend_newest_pip_over_source():
    inv = {
        "pip": [
            {"kind": "pip", "variant": "pip", "venv": "/v/old", "lab_version": "1.4.0"},
            {"kind": "pip", "variant": "pip", "venv": "/v/new", "lab_version": "2.1.0"},
        ],
        "source": [{"kind": "source", "variant": "source", "path": "/src/IsaacLab"}],
    }
    rec = detect.recommend(inv)
    assert rec["venv"] == "/v/new"


def test_recommend_source_when_no_pip():
    inv = {"pip": [], "source": [{"kind": "source", "variant": "source", "path": "/src/IsaacLab"}]}
    assert detect.recommend(inv)["path"] == "/src/IsaacLab"


def test_static_tls_scan_detects_hazard(tmp_path):
    venv = tmp_path
    (venv / "bin").mkdir()
    (venv / "bin" / "activate").write_text(
        'export GLIBC_TUNABLES="glibc.rtld.optional_static_tls=2097152"\n')
    assert activate_has_static_tls(venv) is True


def test_static_tls_scan_clean_activate(tmp_path):
    venv = tmp_path
    (venv / "bin").mkdir()
    (venv / "bin" / "activate").write_text("export PATH=...\n")
    assert activate_has_static_tls(venv) is False


def test_static_tls_scan_no_activate(tmp_path):
    assert activate_has_static_tls(tmp_path) is False


def test_dist_version_via_python_authoritative():
    import sys
    from fuzzydroid_isaaclab.detect import _dist_version_via_python
    # pytest is installed in this test env — the interpreter must report it
    assert _dist_version_via_python(Path(sys.executable), "pytest")
    # and must return None (not raise) for a dist that isn't installed
    assert _dist_version_via_python(Path(sys.executable), "definitely-not-a-dist") is None


def test_abs_verbatim_keeps_symlink_identity(tmp_path):
    from fuzzydroid_isaaclab.setup import _abs_verbatim
    real = tmp_path / "real-python"
    real.write_text("")
    link = tmp_path / "venv-python"
    link.symlink_to(real)
    # the recorded path must stay the symlink, not its target
    assert _abs_verbatim(str(link)) == link


def test_source_checkout_detection(tmp_path):
    checkout = tmp_path / "IsaacLab"
    (checkout / "source" / "isaaclab").mkdir(parents=True)
    (checkout / "isaaclab.sh").write_text("#!/bin/bash\n")
    hits = detect.find_source_checkouts([str(tmp_path)])
    assert any(h["path"] == str(checkout) for h in hits)
