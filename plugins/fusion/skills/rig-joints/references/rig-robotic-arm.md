# Route: rig a serial robotic arm (against a URDF)

The mechanism: an open serial chain of revolutes (UR3e/5e/10e/16e, Franka, KUKA,
xArm — anything with a canonical URDF). You have vendor CAD (often a STEP import with
no joints) and a URDF you want the CAD to match frame-for-frame, so the rigged design
drives in the same coordinates as the robot description.

Use the current robot's geometry and description as inputs. The method below
does not require a particular vendor model or a previous rigging session.

## The four moves that make an arm rig work

### 1. Verify the CAD is the robot you think it is (kinematic fingerprint)
Component names lie (a UR5e STEP ships as `Base_UR5_STEP`, `Link1..6_UR5_STEP`);
geometry doesn't. Measure 3–4 characteristic axis-to-axis distances from large
cylinder faces (`face.geometry`, radius/area-filtered — Law 1) and compare to the
URDF `<origin>` chain. For the UR5 vs UR5e the shoulder-lift height above the base
face (89.2 vs 162.5 mm) alone disambiguates. Do this before investing in rigging.

### 2. Solve the global registration OUTSIDE Fusion
Vendor arms usually ship posed at a KNOWN non-zero pose, not URDF zero — UR STEP
files sit at the teach-pendant home `[0, −90°, 0, −90°, 0, 0]`. Because the pose is
known, registration collapses to a small search:

1. Parse the URDF; FK at the shipped pose AND at zero → target axis lines per joint.
2. Dump the CAD's measured axis lines (cylinder faces, cm) and try the handful of
   candidate world rotations (e.g. yaw ∈ {0,90,180,270}° composed with the Y-up→Z-up
   `Rx(90°)`); pick the minimal axis-line error. The UR5e solved to `Rz(180°)·Rx(90°)`,
   residual 1 mm → 0.1 mm.
3. Rotate each subtree from the shipped pose to zero about its own axis (pick signs by
   candidate residual, never by hand).
4. Emit absolute per-occurrence 4×4 corrections to JSON. Final residuals ≤ 50 µm.

If the shipped pose is unknown: same solver, but solve per-joint sequentially — align
each next axis line onto its zero-pose target about the current axis, iterating and
measuring (the 4-bar route's `05_iterative_angle_converge.py` shows the iterate form).

### 3. Apply, then build gated circle-pair revolutes
Apply the corrections `transform2 = corr @ old` (cm!) in PARAMETRIC mode with a
snapshot after each batch (Law 2 — a direct-mode apply is silently discarded on the
parametric switch), rename components to URDF link names, and **ground `base_link`
before any drive** or the whole arm walks off. Then build the revolutes
proximal→distal with the gated create→measure→delete→recreate loop (Laws 4–6) from
coincident mating-rim **circle pairs** — never as-built (pivot-permutation explosion)
and never cylinder-face `MiddleKeyPoint` (pivots land on the surface). Expect
arbitrary snap compensations (a UR5e run needed shoulder_lift +90°, elbow flip−90°,
wrist_1 −60°, wrist_3 −120°); the gate guarantees correctness, not the numbers.

### 4. Limits and sign calibration — the two arm-specific traps
- **Limits: leave full-turn joints UNLIMITED.** Fusion normalizes stored limit angles
  mod 2π, so a "full circle" `[0.0001, 6.2831]` is enforced literally and blocks any
  drive through zero after save/reopen (Law 8). Give a real sub-2π joint its honest
  range (elbow ±π works perfectly); leave the rest unlimited and keep the authoritative
  ranges in the URDF.
- **Sign calibration: the Fusion drive direction can be anti-parallel to the URDF axis
  per joint.** Do NOT assume drive == model. Deflect one joint at a time (+0.2 rad),
  read a pose-invariant flange landmark (the rim FARTHEST from the neighbouring link —
  "largest circle" ties nondeterministically), and record the per-joint sign map (the
  UR5e came out `[-1,-1,-1,+1,+1,±]`). The URDF stays the truth for signed q; document
  the map, don't fight it. This is the serial-arm form of the drive↔model lesson (the
  4-bar route adds an offset term).

## Validate
Drive all joints to a bent pose; every joint's mating cylinders must stay coaxial
(live edge geometry, dist 0.0) and the zero-restore must be exact. If a URDF FK / IK
model exists, reach a target in the rigged CAD and check the flange landmark (the UR5e
reached a tool-down target within 0.6 mm). Then run the acceptance test in the parent
SKILL.md's Validation section (robot jog).
