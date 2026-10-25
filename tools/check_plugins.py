#!/usr/bin/env python3
"""Validate the commit's plugin assets and optionally ask Codex to load them.

Use --codex for a read-only smoke check with the installed Codex app server.
Neither mode installs plugins or changes the user's Codex configuration.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import selectors
import subprocess
import tempfile
import time
from pathlib import Path

from sync_plugins import ROOT, generated_files


def check_plugin_layout(name: str, directory: Path) -> list[str]:
    """Keep host discovery to one entry point and verify its local links."""
    errors = []
    main = directory / "skills" / name / "SKILL.md"
    actual = set(directory.rglob("SKILL.md"))
    if actual != {main}:
        errors.append(
            f"{name}: expected only skills/{name}/SKILL.md; found "
            + ", ".join(str(p.relative_to(directory)) for p in sorted(actual))
        )
    if any((directory / "commands").rglob("*.md")):
        errors.append(
            f"{name}: commands/ exposes extra Claude entry points; use internal workflows"
        )
    if main.is_file():
        text = main.read_text()
        if not re.search(rf"^name: {re.escape(name)}$", text, re.MULTILINE):
            errors.append(f"{name}: main skill name must match the plugin")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            path = (main.parent / target.split("#", 1)[0]).resolve()
            if not path.is_relative_to(directory.resolve()) or not path.is_file():
                errors.append(
                    f"{name}: missing or external internal reference: {target}"
                )
    return errors


def check_files() -> list[str]:
    errors = []
    catalog = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    for entry in catalog["plugins"]:
        errors.extend(check_plugin_layout(entry["name"], ROOT / entry["source"]))
    for path, expected in generated_files().items():
        if not path.is_file() or path.read_text() != expected:
            errors.append(f"{path.relative_to(ROOT)}: run tools/sync_plugins.py")
    # Include untracked additions and staged deletions in the release candidate.
    names = (
        subprocess.check_output(
            ["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    for name in sorted(set(names) - {""}):
        path = ROOT / name
        if not path.is_file():
            continue
        if "/tutorials/" in name and name.startswith("plugins/"):
            errors.append(
                f"{name}: personal tutorials belong outside installable plugins"
            )
        if path.stat().st_size >= 100 * 1024 * 1024:
            errors.append(f"{name}: exceeds GitHub's 100 MiB file limit")
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(), filename=name)
            except (SyntaxError, UnicodeError) as exc:
                errors.append(f"{name}: {exc}")
        if path.name == "SKILL.md":
            if len(path.relative_to(ROOT / "plugins").parts) != 4:
                errors.append(f"{name}: nested tutorial would be discovered as a skill")
            text = path.read_text()
            front = text.split("---", 2)[1] if text.startswith("---\n") else ""
            fields = dict(
                re.findall(r"^(name|description): (.+)$", front, re.MULTILINE)
            )
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields.get("name", "")):
                errors.append(f"{name}: invalid skill name")
            if not 1 <= len(fields.get("description", "")) <= 1024:
                errors.append(f"{name}: description must contain 1–1024 characters")
    return errors


def check_codex() -> None:
    """Exercise the real host parser with explicit repo discovery context."""
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(
            ["codex", "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
            bufsize=1,
        )
        assert process.stdin is not None and process.stdout is not None

        def request(request_id: int, method: str, params: dict) -> dict:
            process.stdin.write(
                json.dumps({"id": request_id, "method": method, "params": params})
                + "\n"
            )
            process.stdin.flush()
            deadline = time.monotonic() + 30
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while time.monotonic() < deadline:
                    if not selector.select(timeout=1):
                        continue
                    line = process.stdout.readline()
                    if not line:
                        raise RuntimeError("Codex app server exited unexpectedly")
                    response = json.loads(line)
                    if response.get("id") == request_id:
                        if "error" in response:
                            raise RuntimeError(f"{method}: {response['error']}")
                        return response["result"]
            raise TimeoutError(f"Codex did not answer {method} within 30 seconds")

        try:
            request(
                1,
                "initialize",
                {
                    "clientInfo": {"name": "fuzzydroid-check", "version": "0.1.0"},
                    "capabilities": {"experimentalApi": True},
                },
            )
            process.stdin.write('{"method":"initialized","params":{}}\n')
            process.stdin.flush()
            result = request(2, "plugin/list", {"cwds": [str(ROOT)]})
            marketplace = next(
                (
                    m
                    for m in result["marketplaces"]
                    if m["name"] == "fuzzydroid"
                    and Path(m["path"]) == ROOT / ".agents/plugins/marketplace.json"
                ),
                None,
            )
            if marketplace is None:
                raise RuntimeError("Codex did not discover the repo marketplace")
            catalog = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
            for index, entry in enumerate(catalog["plugins"], 10):
                name = entry["name"]
                plugin = request(
                    index,
                    "plugin/read",
                    {"marketplacePath": marketplace["path"], "pluginName": name},
                )["plugin"]
                directory = ROOT / entry["source"]
                expected = {f"{name}:{name}"}
                actual = {s["name"] for s in plugin["skills"]}
                if actual != expected:
                    raise RuntimeError(
                        f"{name}: discovered skills {actual}, expected {expected}"
                    )
                mcp = directory / ".mcp.json"
                expected_servers = (
                    set(json.loads(mcp.read_text())["mcpServers"])
                    if mcp.exists()
                    else set()
                )
                if set(plugin["mcpServers"]) != expected_servers:
                    raise RuntimeError(
                        f"{name}: bundled MCP servers were not discovered"
                    )
                print(
                    f"Codex loaded {name}: {len(actual)} skills, {len(expected_servers)} MCP servers"
                )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", action="store_true")
    args = parser.parse_args()
    errors = check_files()
    if errors:
        print("\n".join(errors))
        return 1
    if args.codex:
        check_codex()
    print("Plugin packaging checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
