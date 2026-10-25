"""Health check for /isaaclab:doctor — rows DRIVEN BY the state file.

Components the setup did not install/record read "N/A — not installed",
never FAIL. The one active hazard scan: the static-TLS tunable in the Lab
venv's activate script FAILS the check even though setup didn't put it there,
because its presence breaks every Lab standalone run on this box.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fuzzydroid_isaaclab import PLUGIN_NAME
from fuzzydroid_isaaclab import _common as c
from fuzzydroid_isaaclab.detect import _dist_version_via_python, _import_probe
from fuzzydroid_isaaclab.setup import STATIC_TLS_MARKER, activate_has_static_tls

OK, FAIL, WARN, NA = "✅", "❌", "⚠️", "N/A"


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
        print(f"| state file | {FAIL} | {state_path} missing — run /isaaclab:setup |")
        return 1
    add("state file", OK, f"`{state_path}` parses (v{state.get('plugin_version', '?')})")

    venv = Path(state.get("venv_path", ""))
    if c.venv_python(venv).exists():
        add("plugin venv", OK, f"`{venv}`")
    else:
        add("plugin venv", FAIL, f"python missing at `{c.venv_python(venv)}` — re-run /isaaclab:setup")
        rc = 1
    plugin_root = Path(__file__).resolve().parents[1]
    pyproject = plugin_root / "pyproject.toml"
    if pyproject.exists() and state.get("pyproject_hash"):
        if c.hash_file(pyproject) == state["pyproject_hash"]:
            add("pyproject drift", OK, "deps unchanged since setup")
        else:
            add("pyproject drift", FAIL, "deps changed since setup — re-run /isaaclab:setup")
            rc = 1

    variant = state.get("variant", "?")
    lab_root = Path(state.get("lab_root", ""))
    if state.get("lab_root"):
        if lab_root.is_dir():
            add("lab root", OK, f"`{lab_root}` ({variant}, {state.get('lab_version', 'version unrecorded')})")
        else:
            add("lab root", FAIL, f"recorded root gone: `{lab_root}` — re-run /isaaclab:setup")
            rc = 1
    else:
        add("lab root", NA, "not recorded")

    if state.get("lab_python"):
        lp = Path(state["lab_python"])
        if not lp.exists():
            add("lab python", FAIL, f"recorded python gone: `{lp}`")
            rc = 1
        else:
            # runtime truth first: what a Lab run would actually import (a
            # source checkout on the import path can shadow the pip dist, and
            # dist metadata can't see that). Metadata is the fallback probe.
            probe = _import_probe(lp, "isaaclab")
            if probe and probe.get("version"):
                detail = f"import under `{lp}` runs isaaclab {probe['version']}"
                origin = probe.get("file")
                if origin and str(state.get("lab_root", "")) not in origin:
                    detail += (f" — import resolves OUTSIDE the venv: `{origin}` "
                               "(a source checkout shadows the pip dist)")
                add("isaaclab dist", OK, detail)
            else:
                meta = _dist_version_via_python(lp, "isaaclab")
                if meta:
                    add("isaaclab dist", WARN,
                        f"metadata reports isaaclab {meta} but `import isaaclab` failed "
                        "under the recorded python — a Lab run would fail the same way")
                else:
                    add("isaaclab dist", FAIL, f"`{lp}` cannot import or resolve the isaaclab dist — env was rebuilt? re-run /isaaclab:setup")
                    rc = 1
    else:
        add("lab python", NA, "no venv recorded (source install)")

    # the guard rule — an active hazard, not an install artifact
    if variant == "pip" and lab_root.is_dir():
        if activate_has_static_tls(lab_root):
            add("static-TLS guard rule", FAIL,
                f"`bin/activate` exports {STATIC_TLS_MARKER} — breaks PhysX GPU init in Lab "
                "standalone runs (reset() hang). Remove it; guards are per-profile launcher "
                "business (isaac-ctl full-app profile only).")
            rc = 1
        else:
            add("static-TLS guard rule", OK, "no blanket static-TLS export in the venv activate")
    else:
        add("static-TLS guard rule", NA, "no venv activate to scan (source install)")

    if state.get("omni_kit_mcp"):
        okm = Path(state["omni_kit_mcp"])
        if (okm / "exts" / "omni.kit.mcp").is_dir():
            add("omni-kit-mcp checkout", OK, f"`{okm}`")
        else:
            add("omni-kit-mcp checkout", FAIL, f"recorded at `{okm}` but exts/omni.kit.mcp missing")
            rc = 1
    else:
        add("omni-kit-mcp checkout", NA, "not recorded — bridge launches need it; see the bridge-launch reference")

    add("mcp port", OK if state.get("mcp_port") else NA,
        f"OMNI_KIT_MCP_PORT={state.get('mcp_port')} (used per-launch; only live during a run)"
        if state.get("mcp_port") else "not recorded")

    print("| component | status | detail |")
    print("|---|---|---|")
    for component, status, detail in rows:
        print(f"| {component} | {status} | {detail} |")
    print()
    print("all recorded components healthy." if rc == 0 else "issues found — see failing rows above.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
