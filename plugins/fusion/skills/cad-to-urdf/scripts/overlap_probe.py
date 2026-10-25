"""overlap_probe.py  —  Fusion-side (run through the fzd-fusion bridge).

The coupling-measurement primitive, CORRECTED. Reports the BOOLEAN-INTERSECTION overlap
volume between two parts (read-only, via TemporaryBRepManager) and optionally axial-sweeps to
find the flush seat. This REPLACES the old min-distance contact test — `measureMinimumDistance`
returns 0 for touching AND interpenetrating solids, so it cannot distinguish a clean seat from
a collision. Overlap volume can.

Run:
    cat overlap_probe.py | ~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json exec -

Parameters — write to /tmp/overlap_params.json first:

    {
      "doc_name": "ur5e_rg2_station",
      "part_a": "quick_changer",   # occurrence fullPathName substring
      "part_b": "rg2 v26",         # occurrence fullPathName substring
      "sweep_axis": [0,-1,0],      # optional: approach axis (unit). If given, sweep part_b along it.
      "sweep_mm": [0.0, 3.0],      # optional: [start,end] displacement to sweep (mm)
      "sweep_step_mm": 0.1
    }

Key facts baked in: assembly occurrences have EMPTY .bRepBodies (recurse into children);
pre-filter by bbox overlap; report per-pair volumes so you can split designed telescoping
(cam/coupler/connector) from real mount-face collision by part number.
"""
import adsk.core, adsk.fusion, traceback, json

PARAMS = "/tmp/overlap_params.json"

def run(context):
    app = adsk.core.Application.get()
    try:
        with open(PARAMS) as f:
            p = json.load(f)
        for i in range(app.documents.count):
            d = app.documents.item(i)
            if d.name.startswith(p["doc_name"]):
                d.activate(); break
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        tbm = adsk.fusion.TemporaryBRepManager.get()

        A = solids_of(root, p["part_a"])
        B = solids_of(root, p["part_b"])
        out = {"ok": True, "a_solids": len(A), "b_solids": len(B)}
        out["overlap_at_current"] = overlap(tbm, A, B, None)

        ax = p.get("sweep_axis")
        if ax:
            lo, hi = p.get("sweep_mm", [0.0, 3.0]); step = p.get("sweep_step_mm", 0.1)
            curve = []; d = lo
            while d <= hi + 1e-9:
                M = adsk.core.Matrix3D.create()
                M.translation = adsk.core.Vector3D.create(ax[0]*d/10.0, ax[1]*d/10.0, ax[2]*d/10.0)
                curve.append({"d_mm": round(d, 3), **overlap(tbm, A, B, M)})
                d += step
            out["sweep_move_b"] = curve
            out["hint"] = "flush seat = smallest d where total_mm3 -> ~0 (that residual is designed telescoping/connector)"
        print(json.dumps(out))
    except Exception:
        print(json.dumps({"ok": False, "err": traceback.format_exc()}))


def solids_of(root, name_sub):
    """Recursively gather solid bodies of the top occurrence(s) matching name_sub."""
    out = []
    def rec(o):
        for k in range(o.bRepBodies.count):
            b = o.bRepBodies.item(k)
            if b.isSolid: out.append(b)
        for j in range(o.childOccurrences.count):
            rec(o.childOccurrences.item(j))
    for i in range(root.occurrences.count):
        oc = root.occurrences.item(i)
        if name_sub in oc.name:
            rec(oc)
    return out


def _bbox_overlap(a, b):
    A = a.boundingBox; B = b.boundingBox
    return (A.minPoint.x <= B.maxPoint.x and A.maxPoint.x >= B.minPoint.x and
            A.minPoint.y <= B.maxPoint.y and A.maxPoint.y >= B.minPoint.y and
            A.minPoint.z <= B.maxPoint.z and A.maxPoint.z >= B.minPoint.z)


def overlap(tbm, A, B, moveB):
    """Total + largest-pair overlap (mm³) between solids A and B; B optionally moved by moveB."""
    total = 0.0; largest = 0.0; pairs = 0
    for bb in B:
        cb0 = tbm.copy(bb)
        if moveB is not None:
            tbm.transform(cb0, moveB)
        for a in A:
            # bbox pre-filter (note: uses un-moved bbox for B when moveB set — cheap approx; the
            # boolean below is exact, so at worst we do a few extra ops)
            if moveB is None and not _bbox_overlap(a, bb):
                continue
            ca = tbm.copy(a); cc = tbm.copy(cb0)
            if tbm.booleanOperation(ca, cc, adsk.fusion.BooleanTypes.IntersectionBooleanType):
                v = ca.volume
                if v and v > 1e-9:
                    mm3 = v * 1000.0
                    total += mm3; largest = max(largest, mm3); pairs += 1
    return {"total_mm3": round(total, 3), "largest_pair_mm3": round(largest, 3), "pairs": pairs}
