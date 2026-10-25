---
name: add-physics
description: Add and validate colliders and rigid-body physics for CAD parts in Isaac Sim and USD. Choose primitive, hull, or SDF collision geometry; preserve concave mating bores and sockets; author swappable dynamic, kinematic, or fixed physics layers; and verify seating and settling in simulation. Use for physics preparation, SDF colliders, or parts that jitter, sink, or pass through each other. Run before the animation workflow.
---

## Agent host compatibility

This skill works in Claude Code and Codex. Resolve symlinks on this file; the
plugin root is three parent directories above this `SKILL.md`. Use that absolute
root for `plugins/<plugin>/...` examples, regardless of the working directory.
When `CLAUDE_PLUGIN_ROOT` is unavailable, pass the resolved root under that name
to commands that use it. Use the host's equivalent tools for `Bash`, `Read`,
`WebFetch` and user questions. In Codex, `$plugin:skill` invokes the sibling skill
named by a `/plugin:skill` reference. Read sibling `SKILL.md` files directly when
needed; do not assume another host's slash commands exist.

# add-physics (colliders + rigid bodies for CAD assembly)

Author the **collision layer** for CAD assembly parts and validate it with physics: assemble the parts in Isaac Sim, hit play, and confirm every part **settles** — no jitter, no pass-through, seated correctly. The decision of *which* collider a part needs must be made from the CAD itself, so this is judgment + live inspection, not a fixed recipe.

## Requirements (external pipeline deps — real, not bundled)

This skill authors USD but relies on an **external Isaac pipeline** on the machine.
These are genuine dependencies, documented rather than rewritten:

- **`~/Documents/isaacsim/`** — pipeline root. The CAD/USD analysis env runs as
  `cd ~/Documents/isaacsim && uv run python …` (trimesh, cascadio, usd-core, shapely,
  manifold3d). `scripts/author_collision.py` does `sys.path.insert(0, ~/Documents/isaacsim)`
  and imports **`cad_to_usd.box_decompose`** from there — so that module must be importable.
- **`~/Documents/isaacsim/scene_tools/`** — the sim-side module dir the bridge loads inside
  Isaac Kit: `measure_settle.py` (the settle/jitter meter) plus `new_stage`, `load_scene`,
  `add_objects`, `assemble_objects`, `read_state`, `sim_control`. Driven via `bridge.py`.
- **`bridge.py`** at the pipeline root — the omni.kit.mcp bridge front-end
  (`python3 bridge.py sync`, then `bridge.py <tool> '<json>'`). Isaac Sim runs on a GPU box
  (default dual-a4500; `ISAACSIM_HOST` / `ISAACSIM_SSH` override).
- **`aruco-grasp-annotator/utils/mesh_quality.py`** — external repo, used for the
  weld/watertight/manifold mesh QC that root-causes SDF jitter.
- **Downstream skill `/isaacsim:animation`** consumes the `_physics.usd` layers this
  skill emits.

