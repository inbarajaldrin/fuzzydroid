"""Check that Codex's plugin root reaches existing setup and CLI workflows."""

from pathlib import Path
from types import SimpleNamespace

from fuzzydroid_fusion import cli, doctor, setup


def test_codex_root_reaches_setup_and_doctor(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setenv("PLUGIN_ROOT", str(tmp_path))
    roots = []

    def run_setup(plugin_root):
        roots.append(plugin_root)
        return SimpleNamespace(ok=True)

    def run_doctor(plugin_root):
        roots.append(plugin_root)
        return 0

    monkeypatch.setattr(setup, "run_setup", run_setup)
    monkeypatch.setattr(doctor, "run_doctor", run_doctor)
    assert setup.main() == 0
    assert doctor.main() == 0
    assert roots == [tmp_path, tmp_path]


def test_export_script_resolution_accepts_codex_root(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setenv("PLUGIN_ROOT", str(tmp_path))
    (tmp_path / "scripts").mkdir()
    assert cli._find_plugin_scripts_dir() == tmp_path / "scripts"


def test_claude_root_takes_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    monkeypatch.setenv("PLUGIN_ROOT", str(tmp_path / "another-plugin"))
    (tmp_path / "scripts").mkdir()
    assert cli._find_plugin_scripts_dir() == Path(tmp_path / "scripts")
