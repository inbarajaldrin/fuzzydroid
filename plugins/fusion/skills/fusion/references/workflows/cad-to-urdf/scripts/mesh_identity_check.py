"""mesh_identity_check.py  —  host-side (normal Python venv: numpy, scipy, trimesh).

The q=0 verification primitive. Densely samples points on two STL surfaces and reports the
nearest-neighbour distance distribution between them — the ONLY reliable check that an
exported link mesh is geometrically identical to a static CAD reference at the export pose.

Pin/circle-center, bounding-box, and Z-range checks are NOT sufficient: they pass even when
an asymmetric part is mirrored, rotated about a two-pin line, or left/right swapped. This
compares actual surface geometry.

Deliberately does NOT depend on `rtree` (often unavailable) — nearest-neighbour is done with
scipy.spatial.cKDTree. Optional Kabsch/ICP rigid align (use ONLY to diagnose a pure pose
offset; a healthy export needs NO alignment — the meshes should already coincide in the link
frame).

Usage:
    python mesh_identity_check.py export.stl reference.stl [--samples 200000] [--align]

Healthy: max NN distance in microns (RG2 covers hit ~6e-6 mm). > ~0.03 mm => the mesh is
placed/oriented wrong even if pin centers line up. Report per-link max + 99th percentile.
"""
import sys, argparse, numpy as np
import trimesh
from scipy.spatial import cKDTree


def sample(mesh_path, n):
    m = trimesh.load(mesh_path, force="mesh")
    pts, _ = trimesh.sample.sample_surface(m, n)
    return np.asarray(pts), m


def kabsch(P, Q):
    """Rigid transform (R,t) aligning P onto Q (both Nx3, correspondence by row)."""
    cp, cq = P.mean(0), Q.mean(0)
    H = (P - cp).T @ (Q - cq)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    t = cq - R @ cp
    return R, t


def icp(src, dst, iters=30):
    """Point-to-point ICP: align src onto dst via repeated NN + Kabsch. Diagnostic only."""
    tree = cKDTree(dst)
    P = src.copy()
    R_tot, t_tot = np.eye(3), np.zeros(3)
    for _ in range(iters):
        _, idx = tree.query(P)
        R, t = kabsch(P, dst[idx])
        P = (R @ P.T).T + t
        R_tot = R @ R_tot
        t_tot = R @ t_tot + t
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export_stl")
    ap.add_argument("reference_stl")
    ap.add_argument("--samples", type=int, default=200000)
    ap.add_argument("--align", action="store_true",
                    help="run ICP first (diagnose a pose offset; healthy exports need this OFF)")
    a = ap.parse_args()

    ep, _ = sample(a.export_stl, a.samples)
    rp, _ = sample(a.reference_stl, a.samples)

    if a.align:
        ep = icp(ep, rp)

    # symmetric nearest-neighbour: every export point to nearest reference point
    d_er = cKDTree(rp).query(ep)[0]
    d_re = cKDTree(ep).query(rp)[0]
    d = np.concatenate([d_er, d_re])

    # STL units are mm; report mm
    print(f"max NN distance      : {d.max():.6g} mm")
    print(f"99th percentile      : {np.percentile(d, 99):.6g} mm")
    print(f"mean NN distance     : {d.mean():.6g} mm")
    verdict = "IDENTITY OK" if d.max() < 0.03 else "MISMATCH — mesh placed/oriented wrong"
    print(f"verdict (<0.03 mm)   : {verdict}")
    sys.exit(0 if d.max() < 0.03 else 1)


if __name__ == "__main__":
    main()
