import pytest

from fuzzydroid_kicad import platform


@pytest.mark.parametrize("system", ["Darwin", "Windows", "Linux"])
def test_user_state_and_runtime_paths_for_each_supported_os(system, tmp_path, monkeypatch):
    monkeypatch.setattr(platform.platform, "system", lambda: system)
    monkeypatch.setattr(platform.Path, "home", lambda: tmp_path / "home")
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    if system == "Windows":
        assert platform.config_dir() == tmp_path / "roaming/fuzzydroid"
        assert platform.shared_venv_path() == tmp_path / "local/fuzzydroid/venv"
        assert platform.venv_python(tmp_path) == tmp_path / "Scripts/python.exe"
    else:
        assert platform.config_dir() == tmp_path / "home/.config/fuzzydroid"
        assert platform.shared_venv_path() == tmp_path / "home/.local/share/fuzzydroid/venv"
        assert platform.venv_python(tmp_path) == tmp_path / "bin/python"


def test_unsupported_platform_has_a_clear_error(monkeypatch):
    monkeypatch.setattr(platform.platform, "system", lambda: "Unknown")
    with pytest.raises(RuntimeError, match="Unsupported platform"):
        platform.detect_os()
