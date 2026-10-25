#!/usr/bin/env python3
"""author_collision.py — author the COLLISION and PHYSICS layers for one CAD part, kept SEPARATE.

Two references-overlays on the geometry USD (collision and physics are distinct USD API sets, so they
get distinct swappable layers):
  <part>.collision.usda   references the geometry; adds PhysicsCollisionAPI + the collider(s) ONLY.
  <part>_physics.usd      references the collision layer; adds the rigid body (see body-type flags).
`add_objects` auto-loads `<part>_physics.usd`, which composes physics -> collision -> geometry. Body type:
  default       dynamic   -> RigidBodyAPI; falls + settles under gravity.
  --kinematic   kinematic -> RigidBodyAPI + physics:kinematicEnabled=true; a FIXED fixture/anchor that
                             never falls but still collides and can be repositioned/animated.
  --fixed       static    -> NO rigid body (pure collision geometry, infinite mass). Rare.

Collider = an analytic PRIMITIVE if the shape genuinely is one (Box/Cylinder/Cone/Sphere/Capsule —
verified against Isaac + the NVIDIA docs); a 'compound' set of primitives (--compound-spec) if the part
is several primitives fused (e.g. a cuboid post + a cylinder tenon) with NO concave MATING feature;
otherwise SDF (exact concave geometry — required whenever another part seats into a bore/socket). No
convex hull / decomposition. See the skill's references/collision-tiers.md.

Run in the isaacsim CAD env (reads exported USD; no Fusion):
    cd ~/Documents/isaacsim && uv run python <path>/author_collision.py assets/objects/fmb1/Body2.usd --tier box
"""
import argparse, json, os, sys
import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics, Sdf, Gf, Vt

ISAAC = os.path.expanduser("~/Documents/isaacsim")
sys.path.insert(0, ISAAC)  # cad_to_usd.box_decompose


def find_mesh(stage):
    return next((p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh)), None)


def mesh_arrays(prim):
    m = UsdGeom.Mesh(prim)
    pts = np.array(m.GetPointsAttr().Get())
    cnt = np.array(m.GetFaceVertexCountsAttr().Get()); idx = np.array(m.GetFaceVertexIndicesAttr().Get())
    faces = []; o = 0
    for c in cnt:
        f = idx[o:o + c]; o += c
        for k in range(1, c - 1):
            faces.append([int(f[0]), int(f[k]), int(f[k + 1])])
    return pts, np.array(faces)


def add_api_schemas(prim, names):
    op = prim.GetMetadata("apiSchemas")
    items = list(op.GetAddedOrExplicitItems()) if op else []
    for n in names:
        if n not in items:
            items.append(n)
    newop = Sdf.TokenListOp(); newop.prependedItems = items
    prim.SetMetadata("apiSchemas", newop)


def _read_mesh_usd(path):
    """Read a plain mesh USD -> (points Nx3, triangulated faces Mx3)."""
    s = Usd.Stage.Open(path)
    m = next(p for p in s.Traverse() if p.IsA(UsdGeom.Mesh))
    return mesh_arrays(m)


def _add_sdf_mesh(st, parent_path, i, pts, faces, sdf_res):
    """A collision-only Mesh child carrying its own geometry + SDF approximation (for a concave
    round sub-feature like a socket bore — NOT the whole part)."""
    sm = UsdGeom.Mesh.Define(st, parent_path.AppendChild(f"collider_{i:02d}_sdf"))
    sm.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(pts.astype(np.float32)))
    sm.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(faces), 3, np.int32)))
    sm.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(faces.reshape(-1).astype(np.int32)))
    mn, mx = pts.min(0), pts.max(0)
    sm.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*mn.astype(float)), Gf.Vec3f(*mx.astype(float))]))
    sm.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mp = sm.GetPrim()
    UsdPhysics.CollisionAPI.Apply(mp)
    UsdPhysics.MeshCollisionAPI.Apply(mp).CreateApproximationAttr("sdf")
    add_api_schemas(mp, ["PhysxCollisionAPI", "PhysxSDFMeshCollisionAPI"])
    mp.CreateAttribute("physxSDFMeshCollision:sdfResolution", Sdf.ValueTypeNames.Int, True).Set(sdf_res)
    mp.CreateAttribute("physxCollision:restOffset", Sdf.ValueTypeNames.Float, True).Set(0.0)


