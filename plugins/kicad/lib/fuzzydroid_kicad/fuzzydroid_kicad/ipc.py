"""Official IPC operations: isolated from the embedded legacy backend."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
from pathlib import Path

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message
from kipy import KiCad
from kipy.geometry import Angle, Vector2
from kipy.proto.common.types import DocumentType

from .paths import cli_path


def encode(value):
    if isinstance(value, Message):
        return MessageToDict(value, preserving_proto_field_name=True)
    if hasattr(value, "proto"):
        return encode(value.proto)
    return str(value)


def connect(socket: str | None = None):
    client = KiCad(socket_path=socket, timeout_ms=3000)
    client.ping()
    return client


def board_path(board) -> str:
    doc = board.document
    return str((Path(doc.project.path) / doc.board_filename).resolve())


def checked_board(client, expected_board: str | None = None):
    board = client.get_board()
    if expected_board and Path(expected_board).expanduser().resolve() != Path(board_path(board)):
        raise ValueError(f"Active board is {board_path(board)}, expected {expected_board}")
    return board


def ping(socket: str | None = None):
    client = connect(socket)
    return {
        "status": "ok",
        "transport": "native-ipc",
        "version": str(client.get_version()),
        "documents": list(client.get_open_documents(DocumentType.DOCTYPE_PCB)),
    }


def inspect_board(socket: str | None = None):
    client = connect(socket)
    board = checked_board(client)
    footprints = []
    for fp in board.get_footprints():
        footprints.append(
            {
                "id": fp.id,
                "reference": fp.reference_field.text.value,
                "value": fp.value_field.text.value,
                "x_mm": fp.position.x / 1e6,
                "y_mm": fp.position.y / 1e6,
                "angle_deg": fp.orientation.degrees,
                "definition": fp.definition.id,
            }
        )
    return {
        "board": board_path(board),
        "footprints": footprints,
        "tracks": len(board.get_tracks()),
        "vias": len(board.get_vias()),
        "nets": list(board.get_nets()),
        "selection": list(board.get_selection()),
    }


def execute_python(
    code: str,
    expected_board: str,
    mutate: bool = False,
    message: str = "KiCad agent edit",
    socket: str | None = None,
):
    """Run trusted local Python against the live IPC objects. Writes are undo grouped.

    This is an execution interface, not a Python sandbox. mutate=False is a caller
    declaration for reads; it does not prevent arbitrary Python from writing.
    """
    client = connect(socket)
    board = checked_board(client, expected_board)
    namespace = {
        "kicad": client,
        "board": board,
        "Vector2": Vector2,
        "Angle": Angle,
        "Path": Path,
        "result": None,
    }
    output = io.StringIO()
    commit = board.begin_commit() if mutate else None
    try:
        with contextlib.redirect_stdout(output):
            exec(compile(code, "<kicad-agent>", "exec"), namespace)  # noqa: S102 - trusted operator interface
        if commit is not None:
            board.push_commit(commit, message)
    except BaseException:
        if commit is not None:
            board.drop_commit(commit)
        raise
    return {
        "board": board_path(board),
        "stdout": output.getvalue(),
        "result": namespace["result"],
        "undo_grouped": mutate,
        "saved": False,
    }


def move_footprint(
    reference: str,
    x_mm: float,
    y_mm: float,
    expected_board: str,
    angle_deg: float | None = None,
    socket: str | None = None,
):
    client = connect(socket)
    board = checked_board(client, expected_board)
    matches = [fp for fp in board.get_footprints() if fp.reference_field.text.value == reference]
    if len(matches) != 1:
        raise ValueError(f"Expected one {reference} footprint; found {len(matches)}")
    fp = matches[0]
    if fp.locked:
        raise ValueError(f"{reference} is locked")
    commit = board.begin_commit()
    try:
        fp.position = Vector2.from_xy_mm(x_mm, y_mm)
        if angle_deg is not None:
            fp.orientation = Angle.from_degrees(angle_deg)
        updated = board.update_items(fp)
        if len(updated) != 1:
            raise RuntimeError("KiCad did not update the footprint")
        board.push_commit(commit, f"Move {reference}")
    except BaseException:
        board.drop_commit(commit)
        raise
    current = next(f for f in board.get_footprints() if f.reference_field.text.value == reference)
    return {
        "reference": reference,
        "x_mm": current.position.x / 1e6,
        "y_mm": current.position.y / 1e6,
        "angle_deg": current.orientation.degrees,
        "saved": False,
        "note": "Existing tracks are not rerouted by moving a footprint.",
    }


def save_board(expected_board: str, socket: str | None = None):
    board = checked_board(connect(socket), expected_board)
    board.save()
    return {"saved": True, "board": board_path(board)}


def snapshot_job(kind: str, output: str, expected_board: str, socket: str | None = None):
    """Use a fresh IPC snapshot for CLI exports without saving the user's board."""
    board = checked_board(connect(socket), expected_board)
    destination = Path(output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    import tempfile

    # Keep the temporary snapshot beside the real board to preserve KIPRJMOD.
    descriptor, filename = tempfile.mkstemp(
        prefix=".fzd-kicad-", suffix=".kicad_pcb", dir=Path(board_path(board)).parent
    )
    os.close(descriptor)
    snapshot = Path(filename)
    try:
        snapshot.write_text(board.get_as_string(), encoding="utf-8")
        if kind == "render":
            args = [
                "pcb",
                "render",
                "--width",
                "1600",
                "--height",
                "1100",
                "--background",
                "opaque",
                "--rotate",
                "35,0,25",
            ]
        elif kind == "step":
            if destination.exists():
                raise FileExistsError(destination)
            args = ["pcb", "export", "step"]
        elif kind == "drc":
            args = ["pcb", "drc", "--exit-code-violations"]
        else:
            raise ValueError(f"Unknown export: {kind}")
        args += [
            "-o",
            str(destination),
            str(snapshot),
        ]
        completed = subprocess.run(
            [str(cli_path()), *args], capture_output=True, text=True, timeout=120, check=False
        )
    finally:
        snapshot.unlink(missing_ok=True)
    if completed.returncode not in ([0, 5] if kind == "drc" else [0]):
        raise RuntimeError(completed.stderr + completed.stdout)
    if not destination.exists():
        raise RuntimeError("KiCad did not create the requested output")
    return {
        "output": str(destination),
        "source": "live-ipc-snapshot",
        "returncode": completed.returncode,
        "log": completed.stdout + completed.stderr,
        "note": "DRC of a snapshot does not include project-specific rule files."
        if kind == "drc"
        else "",
    }
