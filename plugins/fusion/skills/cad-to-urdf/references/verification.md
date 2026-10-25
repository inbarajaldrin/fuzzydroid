# Verification — a URDF that parses is not a correct URDF

Four independent checks. Each catches a different class of error; a URDF isn't done until
all four pass. The point is that they are INDEPENDENT — a mesh can be geometrically wrong
in a way the FK test can't see, and a joint can be wrong in a way mesh identity can't see.

## 1. FK pytest against a validated table (the drift-killer)

Pin the URDF's forward kinematics to a table of known-good poses. This is what stops a
future edit from silently moving a frame. The RG2 test
(`test/test_fk_against_settlement.py`) does this:

- Loads the xacro, walks the joint tree, computes FK from a chosen root to a target frame.
- Asserts poses against a firmware/CAD-validated table (e.g. `tool0→rg2_base = (0,0,18.10)mm`,
  the grasp reach 0.1946 m, the per-width depth model `55·cos(α0+θ)+139.6` mm). The `139.6`
  depth constant is measured **from the `rg2_base` datum**: 144.1 mm (from the RG2 seat/mount
  face) − 4.5 mm (seat → `rg2_base`) = 139.6 mm.
- Asserts the STRUCTURE too: parent links, joint origins, mimic multipliers
  (`LOCKED_MIMICS` incl. cover ±1.0 / bumper ∓1.0), link presence. So a refactor that
  changes a parent or a mimic sign fails loudly.

Run it in a venv with `xacro`, `numpy`, `pytest`. Keep it green as a merge gate. 7/7 passing
was the bar for the RG2 package.

## 2. q=0 mesh identity (the mirror/rotate/swap catcher)

At the export pose (q=0 / rest), the URDF's link meshes must be geometrically IDENTICAL to
a static CAD reference of the same links. This catches the errors FK can't:

- **Sample a DENSE set of points across each mesh surface** and compare rig/export mesh vs
  reference with nearest-neighbour distance (use `scripts/mesh_identity_check.py`).
- **Do NOT use pin-center / circle-center / bounding-box / Z-range checks as the final
  test.** They PASS even when an asymmetric part is mirrored, rotated about a two-pin line,
  or left/right swapped. Mesh identity is the law; center checks are diagnostics only.
- Healthy values are microns: RG2 covers converged to ~6e-6 mm max deviation. Anything
  above ~0.03 mm means the mesh is placed/oriented wrong, even if pins line up.

Sub-traps this caught in the RG2 work:
- The right bumper joint origin used the moment-arm-frame z (+0.022195) instead of the
  mirror of the left (−0.014221) — a 36 mm z misplacement that pin-centers would have
  passed. Mirror the LEFT origin; don't reuse the right frame's own value.
- Whole-robot centroid alignment is invalid when finger meshes are split — do per-link
  checks with a fixed frame offset, not a global centroid fit.

## 2b. Two-sided extent regression gate (the truncation catcher)

`is_volume` and the FK test both MISS a truncated mesh (a stub is watertight; FK reads
joint frames, not mesh extents). Pin every collision mesh's full bbox extents to a
known-good baseline and assert per-axis within tolerance on BOTH sides — SHRINK
(truncation) and growth. A growth-only gate shipped the RG2 moment_arm 30 mm stub; a
Z-window-only datum check missed its X/Y truncation. Baseline the PRUNED links post-prune
and the NON-pruned links at full known-good extent, so intended prune-shrink is
distinguished from truncation. Reference:
`onrobot_rg2_description/test/test_fk_against_settlement.py::test_collision_extents_no_truncation`
(per-axis, ±0.5 mm). See also `references/colored-visuals.md` "THE OPEN-SURFACE TRUNCATION TRAP".

**MANDATORY: after ANY bake-pipeline change, audit ALL links, not just the reported-broken
one.** A pipeline change (e.g. adding the `is_volume` repair ladder) is a systemic cause —
it can truncate every link that hits the same condition. When the RG2 moment_arm stub was
reported, a full per-link audit of all 11 links (each bake vs the 5ee59d6 known-good, in
BOTH collision and visual) found a SECOND silent casualty — the hand collision, −1.7 mm at
the tip — that spot-checking only the reported link would have shipped. Compare every link
to the last-known-good, accounting for intended prune-shrink; treat any unexplained
shrink as a truncation until proven otherwise.

