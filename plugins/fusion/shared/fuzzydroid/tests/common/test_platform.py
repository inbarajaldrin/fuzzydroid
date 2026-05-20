"""Tests for fuzzydroid.common.platform."""
from pathlib import Path
from unittest.mock import patch

import pytest

from fuzzydroid.common import platform as fd_platform


class TestDetectOS:
    def test_darwin_returns_macos(self):
        with patch("platform.system", return_value="Darwin"):
            assert fd_platform.detect_os() == "macos"

    def test_windows_returns_windows(self):
        with patch("platform.system", return_value="Windows"):
            assert fd_platform.detect_os() == "windows"

    def test_linux_returns_linux(self):
        with patch("platform.system", return_value="Linux"):
            assert fd_platform.detect_os() == "linux"

    def test_unknown_raises(self):
        with patch("platform.system", return_value="Plan9"):
            with pytest.raises(fd_platform.UnsupportedPlatformError):
                fd_platform.detect_os()


class TestSharedVenvPath:
    def test_macos_uses_local_share(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/alice")
        with patch("platform.system", return_value="Darwin"):
            assert fd_platform.shared_venv_path() == Path("/Users/alice/.local/share/fuzzydroid/venv")

    def test_windows_uses_localappdata(self, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", "C:\\Users\\alice\\AppData\\Local")
        with patch("platform.system", return_value="Windows"):
            result = fd_platform.shared_venv_path()
            assert str(result).replace("\\", "/").endswith("AppData/Local/fuzzydroid/venv")

    def test_windows_missing_localappdata_raises(self, monkeypatch):
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        with patch("platform.system", return_value="Windows"):
            with pytest.raises(RuntimeError, match="LOCALAPPDATA"):
                fd_platform.shared_venv_path()


class TestConfigDir:
    def test_macos_uses_xdg_config(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/alice")
        with patch("platform.system", return_value="Darwin"):
            assert fd_platform.config_dir() == Path("/Users/alice/.config/fuzzydroid")

    def test_windows_uses_appdata(self, monkeypatch):
        monkeypatch.setenv("APPDATA", "C:\\Users\\alice\\AppData\\Roaming")
        with patch("platform.system", return_value="Windows"):
            result = fd_platform.config_dir()
            assert str(result).replace("\\", "/").endswith("AppData/Roaming/fuzzydroid")

    def test_windows_missing_appdata_raises(self, monkeypatch):
        monkeypatch.delenv("APPDATA", raising=False)
        with patch("platform.system", return_value="Windows"):
            with pytest.raises(RuntimeError, match="APPDATA"):
                fd_platform.config_dir()


class TestFusionAddinsDir:
    def test_macos_path(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/alice")
        with patch("platform.system", return_value="Darwin"):
            result = fd_platform.fusion_addins_dir()
            assert result == Path(
                "/Users/alice/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
            )

    def test_windows_path(self, monkeypatch):
        monkeypatch.setenv("APPDATA", "C:\\Users\\alice\\AppData\\Roaming")
        with patch("platform.system", return_value="Windows"):
            result = fd_platform.fusion_addins_dir()
            assert str(result).replace("\\", "/").endswith(
                "AppData/Roaming/Autodesk/Autodesk Fusion 360/API/AddIns"
            )

    def test_windows_missing_appdata_raises(self, monkeypatch):
        monkeypatch.delenv("APPDATA", raising=False)
        with patch("platform.system", return_value="Windows"):
            with pytest.raises(RuntimeError, match="APPDATA"):
                fd_platform.fusion_addins_dir()

    def test_linux_raises(self):
        with patch("platform.system", return_value="Linux"):
            with pytest.raises(fd_platform.UnsupportedPlatformError, match="Linux"):
                fd_platform.fusion_addins_dir()


class TestVenvPython:
    def test_macos_bin_python(self):
        venv = Path("/home/alice/.local/share/fuzzydroid/venv")
        with patch("platform.system", return_value="Darwin"):
            assert fd_platform.venv_python(venv) == venv / "bin" / "python"

    def test_windows_scripts_python_exe(self):
        venv = Path("C:/Users/alice/venv")
        with patch("platform.system", return_value="Windows"):
            assert fd_platform.venv_python(venv) == venv / "Scripts" / "python.exe"
