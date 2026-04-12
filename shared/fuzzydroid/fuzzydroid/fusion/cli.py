"""cli-anything-fusion — CLI harness for Autodesk Fusion 360.

Entry point for the CLI. Provides commands for project management, design
inspection, export, API calls, Python execution, and an interactive REPL.

Architecture:
    CLI (this file) → core.bridge → TCP :8765 → fusion_bridge add-in → Fusion API
"""

import json
import os
import shlex
import sys
from typing import Optional

import click

from fuzzydroid.fusion import __version__
from fuzzydroid.fusion.core import bridge

# ── Helpers ──────────────────────────────────────────────────────────────────


def _output(ctx: click.Context, result: dict) -> None:
    """Print result as JSON or human-readable text based on context."""
    if ctx.obj.get("json_mode"):
        click.echo(json.dumps(result, indent=2))
        return

    status = result.get("status", "unknown")

    if status == "error":
        click.secho(f"  Error: {result.get('message', 'Unknown error')}", fg="red", err=True)
        return

    # Auto-format based on known response shapes
    _format_human(result)


def _format_human(result: dict) -> None:
    """Format a bridge response for human-readable terminal output."""
    # Remove status field for cleaner display
    data = {k: v for k, v in result.items() if k != "status"}

    if not data:
        click.secho("  OK", fg="green")
        return

    # List-type responses
    for list_key in ("projects", "bodies", "components", "matches", "items"):
        if list_key in data:
            items = data[list_key]
            if not items:
                click.echo(f"  No {list_key} found.")
                return
            click.echo()
            for i, item in enumerate(items, 1):
                if isinstance(item, dict):
                    # Timeline items, cached search results, etc.
                    label = item.get("name") or item.get("path") or json.dumps(item)
                    extra_parts = []
                    for k, v in item.items():
                        if k not in ("name", "path"):
                            extra_parts.append(f"{k}={v}")
                    extra = f"  ({', '.join(extra_parts)})" if extra_parts else ""
                    click.echo(f"  {i:3d}. {label}{extra}")
                else:
                    click.echo(f"  {i:3d}. {item}")
            # Print count if available
            count = data.get("count")
            if count is not None:
                click.echo(f"\n  Total: {count}")
            click.echo()
            return

    # Bounding box
    if "min" in data and "max" in data:
        mn = data["min"]
        mx = data["max"]
        click.echo()
        click.echo(f"  Min: X={mn['x']:.3f}  Y={mn['y']:.3f}  Z={mn['z']:.3f}  cm")
        click.echo(f"  Max: X={mx['x']:.3f}  Y={mx['y']:.3f}  Z={mx['z']:.3f}  cm")
        dx = mx["x"] - mn["x"]
        dy = mx["y"] - mn["y"]
        dz = mx["z"] - mn["z"]
        click.echo(f"  Size: {dx:.3f} x {dy:.3f} x {dz:.3f} cm")
        click.echo()
        return

    # Key-value pairs (document info, ping, export result, etc.)
    click.echo()
    max_key_len = max(len(str(k)) for k in data) if data else 0
    for key, value in data.items():
        click.echo(f"  {key:<{max_key_len}}  {value}")
    click.echo()


def _check_result(result: dict) -> bool:
    """Return True if result indicates success, False on error."""
    return result.get("status") != "error"


# ── Main CLI group ───────────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, default=False,
              help="Output machine-readable JSON.")
@click.option("--host", default=None, help="Bridge host (default: 127.0.0.1).")
@click.option("--port", default=None, type=int, help="Bridge port (default: 8765).")
@click.version_option(version=__version__, prog_name="cli-anything-fusion")
@click.pass_context
def cli(ctx: click.Context, json_mode: bool, host: Optional[str], port: Optional[int]) -> None:
    """cli-anything-fusion — Control Fusion 360 from the command line.

    Run without a subcommand to enter interactive REPL mode.
    """
    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    ctx.obj["host"] = host or os.environ.get("FUSION_BRIDGE_HOST", "127.0.0.1")
    ctx.obj["port"] = port or int(os.environ.get("FUSION_BRIDGE_PORT", "8765"))

    # Set environment variables so bridge module picks them up
    if host:
        os.environ["FUSION_BRIDGE_HOST"] = host
    if port:
        os.environ["FUSION_BRIDGE_PORT"] = str(port)

    # If no subcommand given, enter REPL
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ── ping ─────────────────────────────────────────────────────────────────────


@cli.command()
@click.pass_context
def ping(ctx: click.Context) -> None:
    """Check bridge connectivity."""
    result = bridge.ping()
    _output(ctx, result)


# ── project group ────────────────────────────────────────────────────────────


@cli.group()
@click.pass_context
def project(ctx: click.Context) -> None:
    """Manage Fusion 360 projects and files."""
    pass


@project.command("list")
@click.pass_context
def project_list(ctx: click.Context) -> None:
    """List all projects in the data hub."""
    result = bridge.list_projects()
    _output(ctx, result)


