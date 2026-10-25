"""fzd-kicad: a JSON CLI over the same providers used by MCP and the panel."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .client import BridgeError
from .service import Service


def emit(ctx, function):
    try:
        result = function()
        click.echo(json.dumps({"ok": True, "data": result}, indent=None if ctx.obj["json"] else 2))
    except Exception as error:
        response = (
            error.response
            if isinstance(error, BridgeError)
            else {"error": str(error), "type": type(error).__name__}
        )
        click.echo(json.dumps(dict(response, ok=False)))
        raise click.exceptions.Exit(1) from error


@click.group()
@click.option("--json", "as_json", is_flag=True, help="Compact machine-readable JSON output.")
@click.option(
    "--instance", type=int, help="Native KiCad process PID; required if discovery is ambiguous."
)
@click.pass_context
def main(ctx, as_json, instance):
    ctx.obj = {"json": as_json, "service": Service(instance)}


@main.command()
@click.option("--backend", type=click.Choice(["ipc", "native"]), default="ipc")
@click.pass_context
def ping(ctx, backend):
    emit(ctx, lambda: ctx.obj["service"].call(backend + ".ping"))


@main.command()
@click.pass_context
def tools(ctx):
    """Discover the live tool registry and input schemas."""
    emit(ctx, ctx.obj["service"].catalog)


@main.command("call")
@click.argument("tool")
@click.option("--params-file", default="-", help="JSON file; - reads stdin, empty stdin means {}.")
@click.pass_context
def call_tool(ctx, tool, params_file):
    def invoke():
        raw = (
            sys.stdin.read()
            if params_file == "-"
            else Path(params_file).read_text(encoding="utf-8")
        )
        return ctx.obj["service"].call(tool, json.loads(raw) if raw.strip() else {})

    emit(ctx, invoke)


@main.command("exec")
@click.argument("file", type=str)
@click.option("--board", required=True)
@click.option("--backend", type=click.Choice(["ipc", "native"]), default="ipc")
@click.option(
    "--mutate", is_flag=True, help="IPC only: create an undo group and roll back on error."
)
@click.option("--message", default="Agent edit")
@click.pass_context
def execute(ctx, file, board, backend, mutate, message):
    def invoke():
        code = sys.stdin.read() if file == "-" else Path(file).read_text(encoding="utf-8")
        params = {"code": code, "board": board}
        if backend == "ipc":
            params.update(mutate=mutate, message=message)
        elif mutate:
            raise ValueError(
                "Native Python has no automatic rollback; --mutate is an IPC-only option"
            )
        return ctx.obj["service"].call(backend + ".python", params)

    emit(ctx, invoke)


@main.command()
@click.pass_context
def doctor(ctx):
    """Verify installation artifacts, dependency drift, and both control paths."""
    from .doctor import diagnose

    emit(ctx, diagnose)


@main.command()
@click.option("--plugin-root", type=click.Path(path_type=Path), required=True)
@click.option("--kicad-cli", type=str)
@click.option("--plugin-dir", type=click.Path(path_type=Path))
@click.option("--native/--no-native", default=True)
@click.pass_context
def setup(ctx, plugin_root, kicad_cli, plugin_dir, native):
    """Idempotent setup. A changed loader takes effect on the next PCB Editor launch."""
    from .setup import install

    emit(ctx, lambda: install(plugin_root, kicad_cli, plugin_dir, native))


@main.command()
@click.pass_context
def mcp(ctx):
    """Run the stdio MCP gateway; stdout is reserved for the protocol."""
    from .mcp import run

    run(ctx.obj["service"])


if __name__ == "__main__":
    main()
