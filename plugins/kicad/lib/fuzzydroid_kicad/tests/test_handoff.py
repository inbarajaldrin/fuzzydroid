import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from fuzzydroid_kicad import handoff


class LiveBoard:
    def __init__(self, layers=2):
        self.layers = layers

    def call(self, tool, params):
        if tool == "ipc.save":
            return {"saved": True}
        assert tool == "native.python"
        return {
            "result": {
                "copper_layers": self.layers,
                "width_mm": 35,
                "height_mm": 25,
                "thickness_mm": 1.6,
                "footprints": [],
            }
        }


def sources(tmp_path):
    board = tmp_path / "board.kicad_pcb"
    board.write_text("board")
    board.with_suffix(".kicad_sch").write_text("schematic")
    return board


def test_existing_output_is_preserved(tmp_path):
    board = sources(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    original = out / "keep.txt"
    original.write_text("keep")
    with pytest.raises(FileExistsError):
        handoff.run(str(board), str(out))
    assert original.read_text() == "keep"


@pytest.mark.parametrize("failed_check", ["erc", "drc"])
def test_rule_failure_prevents_fabrication_exports(tmp_path, monkeypatch, failed_check):
    board = sources(tmp_path)
    calls = []

    def process(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(
            returncode=5 if failed_check in args else 0,
            stdout="rule violation" if failed_check in args else "10.0.7",
            stderr="",
        )

    monkeypatch.setattr(handoff, "cli_path", lambda: Path("kicad-cli"))
    monkeypatch.setattr(handoff.subprocess, "run", process)
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="rule violation"):
        handoff.run(str(board), str(out), service=LiveBoard())
    assert not any("gerbers" in call for call in calls)
    assert not list(out.rglob("*.zip"))
    assert json.loads((out / "handoff.json").read_text())["status"] == "failed"


def test_multilayer_board_cannot_use_two_layer_preset(tmp_path):
    board = sources(tmp_path)
    with pytest.raises(ValueError, match="two-layer"):
        handoff.run(str(board), str(tmp_path / "out"), service=LiveBoard(layers=4))


def test_fusion_cli_can_use_legacy_or_current_console_name(tmp_path, monkeypatch):
    monkeypatch.setattr(handoff, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(handoff, "detect_os", lambda: "macos")
    monkeypatch.setattr(handoff, "venv_python", lambda _: tmp_path / "bin/python")
    (tmp_path / "fusion.toml").write_text('venv_path = "test"')
    folder = tmp_path / "bin"
    folder.mkdir()
    old = folder / "cli-anything-fusion"
    old.touch()
    assert handoff.fusion_cli() == old
    current = folder / "fzd-fusion"
    current.touch()
    assert handoff.fusion_cli() == current
