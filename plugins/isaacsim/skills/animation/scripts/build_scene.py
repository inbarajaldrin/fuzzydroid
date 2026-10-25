#!/usr/bin/env python3
"""build_scene.py — build the assembled SCENE layer the animation sublayers.

References each part at its SEATED pose + adds dome/key lights. The anim layer overrides the moving
parts' xformOps on top. Reads assembly.json (order + base_part) + poses.json (poses) from the board
dir. By default references the geometry (`<name>.usd`); pass --ref-suffix _physics.usd to reference
the collision/physics layers so you can PLAY the animation with real colliders (see the
/isaacsim:add-physics skill). Run in the CAD env.
"""
import argparse, os, json
from pxr import Usd, UsdGeom, UsdLux, Gf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_dir")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ref-suffix", default=".usd",
                    help="per-part reference: '.usd' (geometry) or '_physics.usd' (with colliders)")
    a = ap.parse_args()

    d = os.path.abspath(a.board_dir); name = os.path.basename(d.rstrip("/"))
    order = json.load(open(f"{d}/assembly.json"))
    poses = {p["name"]: p for p in json.load(open(f"{d}/poses.json"))["parts"]}
    out = a.out or f"{d}/{name}.scene.usda"

    st = Usd.Stage.CreateNew(out)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    world = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(world.GetPrim())
    for n in order["assembly_order"]:
        x = UsdGeom.Xform.Define(st, f"/World/{n}")
        p = poses[n]; t = [v / 1000.0 for v in p["translation_mm"]]; q = p["quat_wxyz"]
        # Reference the part's GEOMETRY usd. For FMB the part name IS the geometry file
        # (Body1 -> Body1.usd); for furniture, several instances (leg1..leg4) SHARE one
        # geometry (square_table_leg.usd), so honor the part's "geometry" field when present.
        geom = p.get("geometry", n)
        x.GetPrim().GetReferences().AddReference(f"./{geom}{a.ref_suffix}")
        x.AddTranslateOp().Set(Gf.Vec3d(*t))
        x.AddOrientOp().Set(Gf.Quatf(q[0], q[1], q[2], q[3]))
    UsdGeom.Xform.Define(st, "/World/Lights")
    UsdLux.DomeLight.Define(st, "/World/Lights/Dome").CreateIntensityAttr(700.0)
    key = UsdLux.DistantLight.Define(st, "/World/Lights/Key")
    key.CreateIntensityAttr(2200.0); key.CreateAngleAttr(1.0)
    UsdGeom.Xformable(key.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(310.0, 0.0, 25.0))
    st.GetRootLayer().Save()
    print(f"[scene] {os.path.basename(out)}: {len(order['assembly_order'])} parts (ref {a.ref_suffix}) at seated poses + lights")


if __name__ == "__main__":
    main()
