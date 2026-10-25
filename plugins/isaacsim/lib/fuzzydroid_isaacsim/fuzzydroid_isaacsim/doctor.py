"""Health check for /isaacsim:doctor — rows DRIVEN BY the state file.

The rule: components the setup did not install read "N/A — not installed",
never FAIL. A box without isaac-ctl, without ROS, or without a viewer is a
normal box, not a broken one. Only artifacts the state file says setup
created/recorded can fail.

Liveness probes (bridge port, running sim) WARN rather than FAIL — a stopped
sim is a normal state. Exit code 1 only for hard breakage of recorded
artifacts.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

from fuzzydroid_isaacsim import PLUGIN_NAME
from fuzzydroid_isaacsim import _common as c
from fuzzydroid_isaacsim import ros_bridge

OK, FAIL, WARN, NA = "✅", "❌", "⚠️", "N/A"


def _oneline(text: str) -> str:
    """Collapse subprocess stderr to a single markdown-table-safe cell."""
    return " ".join((text or "").split()).replace("|", "/")[:200]


def _tcp_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """True if a TCP connection to host:port opens — a bind-host liveness check
    that says nothing about the bridge protocol, only that something listens."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def probe_via_client(okm: Path, port: int | None = None, host: str | None = None,
                     timeout: float = 2.0):
    """Probe the bridge through omni-kit-mcp's stdlib-only reference client CLI.

    Runs `python -m kit_mcp.client list_tools [--host H] [--port N]` with
    `PYTHONPATH=<omni_kit_mcp checkout>` so `import kit_mcp.client` resolves
    (it needs no `mcp` SDK). With neither host nor port, the client
    auto-discovers a lone running bridge from its runtime portfile (the
    zero-config common case); pass `port` to pin a specific process when
    several Kit apps run. The CLI's own exit-code contract IS the probe
    result — we never re-implement the wire protocol:
        0 → success, 1 → bridge answered an error, 2 → unreachable/ambiguous.
    Returns (rc, stdout, stderr). rc is forced to 2 on any launch failure.
    """
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(okm) + (os.pathsep + existing if existing else "")
    cmd = [sys.executable, "-m", "kit_mcp.client", "list_tools", "--timeout", str(timeout)]
    if host is not None:
        cmd += ["--host", host]
    if port is not None:
        cmd += ["--port", str(port)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout + 3, env=env)
        return out.returncode, out.stdout, out.stderr
    except subprocess.TimeoutExpired:
        return 2, "", f"reference client timed out after {timeout + 3}s"
    except Exception as e:
        return 2, "", f"{type(e).__name__}: {e}"


