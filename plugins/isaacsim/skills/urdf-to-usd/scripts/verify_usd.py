#!/usr/bin/env python3
"""Headless USD articulation audit — run after any URDF->USD conversion.
Run inside the Isaac Sim python env:  python verify_usd.py /path/to/robot.usd
Prints joint/body/articulation counts; exit code 1 if no articulation root.

FIELD NOTES (each one cost real debugging time):
  - print() after SimulationApp starts NEEDS flush=True — Kit teardown drops
    unflushed stdout, making a successful run look silent.
  - run from a CLEAN cwd (never /tmp): stray stdlib-shadowing files there
    (e.g. /tmp/inspect.py) break the kernel bootstrap with unrelated errors.
  - meshes usually count 0: the importer makes them instanceable and a default
    Usd.Stage traverse skips instance internals. Check folder size instead.
"""
import sys

USD = sys.argv[1] if len(sys.argv) > 1 else None
if not USD:
    print("usage: python verify_usd.py <robot.usd>"); sys.exit(2)

from isaacsim import SimulationApp
sim = SimulationApp({"headless": True})
from pxr import Usd, UsdPhysics

s = Usd.Stage.Open(USD)
joints = {"Prismatic": 0, "Revolute": 0, "Spherical": 0, "Fixed": 0}
bodies = 0
for p in s.Traverse():
    t = p.GetTypeName()
    for k in joints:
        if t == f"Physics{k}Joint": joints[k] += 1
    if p.HasAPI(UsdPhysics.RigidBodyAPI): bodies += 1
roots = [p.GetPath().pathString for p in s.Traverse()
         if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
dp = s.GetDefaultPrim()
print("JOINTS:", joints, flush=True)
print("RIGID BODIES:", bodies, flush=True)
print("ARTICULATION ROOTS:", roots, flush=True)
print("DEFAULT PRIM:", dp.GetPath().pathString if dp else "NONE  <-- references will "
      "compose HOLLOW via add_reference_to_stage; use AddReference(path, src_prim)", flush=True)
sim.close()
sys.exit(0 if roots else 1)
