"""Check package integrity and preservation of user files during viewer exports."""

import importlib.util
import http.client
import json
import threading
import xml.etree.ElementTree as ET
from http.server import HTTPServer
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "serve_urdf", Path(__file__).resolve().parents[3] / "viewer/urdf/serve_urdf.py"
)
viewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viewer)


def make_package(tmp_path, mesh_ref):
    package = tmp_path / "robot"
    urdf = package / "urdf/robot.urdf"
    urdf.parent.mkdir(parents=True)
    urdf.write_text(
        '<robot name="test"><link name="base">'
        f'<visual><geometry><mesh filename="{mesh_ref}"/></geometry></visual>'
        '<visual><geometry><box size="1 1 1"/></geometry></visual>'
        "</link></robot>"
    )
    return package, urdf


@pytest.mark.parametrize(
    "reference", ["../meshes/part.stl", "package://robot/meshes/part.stl"]
)
def test_export_preserves_sources_and_previous_exports(tmp_path, reference):
    package, urdf = make_package(tmp_path, reference)
    mesh = package / "meshes/part.stl"
    mesh.parent.mkdir()
    mesh.write_text("solid original")
    original = urdf.read_bytes()
    previous = tmp_path / "robot_pruned/keep.txt"
    previous.parent.mkdir()
    previous.write_text("user work")

    first = viewer.export_pruned(package, urdf, [{"link": "base", "visualIndex": 1}])
    second = viewer.export_pruned(package, urdf, [])

    assert first["output_dir"] != second["output_dir"]
    assert previous.read_text() == "user work"
    assert urdf.read_bytes() == original
    assert (
        Path(first["output_dir"]) / "meshes/part.stl"
    ).read_bytes() == mesh.read_bytes()
    tree = ET.parse(Path(first["output_dir"]) / "urdf/robot.urdf")
    assert len(list(tree.getroot().iter("visual"))) == 1


@pytest.mark.parametrize("reference", ["../meshes/missing.stl", "../../outside.stl"])
def test_invalid_mesh_fails_without_creating_an_export(tmp_path, reference):
    package, urdf = make_package(tmp_path, reference)
    (tmp_path / "outside.stl").write_text("private")
    with pytest.raises((ValueError, FileNotFoundError)):
        viewer.export_pruned(package, urdf, [])
    assert not list(tmp_path.glob("robot_pruned*"))


@pytest.mark.parametrize(
    "origin,allowed",
    [(None, True), ("same", True), ("http://foreign.invalid", False), ("null", False)],
)
def test_viewer_export_rejects_foreign_websites(tmp_path, origin, allowed):
    package, urdf = make_package(tmp_path, "../meshes/part.stl")
    mesh = package / "meshes/part.stl"
    mesh.parent.mkdir()
    mesh.write_text("solid test")
    server = HTTPServer(("127.0.0.1", 0), viewer.make_handler(package, urdf))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(*server.server_address, timeout=3)
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = (
            f"http://127.0.0.1:{server.server_port}" if origin == "same" else origin
        )
    try:
        connection.request("POST", "/export", body='{"prune": []}', headers=headers)
        response = connection.getresponse()
        body = response.read()
        assert response.status == (200 if allowed else 403)
        if allowed:
            assert json.loads(body)["ok"] is True
        assert len(list(tmp_path.glob("robot_pruned*"))) == int(allowed)
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
