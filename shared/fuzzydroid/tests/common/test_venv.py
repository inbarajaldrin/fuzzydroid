"""Tests for fuzzydroid.common.venv."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fuzzydroid.common import venv as fd_venv


class TestIsUvAvailable:
    def test_returns_true_when_uv_on_path(self):
        with patch("shutil.which", return_value="/usr/local/bin/uv"):
            assert fd_venv.is_uv_available() is True

    def test_returns_false_when_uv_missing(self):
        with patch("shutil.which", return_value=None):
            assert fd_venv.is_uv_available() is False


class TestEnsureVenv:
    def test_creates_venv_when_missing(self, tmp_path):
        venv = tmp_path / "venv"
        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            mock_run.return_value.returncode = 0
            fd_venv.ensure_venv(venv, python_version="3.11")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Assert exact argument order: uv venv <path> --python 3.11
        assert cmd[0] == "uv"
        assert cmd[1] == "venv"
        assert cmd[2] == str(venv)
        assert "--python" in cmd
        assert "3.11" in cmd
        # Assert --python is immediately followed by version
        python_idx = cmd.index("--python")
        assert cmd[python_idx + 1] == "3.11"

    def test_skips_creation_when_venv_exists(self, tmp_path):
        venv = tmp_path / "venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").touch()

        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            fd_venv.ensure_venv(venv, python_version="3.11")

        mock_run.assert_not_called()

    def test_raises_venv_error_on_uv_failure(self, tmp_path):
        venv = tmp_path / "venv"
        with patch("subprocess.run") as mock_run, \
             patch("platform.system", return_value="Darwin"):
            result = MagicMock()
            result.returncode = 1
            result.stderr = "uv: no such Python"
            mock_run.return_value = result
            with pytest.raises(fd_venv.VenvError, match="uv venv failed"):
                fd_venv.ensure_venv(venv, python_version="3.11")


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
            fd_venv.install_editable(venv, package)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Assert exact argument structure: uv pip install --python <venv-python> -e <package>
        assert cmd[0] == "uv"
        assert cmd[1] == "pip"
        assert cmd[2] == "install"
        assert "--python" in cmd
        python_idx = cmd.index("--python")
        assert cmd[python_idx + 1] == str(venv / "bin" / "python")
        assert "-e" in cmd
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
            with pytest.raises(fd_venv.VenvError, match="install"):
                fd_venv.install_editable(venv, package)


class TestVenvErrorType:
    def test_venv_error_is_runtime_error(self):
        assert issubclass(fd_venv.VenvError, RuntimeError)
