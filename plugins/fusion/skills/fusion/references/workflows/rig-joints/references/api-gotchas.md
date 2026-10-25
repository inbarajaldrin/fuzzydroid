# Fusion API failure catalog (symptom → cause → fix)

Every entry below was hit for real while rigging a UR5e and an OnRobot RG2 (2026-07-07).
Ordered roughly by when they bite in a rigging session.

## Session / document management

**Symptom:** Your script errors with joints/components that don't exist in your design.
**Cause:** `app.activeProduct` follows the ACTIVE TAB; the user (or a stray open) switched documents.
**Fix:** Every exec starts with:
```python
docs = app.documents
for i in range(docs.count):
    d = docs.item(i)
    if d.name.startswith("my_design"): t = d
if app.activeDocument.name != t.name:
    t.activate(); adsk.doEvents()
```

**Symptom:** `printf '...' | fzd-fusion exec -` produces `SyntaxError: invalid decimal literal`.
**Cause:** printf consumed `%d`/`%s` in your Python.
**Fix:** write the script to a file, `cat file | fzd-fusion --json exec -`.

**Symptom:** Bridge exec times out client-side on long batches (>2 min).
**Cause:** Fusion is still running your script on its main thread; the socket gave up.
**Fix:** it usually completes anyway — poll for the script's output artifacts (files, manifest).
Write scripts to emit a completion file. Increase Bash timeout for known-long jobs.

## Measurement

**Symptom:** Geometry "didn't move" after a drive, or moved to nonsense positions.
**Cause:** `boundingBox` (occurrence AND body) and vertex proxies are stale caches; they can
even be stale at *different historical poses per body*.
**Fix:** measure only via `face.geometry` / `edge.geometry` on assembly-context proxies.
Circle-edge centers are exact points. Re-fetch entities freshly inside each attempt — BRep
proxies invalidate after joint create/delete cycles ("Invalid parameter face").

**Symptom:** Kabsch/registration from face `origin` correspondences gives a self-consistent but
WRONG transform for some bodies.
**Cause:** plane/cylinder `origin` is an arbitrary anchor; native vs proxy anchors need not
correspond. The residual can be exactly 0 while the transform is off along the cylinder axis.
**Fix:** don't do correspondence math at all for export — use the copy-to-temp-component trick
(below). For registration, use circle-edge centers only.

## Transforms & structure

**Symptom:** All your careful re-positioning vanished.
**Cause:** transform2 edits in direct mode are discarded on the switch to parametric.
**Fix:** switch designType FIRST; after transform batches call `design.snapshots.add()`.

**Symptom:** `transform2` assignment silently no-ops.
**Cause:** occurrence participates in joints (parametric).
**Fix:** delete the involved joints, move, snapshot, recreate joints. Deleting a regular joint
restores the child's pre-snap pose — use that as your undo.

**Symptom:** Drive moves one body; its groupmates stay behind.
**Cause:** API-created groups aren't rigid to the solver.
**Fix:** rigid groups per link. If `rigidGroups.add` throws "joint in system exists", verify
empirically whether rigidity is already effective (drive + measure a non-jointed member);
`root.rigidGroups` can enumerate empty while constraints persist.

**Symptom:** `root component name cannot be changed`.
**Cause:** root component takes the document name.
**Fix:** name it via `saveAs`.

## Joints

**Symptom:** Assembly explodes on drive — parts orbit their pivots at growing radii.
**Cause:** as-built revolute rotates about a permuted pivot (geometry origin z→pivot y). The
reported `rotationAxisVector` direction is truthful; the pivot POINT is wrong.
**Fix:** regular joints with two-sided geometry.

**Symptom:** `Key point type should not be CenterKeyPoint` — cylinders want `MiddleKeyPoint`.
**Symptom:** `AsBuiltJointInput is only supported in parametric` — switch design type.
**Symptom:** custom rotation axis entity ignored — as-built custom direction needs a LINEAR
entity (edge/axis/sketch line), not a cylindrical face; it fails silently.

**Symptom:** Regular joint creation teleports the child (rotation / 180° flip / axial slide).
**Cause:** snap aligns full frames incl. X axes; circle X-parameterizations are arbitrary; circle
normals may be anti-parallel; anchor heights differ.
**Fix:** the gated create-measure-delete-recreate loop with `JointInput.angle` (rotation about
axis), `.isFlipped` (180° flips — set on the INPUT; post-creation `joint.isFlipped` needs a
timeline rollback), `.offset` (axial). Compute the compensation FROM the measurement:
angle = atan2-signed angle taking a landmark to its target about the axis; iterate ≤5 times.

**Symptom:** Joint claims value cur=π at creation (or any offset) even though nothing moved.
**Cause:** Fusion's joint zero = its snap frame, not your convention. Harmless for geometry;
poisonous for limits if you forget to center them on `cur`.

**Symptom:** Whole mechanism frozen; `rotationValue` stores but geometry never moves; every
sign-search candidate measures identically.
**Cause:** a closed loop of revolutes (3D over-constraint) — or you're measuring with stale reads.
**Fix:** delete the loop-closing joint; add Motion Links (URDF-mimic equivalents); verify each
link's `isReversed` by loop-closure error under a small drive, with rigid groups already in place.

