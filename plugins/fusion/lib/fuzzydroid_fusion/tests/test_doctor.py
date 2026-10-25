"""Tests for fuzzydroid_fusion.doctor."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fuzzydroid_fusion import _common
from fuzzydroid_fusion import doctor as fd_doctor


class TestCheckStateFile:
    def test_missing_returns_fail(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        check = fd_doctor.check_state_file()
        assert check.ok is False
        assert "setup" in check.message.lower()

    def test_present_returns_pass(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        _common.save_state("fusion", {"plugin_version": "0.2.0"})
        check = fd_doctor.check_state_file()
        assert check.ok is True

    def test_corrupt_state_file_returns_fail(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        (tmp_path / "fusion.toml").write_text("this is = not = valid toml [[[\n")
        check = fd_doctor.check_state_file()
        assert check.ok is False
        assert "corrupt" in check.message.lower() or "invalid" in check.message.lower()


class TestCheckPyprojectDrift:
    def test_same_hash_passes(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname='x'\n")
        state = {"pyproject_hash": _common.hash_file(pyproject)}
        check = fd_doctor.check_pyproject_drift(state, pyproject)
        assert check.ok is True

    def test_different_hash_fails(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname='x'\n")
        state = {"pyproject_hash": "stale123"}
        check = fd_doctor.check_pyproject_drift(state, pyproject)
        assert check.ok is False
        assert "setup" in check.message.lower()

    def test_missing_hash_in_state_fails(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname='x'\n")
        check = fd_doctor.check_pyproject_drift({}, pyproject)
        assert check.ok is False
        assert "pyproject_hash" in check.message

    def test_missing_pyproject_file_fails(self, tmp_path):
        state = {"pyproject_hash": "abc"}
        check = fd_doctor.check_pyproject_drift(state, tmp_path / "nope.toml")
        assert check.ok is False
        assert "not found" in check.message.lower()


class TestCheckSymlink:
    def test_valid_symlink_passes(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        link = tmp_path / "link"
        link.symlink_to(source, target_is_directory=True)
        state = {"addin_symlink_path": str(link)}
        check = fd_doctor.check_addin_symlink(state)
        assert check.ok is True

    def test_missing_symlink_fails(self, tmp_path):
        state = {"addin_symlink_path": str(tmp_path / "missing")}
        check = fd_doctor.check_addin_symlink(state)
        assert check.ok is False

    def test_real_dir_not_symlink_fails(self, tmp_path):
        real = tmp_path / "real"
        real.mkdir()
        state = {"addin_symlink_path": str(real)}
        check = fd_doctor.check_addin_symlink(state)
        assert check.ok is False
        assert "not a symlink" in check.message.lower()

    def test_missing_key_in_state_fails(self):
        check = fd_doctor.check_addin_symlink({})
        assert check.ok is False
        assert "addin_symlink_path" in check.message


class TestCheckVenv:
    def test_missing_key_fails(self):
        check = fd_doctor.check_venv({})
        assert check.ok is False
        assert "venv_path" in check.message

    def test_missing_python_bin_fails(self, tmp_path):
        state = {"venv_path": str(tmp_path / "venv_that_doesnt_exist")}
        check = fd_doctor.check_venv(state)
        assert check.ok is False
        assert "python" in check.message.lower()

    def test_valid_venv_passes(self, tmp_path, monkeypatch):
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").touch()
        monkeypatch.setattr("fuzzydroid_fusion._common.detect_os", lambda: "macos")
        check = fd_doctor.check_venv({"venv_path": str(venv)})
        assert check.ok is True


class TestCheckBridgePing:
    def test_no_live_endpoint_returns_fail(self, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid_fusion.core.bridge.resolve_endpoint", lambda: None
        )
        check = fd_doctor.check_bridge_ping()
        assert check.ok is False
        assert "no live endpoint" in check.message.lower()

    def test_live_tcp_endpoint_returns_pass(self, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid_fusion.core.bridge.resolve_endpoint",
            lambda: {"transport": "tcp", "host": "127.0.0.1", "port": 9999},
        )
        check = fd_doctor.check_bridge_ping()
        assert check.ok is True
        assert "tcp:127.0.0.1:9999" in check.message

    def test_live_uds_endpoint_returns_pass(self, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid_fusion.core.bridge.resolve_endpoint",
            lambda: {"transport": "uds", "path": "/tmp/fusion_bridge.sock"},
        )
        check = fd_doctor.check_bridge_ping()
        assert check.ok is True
        assert "uds:/tmp/fusion_bridge.sock" in check.message


class TestEditableInstallTarget:
    def test_percent_encoded_direct_url_matches(self, tmp_path, monkeypatch):
        """direct_url.json percent-encodes spaces; the check must decode them."""
        import json as _json
        monkeypatch.setattr("fuzzydroid_fusion._common.detect_os", lambda: "macos")
        plugin_root = tmp_path / "untitled folder" / "plugin"
        (plugin_root / "lib" / "fuzzydroid_fusion").mkdir(parents=True)
        venv = tmp_path / "venv"
        site = venv / "lib" / "python3.11" / "site-packages"
        dist = site / "fuzzydroid_fusion-0.2.0.dist-info"
        dist.mkdir(parents=True)
        target = (plugin_root / "lib" / "fuzzydroid_fusion").resolve()
        from urllib.parse import quote
        (dist / "direct_url.json").write_text(_json.dumps(
            {"url": "file://" + quote(str(target)), "dir_info": {"editable": True}}))
        check = fd_doctor.check_editable_install_target(
            {"venv_path": str(venv)}, plugin_root)
        assert check.ok is True, check.message


class TestRunDoctor:
    def test_no_state_prints_table_and_returns_1(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        rc = fd_doctor.run_doctor()
        assert rc == 1
        out = capsys.readouterr().out
        assert "| Check | Status | Detail |" in out
        assert "state file" in out

    def test_corrupt_state_does_not_crash(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        (tmp_path / "fusion.toml").write_text("garbage = = =\n")
        rc = fd_doctor.run_doctor()
        assert rc == 1
        out = capsys.readouterr().out
        assert "state file" in out

    def test_all_checks_pass_returns_0(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        monkeypatch.setattr("fuzzydroid_fusion._common.detect_os", lambda: "macos")

        # Prepare a valid venv layout
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").touch()

        # Valid symlink
        source = tmp_path / "addin-source"
        source.mkdir()
        link = tmp_path / "addin-link"
        link.symlink_to(source, target_is_directory=True)

        # Valid pyproject + matching hash, bundled inside plugin_root
        plugin_root = tmp_path / "plugin"
        (plugin_root / "lib" / "fuzzydroid_fusion").mkdir(parents=True)
        pyproject = plugin_root / "lib" / "fuzzydroid_fusion" / "pyproject.toml"
        pyproject.write_text("[project]\nname='fuzzydroid-fusion'\n")

        # Fake editable install pointing at the plugin_root's bundled package
        site_packages = venv / "lib" / "python3.11" / "site-packages"
        dist_info = site_packages / "fuzzydroid_fusion-0.2.0.dist-info"
        dist_info.mkdir(parents=True)
        target = (plugin_root / "lib" / "fuzzydroid_fusion").resolve()
        (dist_info / "direct_url.json").write_text(
            '{"url":"file://' + str(target) + '","dir_info":{"editable":true}}'
        )

        _common.save_state(
            "fusion",
            {
                "plugin_version": "0.2.0",
                "venv_path": str(venv),
                "addin_symlink_path": str(link),
                "pyproject_hash": _common.hash_file(pyproject),
            },
        )

        monkeypatch.setattr(
            "fuzzydroid_fusion.core.bridge.resolve_endpoint",
            lambda: {"transport": "uds", "path": "/tmp/fusion_bridge.sock"},
        )
        rc = fd_doctor.run_doctor(plugin_root=plugin_root)

        assert rc == 0
        out = capsys.readouterr().out
        assert "| Check |" in out
        assert "❌" not in out


class TestMain:
    def test_main_without_env_var_still_runs_doctor(self, monkeypatch, tmp_path, capsys):
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        rc = fd_doctor.main()
        assert rc == 1  # no state file → fails
        out = capsys.readouterr().out
        assert "| Check |" in out

    def test_main_with_env_var_passes_plugin_root(self, monkeypatch, tmp_path, capsys):
        plugin_root = tmp_path / "plugins" / "fusion"
        plugin_root.mkdir(parents=True)
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
        monkeypatch.setattr(
            "fuzzydroid_fusion._common.config_dir", lambda: tmp_path / "cfg"
        )
        (tmp_path / "cfg").mkdir()
        rc = fd_doctor.main()
        assert rc == 1  # no state file
