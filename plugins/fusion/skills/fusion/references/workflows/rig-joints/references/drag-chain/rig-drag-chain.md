# Rig Drag Chain — serial modular chains in Fusion 360 via fzd-fusion

> Route within the `rig-joints` skill (absorbed from the former standalone `rig-drag-chain`
> skill). Use for a drag chain / energy chain / cable carrier — or any serial chain of
> identical modular links (tank tracks, roller chains, repeated pin joints): discover the
> link order from pin-circle coincidence, create the inter-link revolutes with a gate ladder,
> heal bridging joints by driving, recover corruption by drive-healing, and drape the whole
> chain from one carriage variable with the calibrated θᵢ(q) pose engine — WITHOUT closing
> the kinematic loop. Read the parent workflow.md's Ten Laws first.

A drag chain is not a normal mechanism: N identical links, N+1 pin joints, a shape
governed by contact and inextensibility rather than by its joint DOFs. This skill
turns one into a fully-jointed, drivable, animatable Fusion assembly — validated
end-to-end on a 27-part Vention energy chain (sub-millimeter fit, exact restores).

**Prerequisites:** fuzzydroid fusion plugin (`fzd-fusion --json ping` → pong); the
Ten Laws in this skill's parent `workflow.md` (this route assumes them); the chain's parent
mechanism already rigged (e.g., the carriage slider the chain follows).
Use the bundled `chain-recipes.md` skeletons with measurements from the current chain.

## Phase 0 — Pose table first

Record a landmark for EVERY part (first planar-face origin of first body → JSON)
before touching anything. Chain rigging involves joint snaps that can throw parts
tens of cm; the pose table is what makes every mistake reversible by driving. This
is non-negotiable — it converts catastrophic failures into 2-minute recoveries.

## Phase 1 — Discover the chain from its pins

Modular links mate via coincident circle pairs (pin rims). This makes the chain
machine-readable:

1. Collect circle edges near the pin radius on every chain part.
2. Two parts are adjacent iff a same-radius pair (<0.2 mm radius diff) is coincident
   (<0.6 mm center distance).
3. Build the adjacency graph; it should be a simple path. Walk it from the anchored
   end → ordered edge list `(parent, child, pivot)`.
4. If an end bracket doesn't appear in the graph, widen the radius window — brackets
   often use slightly different pin geometry.

Verify: pin count = parts − 1, consecutive pin distances ≈ one pitch, straight-run
pins share z. Record pitch and the run heights now (you need them in Phase 5).

## Phase 2 — Anchor the moving end

Weld the chain's moving-end bracket into the moving link of the parent mechanism
(as-built rigid joints, null geometry is fine for rigid). If the moving link is a
multi-part carriage, it must be a rigid GROUP (rig-joints Law 3) — never a rigid
joint on a sub-assembly container.

**Leave the other end (tail) kinematically FREE.** Do not attach it to anything —
see "Never close the loop" below.

## Phase 3 — Inter-link revolutes: the gate ladder

For each edge in chain order, create a regular revolute on the coincident pin
circles (`JointGeometry.createByCurve(edge, CenterKeyPoint)` both sides). The snap
teleports the child (arbitrary X-frame alignment), so gate every creation by
measuring a far landmark on the child; escalate through this ladder — each level
exists because a real chain forced it:

1. **Angle compensation**: measure the child's rotation about the pivot, recreate
   with `inp.angle = -measured` (try both signs). Handles straight-run and bend links.
2. **× coincident-pair choice**: each pivot has ~3 coincident pairs (two rims + a
   collar within 0.1 mm radius of each other). The wrong pick throws the child
   laterally — no angle can fix it. Brute-force all pairs.
3. **× isFlipped**: anti-parallel circle normals (~π at first attempt) → flip.
4. **× swapped geometry direction**: joints that BRIDGE two already-jointed segments
   diverge under forward compensation (error doubles per iteration). Swapping which
   side supplies geometry-one lets the solver resolve through the other side.

