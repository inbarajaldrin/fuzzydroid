"""Tests for fuzzydroid.common.config."""
from pathlib import Path

import pytest

from fuzzydroid.common import config as fd_config


class TestSaveAndLoadState:
    def test_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: tmp_path,
        )
        state = {
            "venv_path": "/home/alice/.local/share/fuzzydroid/venv",
            "plugin_version": "0.1.0",
            "pyproject_hash": "abc123",
            "install_timestamp": "2026-04-10T12:00:00",
            "python_version": "3.11",
        }
        fd_config.save_state("fusion", state)
        loaded = fd_config.load_state("fusion")
        assert loaded == state

    def test_load_missing_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: tmp_path,
        )
        assert fd_config.load_state("nope") is None

    def test_save_creates_config_dir(self, tmp_path, monkeypatch):
        nested = tmp_path / "nested" / "config"
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: nested,
        )
        fd_config.save_state("fusion", {"plugin_version": "0.1.0"})
        assert (nested / "fusion.toml").exists()

    def test_save_with_nested_plugin_specific_field(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: tmp_path,
        )
        state = {
            "plugin_version": "0.1.0",
            "addin_symlink_path": "/Users/alice/Library/.../fusion_bridge",
        }
        fd_config.save_state("fusion", state)
        loaded = fd_config.load_state("fusion")
        assert loaded["addin_symlink_path"] == state["addin_symlink_path"]

    def test_save_handles_bool_and_int_values(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: tmp_path,
        )
        state = {
            "plugin_version": "0.1.0",
            "dry_run": True,
            "retry_count": 3,
        }
        fd_config.save_state("fusion", state)
        loaded = fd_config.load_state("fusion")
        assert loaded["dry_run"] is True
        assert loaded["retry_count"] == 3

    def test_save_rejects_unsupported_types(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: tmp_path,
        )
        with pytest.raises(TypeError):
            fd_config.save_state("fusion", {"bad": [1, 2, 3]})

    def test_save_escapes_single_quotes_in_strings(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: tmp_path,
        )
        state = {"plugin_version": "0.1.0", "note": "it's a test"}
        fd_config.save_state("fusion", state)
        loaded = fd_config.load_state("fusion")
        assert loaded["note"] == "it's a test"

    def test_save_round_trips_double_quotes_and_backslashes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "fuzzydroid.common.platform.config_dir",
            lambda: tmp_path,
        )
        state = {
            "plugin_version": "0.1.0",
            "windows_path": "C:\\Users\\alice\\AppData",
            "quoted": 'she said "hello"',
        }
        fd_config.save_state("fusion", state)
        loaded = fd_config.load_state("fusion")
        assert loaded["windows_path"] == "C:\\Users\\alice\\AppData"
        assert loaded["quoted"] == 'she said "hello"'


class TestHashPyproject:
    def test_identical_files_same_hash(self, tmp_path):
        a = tmp_path / "a.toml"
        b = tmp_path / "b.toml"
        a.write_text("[project]\nname = 'x'\n")
        b.write_text("[project]\nname = 'x'\n")
        assert fd_config.hash_pyproject(a) == fd_config.hash_pyproject(b)

    def test_different_files_different_hash(self, tmp_path):
        a = tmp_path / "a.toml"
        b = tmp_path / "b.toml"
        a.write_text("[project]\nname = 'x'\n")
        b.write_text("[project]\nname = 'y'\n")
        assert fd_config.hash_pyproject(a) != fd_config.hash_pyproject(b)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            fd_config.hash_pyproject(tmp_path / "missing.toml")

    def test_hash_is_hex_string(self, tmp_path):
        a = tmp_path / "a.toml"
        a.write_text("x")
        h = fd_config.hash_pyproject(a)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex
        int(h, 16)  # must be valid hex