def _new_overlay(out, ref_path, root_path):
    """A stage that references `ref_path` at root_path and defaults to it."""
    st = Usd.Stage.CreateNew(out)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    root = st.DefinePrim(root_path)
    root.GetReferences().AddReference(os.path.relpath(ref_path, os.path.dirname(out)))
    st.SetDefaultPrim(root)
    return st


def _add_primitive(st, parent_path, i, spec):
    """Author ONE analytic collider (box|cylinder|cone|capsule|sphere) from a spec dict, in metres.
    spec: {"type","center":[x,y,z], + "size":[sx,sy,sz] (box) | "radius","height","axis" (cyl/cone/capsule) | "radius" (sphere)}"""
    t = spec["type"]
    c = [float(x) for x in spec["center"]]
    if t == "box":
        cube = UsdGeom.Cube.Define(st, parent_path.AppendChild(f"collider_{i:02d}_box"))
        cube.CreateSizeAttr(1.0)
        xf = UsdGeom.Xformable(cube.GetPrim())
        xf.AddTranslateOp().Set(Gf.Vec3d(*c)); xf.AddScaleOp().Set(Gf.Vec3f(*[float(s) for s in spec["size"]]))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        return f"box size={spec['size']}"
    if t == "sphere":
        sph = UsdGeom.Sphere.Define(st, parent_path.AppendChild(f"collider_{i:02d}_sphere"))
        sph.CreateRadiusAttr(float(spec["radius"]))
        UsdGeom.Xformable(sph.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*c))
        UsdPhysics.CollisionAPI.Apply(sph.GetPrim())
        return f"sphere r={spec['radius']}"
    prim_t = {"cone": UsdGeom.Cone, "capsule": UsdGeom.Capsule}.get(t, UsdGeom.Cylinder)
    shp = prim_t.Define(st, parent_path.AppendChild(f"collider_{i:02d}_{t}"))
    shp.CreateRadiusAttr(float(spec["radius"])); shp.CreateHeightAttr(float(spec["height"]))
    shp.CreateAxisAttr(spec.get("axis", "Z").upper())
    UsdGeom.Xformable(shp.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*c))
    UsdPhysics.CollisionAPI.Apply(shp.GetPrim())
    return f"{t} r={spec['radius']} h={spec['height']} axis={spec.get('axis','Z')}"