**Symptom:** Joint limit values read back 0 after assignment; later all drives clamp to 0.
**Cause:** limit magnitude ≥ 2π rejected silently; enabled min=max=0 remains.
**Fix:** clamp to ±(2π−1e-4); expect mod-2π normalization on read-back; span is what counts.

**Symptom:** Drive to a far value silently reverts; small steps work.
**Fix:** step large moves (≤0.15 rad in loaded mechanisms).

**Symptom:** A revolute is laterally perfect but its child sits N mm off along the joint axis
(only visible in exported meshes or a z-audit; kinematics of planar mechanisms won't show it).
**Cause:** axial snap offset went unmeasured (gates checked XY only, or checked the group
transform while the nested child slid).
**Fix:** audit circle-edge z per link vs expectation; correct via `joint.offset.value` (editable
live; the solver re-solves; adjacent joints tolerated it in practice). One iteration converges.

## Export

**Symptom:** Exported STL is in the wrong place — matches neither world nor link frame.
**Cause:** STL export is ALWAYS in the entity's native component space; assembly context ignored.
**Fix:**
```python
tmp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
cp = body.copyToComponent(tmp)     # copy BAKES world coordinates
em.execute(em.createSTLExportOptions(cp, path))   # mm, world
cp.deleteMe()
```
Then trimesh: `apply_transform(inv(link_frame_at_export_pose))`, `apply_scale(0.001)`.
Remember the export pose is whatever the model is in NOW (drive values persist through save,
so it's whatever pose was last saved/driven): link frames must be evaluated AT THAT POSE (moving links' frames rotate
with their joints; a parallel-jaw finger's frame does not rotate).

**Symptom:** `(1)` suffixes on exported files.
**Fix:** the rename-before-copy pattern (see `../../cad-to-urdf/workflow.md` `references/exporter-recipe.md`).

**Symptom (post-save):** All joints of a saved doc refuse to drive except one; values assign but
geometry never moves; resets don't restore.
**Cause:** enabled "full-circle" limits that were mod-2π-normalized to [0.0001, 6.2831] are
enforced literally — motion through zero is blocked. (The one joint that still moved had honest
±π limits.) Discovered on the UR5e doc after reopening it for an IK demo.
**Fix:** `isMinimumValueEnabled = isMaximumValueEnabled = False` for full-turn joints; keep
real limits only where they're genuinely sub-2π.

**Symptom:** A landmark measurement jumps ~cm between otherwise identical reads.
**Cause:** landmark selected by "largest circle" — several circles tie on radius (e.g. two Ø75
rims 4.3 cm apart on a wrist) and the tie-break is nondeterministic.
**Fix:** make selection pose-invariant and unique — e.g. "the candidate FARTHEST from a reference
feature on the neighboring link" (flange rim = farthest from wrist_2), never "the largest/first".

**Symptom:** After save/reload, `root.rigidGroups` enumerates EMPTY, every rigid-group or as-built
weld creation is rejected with "A joint in system exists" — yet jointless members may or may not
follow their links.
**Cause:** the rigid groups still exist as TIMELINE features (phantoms invisible to the
collection). Creation fails because they're duplicates of live constraints.
**Fix:** enumerate `design.timeline` and filter `type(item.entity).__name__ == "RigidGroup"` —
that's the truth. Then verify FUNCTION empirically (drive a joint; a jointless cover/washer must
move in lockstep with the link's jointed body). Trust neither the collection nor the error text.

**Symptom:** A part classified by min-distance contact (0.0 = "attached") turns out to belong to a
different link — it only sits correctly at the as-modeled pose and drifts at every other angle.
**Cause:** touching is not fastening. Pin ends, running surfaces, and covers touch parts they do
NOT move with.
**Fix:** classify by FASTENER COINCIDENCE: find small boss/hole (screw/pin) pairs between the part
and each candidate link and check they remain coincident ACROSS DRIVEN POSES. The link whose
fasteners track the part owns it. (Fixing membership later: delete the affected phantom/real
rigid groups via their TIMELINE entities — deleting one invalidates the iterator, wrap item
access in try — then moveToComponent, then recreate rigid groups; creation un-blocks once true
phantoms are gone.)

**Symptom:** Hundreds of RGB axis triads clutter the viewport; hiding component Origin folders
and origin construction elements does nothing.
**Cause:** they are not origins at all — STEP files carry named coordinate systems and the
importer materializes each as a visible **UserCoordinateSystem** feature (an RG2 STEP produced 241).
**Fix:** iterate `design.timeline`, filter `type(item.entity).__name__ == "UserCoordinateSystem"`,
set `entity.isLightBulbOn = False`. Save afterwards — F3D carries display state (STEP export doesn't).

**Symptom:** After save + reopen, the model is not in the pose you left it in.
**Cause (corrected understanding):** joint drive VALUES persist through save/reopen — the file
reopens at whatever pose it was saved in. Park the canonical pose BEFORE the final save.
(An earlier session note claimed saves reset drives to zero — wrong; what actually happened was
saving while the model sat at a non-canonical pose.)
