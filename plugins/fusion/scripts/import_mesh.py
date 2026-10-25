"""Import mesh file(s) (OBJ / STL / 3MF) into Fusion 360 with correct units.

Programmatic mesh import via the classic mesh API
`Component.meshBodies.add(filename, MeshUnits)`. Once imported, a mesh body is
manipulable like any other body (move, scale, combine, convert to BRep), so for
RIGID parts that ship as STL/OBJ this is all you need -- no URDF wrapper.

Runs INSIDE Fusion via the bridge `exec`. Reads a handoff file
(default /tmp/fusion_import_mesh.json):

    {
      "units": "m",                 # m | cm | mm | in | ft  (mesh file units)
      "doc": "new",                 # new | active
      "doc_name": "my_part",        # name for a new document
      "meshes": [
        {"file": "/abs/a.obj", "name": "partA",
         "xyz_m": [0,0,0], "rpy": [0,0,0]}   # placement optional (metres, rad)
      ]
    }

If a mesh has a "name" it lands in its own named component placed at xyz/rpy;
otherwise it imports into the active/root component at the origin. URDF metres ->
Fusion internal cm (x100) for placement.

For ARTICULATED inputs (a robot/gripper/mechanism with real joints + limits),
use import_urdf.py instead -- it preserves the kinematic tree. For a bag of rigid
parts, prefer THIS.
"""
import os
import json
import math

import adsk.core
import adsk.fusion

HANDOFF = "/tmp/fusion_import_mesh.json"

_UNITS = None  # populated at runtime from adsk.fusion.MeshUnits


def _units_enum(key):
    m = {
        "m": adsk.fusion.MeshUnits.MeterMeshUnit,
        "cm": adsk.fusion.MeshUnits.CentimeterMeshUnit,
        "mm": adsk.fusion.MeshUnits.MillimeterMeshUnit,
        "in": adsk.fusion.MeshUnits.InchMeshUnit,
        "ft": adsk.fusion.MeshUnits.FootMeshUnit,
    }
    return m.get(key, adsk.fusion.MeshUnits.MeterMeshUnit)


def _rpy_matrix(xyz_cm, rpy):
    r, p, y = rpy
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    R = [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp,     cp * sr,                cp * cr],
    ]
    m = adsk.core.Matrix3D.create()
    m.setWithArray([
        R[0][0], R[0][1], R[0][2], xyz_cm[0],
        R[1][0], R[1][1], R[1][2], xyz_cm[1],
        R[2][0], R[2][1], R[2][2], xyz_cm[2],
        0.0, 0.0, 0.0, 1.0,
    ])
    return m


def run():
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        cfg = json.load(open(HANDOFF))
        units = _units_enum(cfg.get("units", "m"))

        if cfg.get("doc", "new") == "new":
            app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent

        imported = []
        for spec in cfg.get("meshes", []):
            f = spec.get("file")
            if not f or not os.path.exists(f):
                imported.append("MISSING:%s" % f)
                continue
            name = spec.get("name")
            if name:
                occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                comp = occ.component
                comp.name = name
                comp.meshBodies.add(f, units)
                xyz = spec.get("xyz_m", [0, 0, 0])
                rpy = spec.get("rpy", [0, 0, 0])
                occ.transform2 = _rpy_matrix(
                    [xyz[0] * 100.0, xyz[1] * 100.0, xyz[2] * 100.0], rpy)
            else:
                root.meshBodies.add(f, units)
            mb = (comp.meshBodies if name else root.meshBodies)
            body = mb.item(mb.count - 1)
            bb = body.boundingBox
            ext = max(bb.maxPoint.x - bb.minPoint.x,
                      bb.maxPoint.y - bb.minPoint.y,
                      bb.maxPoint.z - bb.minPoint.z)
            imported.append("%s(%.1fcm)" % (name or os.path.basename(f), ext))

        msg = "IMPORTED %d mesh(es): %s" % (len(imported), imported)
        app.log(msg)
        print(msg)
        if cfg.get("doc_name"):
            try:
                app.activeDocument.saveAs(cfg["doc_name"], app.data.activeProject.rootFolder, "mesh import", "")
            except Exception:
                pass
        return "OK"
    except Exception:
        import traceback
        tb = traceback.format_exc()
        app.log("ERROR: %s" % tb)
        print("ERROR: %s" % tb)
        return "ERROR"


run()