def author_collision_layer(geom, tier, out, sdf_res, compound_spec=None, recipe=None):
    """Colliders ONLY (no rigid body). Primitives as children of the mesh; SDF on the mesh."""
    gsrc = Usd.Stage.Open(geom)
    gmesh = find_mesh(gsrc)
    if not gmesh:
        sys.exit(f"no mesh in {geom}")
    mesh_path = gmesh.GetPath()                       # /Root/<name>/<name>
    root_path = mesh_path.GetParentPath().GetParentPath()  # /Root
    st = _new_overlay(out, geom, root_path)

    if tier == "recipe":
        # CAD-RESOLVED mixed collider: box_decompose an ISOLATED rectilinear sub-mesh into exact cubes,
        # + explicit primitive(s) for round-convex features (e.g. a cylinder tenon), + an SDF sub-mesh
        # for each round-CONCAVE mating feature (e.g. socket bores). Feed box_decompose only the
        # rectilinear geometry — a round feature explodes it into slivers / times out. Recipe JSON:
        #   {"box_from": "sub.usd", "cylinders": [ {type,center,radius,height,axis} ],
        #    "sdf_from": ["bores.usd", ...], "sdf_res": 256}   (paths relative to the geom USD dir)
        if not recipe:
            sys.exit("--recipe <file.json> required for tier=recipe")
        rec = json.load(open(recipe))
        base = os.path.dirname(os.path.abspath(geom))
        rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
        notes = []; i = 0
        if rec.get("box_from"):
            from cad_to_usd.geometry import box_decompose
            bpts, bfaces = _read_mesh_usd(rel(rec["box_from"]))
            for center, size in box_decompose(bpts, bfaces):
                _add_primitive(st, mesh_path, i, {"type": "box",
                    "center": [float(x) for x in center], "size": [float(x) for x in size]}); i += 1
            notes.append(f"box_decompose({rec['box_from']})={i} cubes")
        for cy in rec.get("cylinders", []):
            notes.append(_add_primitive(st, mesh_path, i, cy)); i += 1
        for sp in rec.get("sdf_from", []):
            spts, sfaces = _read_mesh_usd(rel(sp))
            _add_sdf_mesh(st, mesh_path, i, spts, sfaces, rec.get("sdf_res", sdf_res)); i += 1
            notes.append(f"SDF({sp})")
        note = "recipe: " + "; ".join(notes)
    elif tier == "compound":
        # exact analytic MULTI-primitive collider from an explicit spec (e.g. cuboid post + cylinder
        # tenon). For a genuine compound part that no single primitive fits but that is NOT concave at
        # a MATING feature (concave mating -> SDF). Caller supplies dims in the geometry's local metres.
        if not compound_spec:
            sys.exit("--compound-spec <file.json> required for tier=compound")
        prims = json.load(open(compound_spec))
        notes = [_add_primitive(st, mesh_path, i, p) for i, p in enumerate(prims)]
        note = f"compound = {len(prims)} colliders [{'; '.join(notes)}]"
    elif tier in ("box", "cylinder", "cone", "sphere", "capsule"):
        pts, faces = mesh_arrays(gmesh)
        lo, hi = pts.min(0), pts.max(0); c = (lo + hi) / 2.0; ext = hi - lo
        if tier == "box":
            from cad_to_usd.geometry import box_decompose
            boxes = box_decompose(pts, faces)
            for i, (center, size) in enumerate(boxes):
                cube = UsdGeom.Cube.Define(st, mesh_path.AppendChild(f"collider_{i:02d}"))
                cube.CreateSizeAttr(1.0)
                xf = UsdGeom.Xformable(cube.GetPrim())
                xf.AddTranslateOp().Set(Gf.Vec3d(*[float(x) for x in center]))
                xf.AddScaleOp().Set(Gf.Vec3f(*[float(x) for x in size]))
                UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
            note = f"box compound = {len(boxes)} Cube colliders"
        elif tier == "sphere":
            R = float(np.linalg.norm(pts - c, axis=1).max())
            sph = UsdGeom.Sphere.Define(st, mesh_path.AppendChild("collider_sphere"))
            sph.CreateRadiusAttr(R)
            UsdGeom.Xformable(sph.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*[float(x) for x in c]))
            UsdPhysics.CollisionAPI.Apply(sph.GetPrim())
            note = f"sphere r={R:.4f}"
        else:  # cylinder | cone | capsule
            axis = int(np.argmax(ext)); r = float(min(ext[i] for i in range(3) if i != axis) / 2.0)
            h = float(max(float(ext[axis]) - (2.0 * r if tier == "capsule" else 0.0), 0.0))
            prim_t = {"cone": UsdGeom.Cone, "capsule": UsdGeom.Capsule}.get(tier, UsdGeom.Cylinder)
            shp = prim_t.Define(st, mesh_path.AppendChild(f"collider_{tier}"))
            shp.CreateRadiusAttr(r); shp.CreateHeightAttr(h); shp.CreateAxisAttr("XYZ"[axis])
            UsdGeom.Xformable(shp.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(*[float(x) for x in c]))
            UsdPhysics.CollisionAPI.Apply(shp.GetPrim())
            note = f"{tier} r={r:.4f} h={h:.4f} axis={'XYZ'[axis]}"
    else:  # sdf — exact concave geometry on the mesh prim
        mp = st.OverridePrim(mesh_path).GetPrim()
        UsdPhysics.CollisionAPI.Apply(mp)
        UsdPhysics.MeshCollisionAPI.Apply(mp).CreateApproximationAttr("sdf")
        add_api_schemas(mp, ["PhysxCollisionAPI", "PhysxSDFMeshCollisionAPI"])
        mp.CreateAttribute("physxSDFMeshCollision:sdfResolution", Sdf.ValueTypeNames.Int, True).Set(sdf_res)
        mp.CreateAttribute("physxCollision:restOffset", Sdf.ValueTypeNames.Float, True).Set(0.0)
        note = f"SDF (sdfResolution={sdf_res}, restOffset=0)"
    st.GetRootLayer().Save()
    return mesh_path, note