Delete failed attempts with `entity.deleteMe()` (timeline-item deletion silently
no-ops in direct mode and leaves over-constraining phantoms).

## Phase 4 — The last joints: create once, heal by driving

**The cardinal rule: create→measure→delete gating is only safe while the pose is
virgin.** Once any chain joints have been driven (or a snap has moved segments),
each new creation redistributes drive values across neighboring joints, and deletion
does not undo that — retry loops compound corruption.

For the final/bridging joints, switch strategy:
1. If a dangling segment is misplaced, rigid-move it home with `transform2`
   (works in direct mode even on jointed occurrences; conjugate the world correction
   through the parent occurrence transform).
2. Create the joint ONCE on the nearest pin pair. Tolerate the snap explosion —
   even 30 cm.
3. **Heal by driving**: walk joints proximal→distal; for each, compute the signed
   angle (about the pivot, in the chain plane) that takes the child's landmark to
   its pose-table target, test both signs, keep the better; 2–4 rounds converge.
   Drives are non-destructive and always convergent because the pivots are
   physically correct — this same loop is your universal recovery from ANY
   corruption. Audit every part (including the far end!) before every save.

## Phase 5 — The θᵢ(q) pose engine

The chain's drape is a function of one variable. Compute it; don't ask the solver.

**Calibrate once** (see `pose-engine-math.md` for the math and
`chain-recipes.md` for the code):
- Fresh pin positions, joint zero values `r₀ₖ`, and the **empirical rotation sign
  `sₖ`** per joint (drive +0.06 rad, measure which way the child actually rotates —
  expect a few inverted joints; never assume).
- Path parameters from the pins: run heights from the FIRST/LAST few pins only
  (bend pins contaminate z-filters), `R = (z_top − z_bot)/2`, pitch, anchor, tail.

**Per pose q**: build the path (straight run → half-circle bend → straight run),
chord-walk pins at exactly one pitch, solve the bend center by shooting so the tail
lands where physics says, convert consecutive pin directions to relative angles,
apply `jointₖ = r₀ₖ + sₖ·wrap(δₖ(q) − δₖ(0))`.

**Tail physics (drape-first, pull-only)** — chains push their links, not their tail:
- Default: tail planted at its park position; ALL motion absorbed by bend migration
  (at exactly half the carriage speed — verify this; it's the signature of a correct
  model).
- Only when the bottom run is exhausted does the tail get *dragged* (never pushed
  forward past park): `x_t = max(rail_min, x_b − L_min)`.

A correct calibration reproduces the as-modeled pins to <0.1 mm and restores park
to 0.0000 after any sweep. Both are hard acceptance criteria.

## Never close the loop

It is tempting to attach the tail to its rail (weld / pin-slot / slider) so "the
solver figures it out". Verified three ways: a closed chain loop has ~¾ of its DOF
redundant, so Fusion's solver *wanders* between valid solutions and, at geometric
jams, **breaks constraints silently** — corrupting poses with no error dialog. The
open chain + scripted poses gives the same visual behavior deterministically, and
the tail's rail-guidance emerges from the math for free. If a user insists, test on
a saved state and audit everything afterward.

## Deliverables

- Sweep GIF: pose sweep with a FIXED camera → ffmpeg (recipe:
  `../making-gifs.md`).
- Export F3D (keeps joints) + STEP (geometry) of the parked state.
- The calibration JSON + pose script — they are the chain's "driver" and port
  directly to a ROS joint-state publisher for URDF animation.

## References

- `chain-recipes.md` — copy-paste script skeletons: adjacency discovery,
  gate ladder, create-once-heal, drive-heal recovery, calibration, pose engine,
  sweep. Read before writing any chain exec script.
- `pose-engine-math.md` — the path model, chord-walk, shooting, angle
  mapping, tail clamp; with the validation numbers a correct implementation hits.
