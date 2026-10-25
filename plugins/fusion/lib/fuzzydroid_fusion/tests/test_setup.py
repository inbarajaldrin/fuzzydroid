"""Tests for fuzzydroid_fusion.setup."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fuzzydroid_fusion import setup as fd_fusion_setup


def _seed_bundled_package(plugin_root: Path) -> None:
    """Create the bundled lib/fuzzydroid_fusion/pyproject.toml under plugin_root."""
    bundle = plugin_root / "lib" / "fuzzydroid_fusion"
    bundle.mkdir(parents=True)
    (bundle / "pyproject.toml").write_text("[project]\nname='fuzzydroid-fusion'\n")


class TestRunSetup:
    def test_aborts_on_linux(self, tmp_path):
        with patch("fuzzydroid_fusion._common.detect_os", return_value="linux"):
            log = MagicMock()
            result = fd_fusion_setup.run_setup(plugin_root=tmp_path, log=log)
            assert result.ok is False
            assert "linux" in result.message.lower()

    def test_aborts_without_uv(self, tmp_path):
        with patch("fuzzydroid_fusion._common.detect_os", return_value="macos"), \
             patch("fuzzydroid_fusion._common.is_uv_available", return_value=False):
            log = MagicMock()
            result = fd_fusion_setup.run_setup(plugin_root=tmp_path, log=log)
            assert result.ok is False
            assert "uv" in result.message.lower()

    def test_happy_path_writes_state_file(self, tmp_path, monkeypatch):
        # Fake plugin root: contains addin/fusion_bridge AND bundled lib/fuzzydroid_fusion
        plugin_root = tmp_path / "plugin"
        (plugin_root / "addin" / "fusion_bridge").mkdir(parents=True)
        (plugin_root / "addin" / "fusion_bridge" / "manifest").write_text("stub")
        _seed_bundled_package(plugin_root)

        fake_addins = tmp_path / "fusion_addins"
        fake_addins.mkdir()
        fake_config = tmp_path / "config"
        fake_venv = tmp_path / "venv"

        monkeypatch.setattr("fuzzydroid_fusion._common.detect_os", lambda: "macos")
        monkeypatch.setattr("fuzzydroid_fusion._common.is_uv_available", lambda: True)
        monkeypatch.setattr(
            "fuzzydroid_fusion._common.plugin_venv_path", lambda name: fake_venv
        )
        monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: fake_config)
        monkeypatch.setattr("fuzzydroid_fusion.setup.fusion_addins_dir", lambda: fake_addins)
        monkeypatch.setattr("fuzzydroid_fusion._common.ensure_venv", lambda *a, **k: None)
        monkeypatch.setattr("fuzzydroid_fusion._common.install_editable", lambda *a, **k: None)

        def fake_symlink(source, target):
            target.symlink_to(source, target_is_directory=True)
            return None
        monkeypatch.setattr(
            "fuzzydroid_fusion._symlink.create_directory_symlink", fake_symlink
        )

        log = MagicMock()
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=log)

        assert result.ok is True
        state_file = fake_config / "fusion.toml"
        assert state_file.exists()
        assert "plugin_version" in state_file.read_text()
        assert (fake_addins / "fusion_bridge").is_symlink()


# ---------- raise-path coverage ----------


def _make_happy_env(tmp_path, monkeypatch):
    """Build a plugin_root + patched environment that reaches Step 5.

    Returns (plugin_root, fake_addins, fake_config, fake_venv). The bundled
    lib/fuzzydroid_fusion/pyproject.toml is seeded under plugin_root.
    """
    plugin_root = tmp_path / "plugin"
    (plugin_root / "addin" / "fusion_bridge").mkdir(parents=True)
    _seed_bundled_package(plugin_root)

    fake_addins = tmp_path / "fusion_addins"
    fake_addins.mkdir()
    fake_config = tmp_path / "config"
    fake_venv = tmp_path / "venv"

    monkeypatch.setattr("fuzzydroid_fusion._common.detect_os", lambda: "macos")
    monkeypatch.setattr("fuzzydroid_fusion._common.is_uv_available", lambda: True)
    monkeypatch.setattr(
        "fuzzydroid_fusion._common.plugin_venv_path", lambda name: fake_venv
    )
    monkeypatch.setattr("fuzzydroid_fusion._common.config_dir", lambda: fake_config)
    monkeypatch.setattr("fuzzydroid_fusion.setup.fusion_addins_dir", lambda: fake_addins)
    monkeypatch.setattr("fuzzydroid_fusion._common.ensure_venv", lambda *a, **k: None)
    monkeypatch.setattr("fuzzydroid_fusion._common.install_editable", lambda *a, **k: None)
    return plugin_root, fake_addins, fake_config, fake_venv


class TestRaisePaths:
    def test_unsupported_platform_error_returns_fail(self, tmp_path):
        from fuzzydroid_fusion import _common

        def boom():
            raise _common.UnsupportedPlatformError("FreeBSD")

        with patch("fuzzydroid_fusion._common.detect_os", side_effect=boom):
            result = fd_fusion_setup.run_setup(plugin_root=tmp_path, log=MagicMock())
        assert result.ok is False
        assert "unsupported platform" in result.message.lower()

    def test_ensure_venv_error_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid_fusion import _common

        def boom(*a, **k):
            raise _common.VenvError("uv venv failed: boom")

        monkeypatch.setattr("fuzzydroid_fusion._common.ensure_venv", boom)
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=MagicMock())
        assert result.ok is False
        assert "boom" in result.message

    def test_install_editable_error_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid_fusion import _common

        def boom(*a, **k):
            raise _common.VenvError("install failed: pkg missing")

        monkeypatch.setattr("fuzzydroid_fusion._common.install_editable", boom)
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=MagicMock())
        assert result.ok is False
        assert "pkg missing" in result.message

    def test_fusion_addins_dir_unsupported_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid_fusion import _common

        def boom():
            raise _common.UnsupportedPlatformError("no addins dir on linux")

        monkeypatch.setattr("fuzzydroid_fusion.setup.fusion_addins_dir", boom)
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=MagicMock())
        assert result.ok is False
        assert "addins" in result.message.lower()

    def test_fusion_not_installed_when_addins_parent_missing(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        bogus = tmp_path / "nowhere" / "AddIns"
        monkeypatch.setattr("fuzzydroid_fusion.setup.fusion_addins_dir", lambda: bogus)
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=MagicMock())
        assert result.ok is False
        assert "fusion 360 not installed" in result.message.lower()

    def test_symlink_error_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)
        from fuzzydroid_fusion import _symlink

        def boom(source, target):
            raise _symlink.SymlinkError("mklink exploded")

        monkeypatch.setattr("fuzzydroid_fusion._symlink.create_directory_symlink", boom)
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=MagicMock())
        assert result.ok is False
        assert "mklink exploded" in result.message

    def test_symlink_filenotfound_returns_fail(self, tmp_path, monkeypatch):
        plugin_root, *_ = _make_happy_env(tmp_path, monkeypatch)

        def boom(source, target):
            raise FileNotFoundError(f"missing: {source}")

        monkeypatch.setattr("fuzzydroid_fusion._symlink.create_directory_symlink", boom)
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=MagicMock())
        assert result.ok is False
        assert "missing" in result.message.lower()

    def test_backup_warning_logged_when_existing_dir_backed_up(self, tmp_path, monkeypatch):
        plugin_root, fake_addins, *_ = _make_happy_env(tmp_path, monkeypatch)

        def fake_symlink(source, target):
            target.symlink_to(source, target_is_directory=True)
            return target.with_name(target.name + ".bak-20260410-120000")

        monkeypatch.setattr(
            "fuzzydroid_fusion._symlink.create_directory_symlink", fake_symlink
        )
        log = MagicMock()
        result = fd_fusion_setup.run_setup(plugin_root=plugin_root, log=log)
        assert result.ok is True
        warning_calls = [c for c in log.warning.call_args_list]
        assert any("backed up" in str(c).lower() for c in warning_calls)


class TestFusionAddinsDir:
    def test_macos_path(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/alice")
        with patch("platform.system", return_value="Darwin"):
            result = fd_fusion_setup.fusion_addins_dir()
            assert result == Path(
                "/Users/alice/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns"
            )

    def test_windows_path(self, monkeypatch):
        monkeypatch.setenv("APPDATA", "C:\\Users\\alice\\AppData\\Roaming")
        with patch("platform.system", return_value="Windows"):
            result = fd_fusion_setup.fusion_addins_dir()
            assert str(result).replace("\\", "/").endswith(
                "AppData/Roaming/Autodesk/Autodesk Fusion 360/API/AddIns"
            )

    def test_windows_missing_appdata_raises(self, monkeypatch):
        monkeypatch.delenv("APPDATA", raising=False)
        with patch("platform.system", return_value="Windows"):
            with pytest.raises(RuntimeError, match="APPDATA"):
                fd_fusion_setup.fusion_addins_dir()

    def test_linux_raises(self):
        from fuzzydroid_fusion import _common
        with patch("platform.system", return_value="Linux"):
            with pytest.raises(_common.UnsupportedPlatformError, match="Linux"):
                fd_fusion_setup.fusion_addins_dir()


class TestMain:
    def test_main_without_env_var_returns_1(self, monkeypatch, capsys):
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
        rc = fd_fusion_setup.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "CLAUDE_PLUGIN_ROOT" in out

    def test_main_delegates_to_run_setup_and_returns_exit_code(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))

        monkeypatch.setattr(
            fd_fusion_setup, "run_setup",
            lambda **kw: fd_fusion_setup.SetupResult(ok=False, message="fake"),
        )
        assert fd_fusion_setup.main() == 1

        monkeypatch.setattr(
            fd_fusion_setup, "run_setup",
            lambda **kw: fd_fusion_setup.SetupResult(ok=True, message="ok"),
        )
        assert fd_fusion_setup.main() == 0