@project.command("open")
@click.option("--project", "proj", required=True, help="Project name.")
@click.option("--file", "fname", required=True, help="File name to open.")
@click.option("--folder", "folders", multiple=True, help="Subfolder(s) to navigate (repeat for nested).")
@click.pass_context
def project_open(ctx: click.Context, proj: str, fname: str, folders: tuple[str, ...]) -> None:
    """Open a file from the Fusion data hub."""
    folder_list = list(folders) if folders else None
    result = bridge.open_file(project=proj, file=fname, folders=folder_list)
    _output(ctx, result)


@project.command("search")
@click.option("--term", required=True, help="Search term (case-insensitive).")
@click.pass_context
def project_search(ctx: click.Context, term: str) -> None:
    """Search files across all projects (cloud, slow 30-60s)."""
    if not ctx.obj.get("json_mode"):
        click.echo("  Searching cloud (this may take 30-60s)...")
    result = bridge.search_files(term=term)
    _output(ctx, result)


@project.command("cache")
@click.pass_context
def project_cache(ctx: click.Context) -> None:
    """Build local file index (takes 1-3 minutes)."""
    if not ctx.obj.get("json_mode"):
        click.echo("  Building file cache (this may take 1-3 minutes)...")
    result = bridge.cache_files()
    _output(ctx, result)


@project.command("find")
@click.option("--term", required=True, help="Search term (case-insensitive).")
@click.pass_context
def project_find(ctx: click.Context, term: str) -> None:
    """Search cached file index (instant)."""
    result = bridge.search_cached(term=term)
    _output(ctx, result)


# ── design group ─────────────────────────────────────────────────────────────


@cli.group()
@click.pass_context
def design(ctx: click.Context) -> None:
    """Inspect the active Fusion 360 design."""
    pass


@design.command("info")
@click.pass_context
def design_info(ctx: click.Context) -> None:
    """Active document info (name, bodies, components)."""
    result = bridge.get_document()
    _output(ctx, result)


@design.command("bodies")
@click.pass_context
def design_bodies(ctx: click.Context) -> None:
    """List all bodies in the root component."""
    result = bridge.list_bodies()
    _output(ctx, result)


@design.command("components")
@click.pass_context
def design_components(ctx: click.Context) -> None:
    """List all component occurrences."""
    result = bridge.list_components()
    _output(ctx, result)


@design.command("bbox")
@click.pass_context
def design_bbox(ctx: click.Context) -> None:
    """Bounding box (min/max XYZ in cm)."""
    result = bridge.get_bounding_box()
    _output(ctx, result)


@design.command("timeline")
@click.pass_context
def design_timeline(ctx: click.Context) -> None:
    """Design timeline (feature history)."""
    result = bridge.get_timeline()
    _output(ctx, result)


# ── export group ─────────────────────────────────────────────────────────────


@cli.group()
@click.pass_context
def export(ctx: click.Context) -> None:
    """Export the active design."""
    pass


@export.command("step")
@click.option("--path", default=None, help="Output file path (auto-generated if omitted).")
@click.pass_context
def export_step(ctx: click.Context, path: Optional[str]) -> None:
    """Export as STEP (CAD interchange)."""
    result = bridge.export(fmt="step", path=path)
    _output(ctx, result)


@export.command("stl")
@click.option("--path", default=None, help="Output file path (auto-generated if omitted).")
@click.pass_context
def export_stl(ctx: click.Context, path: Optional[str]) -> None:
    """Export as STL (mesh/3D printing)."""
    result = bridge.export(fmt="stl", path=path)
    _output(ctx, result)


@export.command("f3d")
@click.option("--path", default=None, help="Output file path (auto-generated if omitted).")
@click.pass_context
def export_f3d(ctx: click.Context, path: Optional[str]) -> None:
    """Export as F3D (Fusion archive)."""
    result = bridge.export(fmt="f3d", path=path)
    _output(ctx, result)


# ── api group ────────────────────────────────────────────────────────────────


@cli.group()
@click.pass_context
def api(ctx: click.Context) -> None:
    """Generic Fusion 360 API access."""
    pass


@api.command("call")
@click.option("--path", "api_path", required=True, help="Dotted API path.")
@click.option("--args", "args_json", default=None, help="JSON array of positional arguments.")
@click.option("--store-as", default=None, help="Store result for later $name references.")
@click.option("--props", multiple=True, help="Properties to extract from result.")
@click.pass_context
def api_call(ctx: click.Context, api_path: str, args_json: Optional[str],
             store_as: Optional[str], props: tuple[str, ...]) -> None:
    """Call any Fusion API method or property via dotted path."""
    args = json.loads(args_json) if args_json else None
    prop_list = list(props) if props else None
    result = bridge.api_call(
        api_path=api_path,
        args=args,
        store_as=store_as,
        return_properties=prop_list,
    )
    _output(ctx, result)


@api.command("docs")
@click.option("--search", "search_term", required=True, help="Term to search for.")
@click.option("--category", default="class_name",
              type=click.Choice(["class_name", "member_name", "description", "all"]),
              help="Where to search.")
