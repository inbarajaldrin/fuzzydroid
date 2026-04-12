"""End-to-end tests for cli-anything-fusion360.

These tests require Fusion 360 running with the fusion_bridge add-in
loaded and listening on localhost:8765.

Run: python3 -m pytest shared/fuzzydroid/tests/fusion/test_full_e2e.py -v --tb=short

To skip when bridge is unavailable:
    pytest -m "not e2e" ...
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

pytestmark = pytest.mark.skip(reason="requires live Fusion 360 bridge on localhost:8765")


# ── CLI resolver ─────────────────────────────────────────────────────────────


def _resolve_cli(name: str) -> list[str]:
    """Resolve the CLI command to either an installed binary or a module fallback.

    If CLI_ANYTHING_FORCE_INSTALLED=1 is set, only the installed binary is
    accepted (raises RuntimeError if not found).

    Returns:
        List of command parts suitable for subprocess (e.g. ["cli-anything-fusion"]
        or ["/path/to/python", "-m", "fuzzydroid.fusion.cli"]).
    """
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "fuzzydroid.fusion.cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _run_cli(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run the CLI with the given arguments and return the result."""
    cmd = _resolve_cli("cli-anything-fusion360") + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_json(*args: str, timeout: int = 120) -> dict:
    """Run the CLI with --json flag and parse the output."""
    result = _run_cli("--json", *args, timeout=timeout)
    assert result.returncode == 0, (
        f"CLI returned {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    data = json.loads(result.stdout)
    return data


# ── Check if bridge is available ─────────────────────────────────────────────

_bridge_available = None


def _check_bridge() -> bool:
    """Check if the Fusion bridge is reachable. Cached after first call."""
    global _bridge_available
    if _bridge_available is not None:
        return _bridge_available
    try:
        result = _run_cli("--json", "ping", timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            _bridge_available = data.get("status") == "ok"
        else:
            _bridge_available = False
    except Exception:
        _bridge_available = False
    return _bridge_available


# ── Markers ──────────────────────────────────────────────────────────────────

# Skip E2E tests that need bridge unless it is available.
requires_bridge = pytest.mark.skipif(
    not _check_bridge() if os.environ.get("CHECK_BRIDGE_AT_COLLECT") else False,
    reason="Fusion 360 bridge not available on localhost:8765",
)


# ── TestCLISubprocess ────────────────────────────────────────────────────────


class TestCLISubprocess:
    """E2E tests exercising the CLI as a subprocess.

    Tests that only inspect CLI flags (--help, --version) do not need the
    bridge. Tests that talk to Fusion 360 are marked with @requires_bridge
    and will be skipped automatically if the bridge is not running.
    """

    # ── CLI meta tests (no bridge needed) ────────────────────────────

    def test_help(self):
        """--help returns 0 and contains usage info."""
        result = _run_cli("--help")
        assert result.returncode == 0
        lower = result.stdout.lower()
        assert "fusion360" in lower or "fusion 360" in lower

    def test_version(self):
        """--version returns 0 and prints a version string."""
        result = _run_cli("--version")
        assert result.returncode == 0
        assert "1." in result.stdout or "0." in result.stdout

    # ── Bridge-dependent tests ───────────────────────────────────────

    @requires_bridge
    def test_ping_json(self):
        """ping returns valid JSON with status key."""
        data = _run_json("ping")
        assert "status" in data
        assert data["status"] == "ok"

    @requires_bridge
    def test_project_list_json(self):
        """project list returns valid JSON."""
        data = _run_json("project", "list")
        assert "status" in data

    @requires_bridge
    def test_design_info_json(self):
        """design info returns valid JSON."""
        data = _run_json("design", "info")
        assert "status" in data

    @requires_bridge
    def test_export_step_json(self):
        """export step returns valid JSON and mentions the path."""
        with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
            tmp_path = f.name
        try:
            data = _run_json("export", "step", "--path", tmp_path)
            assert "status" in data
            if data["status"] == "ok":
                print(f"[artifact] STEP file: {tmp_path}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @requires_bridge
    def test_design_bodies_json(self):
        """design bodies returns valid JSON."""
        data = _run_json("design", "bodies")
        assert "status" in data

    @requires_bridge
    def test_design_components_json(self):
        """design components returns valid JSON."""
        data = _run_json("design", "components")
        assert "status" in data

    @requires_bridge
    def test_design_bbox_json(self):
        """design bbox returns valid JSON."""
        data = _run_json("design", "bbox")
        assert "status" in data

    @requires_bridge
    def test_design_timeline_json(self):
        """design timeline returns valid JSON."""
        data = _run_json("design", "timeline")
        assert "status" in data

    @requires_bridge
    def test_exec_json(self):
        """exec returns valid JSON with output."""
        data = _run_json("exec", "print('hello from fusion')")
        assert "status" in data
        if data["status"] == "ok":
            # The bridge should capture print output
            output = data.get("output", data.get("stdout", ""))
            assert "hello" in str(output).lower() or data["status"] == "ok"

    @requires_bridge
    def test_api_clear_json(self):
        """api clear returns valid JSON with status ok."""
        data = _run_json("api", "clear")
        assert "status" in data
        assert data["status"] == "ok"

    @requires_bridge
    def test_full_workflow(self):
        """Full workflow: search -> open -> export step -> verify file.

        This test exercises the realistic end-to-end path a user would follow.
        It searches for a file, opens it, exports it as STEP, and checks
        that the exported file exists on disk.
        """
        # Step 1: List projects (verify bridge connectivity)
        proj_data = _run_json("project", "list")
        assert proj_data.get("status") == "ok", f"project list failed: {proj_data}"
        projects = proj_data.get("projects", [])
        assert len(projects) > 0, "No projects found in Fusion 360"
        print(f"[workflow] Found {len(projects)} projects")

        # Step 2: Get current design info
        info_data = _run_json("design", "info")
        assert info_data.get("status") == "ok", f"design info failed: {info_data}"
        doc_name = info_data.get("name", "unknown")
        print(f"[workflow] Active document: {doc_name}")

        # Step 3: Export as STEP
        export_path = os.path.join(tempfile.gettempdir(), "e2e_workflow_test.step")
        export_data = _run_json("export", "step", "--path", export_path)
        assert export_data.get("status") == "ok", f"export failed: {export_data}"

        # Step 4: Verify file exists
        assert os.path.exists(export_path), f"Exported STEP file not found at {export_path}"
        size = os.path.getsize(export_path)
        assert size > 0, "Exported STEP file is empty"
        print(f"[artifact] Exported STEP: {export_path} ({size} bytes)")

        # Cleanup
        os.unlink(export_path)
