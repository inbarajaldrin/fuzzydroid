"""transform_chain.py  —  host-side (normal python + numpy).

Turn a set of WORLD occurrence transforms (read from the Fusion assembly via transform2, in cm,
row-major 4x4) into a URDF-ready report: each part's from-origin pose AND the relative chain
(inv(parent) @ child), as xyz(mm) + rpy(deg, URDF order) + quat(xyzw). This is how you emit the
tf/URDF frame chain for an assembled workstation.

Usage: edit WORLD + CHAIN below (or import and call), then `python transform_chain.py`.

Read the world matrices in Fusion with:  occ.transform2.asArray()   (cm, row-major, list of 16)
"""
import numpy as np

# --- fill these from the assembly (cm, row-major 16) ---
WORLD = {
    "ur5e (arm base)": np.eye(4).flatten().tolist(),
    # "quick_changer": [...16...],
    # "rg2 (gripper)": [...],
    # "camera_mount": [...],
    # "D415 (camera)": [...],
}
# ordered parent->child hops for the relative chain ("world" = identity parent)
CHAIN = [
    ("world", "ur5e (arm base)"),
    # ("ur5e (arm base)", "quick_changer"),
    # ("quick_changer", "rg2 (gripper)"),
    # ("rg2 (gripper)", "camera_mount"),
    # ("camera_mount", "D415 (camera)"),
]


def rpy(R):
    sy = -R[2, 0]
    if abs(sy) < 0.999999:
        p = np.arcsin(sy); r = np.arctan2(R[2, 1], R[2, 2]); y = np.arctan2(R[1, 0], R[0, 0])
    else:
        p = np.pi/2*np.sign(sy); r = np.arctan2(-R[1, 2], R[1, 1]); y = 0.0
    return r, p, y


def quat(R):
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t+1)*2
        return ((R[2,1]-R[1,2])/s, (R[0,2]-R[2,0])/s, (R[1,0]-R[0,1])/s, 0.25*s)
    i = int(np.argmax([R[0,0], R[1,1], R[2,2]]))
    if i == 0:
        s = np.sqrt(1+R[0,0]-R[1,1]-R[2,2])*2
        return (0.25*s, (R[0,1]+R[1,0])/s, (R[0,2]+R[2,0])/s, (R[2,1]-R[1,2])/s)
    if i == 1:
        s = np.sqrt(1-R[0,0]+R[1,1]-R[2,2])*2
        return ((R[0,1]+R[1,0])/s, 0.25*s, (R[1,2]+R[2,1])/s, (R[0,2]-R[2,0])/s)
    s = np.sqrt(1-R[0,0]-R[1,1]+R[2,2])*2
    return ((R[0,2]+R[2,0])/s, (R[1,2]+R[2,1])/s, 0.25*s, (R[1,0]-R[0,1])/s)


def fmt(T):
    xyz = T[:3, 3]*10  # cm -> mm
    r, p, y = rpy(T[:3, :3]); q = quat(T[:3, :3])
    return (f"xyz(mm)=[{xyz[0]:.3f}, {xyz[1]:.3f}, {xyz[2]:.3f}]  "
            f"rpy(deg)=[{np.degrees(r):.2f}, {np.degrees(p):.2f}, {np.degrees(y):.2f}]  "
            f"quat(xyzw)=[{q[0]:.5f}, {q[1]:.5f}, {q[2]:.5f}, {q[3]:.5f}]")


def main():
    W = {k: np.array(v).reshape(4, 4) for k, v in WORLD.items()}
    print("# World placement (from origin)")
    for k, T in W.items():
        print(f"- {k}: {fmt(T)}")
    print("\n# Relative chain (inv(parent) @ child)")
    for par, ch in CHAIN:
        Tp = np.eye(4) if par == "world" else W[par]
        print(f"- {par} -> {ch}: {fmt(np.linalg.inv(Tp) @ W[ch])}")


if __name__ == "__main__":
    main()
