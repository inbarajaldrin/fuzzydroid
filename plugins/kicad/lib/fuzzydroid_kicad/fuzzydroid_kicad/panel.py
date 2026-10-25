"""Registry-driven developer panel; buttons and agent calls share dispatch."""

from __future__ import annotations

import json

_window = None


def show(registry, wx):
    global _window
    if _window is not None and _window:
        _window.Show()
        _window.Raise()
        return
    window = wx.Frame(None, title="fuzzydroid KiCad tools", size=(720, 540))
    _window = window
    panel = wx.Panel(window)
    layout = wx.BoxSizer(wx.VERTICAL)
    tools = wx.Choice(panel)
    params = wx.TextCtrl(panel, value="{}", style=wx.TE_MULTILINE, size=(-1, 140))
    output = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
    description = wx.StaticText(panel, label="Select a tool; enter its parameters as JSON.")
    refresh = wx.Button(panel, label="Refresh tools")
    run = wx.Button(panel, label="Run selected tool")

    def reload_catalog(_event=None):
        tools.Set([tool["name"] for tool in registry.catalog()])
        if tools.GetCount():
            tools.SetSelection(0)

    def selected(_event):
        entry = next(t for t in registry.catalog() if t["name"] == tools.GetStringSelection())
        description.SetLabel(entry["description"])
        required = entry["inputSchema"]["required"]
        values = {key: "" for key in required}
        params.SetValue(json.dumps(values, indent=2))

    def execute(_event):
        try:
            result = registry.dispatch(tools.GetStringSelection(), json.loads(params.GetValue()))
            output.SetValue(json.dumps(result, indent=2))
        except Exception as error:  # noqa: BLE001 - tool/diagnostic boundary
            output.SetValue(str(error))

    refresh.Bind(wx.EVT_BUTTON, reload_catalog)
    run.Bind(wx.EVT_BUTTON, execute)
    tools.Bind(wx.EVT_CHOICE, selected)
    for widget in [tools, description, refresh, params, run]:
        layout.Add(widget, 0, wx.EXPAND | wx.ALL, 8)
    layout.Add(output, 1, wx.EXPAND | wx.ALL, 8)
    panel.SetSizer(layout)
    reload_catalog()
    window.Show()