## 2c. Collision-within-visual envelope gate (the hidden-body-leak catcher)

The extent gate (2b) is BLIND to hidden-body leakage: a hidden body that fills a mating
recess sits INSIDE the link bbox, so extents don't move — yet the collision solid now
protrudes into that recess and interpenetrates a flush-mounted neighbor. This is exactly
how "collision = union ALL bodies" let a hidden RG2 hand body fill the coupler-mate recess
and overlap the quick-changer by ~0.2 cm³ — invisible to `is_volume`, the FK test, AND the
per-link extent gate (bbox unchanged; only the internal volume changed, +1.6 cm³).

Because collision must union the VISIBLE bodies only (== the link's visual geometry), the
collision solid must NOT protrude beyond the union of the link's VISUAL meshes. Gate it:
`excess = volume(collision − union(visual DAEs))` must be `< 0.2 cm³` per link (tessellation
noise is ~0.04 cm³; an interpenetrating leak is ≥1 cm³ — the old hand scored 1.59). Reference:
`onrobot_rg2_description/test/test_fk_against_settlement.py::test_collision_within_visual_envelope`
(needs trimesh + manifold3d + pycollada, all `importorskip`'d). This is the gate that would
have caught the leak at bake time; ship it alongside 2b in every package.

**Inter-link overlap is the workcell-level complement:** the envelope gate is per-package
(collision vs its own visuals). A cross-package interpenetration (gripper hand vs a separate
coupler link) only shows at composition — check it in the COMPOSED description (e.g.
`dime_workcell`) by FK-placing every collision mesh at the neutral pose and boolean-checking
all NON-adjacent link pairs, where "adjacent" is transitive through fixed joints / geometry-
less frame links (the same rule the URDF viewer's collision check uses).

## 3. Xacro variant processing

Process EVERY variant the macro exposes, not just the defaults, and confirm each expands
without error and produces the expected structure:

```bash
xacro onrobot_rg2.urdf.xacro                       # defaults
xacro onrobot_rg2.urdf.xacro covers:=false          # sub-mechanism off
xacro onrobot_rg2.urdf.xacro qc_variant:=io         # / io:=true on the adapter
xacro onrobot_rg2.urdf.xacro grip_config:=internal
xacro onrobot_rg2.urdf.xacro prefix:=left_          # prefixed (dual-arm)
```

A prefix arg that isn't threaded through every link/joint name is the classic breakage;
the variant sweep surfaces it.

## 4. Visual — AssetInspector offscreen + the fuzzydroid URDF viewer

Two visual confirmations:

- **AssetInspector offscreen snapshots** at meaningful configurations (closed, open) to
  confirm articulation — e.g. that covers AND bumpers actually move with the drive joint.
  Protocol (exact tokens matter): `ASSETINSPECTOR_OPEN`, then set joints with
  `ASSETINSPECTOR_JOINTS` using **`name=value` format** (JSON and colon formats are
  silently ignored — proven by md5-comparing the output frames), then
  `ASSETINSPECTOR_SNAPSHOT`.
- **fuzzydroid URDF viewer** for the final package (flags + `package://` resolution:
  `references/urdf-viewer.md`):
  ```bash
  python plugins/fusion/viewer/urdf/serve_urdf.py <pkg_dir> --port 8091 --no-open
  ```
  Screenshot it WITHOUT stealing focus using `bgshot.py` (background window capture). Note
  in your report which URDF the viewer is showing. Stop it with
  `lsof -ti tcp:8091 | xargs kill`.

## Provenance of the checks

Record the numeric results in a `VERIFIED_SPEC.json` next to the export (the passing FK
poses, the mesh-identity max deviations per link, the coupling distances) so a reader can
see exactly what was verified and to what tolerance — not just "verified".
