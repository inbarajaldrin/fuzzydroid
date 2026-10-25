import io
import tarfile
import tomllib
from types import SimpleNamespace

import pytest

from fuzzydroid_kicad import paths, setup


def test_platform_paths_include_windows_and_config_overrides(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "detect_os", lambda: "windows")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.plugin_dir(10) == tmp_path / "kicad/10.0/scripting/plugins"
    monkeypatch.setattr(paths, "detect_os", lambda: "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert paths.plugin_dir(10) == tmp_path / "xdg/kicad/10.0/scripting/plugins"


def fixture_install(tmp_path, monkeypatch):
    root = tmp_path / "plugin"
    package = root / "lib/fuzzydroid_kicad"
    package.mkdir(parents=True)
    (package / "pyproject.toml").write_text('[project]\nname="test"\n')
    executable = tmp_path / "kicad-cli"
    executable.touch()
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    target = tmp_path / "config/kicad.toml"
    monkeypatch.setattr(setup.shutil, "which", lambda name: name)
    monkeypatch.setattr(setup, "cli_path", lambda explicit: executable)
    monkeypatch.setattr(setup, "python_path", lambda: python)
    monkeypatch.setattr(setup, "default_venv_path", lambda: tmp_path / "venv")
    monkeypatch.setattr(setup, "state_path", lambda: target)
    monkeypatch.setattr(setup, "stable_bindings", lambda python: None)
    monkeypatch.setattr(
        setup,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="10.0.7" if args[-1] == "version" else "Python 3.11"
        ),
    )
    return root, target, tmp_path / "plugins"


def test_setup_is_idempotent_and_records_loader_integrity(tmp_path, monkeypatch):
    root, target, destination = fixture_install(tmp_path, monkeypatch)
    setup.install(root, plugin_dir=destination)
    loader = destination / "fzd_kicad_loader.py"
    before = loader.read_bytes()
    setup.install(root, plugin_dir=destination)
    state = tomllib.loads(target.read_text())
    assert loader.read_bytes() == before
    assert state["loader_hash"] == setup.digest(loader)
    assert state["plugin_root"] == str(root)
    setup.install(root, plugin_dir=destination, native=False)
    assert not loader.exists()


def test_setup_preserves_an_unrelated_loader(tmp_path, monkeypatch):
    root, _, destination = fixture_install(tmp_path, monkeypatch)
    destination.mkdir()
    loader = destination / "fzd_kicad_loader.py"
    loader.write_text("user code")
    with pytest.raises(FileExistsError):
        setup.install(root, plugin_dir=destination)
    assert loader.read_text() == "user code"


def test_archive_path_escape_is_refused(tmp_path):
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as stream:
        entry = tarfile.TarInfo("../outside")
        entry.size = 1
        stream.addfile(entry, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe"):
        setup.extract(archive, tmp_path / "vendor")
    assert not (tmp_path / "outside").exists()


def test_custom_executable_recorded_by_setup_is_used_for_exports(tmp_path, monkeypatch):
    executable = tmp_path / "custom-cli"
    executable.touch()
    monkeypatch.delenv("KICAD_CLI", raising=False)
    monkeypatch.setattr(paths.shutil, "which", lambda _: None)
    monkeypatch.setattr(paths, "read_state", lambda: {"kicad_cli": str(executable)})
    assert paths.cli_path() == executable


def test_generated_loader_does_not_shadow_the_python_package(tmp_path, monkeypatch):
    import subprocess
    import sys

    root, _, destination = fixture_install(tmp_path, monkeypatch)
    setup.install(root, plugin_dir=destination)
    package = root / "lib/fuzzydroid_kicad/fuzzydroid_kicad"
    package.mkdir()
    (package / "__init__.py").write_text("")
    marker = tmp_path / "started"
    (package / "bridge.py").write_text(
        "from pathlib import Path\ndef start():\n    Path(" + repr(str(marker)) + ").touch()\n"
    )
    loader = destination / "fzd_kicad_loader.py"
    code = """import importlib.util, pathlib, sys
path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(path.stem, path)
module = importlib.util.module_from_spec(spec)
sys.modules[path.stem] = module
spec.loader.exec_module(module)
"""
    subprocess.run([sys.executable, "-c", code, str(loader)], check=True)
    assert marker.exists()
