"""MCP schemas come from the provider catalogs, including project registrations."""

from __future__ import annotations

import asyncio
import json

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations

from .client import BridgeError


def server_for(service):
    server = Server("fuzzydroid-kicad")

    @server.list_tools()
    async def list_tools():
        catalog = await asyncio.to_thread(service.catalog)
        return [
            Tool(
                name=item["name"].replace(".", "__"),
                description=item["description"],
                inputSchema=item["inputSchema"],
                annotations=ToolAnnotations(readOnlyHint=not item["mutates"]),
            )
            for item in catalog
        ]

    @server.call_tool()
    async def call_tool(name, arguments):
        try:
            result = await asyncio.to_thread(service.call, name.replace("__", "."), arguments or {})
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as error:  # noqa: BLE001 - tool/diagnostic boundary
            payload = (
                error.response
                if isinstance(error, BridgeError)
                else {"error": str(error), "type": type(error).__name__}
            )
            return CallToolResult(
                isError=True, content=[TextContent(type="text", text=json.dumps(payload))]
            )

    return server


def run(service):
    server = server_for(service)

    async def serve():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(serve())