@click.option("--max", "max_results", default=5, type=int, help="Max results.")
@click.pass_context
def api_docs(ctx: click.Context, search_term: str, category: str, max_results: int) -> None:
    """Search Fusion API docs via runtime introspection."""
    result = bridge.api_docs(search_term=search_term, category=category, max_results=max_results)
    _output(ctx, result)


@api.command("online")
@click.option("--class", "class_name", required=True, help="API class name.")
@click.option("--member", "member_name", default=None, help="Method or property name.")
@click.pass_context
def api_online(ctx: click.Context, class_name: str, member_name: Optional[str]) -> None:
    """Fetch Autodesk online API documentation."""
    result = bridge.online_docs(class_name=class_name, member_name=member_name)
    _output(ctx, result)


@api.command("clear")
@click.pass_context
def api_clear(ctx: click.Context) -> None:
    """Clear stored API object context."""
    result = bridge.clear_context()
    _output(ctx, result)


# ── exec ─────────────────────────────────────────────────────────────────────


@cli.command("exec")
@click.argument("code", default=None, required=False)
@click.option("--session-id", default=None, help="Session ID for persistent execution.")
@click.option("--persistent", is_flag=True, default=False,
              help="Persist variables for future calls with the same session-id.")
@click.pass_context
def exec_cmd(ctx: click.Context, code: Optional[str], session_id: Optional[str],
             persistent: bool) -> None:
    """Execute Python code in Fusion 360's runtime.

    Pass code as an argument, or use '-' to read from stdin:

        echo "print('hi')" | cli-anything-fusion exec -
    """
    if code == "-" or code is None:
        # Read from stdin
        if not sys.stdin.isatty():
            code = sys.stdin.read().strip()
        elif code is None:
            click.secho("  Error: Provide code as argument or pipe via stdin with '-'", fg="red", err=True)
            ctx.exit(1)
            return

    if not code:
        click.secho("  Error: No code provided.", fg="red", err=True)
        ctx.exit(1)
        return

    result = bridge.exec_python(code=code, session_id=session_id, persistent=persistent)
    _output(ctx, result)


# ── REPL ─────────────────────────────────────────────────────────────────────

# Command help table for REPL
_REPL_COMMANDS = {
    "help":                "Show this help message",
    "ping":                "Check bridge connectivity",
    "project list":        "List all projects",
    "project open":        "Open a file (--project NAME --file NAME [--folder ...])",
    "project search":      "Search files in cloud (--term TERM)",
    "project cache":       "Build local file index",
    "project find":        "Search cached index (--term TERM)",
    "design info":         "Active document info",
    "design bodies":       "List bodies",
    "design components":   "List component occurrences",
    "design bbox":         "Bounding box (min/max XYZ)",
    "design timeline":     "Design timeline (feature history)",
    "export step":         "Export as STEP [--path PATH]",
    "export stl":          "Export as STL [--path PATH]",
    "export f3d":          "Export as F3D [--path PATH]",
    "api call":            "Generic API call (--path PATH [--args JSON] [--store-as NAME])",
    "api docs":            "Search API docs (--search TERM [--category CAT])",
    "api online":          "Fetch online docs (--class CLASS [--member MEMBER])",
    "api clear":           "Clear stored API context",
    "exec CODE":           "Execute Python in Fusion runtime",
    "quit / exit":         "Exit the REPL",
}


@cli.command("repl")
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Start the interactive REPL."""
    from fuzzydroid.fusion.utils.repl_skin import ReplSkin

    skin = ReplSkin("fusion", version=__version__)
    skin.print_banner()

    # Try to create a prompt_toolkit session for history/completion
    pt_session = skin.create_prompt_session()

    json_mode = ctx.obj.get("json_mode", False)

    while True:
        try:
            line = skin.get_input(pt_session, context="")
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        if not line:
            continue

        # Quit commands
        if line.lower() in ("quit", "exit", "q"):
            skin.print_goodbye()
            break

        # Help
        if line.lower() in ("help", "?"):
            skin.help(_REPL_COMMANDS)
            continue

        # Dispatch to Click commands by parsing the line as CLI args
        try:
            args = shlex.split(line)
        except ValueError as e:
            skin.error(f"Parse error: {e}")
            continue

        if not args:
            continue

        # Special handling for 'exec' — everything after 'exec' is the code
        if args[0] == "exec":
            code_str = line[len("exec"):].strip()
            if not code_str:
                skin.error("Usage: exec <python code>")
                continue
            args = ["exec", code_str]

        # Inject --json flag if in json mode
        if json_mode and "--json" not in args:
            args = ["--json"] + args

        try:
            # Use cli.main() with standalone_mode=False to catch SystemExit
            cli.main(args=args, standalone_mode=False, obj=ctx.obj)
        except click.exceptions.UsageError as e:
            skin.error(str(e))
        except click.exceptions.Abort:
            pass
        except SystemExit:
            pass
        except Exception as e:
            skin.error(f"Unexpected error: {e}")


# ── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Main entry point for the CLI."""
    # Envvar prefix stays FUSION360 for backward compatibility with existing env vars.
    cli(auto_envvar_prefix="FUSION360")
