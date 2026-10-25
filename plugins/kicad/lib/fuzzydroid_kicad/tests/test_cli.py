import json

from click.testing import CliRunner

from fuzzydroid_kicad import cli


def test_cli_reports_invalid_json_as_a_failed_command():
    result = CliRunner().invoke(cli.main, ["--json", "call", "ipc.save"], input="{broken")
    assert result.exit_code == 1
    assert json.loads(result.output)["ok"] is False


def test_cli_never_promises_native_rollback():
    result = CliRunner().invoke(
        cli.main,
        ["--json", "exec", "-", "--board", "/a.kicad_pcb", "--backend", "native", "--mutate"],
        input="result = 1",
    )
    assert result.exit_code == 1
    assert "no automatic rollback" in json.loads(result.output)["error"]


def test_cli_forwards_the_named_tool_and_parameters(monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli.Service,
        "call",
        lambda self, tool, params: calls.append((tool, params)) or {"value": 42},
    )
    result = CliRunner().invoke(
        cli.main, ["--json", "call", "demo.answer"], input='{"question": 1}'
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["data"] == {"value": 42}
    assert calls == [("demo.answer", {"question": 1})]
