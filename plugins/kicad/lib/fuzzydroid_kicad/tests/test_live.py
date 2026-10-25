"""Opt-in qualification on a saved LED demo PCB; restores all probe mutations."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from fuzzydroid_kicad import ipc
from fuzzydroid_kicad.service import Service

BOARD = os.getenv("FZD_KICAD_LIVE_BOARD")
LIBRARY = os.getenv("FZD_KICAD_TEST_LIBRARY")
pytestmark = pytest.mark.skipif(not BOARD, reason="Set FZD_KICAD_LIVE_BOARD to opt into live edits")


def test_live_native_ipc_mcp_and_panel_agree(tmp_path):
    board = ipc.checked_board(ipc.connect(), BOARD)
    before = board.get_as_string()
    service = Service()
    status = service.call("native.ping")
    assert status["main_thread"] is True
    assert Path(status["board"]).resolve() == Path(BOARD).resolve()
    footprints = service.call("ipc.inspect")["footprints"]
    resistor = next(fp for fp in footprints if fp["reference"] == "R1")
    x, y = resistor["x_mm"], resistor["y_mm"]
    try:
        moved = service.call(
            "ipc.move", {"board": BOARD, "reference": "R1", "x_mm": x, "y_mm": y - 1}
        )
        assert moved["y_mm"] == y - 1
    finally:
        service.call("ipc.move", {"board": BOARD, "reference": "R1", "x_mm": x, "y_mm": y})
    with pytest.raises(RuntimeError):
        service.call(
            "ipc.python",
            {
                "board": BOARD,
                "mutate": True,
                "code": """
fp = next(f for f in board.get_footprints() if f.reference_field.text.value == 'R1')
fp.value_field.text.value = 'ROLLBACK_PROBE'
board.update_items(fp)
raise RuntimeError('intentional failure')
""",
            },
        )
    assert board.get_as_string() == before

    with pytest.raises(ValueError):
        service.call("ipc.save", {"board": str(tmp_path / "wrong.kicad_pcb")})

    if LIBRARY:
        try:
            loaded = service.call(
                "native.footprint_add",
                {
                    "board": BOARD,
                    "library": LIBRARY,
                    "name": "LED_D5.0mm",
                    "reference": "D_QUALIFY",
                    "x_mm": 130,
                    "y_mm": 118,
                },
            )
            assert loaded["models"]
            assert "D_QUALIFY" in {
                f["reference"] for f in service.call("ipc.inspect")["footprints"]
            }
        finally:
            service.call("native.footprint_remove", {"board": BOARD, "reference": "D_QUALIFY"})
    assert board.get_as_string() == before

    editor_title = next(
        w["title"] for w in service.call("native.windows") if "PCB Editor" in w["title"]
    )
    menu_path = next(
        item["path"]
        for item in service.call("native.menus", {"window": editor_title})
        if item["path"] == "View > 3D Viewer"
    )
    invoked = service.call("native.menu_invoke", {"window": editor_title, "path": menu_path})
    assert invoked["handled"] is True
    assert any(w["title"] == "3D Viewer" for w in service.call("native.windows"))

    try:
        service.call(
            "native.python",
            {
                "board": BOARD,
                "code": """
registry.tool('qualification.answer', 'Integration probe')(lambda: {'answer': 42})
result = {'registered': True}
""",
            },
        )
        assert "qualification.answer" in {entry["name"] for entry in service.catalog()}
        service.call("native.panel_show")
        panel_result = service.call(
            "native.python",
            {
                "board": BOARD,
                "code": """
import json
window = next(w for w in wx.GetTopLevelWindows() if isinstance(w, wx.Frame) and w.GetTitle() == 'fuzzydroid KiCad tools')
children = window.GetChildren()[0].GetChildren()
refresh = next(w for w in children if isinstance(w, wx.Button) and w.GetLabel() == 'Refresh tools')
refresh.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, refresh.GetId()))
choice = next(w for w in children if isinstance(w, wx.Choice))
assert 'qualification.answer' in choice.GetItems()
choice.SetStringSelection('qualification.answer')
for widget in children:
    if isinstance(widget, wx.TextCtrl) and not widget.GetWindowStyleFlag() & wx.TE_READONLY:
        widget.SetValue('{}')
run = next(w for w in children if isinstance(w, wx.Button) and w.GetLabel() == 'Run selected tool')
run.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, run.GetId()))
output = next(w for w in children if isinstance(w, wx.TextCtrl) and w.GetWindowStyleFlag() & wx.TE_READONLY)
result = json.loads(output.GetValue())
""",
            },
        )
        assert panel_result["result"] == {"answer": 42}
        installed_cli = Path(sys.executable).with_name(
            "fzd-kicad.exe" if os.name == "nt" else "fzd-kicad"
        )
        cli_result = subprocess.run(
            [str(installed_cli), "--json", "call", "qualification.answer"],
            input="",
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(cli_result.stdout)["data"] == {"answer": 42}
        asyncio.run(check_mcp())
    finally:
        service.call(
            "native.python", {"board": BOARD, "code": "registry.unregister('qualification.answer')"}
        )
    assert board.get_as_string() == before
    rendered = service.call(
        "ipc.export", {"board": BOARD, "kind": "render", "output": str(tmp_path / "board.png")}
    )
    assert Path(rendered["output"]).read_bytes().startswith(b"\x89PNG")


async def check_mcp():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "fuzzydroid_kicad.cli", "mcp"]
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        catalog = await session.list_tools()
        assert "qualification__answer" in {tool.name for tool in catalog.tools}
        response = await session.call_tool("qualification__answer", {})
        assert not response.isError
        assert json.loads(response.content[0].text) == {"answer": 42}
        response = await session.call_tool("ipc__save", {"board": "/wrong.kicad_pcb"})
        assert response.isError
