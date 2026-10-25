#!/usr/bin/env python3
"""check_interpenetration.py — the exploded-view animation's NO-PASS-THROUGH gate.

This is a KINEMATIC check, NOT a physics sim: the anim moves each part along authored xform tracks to
its seated target (from poses.json) and stops — no gravity, nothing falls. The gate asks one question
per frame: does any part's mesh actually OVERLAP another's? A part that tunnels through another (e.g. a
leg driven down THROUGH the tabletop instead of inserted from below, or a drawer shoved through the back
wall) shows a deep, sustained interpenetration; a clean mate slides to its seated clearance fit with
~0 overlap.

Two phases, and they do different jobs — this split matters:
  - fcl collision BOOLEAN = pre-filter. A precise mesh-mesh "do these two actually touch/overlap?" test,
    used only to decide WHICH pairs are worth the expensive exact-depth computation. It fires on real
    contact only — unlike a bounding-box test, which for a drawer nested in a cabinet's box would fire
    every frame and run 100x more depth calls.
  - signed-distance DEPTH = the measurement. How far one watertight mesh's points lie INSIDE the other:
    ~0 for any clearance/running fit, large only for a genuine tunnel. (fcl's own contact "depth" is a
    collision-margin artifact that spuriously reads several mm on merely-touching surfaces — NOT used.)
So fcl answers "which pairs," signed-distance answers "how deep," and the gate fires above --threshold-mm.

Geometry is frame-invariant (only each part's transform is animated), so meshes are built ONCE and just
re-transformed per frame. Nested/detailed parts that genuinely touch every frame (a shade over a bulb)
still cost a depth call per frame — use --stride there (a real tunnel spans many frames).

Reads the composed anim stage directly (movers animated, anchor static from the scene sublayer), so it
validates the SAME geometry+poses that get rendered. Run in the CAD env:
    cd ~/Documents/isaacsim && uv run --no-project --with usd-core --with trimesh \
        --with python-fcl --with rtree --with numpy python <skill>/scripts/check_interpenetration.py \
        assets/objects/square_table/square_table.anim.usda
"""
import argparse, os, sys
import numpy as np
from pxr import Usd, UsdGeom, Gf


def _triangulate(counts, indices):
    """Fan-triangulate arbitrary polygon faces -> (M,3) int array."""
    tris, i = [], 0
    for c in counts:
        f = indices[i:i + c]; i += c
        for k in range(1, c - 1):
            tris.append((f[0], f[k], f[k + 1]))
    return np.asarray(tris, dtype=np.int64)


def _part_mesh(prim, xcache, tc):
    """Merge every UsdGeom.Mesh under `prim` into world-space (verts, faces) at timecode tc."""
    import trimesh
    V, F, base = [], [], 0
    for m in Usd.PrimRange(prim):
        if not m.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(m)
        pts = mesh.GetPointsAttr().Get(tc)
        cnts = mesh.GetFaceVertexCountsAttr().Get(tc)
        idx = mesh.GetFaceVertexIndicesAttr().Get(tc)
        if not pts or not cnts:
            continue
        w = xcache.GetLocalToWorldTransform(m)                      # includes the anim override
        P = np.array([[p[0], p[1], p[2]] for p in pts], dtype=np.float64)
        Pw = np.array([w.Transform(Gf.Vec3d(*row)) for row in P])
        tris = _triangulate(list(cnts), list(idx)) + base
        V.append(Pw); F.append(tris); base += len(Pw)
    if not V:
        return None
    return trimesh.Trimesh(vertices=np.vstack(V), faces=np.vstack(F), process=False)


def _rowmat(gf):
    """Gf.Matrix4d -> numpy 4x4 in USD row-vector convention (a point transforms as p_h @ M)."""
    return np.array([[gf[i][j] for j in range(4)] for i in range(4)], dtype=np.float64)


def _apply(M, V):
    """Transform Nx3 points by a row-vector 4x4 (vectorized — no per-point Python loop)."""
    Vh = np.hstack([V, np.ones((len(V), 1))])
    return (Vh @ M)[:, :3]


