import pytest

from fuzzydroid_kicad.registry import Registry


def test_registration_dispatch_and_catalog_share_a_contract():
    registry = Registry()
    calls = []

    @registry.tool("demo.echo", "Echo", {"message": {"type": "string"}}, ["message"])
    def echo(message):
        calls.append(message)
        return {"message": message}

    assert registry.dispatch("demo.echo", {"message": "hello"}) == {"message": "hello"}
    assert calls == ["hello"]
    assert registry.catalog()[0]["inputSchema"]["required"] == ["message"]
    assert "handler" not in registry.catalog()[0]
    with pytest.raises(ValueError, match="Duplicate"):
        registry.tool("demo.echo", "Duplicate")(echo)


@pytest.mark.parametrize("params", [{}, {"value": True}, {"value": "2"}, {"value": 2, "extra": 1}])
def test_invalid_arguments_never_reach_a_handler(params):
    registry = Registry()
    registry.tool("test.number", "Number", {"value": {"type": "number"}}, ["value"])(
        lambda value: pytest.fail("Invalid call reached handler")
    )
    with pytest.raises((ValueError, TypeError)):
        registry.dispatch("test.number", params)


def test_names_round_trip_through_mcp_without_collision():
    registry = Registry()
    with pytest.raises(ValueError):
        registry.tool("demo.a__b", "Ambiguous")
    registry.tool("demo.a_b", "Valid")(dict)
    name = registry.catalog()[0]["name"]
    assert name.replace(".", "__").replace("__", ".") == name


def test_non_json_results_are_rejected():
    registry = Registry()
    registry.tool("test.result", "Result")(lambda: {"bad": object()})
    with pytest.raises(TypeError):
        registry.dispatch("test.result")


def test_project_tools_cannot_shadow_external_providers():
    registry = Registry(reserved_namespaces=("ipc", "bridge"))
    with pytest.raises(ValueError, match="Reserved"):
        registry.tool("ipc.ping", "Shadow")
    registry.tool("project.answer", "Answer")(lambda: 42)
    registry.unregister("project.answer")
    with pytest.raises(ValueError, match="Unknown"):
        registry.dispatch("project.answer")
