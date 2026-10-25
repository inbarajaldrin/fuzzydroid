#!/usr/bin/env python3
"""author_anim.py — author the non-baked ANIMATION layer for an assembly from a motion spec.

Sublayers the assembly's scene and writes time-sampled xformOp:translate + xformOp:orient (+ optional
visibility) on the moving part(s). The MOTION (keyframes) is discovered upstream — by hand, from a
parametric trajectory, or extracted from an HTML/JS viewer (see references/motion-discovery.md) — and
this script AUTHORS it into USD. Motion lives ONLY in this layer; delete it and the geometry/scene are
untouched. `loop` wraps time with a triangle so frame 0 == frame N (seamless).

Motion spec (JSON):
{
  "assembly": "bayonet-lock",
  "scene": "bayonet-lock.scene.usda",         // sublayered; path relative to the spec/out dir
  "fps": 24, "frames": 96, "loop": true,
  "parts": [
    {"name": "plug", "keyframes": [
        {"t": 0.0, "translate_mm": [0,0,65], "quat_wxyz": [1,0,0,0], "visible": true},
        {"t": 0.5, "translate_mm": [0,0,13]},                  // carry quat from prev
        {"t": 1.0, "quat_wxyz": [0.9397,0,0,0.3420]}           // +40deg about Z; carry pos
    ]}
  ]
}
Keyframes are on t in [0,1]; a missing translate_mm/quat_wxyz/visible carries from the previous
keyframe. translate is mm (converted to metres). quat is wxyz. `visible` gives appear/disappear for
sequential builds. Run in the CAD env:
    cd ~/Documents/isaacsim && uv run python <path>/author_anim.py <motion.json>
"""
import argparse, os, json
import numpy as np
from pxr import Usd, UsdGeom, Gf, Sdf


def slerp(q0, q1, u):                       # wxyz shortest-arc
    q0 = np.array(q0, float); q1 = np.array(q1, float)
    d = float(np.dot(q0, q1))
    if d < 0:
        q1 = -q1; d = -d
    if d > 0.9995:
        q = q0 + u * (q1 - q0)
    else:
        th = np.arccos(np.clip(d, -1, 1))
        q = (np.sin((1 - u) * th) * q0 + np.sin(u * th) * q1) / np.sin(th)
    return q / np.linalg.norm(q)


def _full(keyframes):
    """Sorted keyframes with carry-forward of missing pos/quat/visible."""
    pos, quat, vis = [0, 0, 0], [1, 0, 0, 0], True
    out = []
    for k in sorted(keyframes, key=lambda k: k["t"]):
        pos = k.get("translate_mm", pos); quat = k.get("quat_wxyz", quat); vis = k.get("visible", vis)
        out.append((float(k["t"]), np.array(pos, float), np.array(quat, float), bool(vis)))
    return out


def sample(full, u):
    if u <= full[0][0]:
        return full[0][1], full[0][2], full[0][3]
    if u >= full[-1][0]:
        return full[-1][1], full[-1][2], full[-1][3]
    for i in range(len(full) - 1):
        t0, p0, q0, v0 = full[i]; t1, p1, q1, v1 = full[i + 1]
        if t0 <= u <= t1:
            a = (u - t0) / (t1 - t0) if t1 > t0 else 0.0
            return p0 + a * (p1 - p0), slerp(q0, q1, a), v0     # visibility steps at segment start
    return full[-1][1], full[-1][2], full[-1][3]


def triangle(u):
    return 2 * u if u < 0.5 else 2 * (1 - u)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    spec = json.load(open(a.spec))
    d = os.path.dirname(os.path.abspath(a.spec))
    out = a.out or os.path.join(d, spec["assembly"] + ".anim.usda")
    fps = int(spec.get("fps", 24)); nf = int(spec.get("frames", 96)); loop = bool(spec.get("loop", True))

    anim = Usd.Stage.CreateNew(out)
    anim.GetRootLayer().subLayerPaths = [os.path.relpath(os.path.join(d, spec["scene"]), os.path.dirname(out))]
    anim.SetStartTimeCode(0); anim.SetEndTimeCode(nf - 1)
    anim.SetTimeCodesPerSecond(fps); anim.SetFramesPerSecond(fps)
    # Match the sublayered scene's up-axis on THIS layer too. Without it the anim root
    # defaults to Y (the scene's Z opinion does not compose up), so downstream tools /
    # cameras that read the anim's own upAxis render a Z-up asset tipped on its side.
    scene_up = UsdGeom.GetStageUpAxis(Usd.Stage.Open(os.path.join(d, spec["scene"]))) or UsdGeom.Tokens.z
    UsdGeom.SetStageUpAxis(anim, scene_up)

    for part in spec["parts"]:
        full = _full(part["keyframes"])
        over = anim.OverridePrim(f"/World/{part['name']}")
        tr = over.CreateAttribute("xformOp:translate", Sdf.ValueTypeNames.Double3)
        orr = over.CreateAttribute("xformOp:orient", Sdf.ValueTypeNames.Quatf)
        vis = over.CreateAttribute("visibility", Sdf.ValueTypeNames.Token)
        for f in range(nf):
            u = f / (nf - 1)
            u = triangle(u) if loop else u
            p, q, v = sample(full, u)
            tc = Usd.TimeCode(f)
            tr.Set(Gf.Vec3d(float(p[0]) / 1000.0, float(p[1]) / 1000.0, float(p[2]) / 1000.0), tc)
            orr.Set(Gf.Quatf(float(q[0]), float(q[1]), float(q[2]), float(q[3])), tc)
            vis.Set("inherited" if v else "invisible", tc)
    anim.GetRootLayer().Save()
    movers = ", ".join(p["name"] for p in spec["parts"])
    print(f"[anim] {os.path.basename(out)}: {len(spec['parts'])} mover(s) [{movers}], {nf}f @ {fps}fps, loop={loop}")
    print(f"  scene sublayer: {spec['scene']}  ->  {out}")


if __name__ == "__main__":
    main()
