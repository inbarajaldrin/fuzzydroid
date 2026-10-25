#!/usr/bin/env python3
"""sequential_motion.py — generate a SEQUENTIAL-ASSEMBLY motion spec for a board.

The default motion for a multi-part board (FMB, furniture): the anchor (assembly_order[0]) stays put;
each following part is hidden until its turn, then appears at an approach height and drops into its
seated pose, one at a time in assembly order. With loop=true (author_anim wraps time with a triangle),
the board assembles forward then disassembles in reverse — a seamless cycle. This is the discovered
"motion" for a stacking/insertion assembly; hand the output to author_anim.py.

Reads assembly.json (order + base_part) + poses.json (seated poses). Run in the CAD env:
    uv run python sequential_motion.py assets/objects/fmb1 --lift-mm 70
    uv run python author_anim.py assets/objects/fmb1/fmb1.motion.json
"""
import argparse, os, json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_dir")
    ap.add_argument("--lift-mm", type=float, default=70.0,
                    help="approach offset each part travels through (signed; along --axis)")
    ap.add_argument("--axis", choices=["x", "y", "z"], default="z",
                    help="mate/insertion axis the parts explode along and converge in "
                         "(z = vertical drop/rise; x/y = horizontal slide, e.g. a drawer). "
                         "Ignored when --mate-vec is given.")
    ap.add_argument("--mate-vec", default=None,
                    help="arbitrary 3D mate/insertion direction 'x,y,z' (need not be a unit "
                         "vector; it is normalized). Parts explode along +this and seat along "
                         "-this. Use for a TILTED insertion axis, e.g. a duct whose parts seat "
                         "along a 30deg-off-vertical axis: --mate-vec 0.5,0,0.866. Overrides --axis.")
    ap.add_argument("--offset-mm", type=float, default=None,
                    help="explode distance along the mate axis (signed). Defaults to --lift-mm. "
                         "NEGATIVE = start on the -axis side and converge toward +axis "
                         "(e.g. a drawer that opens toward -Y inserts toward +Y: --axis y --offset-mm -90)")
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    d = os.path.abspath(a.board_dir); name = os.path.basename(d.rstrip("/"))
    order = json.load(open(f"{d}/assembly.json"))
    poses = {p["name"]: p for p in json.load(open(f"{d}/poses.json"))["parts"]}
    anchor = order["base_part"]; seq = order["assembly_order"]
    movers = [n for n in seq if n != anchor]; m = len(movers)
    off = a.offset_mm if a.offset_mm is not None else a.lift_mm

    if a.mate_vec is not None:
        v = [float(x) for x in a.mate_vec.split(",")]
        n2 = (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5 or 1.0
        unit = [c / n2 for c in v]                          # explode along +unit, seat along -unit
        mate_desc = f"vec({a.mate_vec})"
    else:
        ax = {"x": 0, "y": 1, "z": 2}[a.axis]
        unit = [1.0 if i == ax else 0.0 for i in range(3)]
        mate_desc = a.axis

    parts = []
    for k, n in enumerate(movers):
        t = poses[n]["translation_mm"]; q = poses[n]["quat_wxyz"]
        appr = [t[i] + off * unit[i] for i in range(3)]       # exploded start, offset along the mate axis
        w0, w1 = k / m, (k + 1) / m                       # this part's slice of assemble-progress
        parts.append({"name": n, "mate_dir": [round(c, 6) for c in unit], "keyframes": [
            {"t": 0.0, "translate_mm": appr, "quat_wxyz": q, "visible": False},   # hidden, waiting
            {"t": round(w0, 4), "translate_mm": appr, "quat_wxyz": q, "visible": True},   # appears aloft
            {"t": round(w1, 4), "translate_mm": list(t), "quat_wxyz": q, "visible": True},  # dropped, seated
            {"t": 1.0, "translate_mm": list(t), "quat_wxyz": q, "visible": True},
        ]})

    spec = {"assembly": name, "scene": f"{name}.scene.usda", "fps": a.fps, "frames": a.frames,
            "loop": True, "mode": "sequential-assembly", "anchor": anchor,
            "mate_axis": mate_desc, "explode_mm": off, "parts": parts}
    out = a.out or f"{d}/{name}.motion.json"
    json.dump(spec, open(out, "w"), indent=1)
    print(f"[motion] {os.path.basename(out)}: sequential — anchor {anchor} static, {m} movers "
          f"converge along {mate_desc} (explode {off:+.0f} mm) in order {movers}")


if __name__ == "__main__":
    main()