def author_physics_layer(coll, out, mesh_path, fixed, kinematic):
    """Rigid body over the collision layer. Three body types:
      dynamic   (default)      -> RigidBodyAPI; falls + settles under gravity.
      kinematic (--kinematic)  -> RigidBodyAPI + physics:kinematicEnabled=true; a FIXED anchor that
                                  never falls but still collides and can be repositioned/animated. The
                                  right pin for a fixture (the standard Isaac way to pin a part).
      static    (--fixed)      -> NO RigidBodyAPI; pure collision geometry (infinite mass, unmovable).
    """
    root_path = mesh_path.GetParentPath().GetParentPath()
    st = _new_overlay(out, coll, root_path)
    if not fixed:
        rb = UsdPhysics.RigidBodyAPI.Apply(st.OverridePrim(mesh_path).GetPrim())
        if kinematic:
            rb.CreateKinematicEnabledAttr(True)
    st.GetRootLayer().Save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geom")
    ap.add_argument("--tier", required=True,
                    choices=["box", "cylinder", "cone", "sphere", "capsule", "compound", "recipe", "sdf"],
                    help="single analytic primitive (box/cylinder/cone/sphere/capsule) if it fits; "
                         "'compound' = explicit primitive set (--compound-spec); 'recipe' = CAD-resolved "
                         "box_decompose + cylinders + SDF-sub-meshes (--recipe); else sdf.")
    ap.add_argument("--out", default=None, help="physics-layer path (default <part>_physics.usd)")
    ap.add_argument("--sdf-res", type=int, default=256)
    ap.add_argument("--compound-spec", default=None,
                    help="JSON file: list of primitive dicts (box/cylinder/cone/capsule/sphere) in the "
                         "geometry's LOCAL metres; required for --tier compound.")
    ap.add_argument("--recipe", default=None,
                    help="JSON file: {box_from, cylinders[], sdf_from[], sdf_res}; required for --tier recipe.")
    ap.add_argument("--fixed", action="store_true",
                    help="STATIC collider (NO RigidBodyAPI) — pure collision geometry, infinite mass. Rare.")
    ap.add_argument("--kinematic", action="store_true",
                    help="KINEMATIC rigid body (RigidBodyAPI + physics:kinematicEnabled=true) — a fixed "
                         "anchor/fixture that never falls under gravity but still collides and can be "
                         "repositioned/animated. The right pin for a fixture.")
    a = ap.parse_args()
    if a.fixed and a.kinematic:
        ap.error("--fixed (static, no rigid body) and --kinematic (kinematic rigid body) are mutually exclusive")

    geom = os.path.abspath(a.geom)
    stem = geom.rsplit(".", 1)[0]
    coll_out = stem + ".collision.usda"
    phys_out = a.out or (stem + "_physics.usd")

    mesh_path, note = author_collision_layer(geom, a.tier, coll_out, a.sdf_res, a.compound_spec, a.recipe)
    author_physics_layer(coll_out, phys_out, mesh_path, a.fixed, a.kinematic)
    body = "STATIC (no rigid body)" if a.fixed else ("KINEMATIC (RigidBodyAPI + kinematicEnabled)" if a.kinematic else "RigidBodyAPI (dynamic)")
    print(f"[collision] {os.path.basename(coll_out)}: {note}")
    print(f"[physics]   {os.path.basename(phys_out)}: {body} -> refs collision")


if __name__ == "__main__":
    main()
