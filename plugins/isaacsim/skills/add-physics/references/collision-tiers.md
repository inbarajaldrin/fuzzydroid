# Collider tiers — NVIDIA grounding + the FMB history

Distilled from NVIDIA's PhysX/USD collision docs and the FMB authoring history so the skill is self-contained.

## The ladder (NVIDIA: primitives first)
NVIDIA omni_physics collision authoring, verbatim principle:
> *"Primitive colliders (Sphere, Capsule, Box, Plane) are highly efficient and should be the first choice if they can adequately approximate the shape of the object being simulated."*

**This project uses only two options: an analytic primitive, or SDF. No convex hull / decomposition, no
triangle-mesh** — accuracy-first (the sim only reveals the tool-call sequence; press-fit is the runtime
tool's job), and hull/decomp both approximate dimensions AND fill concave cavities.

The analytic collider set — **verified by probing Isaac Sim (each rests on the ground, no approximation
warning) AND the NVIDIA docs**:

| Option | Token / prim | Fits | Notes |
|---|---|---|---|
| **primitive** | `UsdGeom.Cube` (compound), `Cylinder`, `Cone`, `Sphere`, `Capsule` | shape genuinely IS that primitive (rectilinear → box set; round prism → cylinder; ball → sphere; …) | cheapest, most stable, **no cooking**, CPU+GPU, dimensionally exact. A union of `Cube`s is NVIDIA's preferred way to collide a boxy part. |
| **`sdf`** | `sdf` (`PhysxSDFMeshCollisionAPI`) | **everything else** — hex prisms, non-rectilinear profiles, and any concave **mating** feature (bore/socket/thread) | NVIDIA: *"for dynamic rigid bodies that require high-detail triangle meshes… e.g. robotic assembly."* Keeps exact concave geometry so parts seat. `sdfResolution=256`, `restOffset=0`. |

(`convexHull` / `convexDecomposition` / `boundingCube` / `none` / `meshSimplification` exist in USD but
are **not used here** — they either approximate or are static-only.)

## The dominating principle (why FMB used SDF)
A collider from primitives or a convex hull is a **UNION → it can only ADD material, never subtract**, so it fills any concave cavity. A bore/socket a peg mates into cannot be a box/hull/decomp collider — the hole gets filled, the peg can't enter. FMB note recorded in-file:
> *"SDF kept for seating; convexHull/decomp unseat parts. quiet at sdf-256."*
> "A convex hull/decomposition rounds off the concave sockets, so a peg can't sit in a hole (the collider fills the hole). SDF preserves the true concave geometry, so parts seat."

## FMB re-tiering (don't over-SDF)
"Everything complex → SDF" was later corrected. The right per-part split:
- **rectilinear** (U-slabs, lines, base plates) → **box compound** (exact).
- **hex prisms** → native **Cylinder + convexHull** (exact).
- **SDF reserved** only for genuine bores / round sockets (e.g. `inverted_u_brown` two Ø13.3 bores; `base2`/`base3` round-socket boards).
Box vs SDF was **runtime-neutral at FMB scale** (cook 1.07 vs 1.06 s; step 2.86 vs 2.85 ms) once the collider was **verified-loaded** (an earlier "box insufficient → SDF" verdict was retracted as a stale-cached-layer confound).

## SDF settings (the shipped `data/usd/*.usda` format)
```
apiSchemas = ["MaterialBindingAPI","PhysicsRigidBodyAPI","PhysicsCollisionAPI",
              "PhysicsMeshCollisionAPI","PhysxCollisionAPI","PhysxSDFMeshCollisionAPI"]
uniform token physics:approximation = "sdf"
bool  physics:collisionEnabled  = 1
bool  physics:rigidBodyEnabled  = 1
custom int physxSDFMeshCollision:sdfResolution = 256
```
- **`sdfResolution = 256`** → longest-axis cell ~0.49 mm; for a Ø13.3 bore the wall error is sub-0.5 mm vs a 1.4 mm radial peg clearance (~3× margin). Bump to 512 (~0.25 mm) **only if the runner reports the peg catching on the wall** — it doubles cook time/memory for no gain otherwise.
- `restOffset = 0.0` (via `PhysxCollisionAPI`); `contactOffset` left at PhysX auto default.
- No `MassAPI` → PhysX auto-mass. (Offline `_physics` overlays that DID set mass used PLA density 1240, friction 0.4/0.35, restitution 0.15; the earlier in-app path used "tenga-like" friction 5.0/5.0, restitution 0.1.)

## Jitter is (almost always) geometry, not a knob
> *"Old committed .usd = welded, watertight… the stale .usda = unwelded soup. An SDF built from unwelded soup gets sign-noise at the duplicated seams → micro-penetration flips → jitter."* → *"welding/watertight was the whole game."*

So when a part vibrates at rest: **check the mesh is welded + watertight + manifold first** (`utils/mesh_quality.py`). Only after that consider `solverPositionIterationCount` (Isaac default ~16, raise for a tight socket) — but it was rarely the fix. Never mask penetration with `restOffset`.

## Verified-load (don't A/B a stale collider)
Kit caches USD layers (`SdfLayer.FindOrOpen`). After re-authoring a collider, prove the *cooked* collider in the running sim matches the file (e.g. an `omni.physx` overlap probe) before trusting any seat/settle/jitter result — a cached layer will silently serve the old collider and invalidate the comparison.

## Sources
- NVIDIA omni_physics — collision authoring: `docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/rigid_bodies_articulations/collision.html`
- Isaac Sim — static collision: `docs.isaacsim.omniverse.nvidia.com/latest/physics/physics_static_collision.html`
- FMB authoring history (Mac sessions): `2cad4df2` (SDF-vs-convex rationale + jitter=unwelded root cause), `02a07d74` (box-vs-SDF A/B, resolution 256-vs-512, re-tiering), `74882779` ("keep SDF-256"). Canonical in-app authoring pair in `aruco-grasp-annotator/utils/`: `set_object_physics_isaacsim.py` then `set_sdf_collider_isaacsim.py`.
