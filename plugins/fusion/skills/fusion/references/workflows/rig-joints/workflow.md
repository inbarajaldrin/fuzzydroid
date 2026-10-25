> Internal workflow loaded by the main skill. The plugin root comes from
> that skill. Resolve this workflow's `references/`, `scripts/`, and
> `evals/` paths relative to this directory.

# Rig Joints — CAD joint authoring in Fusion 360 via fzd-fusion

Turn an inert CAD import into an articulated assembly whose joints drive correctly,
whose frames match a chosen convention, and whose meshes can be exported per link.
Every rule in here was paid for with a real failure; the *why* is stated so you can
adapt rather than cargo-cult.

## Prerequisites

- fuzzydroid fusion plugin installed; bridge alive: `~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json ping`.
- All Fusion work goes through `cat script.py | fzd-fusion --json exec -`. Never printf scripts
  containing `%` (printf eats format specifiers) — write to a file and `cat` it.
- Multiple documents may be open. **Begin every exec by activating your document by name**
  (iterate `app.documents`, `.activate()`) — the active tab can change under you (the user has hands too).
- Fusion API lengths are **cm**, angles radians. STL export is **mm**. URDF is meters. Convert at boundaries.

## Route by mechanism

The Ten Laws below are the shared foundation — read them regardless. Then jump to the
reference for the mechanism you're rigging. Each provides a general method and
the mechanism-specific API traps.

| Your mechanism | Read |
|---|---|
| Serial robotic arm — registration, circle-pair revolutes, limits, drive-sign calibration | `references/rig-robotic-arm.md` |
| Four-bar or parallelogram gripper — pivot fingerprints, motion links, drive-to-model mapping | `references/rig-4-bar-parallelogram.md` |
| Drag chain or repeated modular links — adjacency discovery, gated joints, calibrated pose engine | `references/drag-chain/rig-drag-chain.md` |

Prismatic/slider axes and multi-part moving links (a 7th axis, a gantry) are covered in
`references/slider-and-chain-joints.md`.

## The Ten Laws (violate these and the assembly will lie to you or explode)

### 1. Only face/edge geometry reads are live
`face.geometry` / `edge.geometry` through assembly-context proxies update after joint drives.
`occurrence.boundingBox`, `body.boundingBox`, and **vertex proxies are stale caches** — they
report poses from minutes ago and will send you chasing phantom bugs (or hide real ones).
Measure everything from cylinder faces, plane faces, and circle edges. A circle EDGE's center
is an exact geometric point — the best possible landmark. A cylinder/plane's `origin` is an
*arbitrary anchor* on the surface — fine for axis direction and axis-line position, unreliable
as a correspondence point between native and proxy space.

### 2. Switch to parametric BEFORE moving anything
`occurrence.transform2` edits made in direct-modeling mode are **silently discarded** when you
later set `designType = ParametricDesignType`. Order: import → parametric → transforms
(+ `design.snapshots.add()` after each batch) → ground → joints.

### 3. API-created component groups are not rigid
`occurrences.addNewComponent()` + `moveToComponent()` gives you a tidy tree, but the joint
solver treats each nested child independently — drive a joint and one body leaves its siblings
behind. Make each link a **rigid group** (`rootComponent.rigidGroups.add(coll, True)`).
If rigid-group creation is rejected ("joint in system exists"), test empirically whether the
rigidity is actually present before fighting it — the collection can read empty while the
constraint still works.

