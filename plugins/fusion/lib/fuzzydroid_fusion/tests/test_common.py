"""Tests for fuzzydroid_fusion._common (vendored fleet plumbing)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fuzzydroid_fusion import _common


class TestDetectOS:
    def test_darwin_returns_macos(self):
        with patch("platform.system", return_value="Darwin"):
            assert _common.detect_os() == "macos"

    def test_windows_returns_windows(self):
        with patch("platform.system", return_value="Windows"):
            assert _common.detect_os() == "windows"

    def test_linux_returns_linux(self):
        with patch("platform.system", return_value="Linux"):
            assert _common.detect_os() == "linux"

    def test_unknown_raises(self):
        with patch("platform.system", return_value="Plan9"):
            with pytest.raises(_common.UnsupportedPlatformError):
                _common.detect_os()


class TestPluginVenvPath:
    def test_macos_uses_local_share(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/alice")
        with patch("platform.system", return_value="Darwin"):
            assert _common.plugin_venv_path("fusion") == Path(
                "/Users/alice/.local/share/fuzzydroid/fusion/venv"
            )

    def test_windows_uses_localappdata(self, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\alice\\AppData\\Local")
        with patch("platform.system", return_value="Windows"):
            result = _common.plugin_venv_path("fusion")
            assert str(result).replace("\\", "/").endswith(
                "AppData/Local/fuzzydroid/fusion/venv"
            )

    def test_windows_missing_localappdata_raises(self, monkeypatch):
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        with patch("platform.system", return_value="Windows"):
            with pytest.raises(RuntimeError, match="LOCALAPPDATA"):
                _common.plugin_venv_path("fusion")

    def test_each_plugin_gets_own_venv(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/alice")
        with patch("platform.system", return_value="Darwin"):
            assert _common.plugin_venv_path("fusion") != _common.plugin_venv_path("isaacsim")


class TestConfigDir:
    def test_macos_uses_xdg_config(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/alice")
        with patch("platform.system", return_value="Darwin"):
            assert _common.config_dir() == Path("/Users/alice/.config/fuzzydroid")

    def test_windows_uses_appdata(self, monkeypatch):
        monkeypatch.setenv("APPDATA", "C:\\Users\\alice\\AppData\\Roaming")
        with patch("platform.system", return_value="Windows"):
            result = _common.config_dir()
            assert str(result).replace("\\", "/").endswith("AppData/Roaming/fuzzydroid")

    def test_windows_missing_appdata_raises(self, monkeypatch):
        monkeypatch.delenv("APPDATA", raising=False)
        with patch("platform.system", return_value="Windows"):
            with pytest.raises(RuntimeError, match="APPDATA"):
                _common.config_dir()


class TestVenvPython:
    def test_macos_bin_python(self):
        venv = Path("/home/alice/.local/share/fuzzydroid/fusion/venv")
        with patch("platform.system", return_value="Darwin"):
            assert _common.venv_python(venv) == venv / "bin" / "python"

    def test_windows_scripts_python_exe(self):
        venv = Path("C:/Users/alice/venv")
        with patch("platform.system", return_value="Windows"):
            assert _common.venv_python(venv) == venv / "Scripts" / "python.exe"


class TestSaveAndLoadState:
    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        state = {
            "venv_path": "/home/alice/.local/share/fuzzydroid/fusion/venv",
            "plugin_version": "0.2.0",
            "pyproject_hash": "abc123",
            "install_timestamp": "2026-04-10T12:00:00",
            "python_version": "3.11",
        }
        _common.save_state("fusion", state)
        assert _common.load_state("fusion") == state

    def test_load_missing_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        assert _common.load_state("nope") is None

    def test_save_creates_config_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "nested" / "config"
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: nested)
        _common.save_state("fusion", {"plugin_version": "0.2.0"})
        assert (nested / "fusion.toml").exists()

    def test_save_handles_bool_and_int_values(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        state = {"plugin_version": "0.2.0", "dry_run": True, "retry_count": 3}
        _common.save_state("fusion", state)
        loaded = _common.load_state("fusion")
        assert loaded["dry_run"] is True
        assert loaded["retry_count"] == 3

    def test_save_rejects_unsupported_types(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        with pytest.raises(TypeError):
            _common.save_state("fusion", {"bad": [1, 2, 3]})

    def test_save_round_trips_quotes_and_backslashes(self, tmp_path, monkeypatch):
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: tmp_path)
        state = {
            "plugin_version": "0.2.0",
            "windows_path": "C:\\Users\\alice\\AppData",
            "quoted": 'she said "hello"',
            "note": "it's a test",
        }
        _common.save_state("fusion", state)
        loaded = _common.load_state("fusion")
        assert loaded["windows_path"] == "C:\\Users\\alice\\AppData"
        assert loaded["quoted"] == 'she said "hello"'
        assert loaded["note"] == "it's a test"


class TestHashFile:
    def test_identical_files_same_hash(self, tmp_path):
        a = tmp_path / "a.toml"
        b = tmp_path / "b.toml"
        a.write_text("[project]\nname = 'x'\n")
        b.write_text("[project]\nname = 'x'\n")
        assert _common.hash_file(a) == _common.hash_file(b)

    def test_different_files_different_hash(self, tmp_path):
        a = tmp_path / "a.toml"
        b = tmp_path / "b.toml"
        a.write_text("[project]\nname = 'x'\n")
        b.write_text("[project]\nname = 'y'\n")
        assert _common.hash_file(a) != _common.hash_file(b)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _common.hash_file(tmp_path / "missing.toml")

    def test_hash_is_hex_string(self, tmp_path):
        a = tmp_path / "a.toml"
        a.write_text("x")
        h = _common.hash_file(a)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex
        int(h, 16)


class TestIsUvAvailable:
    def test_returns_true_when_uv_on_path(self):
        with patch("shutil.which", return_value="/usr/local/bin/uv"):
            assert _common.is_uv_available() is True

    def test_returns_false_when_uv_missing(self):
        with patch("shutil.which", return_value=None):
            assert _common.is_uv_available() is False


class TestEnsureVenv:
    def test_creates_venv_when_missing(self, tmp_path):
        venv = tmp_path / "venv"
        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            mock_run.return_value.returncode = 0
            _common.ensure_venv(venv, python_version="3.11")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "uv"
        assert cmd[1] == "venv"
        assert cmd[2] == str(venv)
        python_idx = cmd.index("--python")
        assert cmd[python_idx + 1] == "3.11"

    def test_skips_creation_when_venv_exists(self, tmp_path):
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").touch()
        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            _common.ensure_venv(venv, python_version="3.11")
        mock_run.assert_not_called()

    def test_raises_venv_error_on_uv_failure(self, tmp_path):
        venv = tmp_path / "venv"
        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            result = MagicMock()
            result.returncode = 1
            result.stderr = "uv: no such Python"
            mock_run.return_value = result
            with pytest.raises(_common.VenvError, match="uv venv failed"):
                _common.ensure_venv(venv, python_version="3.11")


class TestInstallEditable:
    def test_invokes_uv_pip_install_editable(self, tmp_path):
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").touch()
        package = tmp_path / "pkg"
        package.mkdir()
        (package / "pyproject.toml").write_text("")

        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            mock_run.return_value.returncode = 0
            _common.install_editable(venv, package)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[:3] == ["uv", "pip", "install"]
        python_idx = cmd.index("--python")
        assert cmd[python_idx + 1] == str(venv / "bin" / "python")
        e_idx = cmd.index("-e")
        assert cmd[e_idx + 1] == str(package)

    def test_raises_on_install_failure(self, tmp_path):
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").touch()
        package = tmp_path / "pkg"
        package.mkdir()

        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            result = MagicMock()
            result.returncode = 1
            result.stderr = "pip install failed"
            mock_run.return_value = result
            with pytest.raises(_common.VenvError, match="install"):
                _common.install_editable(venv, package)


class TestVersionKey:
    def test_orders_dotted_versions(self):
        assert _common.version_key("4.10.0") > _common.version_key("4.2.0")

    def test_non_numeric_parts_sort_low(self):
        assert _common.version_key("4.x") < _common.version_key("4.0")
