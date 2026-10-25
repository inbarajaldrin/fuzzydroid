"""Native tool providers. Imported only inside KiCad (Python 3.9 compatible)."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path


def register(registry, pcbnew, wx):
    board_arg = {"board": {"type": "string", "description": "Absolute expected active board path"}}
    session = {}
    session_board = [None]

    def active(expected):
        board = pcbnew.GetBoard()
        if board is None or not board.GetFileName():
            raise ValueError("Open a saved PCB first")
        path = str(Path(board.GetFileName()).resolve())
        if str(Path(expected).expanduser().resolve()) != path:
            raise ValueError("Active board mismatch: " + path)
        return board

    @registry.tool("native.ping", "Identify the live embedded KiCad process and active board.")
    def ping():
        board = pcbnew.GetBoard()
        return {
            "pid": os.getpid(),
            "main_thread": wx.IsMainThread(),
            "version": pcbnew.GetBuildVersion(),
            "board": board.GetFileName() if board else None,
            "undo_transactions": False,
        }

    @registry.tool(
        "native.inspect", "Inspect the live board through legacy bindings.", board_arg, ["board"]
    )
    def inspect(board):
        target = active(board)
        return {
            "board": target.GetFileName(),
            "footprints": [
                {
                    "reference": f.GetReference(),
                    "value": f.GetValue(),
                    "x_mm": pcbnew.ToMM(f.GetPosition().x),
                    "y_mm": pcbnew.ToMM(f.GetPosition().y),
                    "models": [m.m_Filename for m in f.Models()],
                }
                for f in target.GetFootprints()
            ],
        }

    @registry.tool(
        "native.python",
        "Execute trusted Python inside KiCad's main thread. No automatic rollback.",
        dict(board_arg, code={"type": "string"}),
        ["board", "code"],
        mutates=True,
    )
    def python(board, code):
        target = active(board)
        # Handles to a previous document must never survive a board change.
        identity = (target.GetFileName(), str(target.this))
        if session_board[0] != identity:
            session.clear()
            session_board[0] = identity
        session.update(pcbnew=pcbnew, wx=wx, board=target, registry=registry, result=None)
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                exec(compile(code, "<fzd-kicad-native>", "exec"), session)  # noqa: S102 - trusted operator interface
        except BaseException as error:
            raise RuntimeError(
                f"Native Python failed; edits may have applied. {error}\n{output.getvalue()}"
            ) from error
        return {
            "result": session["result"],
            "stdout": output.getvalue(),
            "main_thread": wx.IsMainThread(),
            "saved": False,
            "rollback": False,
        }

    @registry.tool(
        "native.session_reset", "Clear stored Python variables and stale native handles."
    )
    def reset():
        session.clear()
        return {"reset": True}

    def entries(window):
        matches = [
            w for w in wx.GetTopLevelWindows() if isinstance(w, wx.Frame) and w.GetTitle() == window
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one window titled {window!r}; found {len(matches)}")
        found = []

        def visit(menu, prefix):
            for item in menu.GetMenuItems():
                label = item.GetItemLabelText()
                if not label:
                    continue
                path = prefix + [label]
                if item.GetSubMenu():
                    visit(item.GetSubMenu(), path)
                else:
                    found.append((" > ".join(path), menu, item))

        bar = matches[0].GetMenuBar()
        if bar:
            for index in range(bar.GetMenuCount()):
                visit(bar.GetMenu(index), [bar.GetMenuLabelText(index)])
        return found

    @registry.tool("native.windows", "List native application windows and visibility.")
    def windows():
        return [
            {"title": w.GetTitle(), "shown": w.IsShown()}
            for w in wx.GetTopLevelWindows()
            if isinstance(w, wx.TopLevelWindow)
        ]

    @registry.tool(
        "native.menus",
        "Discover native leaf menu commands; numeric IDs are not stable.",
        {"window": {"type": "string"}},
        ["window"],
    )
    def menus(window):
        return [{"path": path, "enabled": item.IsEnabled()} for path, _, item in entries(window)]

    @registry.tool(
        "native.menu_invoke",
        "Invoke a discovered native menu path through its owning menu.",
        {"window": {"type": "string"}, "path": {"type": "string"}},
        ["window", "path"],
        mutates=True,
    )
    def menu_invoke(window, path):
        matches = [(menu, item) for name, menu, item in entries(window) if name == path]
        if len(matches) != 1:
            raise ValueError("Menu path is missing or ambiguous: " + path)
        menu, item = matches[0]
        if not item.IsEnabled():
            raise ValueError("Menu command is disabled")
        event = wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId())
        event.SetEventObject(menu)
        return {
            "handled": menu.ProcessEvent(event),
            "path": path,
            "note": "Read back windows or application state to verify the result.",
        }

    @registry.tool(
        "native.footprint_add",
        "Load a footprint library file and add it to the live PCB. No automatic undo.",
        dict(
            board_arg,
            library={"type": "string"},
            name={"type": "string"},
            reference={"type": "string"},
            x_mm={"type": "number"},
            y_mm={"type": "number"},
        ),
        ["board", "library", "name", "reference", "x_mm", "y_mm"],
        mutates=True,
    )
    def add(board, library, name, reference, x_mm, y_mm):
        target = active(board)
        if any(f.GetReference() == reference for f in target.GetFootprints()):
            raise ValueError("Reference already exists: " + reference)
        footprint = pcbnew.FootprintLoad(str(Path(library).expanduser().resolve()), name)
        if footprint is None:
            raise ValueError("Footprint could not be loaded")
        footprint.SetReference(reference)
        footprint.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
        target.Add(footprint)
        pcbnew.Refresh()
        return {
            "reference": reference,
            "models": [m.m_Filename for m in footprint.Models()],
            "saved": False,
            "note": "Pads are unassigned; connect nets before fabrication.",
        }

    @registry.tool(
        "native.footprint_remove",
        "Remove exactly one footprint by reference. No automatic undo.",
        dict(board_arg, reference={"type": "string"}),
        ["board", "reference"],
        mutates=True,
    )
    def remove(board, reference):
        target = active(board)
        matches = [f for f in target.GetFootprints() if f.GetReference() == reference]
        if len(matches) != 1:
            raise ValueError("Reference is missing or ambiguous: " + reference)
        target.Remove(matches[0])
        pcbnew.Refresh()
        return {"removed": reference, "saved": False}

    @registry.tool("native.panel_show", "Show the tool panel backed by this same registry.")
    def panel():
        from .panel import show

        show(registry, wx)
        return {"shown": True}
