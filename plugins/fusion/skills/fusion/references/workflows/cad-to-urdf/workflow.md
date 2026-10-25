> Internal workflow loaded by the main skill. The plugin root comes from
> that skill. Resolve this workflow's `references/`, `scripts/`, and
> `evals/` paths relative to this directory.

# CAD → URDF

Turn a rigged Fusion 360 design into a ROS 2 URDF description package that other
packages can compose, with every coupling distance read from the assembled CAD (no
baked reconstructions). This skill is the distilled workflow from building the
OnRobot RG2 gripper + Quick Changer adapter + UR5e station description ecosystem.

Read the reference file for the sub-task you're on — each one carries the non-obvious
lessons that cost real time to learn. Do not skim past the coupling-measurement one.

| Sub-task | Read |
|---|---|
| Run the one-shot `fzd-fusion export urdf` (conventions, output layout, formulas, unit table) | `references/exporter-recipe.md` |
| Pick an export flavour (one-shot / flattened-STEP / merged-per-link) and why A fails on mimic designs | `references/export-flavors.md` |
| Split the robot into description packages (gripper / adapter / workspace) | `references/package-architecture.md` |
| Measure a coupling / seat distance so URDF matches the hardware | `references/coupling-measurement.md` |
| Verify the URDF is correct (not just parseable) | `references/verification.md` |
| View the finished package in the browser (`serve_urdf.py`, `package://` resolution) | `references/urdf-viewer.md` |
| Anything that runs inside Fusion (saving, linked docs, measuring) | `references/fusion-cautions.md` |

`references/exporter-recipe.md` is the exporter recipe (the `export_urdf.py` one-shot +
the canonical unit table). The rest of this skill sits on top of it: it captures why the
one-shot fails on rigged/mimic designs and what to do instead, plus the architecture,
measurement, and verification discipline that recipe doesn't cover.

## Hard rules (true across every sub-task)

- **Run Fusion scripts through the bridge**, one heavy call at a time:
  ```bash
  cat script.py | ~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json exec -
  ```
  Environment variables do NOT cross into the Fusion process — pass parameters via a
  JSON file the script reads (e.g. `/tmp/export_params.json`), not env vars.
- **Three units coexist.** Fusion Python API = **cm**; STL export from `exportManager`
  = **mm**; URDF = **m**. Convert at every boundary. Mixing them is the #1 "100× too
  big" bug. (Full table in `references/exporter-recipe.md`.)
- **Measure live geometry from faces and edges only** — never bounding boxes or vertex
  proxies (they go stale after edits). `measureManager` lives on `app` (the
  `Application`), not on the `Design`.
- **Never confirm a seat/coupling with `measureMinimumDistance`** — it returns 0 for touching
  AND for interpenetrating solids (blind to collision). Use a boolean-intersection overlap
  volume (`TemporaryBRepManager`), and place parts by their own features. See
  `references/coupling-measurement.md` — this is the single most expensive lesson.
- **No-drift law: CAD = URDF = USD.** Read couplings from the CAD; never bake a measured
  delta into the URDF. If the CAD deviates from the datasheet, fix it at the CAD and
  re-export — don't paper over it downstream.
- **Never save a reference/source doc.** Verify any save of a *work* doc by close+reopen
  (Fusion's `save()` returns true but persists nothing while another open doc references
  the target — the phantom-save trap). See `references/fusion-cautions.md`.
- **Verify, don't assert.** A URDF that parses is not a correct URDF. Pin it with an FK
  pytest against a validated table and a q=0 mesh-identity check before claiming it works.
- **Union before tessellation, prune before union.** The locked export flow: rig with
  rich features → symmetry-checked PRUNE pass (default: prompt for one; full-detail is
  the opt-out) → per-link B-Rep boolean union (visuals: union WITHIN each color group,
  one single-color mesh per group; collision: colorblind but prune-AWARE union of the
  VISIBLE bodies, one watertight STL per link) → `is_volume == True` pytest gate on every emitted mesh.
  Full doctrine: `references/colored-visuals.md` "THE EXPORT FLOW".
- **`is_volume` alone does NOT prove a mesh is intact.** A truncated stub is still
  watertight, so `is_volume` passes on it. Two extra guards are mandatory: (a) DETECT
  open-surface (`isSolid==false`) vendor bodies before the bake — the watertight-repair
  ladder truncates them; close them by fan-triangulating their boundary loops, never by
  the repair ladder; and (b) a TWO-SIDED per-link extent gate vs a known-good baseline
  catching SHRINK (truncation) as well as growth — not just growth. Both in
  `references/colored-visuals.md` "THE EXPORT FLOW" and `references/verification.md`.
- **Required outputs of a CAD→URDF pass.** Every pass ships THREE things, not just the
  meshes: (a) a SAVED standalone rigged/reframed Fusion doc in the link/datasheet frame
  (pristine vendor part live-linked, placed by the feature-derived link-frame matrix so
  link == doc identity) — and it must be NATIVE (break the live link so B-Rep is embedded;
  a live-linked doc's `.f3d` is a hollow stub), (b) its STEP export from that same doc,
  and (c) the baked URDF meshes. Full rule: `references/package-architecture.md`
  "Required outputs"; the f3d/breakLink/STEP traps: `references/fusion-cautions.md`.
- **Color lives in the mesh, not the URDF.** DEFAULT: visuals ship as COLLADA `.dae` with
  the CAD appearances embedded per body group; collision stays plain STL; no `<material>`
  tags on mesh visuals (the ur_description/husarion/Robotiq convention). ALL routes
  (no-color, base-color tag, per-material STL split, DAE) are compared in
  `references/colored-visuals.md`, with the pipeline, size discipline, gates, and the
  render-quality WHAT-NOT-TO-DO. **HARD RULE: STL-with-base-color is NEVER the default
  when the source Fusion file already carries color.**

## Scripts (reusable, parameterised)

Bundled in `scripts/` — each reads its parameters from a JSON file so nothing is
session-specific:

- `world_bake_export_stl.py` — copy a body/occurrence into a temp root component, bake
  its world transform, rename to the link name, export STL, discard the temp. The
  merged-per-link and neutral-mesh export primitive. (Fusion-side.)
- `overlap_probe.py` — boolean-intersection overlap volume between two parts (recursive
  solids + bbox pre-filter), with an optional axial sweep to find the flush seat. The
  CORRECTED coupling-measurement primitive (replaces a min-distance probe that was blind to
  interpenetration). (Fusion-side.)
- `linked_insert.py` — build a live-linked assembly correctly: `addByInsert(df, transform,
  isReferencedComponent=True)` into a fresh saved-in-project doc, all parts at identity then
  positioned (avoids the built-assembly corruption). (Fusion-side.)
- `transform_chain.py` — turn world occurrence transforms into a URDF-ready frame chain
  (from-origin + relative hops as xyz/rpy/quat). (Host-side, numpy.)
- `mesh_identity_check.py` — host-side dense point-cloud comparison of two STLs
  (cKDTree nearest-neighbour + optional Kabsch/ICP align). The q=0 verification
  primitive; does NOT depend on `rtree`. (Runs in a normal Python venv with scipy.)

Read the header of each script before running; each documents its JSON parameter schema.
