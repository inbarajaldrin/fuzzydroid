"""Tests for fuzzydroid.common.symlink."""
from pathlib import Path
from unittest.mock import patch

import pytest

from fuzzydroid.common import symlink as fd_symlink


class TestCreateDirectorySymlink:
    def test_macos_uses_os_symlink(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "marker.txt").write_text("hello")

        target = tmp_path / "link"

        with patch("platform.system", return_value="Darwin"):
            fd_symlink.create_directory_symlink(source, target)

        assert target.is_symlink()
        assert (target / "marker.txt").read_text() == "hello"

    def test_target_already_exists_as_symlink_is_replaced(self, tmp_path):
        source_a = tmp_path / "a"
        source_a.mkdir()
        (source_a / "a.txt").write_text("a")

        source_b = tmp_path / "b"
        source_b.mkdir()
        (source_b / "b.txt").write_text("b")

        target = tmp_path / "link"

        with patch("platform.system", return_value="Darwin"):
            fd_symlink.create_directory_symlink(source_a, target)
            fd_symlink.create_directory_symlink(source_b, target)

        assert target.is_symlink()
        assert (target / "b.txt").read_text() == "b"
        assert not (target / "a.txt").exists()

    def test_target_exists_as_real_directory_is_backed_up(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "source.txt").write_text("source")

        target = tmp_path / "link"
        target.mkdir()
        (target / "real.txt").write_text("real")

        with patch("platform.system", return_value="Darwin"):
            backup = fd_symlink.create_directory_symlink(source, target)

        assert target.is_symlink()
        assert (target / "source.txt").read_text() == "source"
        assert backup is not None
        assert backup.is_dir()
        assert (backup / "real.txt").read_text() == "real"
        assert backup.name.startswith("link.bak-")

    def test_source_must_be_directory(self, tmp_path):
        source = tmp_path / "file.txt"
        source.write_text("not a dir")
        target = tmp_path / "link"

        with patch("platform.system", return_value="Darwin"):
            with pytest.raises(NotADirectoryError):
                fd_symlink.create_directory_symlink(source, target)

    def test_source_must_exist(self, tmp_path):
        source = tmp_path / "missing"
        target = tmp_path / "link"

        with patch("platform.system", return_value="Darwin"):
            with pytest.raises(FileNotFoundError):
                fd_symlink.create_directory_symlink(source, target)

    def test_post_check_raises_if_symlink_not_created(self, tmp_path, monkeypatch):
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "link"

        # Stub os.symlink to a no-op so the file is never actually created.
        # The post-check should notice and raise SymlinkError.
        monkeypatch.setattr("os.symlink", lambda *a, **kw: None)

        with patch("platform.system", return_value="Darwin"):
            with pytest.raises(fd_symlink.SymlinkError, match="not a symlink"):
                fd_symlink.create_directory_symlink(source, target)


class TestWindowsJunction:
    def test_windows_invokes_mklink(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "link"

        # On a non-Windows host we need to stub out both detect_os AND the post-check
        # that verifies the target is a symlink — since mklink would only exist on Windows.
        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_result = mock_run.return_value
                mock_result.returncode = 0
                mock_result.stderr = ""
                # Stub the post-creation check so the function returns successfully
                with patch.object(Path, "exists", return_value=True), \
                     patch.object(Path, "is_symlink", return_value=True):
                    fd_symlink.create_directory_symlink(source, target)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        assert "mklink" in cmd_str
        assert "/J" in cmd
        # mklink /J <Link> <Target> — target (the junction path) comes BEFORE source
        assert cmd[-2] == str(target)
        assert cmd[-1] == str(source)

    def test_windows_mklink_failure_raises(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "link"

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_result = mock_run.return_value
                mock_result.returncode = 1
                mock_result.stderr = "ERROR: Access is denied."
                with pytest.raises(fd_symlink.SymlinkError, match="mklink"):
                    fd_symlink.create_directory_symlink(source, target)


class TestSymlinkErrorType:
    def test_symlink_error_is_runtime_error(self):
        assert issubclass(fd_symlink.SymlinkError, RuntimeError)
