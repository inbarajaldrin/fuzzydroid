# Architecture and extension contract

```text
                         official kicad-python -> KiCad IPC server
agent -> MCP / CLI ----<
                         reference TCP client -> embedded KiCad bridge
                                                   |
                                           wx.CallAfter (main thread)
                                                   |
                                           native tool registry
                                              /         \
                                        agent calls    native panel
```

The service composes the official IPC provider's catalog and the running native
registry. The native registry is the source of truth for native CLI calls, MCP
schemas and panel choices. The panel is a developer console: select a tool, enter
JSON parameters, and inspect JSON results. It doesn't duplicate tool behavior.
The panel lists native tools; IPC calls remain in the external service to avoid
synchronously calling the app's own IPC server from its main thread.

The embedded bridge advertises per-process endpoint metadata in a private
per-user runtime directory. It binds an ephemeral loopback TCP port with a
per-process authentication token, so the same transport works on macOS, Linux
and Windows. Tokens never appear in tool discovery output. The client checks
the endpoint against its PID. Ambiguity is an error; writes aren't retried.

Transport threads handle framing only. Each callback is marshalled through
`wx.CallAfter`. Requests cancelled before their main-thread callback starts are
skipped. Once code has started, a deadline cannot establish whether a write
completed; the response marks the outcome uncertain. Native handlers return
JSON payloads or raise; the bridge owns the response envelope.

## Project tools

A project can be a plain importable Python module with `register(registry)`.
Set `FZD_KICAD_TOOL_MODULES` to its comma-separated module names before launching
PCB Editor (and make them importable). Registration is explicit; duplicate names
fail. No source is copied from omni-kit-mcp.

```python
def register(registry):
    @registry.tool("demo.answer", "Return the demo answer.")
    def answer():
        return {"answer": 42}
```

Names must have a namespace and use lowercase letters/digits/underscores; double
underscores are reserved for reversible MCP encoding. Input properties and
required arguments are explicit JSON schemas. The registry validates supported
primitive types and rejects unknown arguments. Handler output must be JSON-safe.

During trusted native Python execution, `registry` also allows prototyping a new
tool interactively. Its appearance in the next `tools`/MCP list and refreshed
panel comes from that one registration. Refresh the agent's MCP tool catalog;
no automatic client refresh is claimed. Arbitrary project-module hot reload is
not implemented. Restart PCB Editor to reload packaged bridge code.

Python session globals are reset when the active native board identity changes.
Registered project modules should own their state rather than keeping stale
board handles. Native exec has no automatic rollback. Ordinary IPC edit scripts
retain the supported begin/push/drop transaction behavior.
