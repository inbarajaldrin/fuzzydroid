# Route: rig a 4-bar / parallelogram linkage (a gripper)

The mechanism: a closed planar 4-bar per side, driven by one joint, where the two
"coupler" bars stay parallel so the jaws translate without rotating (RG2/RG6,
Robotiq 2F, any parallelogram gripper). The rig must reproduce the linkage motion
from ONE drive value — which in URDF terms means `<mimic>` joints, and in Fusion
terms means Motion Links, because a closed 4-bar of four revolutes freezes the solver.

Classify and validate the main linkage and any cover or bumper linkage
separately. Derive pivot membership and coupling from the current mechanism;
neither contact alone nor a previous gripper's part labels establish ownership.

## The four moves that make a linkage rig work

### 1. Classify parts by pivot-hole fingerprint (not by guessing)
For each loose part, record which of the mechanism's pivot axes it has circle edges
at, and read membership directly: on the RG2, holes at {B,D} → finger; {A,B} → moment
arm; {C,D} → truss; {A,C} both sides → housing. Watch the radius filter — an
undersized bearing gets silently missed.

For hole-less parts, do NOT settle membership with `measureManager.measureMinimumDistance`:
min-distance reads 0.0 for touching AND interpenetrating solids and is blind to which
body a part actually MOVES with (the RG2 cover plates were mis-assigned twice this
way). Prefer a boolean-intersection overlap test and — decisively — a **kinematic
sweep**: mark the candidate fastener pair and check it stays coincident ACROSS the
driven stroke; the link whose fastener tracks the part owns it. The discriminating
anchor must live in the OTHER body (a same-rigid-group coincidence check is a
tautology). See `../../cad-to-urdf/workflow.md` `references/coupling-measurement.md` and its
`scripts/overlap_probe.py` for the boolean-overlap discipline.

### 2. Drive joint on a bore with no circle: the origin-point trick
The drive pivot often has no circular geometry on one arm (a clamped shaft bore). If
the vendor modeled that arm in its OWN pivot frame, build the joint from the arm's
origin construction point against the mating part's circle:
`JointGeometry.createByPoint(armComponent.originConstructionPoint.createForAssemblyContext(occ))`
plus the hand's drive-pivot circle (Law 5 fallback). Converge its snap rotation by
iterating the creation `angle` against a distal landmark on the arm.

### 3. Replace the loop-closure joint with Motion Links
Build the open joints (drive A, coupler B, truss C). If the parts are already at the
target pose (the rig-at-zero route of move 4), use **as-built revolutes** — they don't
snap, which deletes the whole creation-angle convergence dance; note as-built joints
require a PARAMETRIC design. Otherwise use gated circle-pair revolutes. Either way,
the 4th revolute D that closes the loop **freezes the mechanism** — 3D
over-constraint, values store and geometry never moves (Law 7). Delete D and add
Motion Links that mirror the URDF `<mimic>` tree (on the RG2: B←A reversed, C←A direct,
right-A←left-A), with the `isReversed` sign found empirically by loop-closure error
under a small drive, AFTER rigid groups exist. One drive value then runs the whole
gripper. Audit the axial (z) slide once via world-bounds — planar kinematics hide arms
that slid tens of mm along their pivot axes; fix with `joint.offset.value`.

### 4. Make the drive↔model map IDENTITY by construction — rig at model zero
The first-generation lesson was "the map is affine, `θ = sign·q + offset`; measure it,
never assume it". The settled doctrine (RG2 v27 rebuild, 2026-07-10) goes one step
further: **don't carry a map at all — EQUALIZE + ZERO the mechanism before creating
any joint.** Vendors freeze assemblies at arbitrary poses with per-side slack (the RG2
STEP ships at link angle L 46.042° / R 45.892°: a +0.315 rad offset AND a 0.150°
asymmetry). Rigging that pose bakes both into the drive forever. Instead, compute the
per-side feature-derived transforms that place the linkage at exactly the model zero
(RG2: α₀ = 27.95°), apply them, THEN rig with as-built joints (no snap). The drive is
then born with sign +1, offset 0, and no inherited assembly asymmetry.

Prove it by **sweep + fit** (the instrument survives even though the constant is gone):
drive to several `q`, fit the measured link angle and the model output (pad gap from
live plane faces) per side. The v27 rebuild fit slope 1.0000000, offset ≤ 4×10⁻⁵ °,
Δ_LR 5×10⁻⁶ °, amplitude 110.00 mm. Beware: Fusion snaps commanded drive values to a
0.05° grid — fit against the `rotationValue` READBACK, not the commanded value. Set
drive limits to the TRUE mechanical stops (RG2: model θ ∈ [−0.452, +0.782]); the
husarion URDF's `+1.0` upper limit over-opens the real hardware.

If you must keep a frozen-pose rig (legacy doc, no rebuild budget), the affine-map
discipline still applies: measure sign AND offset by sweep+fit, and state the datum
your offset is measured against (the RG2's historical 18.05° vs 17.95° dispute was the
CAD-4.45 mm vs firmware-4.6 mm fingertip datum difference, resolved by the rebuild).

## Validate
Sweep the drive and compare the measured mechanism output to the analytic model at
several poses; jaws must stay parallel at every pose and the zero-restore must be
exact. Confirm mesh identity at q=0 (see `../../cad-to-urdf/workflow.md` `references/verification.md`),
then run the acceptance test in the parent workflow.md's Validation section (robot jog).