## Operating environment
- Pipeline root: `~/Documents/isaacsim/` (Mac = authoring source of truth). Sync to the sim box with `python3 bridge.py sync`; drive Isaac with `python3 bridge.py <tool> '<json>'`.
- Isaac Sim runs on a GPU box (default dual-a4500; `ISAACSIM_HOST`/`ISAACSIM_SSH` override). The bridge's `run_python` executes on Kit's main thread — so the box needs the synced `scene_tools/` + `assets/` (that's what `sync` is for).
- CAD analysis env (no Fusion — reads the EXPORTED STEP/USD): `cd ~/Documents/isaacsim && uv run python ...` (trimesh, cascadio, usd-core, shapely, manifold3d).
- **Layers per part** (compose, don't bake): geometry `<part>.usd` · **collision `<part>.collision.usda` ← THIS SKILL** · physics (rigid body / mass) · animation (a later, separate skill: `/isaacsim:animation`). Collision is its own swappable layer *because* the whole job is deciding it per part.

## The decision — PRINCIPLES, not a lookup table
Everything you need is queryable live. Read the mesh (`trimesh`: `is_watertight`, `is_convex`, `bounding_box`, cross-`section`s, `volume`), read the USD, and after a play read the sim's per-part velocities and penetration. Reason from those. The one principle that dominates every choice:

> **A collider made of primitives or a convex hull is a UNION — it can only ADD material, never subtract. So it fills any concave cavity.** A part with a mating **bore / socket / slot** that another part seats into therefore CANNOT be a box / hull / convex-decomposition collider — the hole gets filled and the mate becomes impossible. That part needs **SDF** (the mesh as a signed-distance field) or a plain triangle mesh. This is *why* the FMB parts shipped SDF.

**Collider choice is binary — a primitive, or SDF. No convex hull / decomposition.** (Accuracy first: in
this project the sim only has to reveal the *tool-call sequence*; press-fit tolerance is the runtime
tool's job. So the collider must preserve exact CAD dimensions — a convex hull/decomposition
approximates dimensions AND fills concave cavities, failing on both counts.)

1. **Analytic primitive(s)** — a compound of `UsdGeom.Cube` (rectilinear solid → exact box set, e.g. a
   U-slab = **3** boxes: two legs + bridge), or a single `UsdGeom.Cylinder` / `Cone` / `Sphere` /
   `Capsule` for a genuinely round / tapered / ball / capsular shape. **These five (Box, Sphere,
   Capsule, Cylinder, Cone) are the analytic collider set — verified by probing Isaac Sim (each rests on
   the ground, no approximation warning) and the NVIDIA omni_physics docs.** Cheapest, most stable, and
   **dimensionally exact** where the shape really is that primitive. *First choice whenever one fits.*
2. **`sdf`** — **everything else.** Anything not cleanly one of the five primitives — a hex prism, a
   non-rectilinear profile, and especially any concave **mating** feature (bore, socket, thread) — gets
   SDF (`sdfResolution = 256`, `restOffset = 0`), which keeps the exact concave geometry so parts seat.

So the decision reduces to one question per part: **is the shape genuinely one of the five primitives?
→ that primitive. Otherwise → SDF.** (No convex hull / decomposition — they approximate dimensions AND
fill concave cavities, failing the accuracy goal both ways.)

## Author the collision layer
```
uv run python skills/add-physics/scripts/author_collision.py <geom.usd> \
    --tier {box|cylinder|cone|sphere|capsule|compound|recipe|sdf} \
    [--compound-spec c.json | --recipe r.json] [--out <part>_physics.usd] [--sdf-res 256] \
    [--kinematic | --fixed]
```
- Emits **two separate layers** (collision and physics are distinct API sets, so distinct swappable
  layers): `<part>.collision.usda` (references geometry + `PhysicsCollisionAPI` + the collider — **no**
  rigid body) and `<part>_physics.usd` (references the collision layer + the rigid body). `add_objects`
  loads `_physics.usd`, composing **physics → collision → geometry**. (Both `.collision.` and
  `.scene`/`.anim` files are skipped by `add_objects`' object glob — they're composed layers, not
  standalone objects.)
- `box` → `cad_to_usd.box_decompose` → N `UsdGeom.Cube` colliders (compound); `cylinder`/`cone`/`sphere`/
  `capsule` → one fitted primitive shape as a child of the mesh.
- `compound` (`--compound-spec c.json`) → an EXPLICIT set of primitives you hand-specify (box/cylinder/…
  dicts in local metres). For a genuine multi-primitive part with no concave mating feature.
- **`recipe` (`--recipe r.json`) → CAD-RESOLVED mixed collider** — the right tool for a part that is
  *several* primitives fused, some rectilinear and some round. `box_decompose` **explodes into slivers /
  times out on any round feature**, so you feed it ONLY an isolated rectilinear sub-mesh; round features
  are handled separately. Recipe JSON (paths relative to the geom USD):
  `{"box_from":"post.usd", "cylinders":[{type,center,radius,height,axis}], "sdf_from":["bores.usd"], "sdf_res":256}`
  → box_decompose(`box_from`) cubes + explicit `cylinders` (round-convex, e.g. a tenon) + an SDF sub-mesh
  per `sdf_from` (round-CONCAVE mating feature, e.g. socket bores). *Worked example — the FurnitureBench
  square-table leg = box_decompose(pocketed post)=10 cubes + 1 Cylinder tenon; the tabletop =
  box_decompose(tray)=5 cubes + SDF(4 socket bosses ONLY). Isolate the rectilinear vs round sub-geometry
  by CSG from the parametric dims (trimesh box/cylinder booleans) → per-feature sub-USDs.*
- `sdf` → `PhysicsMeshCollisionAPI` `physics:approximation="sdf"` on the mesh + `PhysxSDFMeshCollisionAPI`
  + `physxSDFMeshCollision:sdfResolution` (matches the shipped `data/usd/*.usda` format exactly). Use for
  a *whole* concave part; for a part that is only concave at one feature, prefer `recipe` (SDF that feature
  only, cubes for the rest) — do NOT SDF an entire rectilinear tray just because it has a few bores.
- **Body type — three choices** (the physics layer's rigid-body flavour, orthogonal to the collider tier):
  - **dynamic** (default) — `RigidBodyAPI`; falls + settles under gravity. Every *movable assembly part*.
  - **`--kinematic`** — `RigidBodyAPI` + `physics:kinematicEnabled=true`. **The right pin for a fixed
    fixture / anchor / jig**: it never falls under gravity and forces don't move it, yet it *is* a rigid
    body — so it collides (dynamic parts seat against it) and can be **repositioned or animated** by
    script. This is the standard Isaac way to fix a part in place. Use it for a board fixture, table,
    mounting bracket, or any part the scene treats as fixed. **A part is "fixed" ⇒ kinematic.**
  - **`--fixed`** — collider only, **no** `RigidBodyAPI` → a pure *static* body. Rare; prefer
    `--kinematic` for fixtures (a static body has no rigid body for Isaac tooling / re-posing to act on).
    Note a base *assembly part* resting on the ground needs **neither** flag — it settles dynamically on
    its own (verified: dynamic fmb1 base wander 0.003 mm). `--fixed`/`--kinematic` are for a genuinely
    *fixed fixture*, not for a base that just happens to sit at the bottom.
- Metres-native, `metersPerUnit = 1`. No `MassAPI` (PhysX auto-mass) unless a density is known.

## Validate in sim — the actual test (never skip)
1. `bridge.py sync` → `new_stage` → `load_scene` → `add_objects` → `assemble_objects` (parts at the FINALIZED poses).
2. `bridge.py measure_settle '{"frames":180}'` — plays physics, steps, returns per-part linear + angular velocity and position drift over the tail frames. **Settled** = every part below the velocity threshold with no net drift.
3. Read the numbers and reason:
   - **All settle, poses hold** → collider correct. Done.
   - **A part jitters / vibrates** → FIRST check the mesh is welded + watertight + manifold (`aruco-grasp-annotator/utils/mesh_quality.py`). An SDF built from *unwelded* mesh gets sign-noise at duplicate seams → micro-penetration flips → jitter. This is the usual cause — **fix the geometry, not a physics knob.**
   - **A part sinks / penetrates, or another part passes through it** → either the collider fills a cavity (wrong tier — climb the ladder) OR the assembly ORDER is wrong (a later part placed where an earlier one already sits). Both are informative failures.
   - **A part explodes on play** → initial overlap (poses too tight, or a collider fatter than the geometry).

## Guardrails — what NOT to do
- **Don't** box / hull / convex-decomp a part with a mating bore or socket — the union fills the hole and the mate fails. SDF (or mesh) only for those.
- **Don't** reach for SDF on a plain rectilinear or convex part — a box compound / cylinder / hull is exact AND far cheaper. SDF is the heavy tool, reserved for concave mating features. (The FMB set was initially over-SDF'd, then re-tiered: box for rectilinear, cylinder+hull for hex, SDF only for genuine bores.)
- **Don't** chase jitter with solver iterations / offsets first. Verify the mesh is welded + watertight + manifold — unwelded geometry is the usual jitter source.
- **Don't** trust a sim A/B without confirming the collider actually loaded from disk — a stale cached USD layer silently re-serves the OLD collider (an `SdfLayer.FindOrOpen` cache confound burned a whole box-vs-SDF verdict once). Verify the cooked collider matches the file.
- **Don't** raise `restOffset` to hide penetration — that masks a wrong collider/geometry.
- **Don't** skip the play/settle validation — a collider that looks right statically but jitters or lets parts pass through is wrong.
- **Don't** author in the wrong scale — metres, `metersPerUnit = 1`; a scale mismatch violates PhysX's ≤ 1:100 collider-size rule and destabilizes contacts.

## Why this runs BEFORE /isaacsim:animation
With physics + correct colliders, a wrong assembly ORDER is straight-up rejected: parts can't pass through each other, so an out-of-order insert fails to seat. That is the *same* signal the runtime agent uses to discover the sequence. Lock colliders + settling here first; author motion (the animation skill) only once the physical assembly holds. (An earlier out-of-order FMB layout would have been rejected instantly under physics — which is the point.)

## Tools this skill packages
- `scripts/author_collision.py` — author the collision layer (all tiers), reusing `cad_to_usd.box_decompose`.
- `~/Documents/isaacsim/scene_tools/measure_settle.py` — the sim-side settle/jitter meter (play + per-part velocities).
- Existing `scene_tools`: `new_stage`, `load_scene`, `add_objects`, `assemble_objects`, `read_state`, `sim_control`.
- `references/collision-tiers.md` — NVIDIA approximation grounding + the FMB SDF-256 rationale + the jitter=unwelded-soup root cause.
