from fuzzydroid_kicad import doctor


def test_doctor_distinguishes_missing_setup_and_closed_app(monkeypatch):
    def missing():
        raise FileNotFoundError("Run setup")

    monkeypatch.setattr(doctor, "read_state", missing)
    monkeypatch.setattr(
        doctor.ipc, "inspect_board", lambda: (_ for _ in ()).throw(RuntimeError("Closed"))
    )
    monkeypatch.setattr(doctor.client, "discover", list)
    report = doctor.diagnose()
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["state"]["ok"] is False
    assert checks["ipc"]["error"] == "Closed"
    assert "restart" in checks["native"]["error"]


def test_doctor_detects_dependency_drift(tmp_path, monkeypatch):
    root = tmp_path / "plugin"
    package = root / "lib/fuzzydroid_kicad"
    package.mkdir(parents=True)
    (package / "pyproject.toml").write_text("changed dependency")
    monkeypatch.setattr(
        doctor,
        "read_state",
        lambda: {
            "plugin_root": str(root),
            "plugin_version": doctor.__version__,
            "pyproject_hash": "old",
        },
    )
    monkeypatch.setattr(doctor.ipc, "inspect_board", dict)
    monkeypatch.setattr(doctor.client, "discover", list)
    report = doctor.diagnose()
    artifact = next(check for check in report["checks"] if check["name"] == "artifacts")
    assert artifact["ok"] is False
    assert "drift" in artifact["error"]


def test_doctor_keeps_native_protobuf_evidence_json_safe(monkeypatch):
    import json

    from google.protobuf.wrappers_pb2 import StringValue

    monkeypatch.setattr(doctor, "read_state", dict)
    monkeypatch.setattr(doctor.ipc, "inspect_board", lambda: {"id": StringValue(value="uuid")})
    monkeypatch.setattr(doctor.client, "discover", list)
    report = doctor.diagnose()
    assert next(c for c in report["checks"] if c["name"] == "ipc")["evidence"] == {"id": "uuid"}
    json.dumps(report)
