> Internal workflow loaded by the main skill. The plugin root comes from
> that skill. Resolve this workflow's `references/`, `scripts/`, and
> `evals/` paths relative to this directory.

# Printable Threads

Build threads from an explicit geometry and motion contract. A visually plausible
helix is not enough: preserve the source profile, derive the mate phase, and prove
the seated target with exact B-Rep interference checks.

## Choose the output state first

- **Clearance experiment:** overlapping solids may remain within one physical
  component, but only to inspect geometry and test cross-component clearance.
- **Production:** every physical part must be one watertight solid. STEP must
  round-trip as one solid per part and STL must use high mesh refinement.

Never describe an experimental multi-solid model as print-ready. A slicer's
auto-union is not geometric validation.

## Quick start

From this skill directory, reproduce the calibrated radii and seated pose:

```bash
python3 scripts/thread_contract.py --male-center-z-at-zero 14.8 \
  --female-local-center-z-at-zero 7.995 --seat-z 7 \
  --angle 188.775 --pretty
```

## Workflow

1. Preserve the existing generator and Fusion document. Create a new script,
   document, and export lineage for the threaded variant.
2. Record major diameter, pitch/lead, depth, included angle, handedness, starts,
   segment count, female slop, thread span, and termination style.
3. Run `scripts/thread_contract.py` to calculate the radii and mate relation.
4. Author the male and female as native modeled B-Reps. Do not convert the
   reference STL/OBJ into a B-Rep and call that parametric. For production,
author and consolidate each complete part in an isolated root document,
subtract a bounded male-shaped cutter for the female groove, then transfer
only the finished one-solid B-Rep.
5. Diff both parts against the reference mesh: envelope, volume, watertightness,
   connected components, and bidirectional sampled surface distance.
6. Derive the female phase and fully seated pose; never eyeball the rotation.
7. Validate every physical body pair at the target with Fusion's exact
   interference analyzer, excluding coincident faces.
8. Apply the relevant export gate below and save the contract and validation as
   JSON beside F3D, STEP, and STL outputs.

## Hard gates

- Screw motion is `dz = pitch * dangle / 360` for the validated right-handed,
  single-start convention. Derive the sign again if the moving part, axis, or
  handedness changes.
- Male and female material-ridge centers are separated by half a pitch at the
  target, modulo one pitch.
- `measureMinimumDistance` does not prove absence of penetration.
- Multi-body occurrence-level interference can return no result. Test native
  body proxies created in each occurrence context, pair by pair.
- Repeated components share one definition. Author the thread once, then reuse
  occurrences; do not independently mutate identical legs.
- Production passes only with zero positive-volume target interference, one
  solid per part, watertight exports, and unchanged intended target transforms.

## Proven baseline

The calibrated reference is a right-handed, single-start, symmetric 90-degree
trapezoid: 24 mm major diameter, 8 mm pitch, 3 mm depth, 96 segments, and BOSL2
female slop 0.10 mm. Its quantized radial clearance is 0.2064283921 mm. The
calibration pair seats the nut at Z=7 mm and Rz=188.775 degrees with zero exact
Fusion interference.

Read `references/geometry-contract.md` for the formulas and reference numbers.
Read `references/fusion-workflow.md` before implementing or validating Fusion
geometry. Read `references/trimming-and-consolidation.md` when a ridge protrudes
past its host or the component still contains overlapping solids.
For supplier hardware, use the actual nut and bolt B-reps, derive the local
axis and seat from the host, and verify clearance with exact interference tests.
Record input hashes, preserved assembly transforms, generator parameters, and
validation outputs in the user's project.

## Production consolidation

Use staged male unions,
bounded subtractive female cutters, isolated root-document construction, and
one-solid transfer into the assembly. The operation order, parameter choices,
known Fusion failures, and acceptance gates are in
`references/trimming-and-consolidation.md`. Derive clipping bounds and thread
phase from the current host instead of copying a previous part's dimensions.

## Downstream motion and simulation handoff

Do not derive a screw command from total part length. Resolve the exact exported
B-rep bytes through their consuming digest, measure both helices, and name
`first_thread_engagement` and `seated`. Keep `full_solid` (material plane to
material plane, including any thread-free lead) distinct from `helix_boundary`
(the coupled screw). Any pre-engagement clearance is a separate axial segment.
Derive one unwrapped constant screw from
`turns = axial_travel / pitch` and
`signed_angle_rad = handedness_sign * 2*pi*turns`; derive the endpoint from that
same authority and refuse a stored endpoint mismatch.

The exact solid and the simulation collider answer different questions. If an
exact OCCT sweep is contact-free but Isaac stops early, inspect collider scope
before touching trajectory or CAD. A connected feature containing sub-thickness
fragments must not automatically become one broad SDF: preserve cookable convex
fragments and localize exact SDF patches to the thin pieces.

One cleared coupling calibration may be reused across parts generated by the
same conjugate-thread contract, but each assembly still owes exact ingest,
named-stroke arithmetic, collider coverage, and assembly-local mate execution.
Physics materials belong to assembly/environment declarations and must be
verified by declaration-to-live readback; they are not Fusion parameters.
