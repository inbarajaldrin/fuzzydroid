"""
Container with Stackable Cap — Fusion 360 Generator Script

Creates a hollow container with a cap that features:
- A curved dome on top (for stackable base cradle when flipped)
- Shelled dome interior
- Parametric trim that removes material where cap overlaps container

Usage:
  1. Set CONFIG values below
  2. Run in Fusion: exec(open('/path/to/create_container_with_cap.py').read())
  Or via bridge: fusion_exec_python(code="exec(open('...').read())")
"""

import adsk.core, adsk.fusion, math, json, traceback

# ═══════════════════════════════════════════════════
# CONFIG — Change these to resize everything
# ═══════════════════════════════════════════════════
CONFIG = {
    # Container dimensions
    "containerWidth":      60,    # mm — X dimension
    "containerDepth":      60,    # mm — Y dimension
    "containerHeight":     50,    # mm — Z dimension
    "wallThickness":       1.5,   # mm — container shell thickness
    "cornerRadius":        8,     # mm — rounded corners
    "bottomFilletRadius":  5,     # mm — base fillet curve

    # Container lip (top rim)
    "lipHeight":           2.5,   # mm
    "lipExtension":        1.5,   # mm — how far lip extends beyond body
    "lipCornerRadius":     10,    # mm — lip corner rounding

    # Cap properties
    "capThickness":        1.5,   # mm — cap wall thickness
    "capClearance":        0.3,   # mm — gap between cap and container

    # Dome (stackable feature on cap top)
    "pocketClearance":     1.5,   # mm — clearance for dome pocket
    "domeHeight":          5,     # mm — dome bump height
    "domeFilletRadius":    5,     # mm — dome curve radius

    # Trim depth (how far cap overlaps container when stacked)
    "trimOverlap":         5,     # mm — overlap for trim cut
}
# ═══════════════════════════════════════════════════

def mm(val):
    """Convert mm to cm (Fusion internal unit)."""
    return val / 10.0