def _pen_depth_mm(a_mesh, b_mesh, max_pts=4000):
    """Exact interpenetration depth (mm): the deepest any vertex of one mesh lies INSIDE the other.

    signed_distance is +inside / -outside for a watertight mesh, so a mere surface touch (clearance
    fit) -> ~0, while a real overlap -> the tunnel depth. Checked both directions; vertices subsampled
    for speed. Falls back to 0 if a mesh isn't watertight (sign undefined -> don't false-fail)."""
    from trimesh.proximity import signed_distance
    best = 0.0
    for ref, qry in ((a_mesh, b_mesh), (b_mesh, a_mesh)):
        if not ref.is_watertight:
            continue
        pts = qry.vertices
        if len(pts) > max_pts:
            idx = np.linspace(0, len(pts) - 1, max_pts).astype(int)
            pts = pts[idx]
        sd = signed_distance(ref, pts)          # + inside ref
        if len(sd):
            best = max(best, float(sd.max()))
    return best * 1000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("anim", help="path to <asm>.anim.usda")
    ap.add_argument("--threshold-mm", type=float, default=1.0,
                    help="fail if any pair OVERLAPS deeper than this (clearance fits are ~0)")
    ap.add_argument("--stride", type=int, default=1, help="check every Nth frame")
    ap.add_argument("--require-watertight", action="store_true",
                    help="treat any non-watertight part as a FAIL — its overlaps CANNOT be trusted "
                         "(signed-distance has no inside/outside sign), so a clean reading there is unverified")
    a = ap.parse_args()
    from trimesh.collision import CollisionManager

    stage = Usd.Stage.Open(a.anim)
    start, end = int(stage.GetStartTimeCode()), int(stage.GetEndTimeCode())
    world = stage.GetPrimAtPath("/World")
    parts = [p for p in world.GetChildren()
             if p.GetName() != "Lights" and UsdGeom.Imageable(p)]
    names = [p.GetName() for p in parts]
    xcache = UsdGeom.XformCache()

    # Geometry is frame-invariant (only the part's transform is animated). Build each part's mesh ONCE
    # in its own local frame, then per frame just re-transform the cached vertices (vectorized) — this
    # removes the per-frame USD read + Python triangulation that dominated the cost.
    ref = Usd.TimeCode(start)
    xcache.SetTime(ref)
    localmesh, nonwater = {}, []
    for p, nm in zip(parts, names):
        wm = _part_mesh(p, xcache, ref)                            # world mesh at the reference frame
        if wm is None:
            continue
        Mref = _rowmat(xcache.GetLocalToWorldTransform(p))
        wm.vertices = _apply(np.linalg.inv(Mref), wm.vertices)     # -> part-local frame
        localmesh[nm] = wm
        if not wm.is_watertight:                                   # signed-distance sign is undefined here
            nonwater.append(nm)

    worst = {}                                                     # (n1,n2) -> (depth_mm, frame)
    for f in range(start, end + 1, a.stride):
        tc = Usd.TimeCode(f)
        xcache.SetTime(tc)
        # skip invisible parts (hidden before they appear) — they aren't in the scene yet
        cm = CollisionManager()
        meshes, present = {}, []
        for p, nm in zip(parts, names):
            if nm not in localmesh:
                continue
            if UsdGeom.Imageable(p).ComputeVisibility(tc) == UsdGeom.Tokens.invisible:
                continue
            m = localmesh[nm].copy()
            m.vertices = _apply(_rowmat(xcache.GetLocalToWorldTransform(p)), localmesh[nm].vertices)
            cm.add_object(nm, m); meshes[nm] = m; present.append(nm)
        if len(present) < 2:
            continue
        # PRE-FILTER: fcl's precise collision boolean — which pairs actually touch/overlap (not depth).
        hit, pairs = cm.in_collision_internal(return_names=True, return_data=False)
        if not hit:
            continue
        # MEASURE: exact signed-distance depth — 0 for a mere touch, the tunnel depth for a real overlap.
        for n1, n2 in pairs:
            depth_mm = _pen_depth_mm(meshes[n1], meshes[n2])
            key = tuple(sorted((n1, n2)))
            if key not in worst or depth_mm > worst[key][0]:
                worst[key] = (depth_mm, f)

    print(f"[interpen] {os.path.basename(a.anim)}: {len(parts)} parts, frames {start}..{end} "
          f"(stride {a.stride}), threshold {a.threshold_mm} mm (true overlap depth)")
    if not worst:
        print("  no candidate pairs at any frame.")
    fails = []
    for (n1, n2), (depth, fr) in sorted(worst.items(), key=lambda kv: -kv[1][0]):
        flag = "FAIL" if depth > a.threshold_mm else "ok  "
        if depth > a.threshold_mm:
            fails.append((n1, n2, depth, fr))
        print(f"  [{flag}] {n1:>10s} <-> {n2:<10s}  max overlap {depth:6.2f} mm  @ frame {fr}")
    # A non-watertight part has NO inside/outside sign, so _pen_depth_mm skips it as a reference and can
    # read a false 0 — a clean result there is UNVERIFIED, not confirmed. Never let that pass silently.
    if nonwater:
        print(f"  [WARN] NON-WATERTIGHT parts: {', '.join(nonwater)} — signed-distance sign is undefined, "
              f"so any pair involving them is UNVERIFIED (a real overlap could read 0). Fix the mesh "
              f"(usually a STEP->OpenCASCADE tessellation defect at pockets-on-curves; re-tessellate the "
              f"same solid via Fusion's STL exporter, shape-preserving), then re-run.")
    verdict = "FAIL" if fails or (a.require_watertight and nonwater) else "PASS"
    note = ""
    if verdict == "FAIL" and fails:
        note = f" ({len(fails)} pair(s) tunnel past {a.threshold_mm} mm)"
    elif verdict == "FAIL":
        note = f" (--require-watertight: {len(nonwater)} non-watertight part(s))"
    elif nonwater:
        note = f" — but UNVERIFIED for {len(nonwater)} non-watertight part(s); treat as provisional"
    print(f"  => {verdict}{note}")
    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