### 4. Use REGULAR joints, not as-built, for revolutes
As-built revolute joints rotate about a **permuted pivot** (the geometry origin's z leaks into
the pivot's y — a real API bug): parts orbit instead of spinning, i.e., the "explosion".
Regular joints (`rootComponent.joints.add`) with geometry on BOTH parts maintain the connection
by construction. As-built is fine for RIGID welds (no axis to permute).

### 5. Joint geometry: coincident circle pairs; fallbacks in order
Best: a circle edge on each part, coaxial, same position (mating rims) —
`JointGeometry.createByCurve(edge, CenterKeyPoint)` on both. Cylindrical faces need
`MiddleKeyPoint` and their axial anchor is unreliable. If one part has NO circular geometry at
the pivot (clamped shafts, spline bores): if the part is modeled in its own pivot frame
(check `nativeObject` coordinates), use `JointGeometry.createByPoint(component.originConstructionPoint
.createForAssemblyContext(occ))`; else create a JointOrigin with computed offsets.

### 6. Gate every joint creation with measurement, and gate the RIGHT thing
The snap aligns full frames (origin + Z + X). The X-alignment parks the joint's zero at the
CAD's as-modeled pose, which is rarely your target pose, so creation MOVES the child: a rotation
about the axis, a 180° flip (anti-parallel circle normals), an axial slide (mismatched anchor
heights) — or all three. Compensate at creation with `JointInput.angle`, `.isFlipped`, `.offset`.
You cannot predict the signs; **iterate**: create → measure child displacement → delete
(deletion restores the pre-snap pose) → recreate with compensation → repeat until clean.
Measure the CHILD'S GEOMETRY (a distal landmark circle), not the group occurrence transform —
snaps can move a nested child while the group transform stays identity. And check the **axial
(z) component** too: a revolute that's laterally perfect can still be slid along its own axis,
which is invisible to XY-only checks and invisible to kinematics (z-invariant mechanisms) but
poisons every exported mesh. `joint.offset.value` is editable after creation for axial fixes.

### 7. Closed kinematic loops freeze the solver — use Motion Links
A planar 4-bar closed with 4 revolutes is over-constrained in Fusion's 3D solver
(4×5 constraints > 3×6 DOF): values store but geometry freezes. Leave the loop OPEN (3 joints)
and add **Motion Links** (`rootComponent.motionLinks`) mirroring the mechanism's coupling —
exactly like URDF `<mimic>`. Determine `isReversed` empirically per link: drive a little and
measure loop-closure error (pivot coincidence between the two open ends); pick the sign that
keeps it ~0. Do this AFTER rigid groups exist, or every sign will measure identically (and lie).

### 8. Limits: don't enable them on full-turn joints at all
Three separate traps, all verified: (a) values outside ±2π are **silently rejected**, leaving
enabled limits at min=max=0 which clamp all drives to zero; (b) Fusion **normalizes stored limit
angles mod 2π** (−2π+ε reads back as +0.0001) — and the normalized range is then enforced
LITERALLY, so a "full circle" limit of [0.0001, 6.2831] **blocks any drive through zero** (the
mechanism reads as mysteriously stuck while one differently-limited joint still moves); (c) limits
only behave when the span is genuinely restrictive and fits inside ±2π un-wrapped (e.g. elbow ±π —
worked perfectly). Rule: enable limits ONLY for joints with real sub-2π restrictions, centered on
the joint's current Fusion zero; leave free-turning joints unlimited and keep the authoritative
ranges in the URDF.

### 9. Drives: doEvents, small steps, and know your zero mapping
Set `RevoluteJointMotion.rotationValue` then `adsk.doEvents()`. Large jumps (≳0.5 rad in
loaded mechanisms) can fail silently — the value reverts; approach in steps. Drive values
**persist through save/reopen** — the file reopens at the pose you saved, so park the canonical
pose BEFORE the final save, and document the Fusion-q ↔ convention-θ mapping
(e.g., `θ_urdf = θ_frozen − q_fusion`). Ground the base BEFORE the first drive or the whole robot walks.

### 10. Mesh export is always native component space — bake world by copying
`exportManager.createSTLExportOptions(entity, path)` ignores assembly context for occurrences
AND body proxies. The reliable recipe: create a temp component occurrence at root (identity),
`body.copyToComponent(tmpOcc)` (copies land at WORLD position), export the copy, delete it.
~1–2 s per body; run long batches with a generous timeout. Post-process into link frames
(subtract link origin, rotate by link orientation at the exported pose, mm→m) with trimesh.

## Workflow

1. **Import & inventory** — `importManager.createSTEPImportOptions` → new doc. Dump the
   occurrence tree with body counts; STEP assemblies keep IDs, flattened ones give `Body1..N`.
2. **Identify links** — fingerprint parts by pivot-hole membership (circle edges near expected
   axes). Resolve hole-less leftovers by which link a part actually MOVES with, not by touch:
   `measureManager.measureMinimumDistance` reads 0.0 for touching AND interpenetrating solids,
   so it cannot tell a rigid mate from a mere contact. Use a boolean-intersection overlap test
   (`../cad-to-urdf/workflow.md` `scripts/overlap_probe.py`) and confirm membership with a kinematic
   sweep — mark the candidate fastener pair and check it stays coincident across the driven
   stroke; the link whose fastener tracks the part owns it. (Min-distance is still fine for the
   different question of running clearance between moving neighbours: ~0.1 mm is a healthy gap.)
   A reference URDF's joint origins tell you where to look; without one, find hinge axes as
   coaxial cylinder clusters shared by exactly two part-sets.
3. **Group** — one component per link, named per convention (URDF link names when available);
   `base_link` at root is required by the plugin's URDF exporter. Rigid-group each (Law 3).
4. **Align frames** — decide the design-origin convention (URDF base frame; else: base mounting
   face = origin, Z-up or +X-approach). Measure current axis lines from cylinders, solve the
   corrective transform numerically OUTSIDE Fusion (Python/numpy — axis-line matching, or exploit
   a known shipped pose like UR's home), apply via `transform2` + snapshot (Law 2). Verify by
   re-measuring axes against targets to sub-0.1 mm.
5. **Joints** — proximal→distal, gated (Laws 4–6). Name joints per convention.
6. **Couple & limit** — motion links for loops/mimics (Law 7); limits (Law 8).
7. **Validate** — drive a sweep; check every joint's mating geometry stays coaxial; if a
   kinematic model exists (URDF FK, gripper width formula), compare numbers — a rigged RG2
   matched its analytic width model within 0.08 mm across the full stroke; expect that grade.
   Audit EVERY body's world position (via the Law-10 copy-export bounds) once — this catches
   axial slides and stale-cache casualties that spot checks miss.
8. **Save & export** — `saveAs` into the target Fusion folder; export F3D/STEP; per-link meshes
   via Law 10.

## Validation — jog the rig as the acceptance test

A rig is "done" when it drives correctly from an interface, not when the script exits.
The acceptance test is the robot-jog palette: open the rigged design and drive its
joints / poses / gripper from the panel (or its JSON API), confirming every joint moves
the right parts by the right amount with no explosion or freeze. See the `fusion` skill's
`references/robot-jog.md` (UR5e + RG2 profiles are bundled; assemblies match multiple
profiles → merged sections). To build a jog/validation panel for a NEW mechanism the
bundled profiles don't cover, use `../create-palette/workflow.md`.

## References

- `references/rig-robotic-arm.md` — serial-arm route: kinematic fingerprint, global
  registration solve, gated circle-pair revolutes, limits, drive-sign calibration.
- `references/rig-4-bar-parallelogram.md` — gripper-linkage route: pivot fingerprinting,
  origin-point drive joint, motion links vs loop-closure, the drive↔model affine map.
- `references/drag-chain/rig-drag-chain.md` — chain route (absorbed from the former
  rig-drag-chain skill): pin-coincidence discovery, gate ladder, create-once-heal, and
  the θᵢ(q) pose engine. With `references/drag-chain/chain-recipes.md` (script skeletons)
  and `references/drag-chain/pose-engine-math.md` (the path model + acceptance numbers).
- `references/api-gotchas.md` — the full failure catalog with symptoms → causes → fixes,
  including exec snippets for each law.
- `references/workflow-recipes.md` — copy-paste script skeletons: axis measurement, gated joint
  builder, motion-link sign search, copy-export mesh pipeline.
- `references/slider-and-chain-joints.md` — prismatic joints (as-built + geometry-frame
  direction resolution, the rail-edge frame trick), multi-part links (rigid GROUP not
  rigid joint), serial-chain gating ladder, the create-once-heal-by-driving pattern,
  drive-heal recovery, and why closed chain loops wander & break (compute coupled poses
  by script instead). From the Vention 7th-axis saga (2026-07-09).
- `references/making-gifs.md` — pose-sweep → viewport screenshots → ffmpeg GIF, with the
  fixed-camera rule and crash-proof park/restore pattern.
