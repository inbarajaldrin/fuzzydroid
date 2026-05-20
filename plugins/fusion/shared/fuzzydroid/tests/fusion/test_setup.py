"""Tests for fuzzydroid.fusion.setup."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fuzzydroid.fusion import setup as fd_fusion_setup


def _seed_bundled_shared(plugin_root: Path) -> None:
    """Create the bundled shared/fuzzydroid/pyproject.toml under plugin_root."""
    bundle = plugin_root / "shared" / "fuzzydroid"
    bundle.mkdir(parents=True)
    (bundle / "pyproject.toml").write_text("[project]\nname='fuzzydroid'\n")


class TestRunSetup:
    def test_aborts_on_linux(self, tmp_path):
        with patch(
            "fuzzydroid.common.platform.detect_os", return_value="linux"
        ):
            log = MagicMock()
            result = fd_fusion_setup.run_setup(
                plugin_root=tmp_path, log=log
            )
            assert result.ok is False
            assert "linux" in result.message.lower()

    def test_aborts_without_uv(self, tmp_path):
        with patch("fuzzydroid.common.platform.detect_os", return_value="macos"), \
             patch("fuzzydroid.common.venv.is_uv_available", return_value=False):
            log = MagicMock()
            result = fd_fusion_setup.run_setup(
                plugin_root=tmp_path, log=log
            )
            assert result.ok is False
            assert "uv" in result.message.lower()

    def test_happy_path_writes_state_file(self, tmp_path, monkeypatch):
        # Fake plugin root: contains addin/fusion_bridge AND bundled shared/fuzzydroid
        plugin_root = tmp_path / "plugin"
        (plugin_root / "addin" / "fusion_bridge").mkdir(parents=True)
        (plugin_root / "addin" / "fusion_bridge" / "manifest").write_text("stub")
        _seed_bundled_shared(plugin_root)

        fake_addins = tmp_path / "fusion_addins"
        fake_addins.mkdir()
        fake_config = tmp_path / "config"
        fake_venv = tmp_path / "venv"

        monkeypatch.setattr(
            "fuzzydroid.common.platform.detect_os", lambda: "macos"
        )
        monkeypatch.setattr(
            "fuzzydroid.common.venv.is_uv_available", lambda: True
        )
        monkeypatch.setattr(
            "fuzzydroid.common.platform.shared_venv_path", lambda: fake_venv
        )
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir", lambda: fake_config
        )
        monkeypatch.setattr(
            "fuzzydroid.common.platform.fusion_addins_dir", lambda: fake_addins
        )
        monkeypatch.setattr(
            "fuzzydroid.common.venv.ensure_venv", lambda *a, **k: None
        )
        monkeypatch.setattr(
            "fuzzydroid.common.venv.install_editable", lambda *a, **k: None
        )

        def fake_symlink(source, target):
            target.symlink_to(source, target_is_directory=True)
            return None
        monkeypatch.setattr(
            "fuzzydroid.common.symlink.create_directory_symlink", fake_symlink
        )

        log = MagicMock()
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=log
        )

        assert result.ok is True
        state_file = fake_config / "fusion.toml"
        assert state_file.exists()
        assert "plugin_version" in state_file.read_text()
        assert (fake_addins / "fusion_bridge").is_symlink()


# ---------- raise-path coverage ----------


def _make_happy_env(tmp_path, monkeypatch):
    """Build a plugin_root + patched environment that reaches Step 5.

    Returns (plugin_root, fake_addins, fake_config, fake_venv). The bundled
    shared/fuzzydroid/pyproject.toml is seeded under plugin_root.
    """
    plugin_root = tmp_path / "plugin"
    (plugin_root / "addin" / "fusion_bridge").mkdir(parents=True)
    _seed_bundled_shared(plugin_root)

    fake_addins = tmp_path / "fusion_addins"
    fake_addins.mkdir()
    fake_config = tmp_path / "config"
    fake_venv = tmp_path / "venv"

    monkeypatch.setattr("fuzzydroid.common.platform.detect_os", lambda: "macos")
    monkeypatch.setattr("fuzzydroid.common.venv.is_uv_available", lambda: True)
    monkeypatch.setattr(
        "fuzzydroid.common.platform.shared_venv_path", lambda: fake_venv
    )
    monkeypatch.setattr(
        "fuzzydroid.common.platform.config_dir", lambda: fake_config
    )
    monkeypatch.setattr(
        "fuzzydroid.common.platform.fusion_addins_dir", lambda: fake_addins
    )
    monkeypatch.setattr(
        "fuzzydroid.common.venv.ensure_venv", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "fuzzydroid.common.venv.install_editable", lambda *a, **k: None
    )
    return plugin_root, fake_addins, fake_config, fake_venv


class TestRaisePaths:
    def test_unsupported_platform_error_returns_fail(self, tmp_path):
        from fuzzydroid.common import platform as fd_platform

        def boom():
            raise fd_platform.UnsupportedPlatformError("FreeBSD")

        with patch("fuzzydroid.common.platform.detect_os", side_effect=boom):
            result = fd_fusion_setup.run_setup(plugin_root=tmp_path, log=MagicMock())
        assert result.ok is False
        assert "unsupported platform" in result.message.lower()

    def test_ensure_venv_error_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid.common import venv as fd_venv

        def boom(*a, **k):
            raise fd_venv.VenvError("uv venv failed: boom")

        monkeypatch.setattr("fuzzydroid.common.venv.ensure_venv", boom)
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=MagicMock()
        )
        assert result.ok is False
        assert "boom" in result.message

    def test_install_editable_error_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid.common import venv as fd_venv

        def boom(*a, **k):
            raise fd_venv.VenvError("install failed: pkg missing")

        monkeypatch.setattr("fuzzydroid.common.venv.install_editable", boom)
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=MagicMock()
        )
        assert result.ok is False
        assert "pkg missing" in result.message

    def test_fusion_addins_dir_unsupported_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid.common import platform as fd_platform

        def boom():
            raise fd_platform.UnsupportedPlatformError("no addins dir on linux")

        monkeypatch.setattr("fuzzydroid.common.platform.fusion_addins_dir", boom)
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=MagicMock()
        )
        assert result.ok is False
        assert "addins" in result.message.lower()

    def test_fusion_not_installed_when_addins_parent_missing(
        self, tmp_path, monkeypatch
    ):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        # Point addins dir at a location whose PARENT doesn't exist
        bogus = tmp_path / "nowhere" / "AddIns"
        monkeypatch.setattr(
            "fuzzydroid.common.platform.fusion_addins_dir", lambda: bogus
        )
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=MagicMock()
        )
        assert result.ok is False
        assert "fusion 360 not installed" in result.message.lower()

    def test_symlink_error_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid.common import symlink as fd_symlink

        def boom(source, target):
            raise fd_symlink.SymlinkError("mklink exploded")

        monkeypatch.setattr(
            "fuzzydroid.common.symlink.create_directory_symlink", boom
        )
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=MagicMock()
        )
        assert result.ok is False
        assert "mklink exploded" in result.message

    def test_symlink_filenotfound_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)

        def boom(source, target):
            raise FileNotFoundError(f"missing: {source}")

        monkeypatch.setattr(
            "fuzzydroid.common.symlink.create_directory_symlink", boom
        )
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=MagicMock()
        )
        assert result.ok is False
        assert "missing" in result.message.lower()

    def test_backup_warning_logged_when_existing_dir_backed_up(
        self, tmp_path, monkeypatch
    ):
        plugin_root, fake_addins, *_ = _make_happy_env(tmp_path, monkeypatch)

        def fake_symlink(source, target):
            target.symlink_to(source, target_is_directory=True)
            return target.with_name(target.name + ".bak-20260410-120000")

        monkeypatch.setattr(
            "fuzzydroid.common.symlink.create_directory_symlink", fake_symlink
        )
        log = MagicMock()
        result = fd_fusion_setup.run_setup(
            plugin_root=plugin_root, log=log
        )
        assert result.ok is True
        # The warning about the backup should have been emitted
        warning_calls = [c for c in log.warning.call_args_list]
        assert any("backed up" in str(c).lower() for c in warning_calls)


class TestMain:
    def test_main_without_env_var_returns_1(self, monkeypatch, capsys):
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        rc = fd_fusion_setup.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "CLAUDE_PLUGIN_ROOT" in out

    def test_main_delegates_to_run_setup_and_returns_exit_code(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))

        def fake_run_setup(**kwargs):
            return fd_fusion_setup.SetupResult(ok=False, message="fake")

        monkeypatch.setattr(fd_fusion_setup, "run_setup", fake_run_setup)
        assert fd_fusion_setup.main() == 1

        monkeypatch.setattr(
            fd_fusion_setup,
            "run_setup",
            lambda **kw: fd_fusion_setup.SetupResult(ok=True, message="ok"),
        )
        assert fd_fusion_setup.main() == 0
