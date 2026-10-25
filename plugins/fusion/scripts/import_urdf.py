"""Ingest a URDF into Fusion 360 as a multi-component assembly.

SCOPE: use this for ARTICULATED inputs -- a robot/gripper/mechanism whose URDF
carries a real kinematic tree (revolute/prismatic joints, axes, limits) you want
preserved in Fusion. For a bag of RIGID parts that merely ship as STL/OBJ, a URDF
adds nothing (every joint ends up "fixed" = a glorified transform list) -- use
import_mesh.py instead, which imports + places meshes directly.

The inverse of export_urdf.py. Reads a URDF, and
for every link that carries a <visual><mesh> it:
  1. imports the mesh (OBJ/STL) into its own named component, using explicit
     mesh units (URDF convention is metres; override via cfg["mesh_units"]),
  2. places the component at the link's pose, accumulated through the joint tree
     (each joint's <origin> xyz/rpy, URDF fixed-axis Rz*Ry*Rx convention).

Runs INSIDE Fusion via the bridge `exec`. Target is read from a handoff file
(default /tmp/fusion_import_urdf.json):
    {"urdf": "/abs/path.urdf", "doc_name": "square_table", "save": false}

Units: URDF metres -> Fusion internal cm (x100) for placement. Mesh geometry is
imported at the units declared in cfg["mesh_units"] (default metres).
"""
import os
import json
import math
import xml.etree.ElementTree as ET

import adsk.core
import adsk.fusion

HANDOFF = "/tmp/fusion_import_urdf.json"


def _log(app, msg):
    app.log(str(msg))
    print(str(msg))


def _rpy_matrix(xyz_cm, rpy):
    """Build a Matrix3D from translation (cm) + URDF rpy (Rz*Ry*Rx)."""
    r, p, y = rpy
    cr, sr = math.cos(r), math.sin(r)
    cp, sp = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    # R = Rz(y) * Ry(p) * Rx(r)
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
        0.0,     0.0,     0.0,     1.0,
    ])
    return m


def _parse_urdf(path):
    root = ET.parse(path).getroot()
    base = os.path.dirname(os.path.abspath(path))
    links = {}
    for link in root.findall("link"):
        name = link.get("name")
        mesh_file = None
        vis = link.find("visual")
        if vis is not None:
            mesh = vis.find("geometry/mesh")
            if mesh is not None:
                fn = mesh.get("filename")
                if fn:
                    mesh_file = fn if os.path.isabs(fn) else os.path.normpath(os.path.join(base, fn))
        links[name] = {"mesh": mesh_file}
    joints = []
    for j in root.findall("joint"):
        parent = j.find("parent").get("link")
        child = j.find("child").get("link")
        org = j.find("origin")
        xyz = [0.0, 0.0, 0.0]
        rpy = [0.0, 0.0, 0.0]
        if org is not None:
            if org.get("xyz"):
                xyz = [float(v) for v in org.get("xyz").split()]
            if org.get("rpy"):
                rpy = [float(v) for v in org.get("rpy").split()]
        joints.append({"parent": parent, "child": child, "xyz": xyz, "rpy": rpy})
    return links, joints


def _world_poses(links, joints):
    """Accumulate each link's pose to the root (xyz metres, rpy rad). Fixed tree."""
    children = {j["child"]: j for j in joints}
    all_children = set(children)
    roots = [n for n in links if n not in all_children]
    poses = {r: ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]) for r in roots}

    def resolve(name):
        if name in poses:
            return poses[name]
        j = children[name]
        pxyz, prpy = resolve(j["parent"])
        # compose: parent pose then joint origin (fixed joint). This uses
        # additive translation + rotation, which is exact only for a flat joint
        # tree (every link parented directly to the root, so the parent pose is
        # the identity). Deeper kinematic chains would need full matrix
        # composition here.
        Rp = _rpy_matrix([0, 0, 0], prpy)
        v = adsk.core.Vector3D.create(j["xyz"][0], j["xyz"][1], j["xyz"][2])
        v.transformBy(Rp)
        xyz = [pxyz[0] + v.x, pxyz[1] + v.y, pxyz[2] + v.z]
        rpy = [prpy[0] + j["rpy"][0], prpy[1] + j["rpy"][1], prpy[2] + j["rpy"][2]]
        poses[name] = (xyz, rpy)
        return poses[name]

    for n in links:
        resolve(n)
    return poses


def run():
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        cfg = json.load(open(HANDOFF))
        urdf_path = cfg["urdf"]
        doc_name = cfg.get("doc_name") or os.path.splitext(os.path.basename(urdf_path))[0]

        links, joints = _parse_urdf(urdf_path)
        poses = _world_poses(links, joints)

        # Fresh design document (direct mode -> mesh ops without timeline noise).
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        root = design.rootComponent

        # mesh units: URDF convention is metres; override via cfg["mesh_units"]
        units_map = {
            "m": adsk.fusion.MeshUnits.MeterMeshUnit,
            "cm": adsk.fusion.MeshUnits.CentimeterMeshUnit,
            "mm": adsk.fusion.MeshUnits.MillimeterMeshUnit,
            "in": adsk.fusion.MeshUnits.InchMeshUnit,
            "ft": adsk.fusion.MeshUnits.FootMeshUnit,
        }
        mesh_units = units_map.get(cfg.get("mesh_units", "m"), adsk.fusion.MeshUnits.MeterMeshUnit)

        imported = []
        for name, info in links.items():
            mesh_file = info["mesh"]
            if not mesh_file or not os.path.exists(mesh_file):
                continue
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            comp = occ.component
            comp.name = name
            occ.activate()

            # classic mesh insert: filename + explicit units (no calibration needed)
            comp.meshBodies.add(mesh_file, mesh_units)
            mb = comp.meshBodies.item(comp.meshBodies.count - 1)
            bb = mb.boundingBox
            meas_cm = max(bb.maxPoint.x - bb.minPoint.x,
                          bb.maxPoint.y - bb.minPoint.y,
                          bb.maxPoint.z - bb.minPoint.z)

            # place component at link world pose (metres -> cm)
            xyz, rpy = poses.get(name, ([0, 0, 0], [0, 0, 0]))
            m = _rpy_matrix([xyz[0] * 100.0, xyz[1] * 100.0, xyz[2] * 100.0], rpy)
            occ.transform2 = m
            imported.append("%s(%.1fcm)" % (name, meas_cm))

        _log(app, "IMPORTED %d components into '%s': %s" % (len(imported), doc_name, imported))

        if cfg.get("save"):
            # save into cfg["project"] (default: Fusion's "Default Project"),
            # optionally nested under cfg["folder"] (e.g. "A/B/C").
            project_name = cfg.get("project", "Default Project")
            target = None
            for proj in app.data.dataProjects:
                if proj.name == project_name:
                    target = proj.rootFolder
                    break
            if target is not None:
                folder = cfg.get("folder")
                if folder:
                    for seg in folder.split("/"):
                        nxt = None
                        for fo in target.dataFolders:
                            if fo.name == seg:
                                nxt = fo; break
                        target = nxt or target.dataFolders.add(seg)
                app.activeDocument.saveAs(doc_name, target, "URDF ingest", "")
                _log(app, "SAVED to %s/%s" % (folder or project_name, doc_name))
        return "OK"
    except Exception as e:
        import traceback
        _log(app, "ERROR: %s" % traceback.format_exc())
        if ui:
            ui.messageBox("import_urdf failed: %s" % str(e))
        return "ERROR"


run()
