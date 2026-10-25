# Export flavours: merged-per-link vs unmerged-per-body

Three ways to get meshes out of Fusion. The one-shot exporter is preferred *when it
applies* — but it does not apply to rigged/mimic designs, which is exactly the class of
gripper/robot this skill exists for. Know which flavour your design needs before you start.

## The decision

| Flavour | Mesh granularity | Use when | Cost |
|---|---|---|---|
| **A — fzd one-shot** (`export_urdf.py`) | one merged STL per link | design has real joints + a component literally named `base_link`, and NO mimic-driven links | cheapest, but fails on the cases below |
| **B — flattened-STEP / per-body** | one STL per body, hand-authored URDF | STEP with no assembly tree, OR any rigged design where Flavour A fails | most control; you author the URDF |
| **Merged-per-link (copy-export pipeline)** | one merged STL per link, but YOU choose the link→body grouping and the frame | you want the current-package mesh style (one clean mesh per link, world-baked) and full control of grouping | recommended for a maintained description package |

The RG2 work used **merged-per-link** for the shipping package (11 links, one mesh each,
covers carry their pins, bumpers split out of the moment arms) and also produced an
**unmerged per-body** export (169 meshes) via Flavour B's path for comparison.

## Why Flavour A fails on rigged / mimic designs

The fzd one-shot (`export_urdf.py`, wrapped by `fzd-fusion export urdf`) is
excellent for a clean articulated design, but it has three disqualifiers for the gripper
class:

1. **It requires a component named `base_link`.** Renaming a component in the source doc
   is a *modification* — and saving that modification into a reference/source lineage
   violates the never-save-a-reference-doc rule. You'd have to fork the doc first.
2. **It emits one merged mesh per link and discovers links from the joint graph.** A
   mimic-driven mechanism (URDF `mimic` joints — a follower link whose angle is a linear
   function of a driver joint, like the RG2 cover 4-bar or a safety shield) has links
   that are NOT independent joint children in the way the exporter expects. It cannot
   attach mimic-driven links; they either vanish or fuse into a parent.
3. **It merges per link by its own rule**, so you lose control over which bodies land in
   which link mesh (e.g. keeping cover pins with the cover, keeping the hand mesh free of
   the slot pins). For a curated package you want that control.

Observed failure directly: `fzd-fusion export urdf` raised
`RuntimeError: 3 : invalid geometry` at `createSTLExportOptions` on the rigged RG2, and
structurally it would have merged the motion-link (mimic) covers away regardless. That
attempt is worth keeping as a documented negative result (we saved a `FLAVOUR_A_ATTEMPT.md`
alongside the export) so nobody retries it expecting a different outcome.

## Merged-per-link (the copy-export pipeline) — recommended for a package

This is Flavour B's world-bake technique applied deliberately, one mesh per link:

1. For each link, decide which bodies belong to it (the grouping is a design decision:
   covers keep their pins; the hand must NOT carry the cover slot pins; bumpers come out
   of the moment arms into their own link).
2. **World-bake each body** into a temp root component so the exported STL is in world
   coordinates, then normalise into the link frame. Use `scripts/world_bake_export_stl.py`.
3. **Mirror convention** (if the mechanism is symmetric): author the left mesh, and serve
   the right side by reusing the left with `rpy(pi,0,0)` and a z-offset — EXCEPT for parts
   whose asymmetry matters (covers/bumpers), which use their own side-native `*_r.stl` at
   `rpy 0`. Getting this wrong passes pin-center checks but fails mesh identity (see
   `references/verification.md`).
4. Apply the constant frame normalisation between Fusion world and the package link frames
   (the RG2 package uses a fixed +10 mm z-shift; know yours and apply it uniformly).

## Flavour B — flattened STEP / per-body (the unmerged export)

When upstream ships a single STEP with no hierarchy, or when you want the raw per-body
export for comparison, follow the fuzzydroid recipe's Flavour B verbatim (import STEP →
classify bodies by spatial signature → export each body as its own STL → optionally merge
in trimesh → hand-author the URDF mirroring a reference topology). The
`scripts/world_bake_export_stl.py` primitive handles the "(1)" filename-suffix trap via
the rename-before-copy pattern.

**Cite which procedure you used** in the export's PROVENANCE.md — Flavour A vs B vs
merged-copy-export — so the provenance is auditable. The unmerged RG2 export cited
"Flavour B (per-body)"; the merged one cited the copy-export pipeline.

## Provenance stamp

Every export directory gets a `PROVENANCE.md` recording: the source doc name **and
version** (e.g. `rg2 v26`), the flavour/procedure used, the frame normalisation applied,
the date, and any per-link grouping decisions. This is what lets a future reader trust the
meshes without re-deriving them. A `VERIFIED_SPEC.json` alongside it pins the numeric
checks that passed (see `references/verification.md`).