def probe_list_tools(port: int, host: str = "127.0.0.1", timeout: float = 2.0):
    """One NDJSON round-trip: {"type":"list_tools","params":{}} → status/result.

    Stdlib socket fallback used only when the omni-kit-mcp checkout is NOT
    recorded (a box set up before `omni_kit_mcp` was tracked), so the probe
    still works without the reference client. Returns the tool-name list on
    success, None otherwise. This is the omni.kit.mcp wire protocol (one JSON
    object per line).
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(json.dumps({"type": "list_tools", "params": {}}).encode() + b"\n")
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    return None
                buf += chunk
        reply = json.loads(buf.split(b"\n", 1)[0].decode())
        if reply.get("status") != "success":
            return None
        result = reply.get("result") or {}
        tools = result.get("tools", result)
        return list(tools) if isinstance(tools, (list, dict)) else []
    except Exception:
        return None


def main() -> int:
    rows: list[tuple[str, str, str]] = []
    rc = 0

    def add(component: str, status: str, detail: str) -> None:
        rows.append((component, status, detail))

    state = c.load_state(PLUGIN_NAME)
    state_path = c.state_file(PLUGIN_NAME)
    if state is None:
        print("| component | status | detail |")
        print("|---|---|---|")
        print(f"| state file | {FAIL} | {state_path} missing — run /isaacsim:setup |")
        return 1
    add("state file", OK, f"`{state_path}` parses (v{state.get('plugin_version', '?')})")

    # plugin venv + drift
    venv = Path(state.get("venv_path", ""))
    if c.venv_python(venv).exists():
        add("plugin venv", OK, f"`{venv}`")
    else:
        add("plugin venv", FAIL, f"python missing at `{c.venv_python(venv)}` — re-run /isaacsim:setup")
        rc = 1
    plugin_root = Path(__file__).resolve().parents[1]  # lib/fuzzydroid_isaacsim
    pyproject = plugin_root / "pyproject.toml"
    if pyproject.exists() and state.get("pyproject_hash"):
        if c.hash_file(pyproject) == state["pyproject_hash"]:
            add("pyproject drift", OK, "deps unchanged since setup")
        else:
            add("pyproject drift", FAIL, "deps changed since setup — re-run /isaacsim:setup")
            rc = 1

    variant = state.get("variant", "?")
    add("install variant", OK, f"`{variant}` (recorded)")

    # recorded install artifacts — FAIL if the state says they exist and they don't
    if variant == "viewer":
        viewer = Path(state.get("viewer_app", ""))
        if state.get("viewer_app"):
            binary = viewer / "Contents" / "MacOS"
            if viewer.exists() and binary.is_dir() and any(binary.iterdir()):
                add("viewer app", OK, f"`{viewer}`")
            else:
                add("viewer app", FAIL, f"missing or broken at `{viewer}` — re-run the isaac-viewer-macos README install")
                rc = 1
        else:
            add("viewer app", NA, "not recorded")
    else:
        root = Path(state.get("isaac_root", ""))
        if state.get("isaac_root"):
            if root.is_dir():
                add("isaac root", OK, f"`{root}` ({state.get('isaac_version', 'version unrecorded')})")
            else:
                add("isaac root", FAIL, f"recorded root gone: `{root}`")
                rc = 1
        else:
            add("isaac root", NA, "not recorded")
        if state.get("isaac_bin"):
            b = Path(state["isaac_bin"])
            add("isaac binary", OK if b.exists() else FAIL, f"`{b}`")
            rc = rc or (0 if b.exists() else 1)
        else:
            add("isaac binary", NA, "not recorded" + (" (binary installs launch via their own scripts)" if variant == "binary" else ""))
        if state.get("isaac_python"):
            p = Path(state["isaac_python"])
            add("isaac venv python", OK if p.exists() else FAIL, f"`{p}`")
            rc = rc or (0 if p.exists() else 1)
        else:
            add("isaac venv python", NA, "no venv (binary/source install)")

    # kit config + ROS bridge (only if setup recorded them)
    if state.get("kit_config"):
        kc = Path(state["kit_config"])
        if kc.is_file():
            add("kit user.config.json", OK, f"`{kc}`")
        else:
            add("kit user.config.json", FAIL, f"recorded config gone: `{kc}`")
            rc = 1
        if state.get("ros_enabled"):
            enabled = ros_bridge.bridge_enabled_id(kc) if kc.is_file() else None
            expected = state.get("ros_bridge_ext")
            if enabled and enabled == expected:
                add("ROS 2 bridge ext", OK, f"`{enabled}` persistently enabled")
            elif enabled:
                add("ROS 2 bridge ext", WARN, f"enabled as `{enabled}` but setup recorded `{expected}` — version drift; re-run setup's ROS step")
            else:
                add("ROS 2 bridge ext", FAIL, f"`{expected}` not in the persistent enabled list — re-run /isaacsim:setup with ROS")
                rc = 1
        else:
            add("ROS 2 bridge ext", NA, "ROS not configured by setup")
    else:
        add("kit user.config.json", NA, "not recorded (omni-kit-mcp registration not run on this box)")
        add("ROS 2 bridge ext", NA, "ROS not configured by setup")

    # omni-kit-mcp checkout — only if setup recorded it (drives the bridge probe below)
    okm_recorded = state.get("omni_kit_mcp")
    if variant == "viewer":
        add("omni-kit-mcp checkout", NA, "no bridge on the viewer-only macOS install")
    elif okm_recorded:
        okm = Path(okm_recorded)
        if (okm / "exts" / "omni.kit.mcp").is_dir():
            add("omni-kit-mcp checkout", OK, f"`{okm}`")
        else:
            add("omni-kit-mcp checkout", FAIL, f"recorded at `{okm}` but exts/omni.kit.mcp missing")
            rc = 1
    else:
        add("omni-kit-mcp checkout", NA, "not recorded — bridge probe falls back to a raw socket; re-run /isaacsim:setup with --omni-kit-mcp to record it")

    # bind host — remote-access posture. The bridge binds localhost by default;
    # a recorded non-loopback host means run_python is exposed to that network.
    bind_host = state.get("bind_host")
    if variant != "viewer":
        if bind_host:
            if bind_host in ("localhost", "127.0.0.1", "::1"):
                add("bind host", OK, f"`{bind_host}` — loopback only; operate remotely via an SSH tunnel")
            else:
                reachable = _tcp_reachable(bind_host, int(state["mcp_port"])) if state.get("mcp_port") else False
                add("bind host", OK if reachable else WARN,
                    f"`{bind_host}` — bridge bound beyond loopback: run_python is REMOTE CODE EXECUTION, keep this a trusted tailnet/LAN, never a public host; "
                    + (f"listening at {bind_host}:{state.get('mcp_port')}" if reachable
                       else f"not currently listening at {bind_host}:{state.get('mcp_port')} (sim stopped?)"))
        else:
            add("bind host", NA, "not recorded — bridge binds localhost (loopback) by default; remote access via SSH tunnel")

    # bridge liveness — WARN, not FAIL: a stopped sim is normal (doctor.md rule).
    # Prefer the reference client (recorded checkout), which auto-discovers a
    # lone bridge (no port needed); pin the recorded port only if discovery is
    # ambiguous. Fall back to the raw socket when no checkout is recorded.
    if variant != "viewer" and state.get("mcp_port"):
        port = int(state["mcp_port"])
        if okm_recorded:
            okm = Path(okm_recorded)
            probe_rc, probe_out, probe_err = probe_via_client(okm)  # discovery, no port
            label = "discovered bridge"
            if probe_rc == 2:  # unreachable, or several bridges up → pin the recorded one
                host = bind_host if (bind_host and bind_host not in ("localhost", "127.0.0.1", "::1")) else None
                probe_rc, probe_out, probe_err = probe_via_client(okm, port=port, host=host)
                label = f"port {port}"
            if probe_rc == 0:
                add("bridge list_tools", OK, f"{label} answered via kit_mcp.client")
            elif probe_rc == 1:
                add("bridge list_tools", WARN, f"{label} reachable but list_tools errored: {_oneline(probe_err or probe_out) or 'bridge error'}")
            else:  # 2 — unreachable/ambiguous; a stopped sim is normal, not a FAIL
                add("bridge list_tools", WARN, f"no bridge answering ({_oneline(probe_err) or 'unreachable'}) — Isaac Sim not running, or the bridge ext isn't registered (omni-kit-mcp scripts/install.py); `--list-bridges` lists any live ones")
        else:
            tools = probe_list_tools(port)
            if tools is not None:
                add("bridge list_tools", OK, f"port {port} answered with {len(tools)} tool(s) (raw socket — omni_kit_mcp not recorded)")
            else:
                add("bridge list_tools", WARN, f"port {port} not answering — Isaac Sim not running, or the bridge ext is not registered (omni-kit-mcp scripts/install.py)")
    else:
        add("bridge list_tools", NA, "no bridge on the viewer-only macOS install" if variant == "viewer" else "mcp_port not recorded")

    # macOS operate-from-another-machine artifacts (a viewer box can also DRIVE
    # a remote sim through a local copy of kit_mcp's reference client)
    if state.get("operate_client"):
        oc = Path(state["operate_client"])
        box = state.get("sim_box_host", "?")
        if oc.is_file():
            add("operate client", OK, f"`{oc}` → drives sim box `{box}`")
        else:
            add("operate client", FAIL, f"recorded at `{oc}` but client.py is gone — re-run /isaacsim:setup")
            rc = 1
    elif variant == "viewer":
        add("operate client", NA, "not set up — /isaacsim:setup can drop kit_mcp's client.py here to drive a remote sim from this Mac")

    # isaac-ctl — only if setup recorded it
    if state.get("isaac_ctl"):
        ctl = Path(state["isaac_ctl"])
        if not ctl.exists():
            add("isaac-ctl", FAIL, f"recorded at `{ctl}` but missing")
            rc = 1
        else:
            try:
                out = subprocess.run([str(ctl), "status"], capture_output=True, text=True, timeout=10)
                status_line = (out.stdout or out.stderr).strip().splitlines()
                add("isaac-ctl", OK, f"`{ctl}` — status: {status_line[0] if status_line else 'ok'}")
            except Exception as e:
                add("isaac-ctl", WARN, f"present but `status` failed: {type(e).__name__}")
    else:
        add("isaac-ctl", NA, "not installed on this box (normal)")

    print("| component | status | detail |")
    print("|---|---|---|")
    for component, status, detail in rows:
        print(f"| {component} | {status} | {detail} |")
    print()
    print("all recorded components healthy." if rc == 0 else "issues found — see failing rows above.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
