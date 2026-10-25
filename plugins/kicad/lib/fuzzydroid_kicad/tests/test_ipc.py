from pathlib import Path
from types import SimpleNamespace

from fuzzydroid_kicad import ipc


def test_snapshot_preserves_project_relative_model_paths_and_is_cleaned(tmp_path, monkeypatch):
    document = SimpleNamespace(
        project=SimpleNamespace(path=str(tmp_path)), board_filename="demo.kicad_pcb"
    )
    board = SimpleNamespace(document=document, get_as_string=lambda: '(kicad_pcb (text "λ"))')
    monkeypatch.setattr(ipc, "connect", lambda _: None)
    monkeypatch.setattr(ipc, "checked_board", lambda *_: board)
    monkeypatch.setattr(ipc, "cli_path", lambda: Path("kicad-cli"))
    snapshots = []
    output = tmp_path / "renders/board.png"

    def export(arguments, **kwargs):
        snapshot = Path(arguments[-1])
        assert snapshot.parent == tmp_path
        assert "λ" in snapshot.read_text(encoding="utf-8")
        snapshots.append(snapshot)
        output.write_bytes(b"\x89PNG")
        return SimpleNamespace(returncode=0, stdout="rendered", stderr="")

    monkeypatch.setattr(ipc.subprocess, "run", export)
    result = ipc.snapshot_job("render", str(output), str(tmp_path / "demo.kicad_pcb"))
    assert result["returncode"] == 0
    assert all(not snapshot.exists() for snapshot in snapshots)