def run_generator():
    app = adsk.core.Application.get()
    ui = app.userInterface
    p = adsk.core.Point3D

    try:
        # Create new document
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent

        C = {k: mm(v) for k, v in CONFIG.items()}

        # ─── Helper: draw rounded rectangle ───
        def draw_rect(sketch, hw, cr):
            s = hw - cr
            ln = sketch.sketchCurves.sketchLines
            ar = sketch.sketchCurves.sketchArcs

            l_b = ln.addByTwoPoints(p.create(-s, -hw, 0), p.create(s, -hw, 0))
            l_r = ln.addByTwoPoints(p.create(hw, -s, 0), p.create(hw, s, 0))
            l_t = ln.addByTwoPoints(p.create(s, hw, 0), p.create(-s, hw, 0))
            l_l = ln.addByTwoPoints(p.create(-hw, s, 0), p.create(-hw, -s, 0))

            ar.addByCenterStartSweep(p.create(s, -s, 0), p.create(hw, -s, 0), -math.pi/2)
            ar.addByCenterStartSweep(p.create(s, s, 0), p.create(s, hw, 0), -math.pi/2)
            ar.addByCenterStartSweep(p.create(-s, s, 0), p.create(-hw, s, 0), -math.pi/2)
            ar.addByCenterStartSweep(p.create(-s, -s, 0), p.create(-s, -hw, 0), -math.pi/2)

        def find_face(body, z_val, normal_z_sign, largest=True):
            """Find a planar face at given Z with given normal direction."""
            best = None
            for f in body.faces:
                geo = f.geometry
                bb = f.boundingBox
                if geo.classType() != 'adsk::core::Plane':
                    continue
                if abs(bb.minPoint.z - z_val) > 0.02 or abs(bb.maxPoint.z - z_val) > 0.02:
                    continue
                if normal_z_sign > 0 and geo.normal.z < 0.5:
                    continue
                if normal_z_sign < 0 and geo.normal.z > -0.5:
                    continue
                if normal_z_sign == 0:
                    pass
                if best is None or (largest and f.area > best.area) or (not largest and f.area < best.area):
                    best = f
            return best

        def find_edges_at_z(body, z_val):
            """Find all edges at a given Z level."""
            edges = adsk.core.ObjectCollection.create()
            for i in range(body.edges.count):
                e = body.edges.item(i)
                bb = e.boundingBox
                if abs(bb.minPoint.z - z_val) < 0.02 and abs(bb.maxPoint.z - z_val) < 0.02:
                    edges.add(e)
            return edges

        def find_vertical_corner_edges(body):
            """Find vertical edges at the rounded corners."""
            edges = adsk.core.ObjectCollection.create()
            for i in range(body.edges.count):
                e = body.edges.item(i)
                bb = e.boundingBox
                geo = e.geometry
                if geo.classType() == 'adsk::core::Line3D':
                    dx = abs(bb.maxPoint.x - bb.minPoint.x)
                    dy = abs(bb.maxPoint.y - bb.minPoint.y)
                    dz = abs(bb.maxPoint.z - bb.minPoint.z)
                    if dx < 0.01 and dy < 0.01 and dz > 0.1:
                        edges.add(e)
            return edges

        # ═══════════════════════════════════════
        # CONTAINER BODY
        # ═══════════════════════════════════════
        print("Building container...")

        cw_half = C['containerWidth'] / 2
        cd_half = C['containerDepth'] / 2
        cr = C['cornerRadius']

        # Base sketch
        base_sk = root.sketches.add(root.xYConstructionPlane)
        base_sk.name = 'ContainerBase'
        draw_rect(base_sk, cw_half, cr)

        # Extrude container body
        ext = root.features.extrudeFeatures
        ci = ext.createInput(base_sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ci.setDistanceExtent(False, adsk.core.ValueInput.createByReal(C['containerHeight']))
        e1 = ext.add(ci)
        e1.name = 'ContainerExtrude'
        body = root.bRepBodies.item(0)
        body.name = 'ContainerBody'

        # Bottom fillet FIRST (matches original order)
        body = root.bRepBodies.item(0)
        bottom_edges = find_edges_at_z(body, 0)
        if bottom_edges.count > 0:
            fi = root.features.filletFeatures.createInput()
            fi.addConstantRadiusEdgeSet(bottom_edges, adsk.core.ValueInput.createByReal(C['bottomFilletRadius']), True)
            fi.isRollingBallCorner = True
            f1 = root.features.filletFeatures.add(fi)
            f1.name = 'BottomFillet'

        # Shell (remove top face)
        body = root.bRepBodies.item(0)
        top_face = find_face(body, C['containerHeight'], 1)
        fc = adsk.core.ObjectCollection.create()
        fc.add(top_face)
        si = root.features.shellFeatures.createInput(fc, False)
        si.insideThickness = adsk.core.ValueInput.createByReal(C['wallThickness'])
        s1 = root.features.shellFeatures.add(si)
        s1.name = 'ContainerShell'

        # Lip — extrude UPWARD from container top (Z=containerHeight to Z=containerHeight+lipHeight)
        body = root.bRepBodies.item(0)
        lip_hw = cw_half + C['lipExtension']
        lip_cr = C['lipCornerRadius']

        lip_plane_input = root.constructionPlanes.createInput()
        lip_plane_input.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(C['containerHeight']))
        lip_plane = root.constructionPlanes.add(lip_plane_input)

        lip_sk = root.sketches.add(lip_plane)
        lip_sk.name = 'LipProfile'
        draw_rect(lip_sk, lip_hw, lip_cr)

        li = ext.createInput(lip_sk.profiles.item(0), adsk.fusion.FeatureOperations.JoinFeatureOperation)
        li.setDistanceExtent(False, adsk.core.ValueInput.createByReal(C['lipHeight']))
        lip_ext = ext.add(li)
        lip_ext.name = 'LipExtrude'

        # Lip fillet 1 — top outer edges at Z = containerHeight + lipHeight
        body = root.bRepBodies.item(0)
        lip_top_z = C['containerHeight'] + C['lipHeight']
        lip_top_edges = find_edges_at_z(body, lip_top_z)
        if lip_top_edges.count > 0:
            fi2 = root.features.filletFeatures.createInput()
            fi2.addConstantRadiusEdgeSet(lip_top_edges, adsk.core.ValueInput.createByReal(C['wallThickness']), True)
            root.features.filletFeatures.add(fi2).name = 'LipFillet1'

        # Lip fillet 2 — inner transition edges at Z = containerHeight
        body = root.bRepBodies.item(0)
        inner_edges = find_edges_at_z(body, C['containerHeight'])
        if inner_edges.count > 0:
            fi3 = root.features.filletFeatures.createInput()
            fi3.addConstantRadiusEdgeSet(inner_edges, adsk.core.ValueInput.createByReal(C['wallThickness']), True)
            try:
                root.features.filletFeatures.add(fi3).name = 'LipFillet2'
            except:
                print("  LipFillet2 skipped")

        container_body = root.bRepBodies.item(0)
        cbb = container_body.boundingBox
        print(f"  Container done: Z={round(cbb.minPoint.z*10,1)} to {round(cbb.maxPoint.z*10,1)}mm, X={round(cbb.minPoint.x*10,1)} to {round(cbb.maxPoint.x*10,1)}mm")

        # ═══════════════════════════════════════
        # CAP COMPONENT
        # ═══════════════════════════════════════
        print("Building cap...")

        cap_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        cap_comp = cap_occ.component
        cap_comp.name = 'Cap'

        # Cap outer dimensions
        cap_hw = cw_half + C['lipExtension'] + C['capClearance'] + C['capThickness']
        cap_cr = C['lipCornerRadius'] + C['capClearance'] + C['capThickness']
        cap_height = C['lipHeight'] + 2 * C['capThickness']

        # Cap outer sketch on XY, extrude down
        cap_sk = cap_comp.sketches.add(cap_comp.xYConstructionPlane)
        cap_sk.name = 'CapOuter'
        draw_rect(cap_sk, cap_hw, cap_cr)

        cap_ext = cap_comp.features.extrudeFeatures
        cei = cap_ext.createInput(cap_sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        cei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-cap_height))
        ce1 = cap_ext.add(cei)
        ce1.name = 'Extrude1'

        # Shell cap (hollow from bottom)
        cap_body = cap_comp.bRepBodies.item(0)
        cap_bot_z = cap_body.boundingBox.minPoint.z
        cap_bot_face = find_face(cap_body, cap_bot_z, 0)

        if cap_bot_face:
            cfc = adsk.core.ObjectCollection.create()
            cfc.add(cap_bot_face)
            csi = cap_comp.features.shellFeatures.createInput(cfc, False)
            csi.insideThickness = adsk.core.ValueInput.createByReal(C['capThickness'])
            try:
                cs1 = cap_comp.features.shellFeatures.add(csi)
                cs1.name = 'Shell1'
                print("  Shell1 done")
            except:
                # Fallback: cut the interior
                inner_hw = cw_half + C['lipExtension'] + C['capClearance']
                inner_cr = C['lipCornerRadius'] + C['capClearance']
                inner_depth = cap_height - C['capThickness']

                bp = cap_comp.constructionPlanes
                bpi = bp.createInput()
                bpi.setByOffset(cap_comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(cap_bot_z))
                bot_plane = bp.add(bpi)

                inner_sk = cap_comp.sketches.add(bot_plane)
                inner_sk.name = 'ShellCut'
                draw_rect(inner_sk, inner_hw, inner_cr)

                ici = cap_ext.createInput(inner_sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
                ici.setDistanceExtent(False, adsk.core.ValueInput.createByReal(inner_depth))
                cap_ext.add(ici).name = 'Shell1_Cut'
                print("  Shell1 done (cut method)")

        # ─── DOME ───
        dome_hw = cw_half + C['pocketClearance']
        dome_cr = cr + C['pocketClearance']

        # Dome sketch on cap top (Z=0)
        dome_sk = cap_comp.sketches.add(cap_comp.xYConstructionPlane)
        dome_sk.name = 'DomeProfile'
        draw_rect(dome_sk, dome_hw, dome_cr)

        # Extrude dome as new body upward
        dei = cap_ext.createInput(dome_sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        dei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(C['domeHeight']))
        de = cap_ext.add(dei)
        de.name = 'DomeExtrude'

        # Join dome to cap
        cap_body = cap_comp.bRepBodies.item(0)
        dome_body = cap_comp.bRepBodies.item(1)
        tc = adsk.core.ObjectCollection.create()
        tc.add(dome_body)
        ji = cap_comp.features.combineFeatures.createInput(cap_body, tc)
        ji.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        ji.isKeepToolBodies = False
        cap_comp.features.combineFeatures.add(ji).name = 'DomeJoin'

        # Fillet dome top
        cap_body = cap_comp.bRepBodies.item(0)
        dome_top_z = C['domeHeight']
        dome_edges = find_edges_at_z(cap_body, dome_top_z)
        if dome_edges.count > 0:
            dfi = cap_comp.features.filletFeatures.createInput()
            dfi.addConstantRadiusEdgeSet(dome_edges, adsk.core.ValueInput.createByReal(C['domeFilletRadius']), True)
            dfi.isRollingBallCorner = True
            cap_comp.features.filletFeatures.add(dfi).name = 'DomeFillet'
        print("  Dome done")

        # ─── DOME SHELL ───
        # Find the inner ceiling face — it's the flat face just above the skirt interior
        cap_body = cap_comp.bRepBodies.item(0)
        inner_ceiling_z = -cap_height + C['capThickness']
        # Try multiple Z values to find the ceiling face
        ceiling_face = find_face(cap_body, inner_ceiling_z, 1)
        if not ceiling_face:
            # Search all flat faces for the inner ceiling
            for f in cap_body.faces:
                geo = f.geometry
                fbb = f.boundingBox
                if geo.classType() == 'adsk::core::Plane' and geo.normal.z > 0.9:
                    z = fbb.minPoint.z
                    if z < 0 and z > -cap_height and f.area > 10:
                        ceiling_face = f
                        break
        if ceiling_face:
            dsfc = adsk.core.ObjectCollection.create()
            dsfc.add(ceiling_face)
            dsi = cap_comp.features.shellFeatures.createInput(dsfc, False)
            dsi.insideThickness = adsk.core.ValueInput.createByReal(C['capThickness'])
            try:
                cap_comp.features.shellFeatures.add(dsi).name = 'DomeShell'
                print("  DomeShell done")
            except:
                print("  DomeShell skipped (geometry issue)")
        else:
            print("  DomeShell skipped (ceiling face not found)")

        # ─── PARAMETRIC TRIM ───
        # Cut container outer profile through cap skirt
        trim_hw = cw_half
        trim_cr = cr

        trim_plane_input = cap_comp.constructionPlanes.createInput()
        trim_plane_input.setByOffset(cap_comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(cap_bot_z))
        trim_plane = cap_comp.constructionPlanes.add(trim_plane_input)
        trim_plane.name = 'TrimPlane'

        trim_sk = cap_comp.sketches.add(trim_plane)
        trim_sk.name = 'TrimProfile'
        draw_rect(trim_sk, trim_hw, trim_cr)

        # Cut through cap
        tri = cap_ext.createInput(trim_sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
        tri.setDistanceExtent(False, adsk.core.ValueInput.createByReal(C['domeHeight'] + cap_height))
        try:
            cap_ext.add(tri).name = 'ParametricTrim'
            print("  ParametricTrim done")
        except:
            tri2 = cap_ext.createInput(trim_sk.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
            tri2.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-(C['domeHeight'] + cap_height)))
            cap_ext.add(tri2).name = 'ParametricTrim'
            print("  ParametricTrim done (neg)")

        # ─── POSITION CAP ───
        # Cap component: Z=0 (top/dome) down to Z=-cap_height (skirt bottom)
        # Position so cap top (Z=0) is at container top + capThickness
        # The skirt wraps down around the container lip
        cap_body = cap_comp.bRepBodies.item(0)
        cap_body.name = 'CapBody'

        cap_z_offset = C['containerHeight'] + C['lipHeight'] + C['capThickness']
        transform = adsk.core.Matrix3D.create()
        transform.translation = adsk.core.Vector3D.create(0, 0, cap_z_offset)
        cap_occ.transform = transform
        print(f"  Cap positioned at Z={round(cap_z_offset*10,1)}mm")

        # ═══════════════════════════════════════
        # DONE
        # ═══════════════════════════════════════
        app.activeViewport.fit()

        result = {
            "status": "ok",
            "container": f"{CONFIG['containerWidth']}x{CONFIG['containerDepth']}x{CONFIG['containerHeight']}mm",
            "cap_outer": f"{round(cap_hw*20,1)}mm",
            "dome": f"{CONFIG['domeHeight']}mm dome, {CONFIG['domeFilletRadius']}mm fillet",
            "features": {
                "container": ["ContainerExtrude", "BottomFillet", "ContainerShell", "LipExtrude", "LipFillet"],
                "cap": [f.name for f in cap_comp.features]
            }
        }
        print(f"\n{'='*50}")
        print(f"DONE: {result['container']} container with stackable cap")
        print(f"Cap outer: {result['cap_outer']}")
        print(f"Dome: {result['dome']}")
        print(f"{'='*50}")
        print(json.dumps(result, indent=2))

    except:
        print(f"ERROR:\n{traceback.format_exc()}")

run_generator()
