> Internal workflow loaded by the main skill. The plugin root comes from
> that skill. Resolve this workflow's `references/`, `scripts/`, and
> `evals/` paths relative to this directory.

# Assemble — robot + tool assembly topologies in Isaac Sim

The doctrine that came out of making the UR5e + QuickChanger + RG2 cell run in BOTH
topologies across two repos (prismatic-manipulation, robo-manipulate), including the
six-round crash bisection that ended in a one-line lifecycle fix. Core law:
**initialize physics on an empty stage, author topology from birth (never flip it),
filter mated pairs by name (never by blanket), and prove assemblies with signed
per-joint checks (never pad-gap swings).**

## The three topologies (two work, one never does)

| Topology | How | Status |
|---|---|---|
| **SPLIT** — arm + free coupler + gripper as separate articulations | Two `PhysicsFixedJoint`s with `physics:excludeFromArticulation=True` (maximal-coordinate welds); coupler is a plain rigid body between them | ✅ production (prismatic default) |
| **BORN-MERGED** — one articulation from birth | ONE URDF of the whole cell through the URDF importer (`fix_base=True`, `parse_mimic=True`, self-collision off or filtered) | ✅ production (dime workcell; prismatic `ur5e_rg2_cell`) |
| **FLIPPED-MERGED** — re-root a built split into one articulation | flip the welds' `excludeFromArticulation` + remove the gripper's `ArticulationRootAPI` (Robot Assembler `single_robot=True` end state) | ❌ **NEVER**: PhysX leaves per-joint INCONSISTENT FRAME SIGNS (a drive target of −0.0777 settles at +0.0788 — exact negation, per-joint, uncompensatable); mimics dislocate; identical on physx 107.3.18 and 107.3.26; minimal repro: prismatic `.local/physx_repro/` |

Choosing: split when the tool must stay independently addressable
(`SingleArticulation("/World/RG2_Gripper").apply_action` — action graphs, native drivers)
and the CAD has no baked inter-body overlap. Born-merged when the mount telescopes by
design (overlap is only collision-filterable cheaply within one articulation) or the
whole cell ships as one URDF. Same control surface either way if the driver resolves the
actuated joint BY NAME in whichever articulation owns it (auto-detect: does the gripper
root prim still carry `ArticulationRootAPI`?).

## THE lifecycle invariant (the CUDA-700 law)

**Initialize the `SimulationContext`/`World` on the EMPTY stage, asynchronously, BEFORE
authoring any articulation.** Deferring it until a robot loader's sync `World.reset()`
lets Fabric first populate on an articulation-bearing stage; assembling/rotating another
articulation afterward corrupts that population and the play() dies with
`carb.cudainterop CUDA error 700: cudaErrorIllegalAddress` (+ NVTT block-compression
noise). One poisoned CUDA context makes EVERYTHING downstream report 700 — including
PhysX — so **read the FIRST error in the log, not the loudest**. This single ordering
bug mimicked: contact explosions, weld-authoring bugs, GPU-solver bugs, renderer bugs,
asset defects — six bisection rounds of red herrings. Sequence, always:

```
new_stage → World() + await initialize_simulation_context_async()   # EMPTY stage
          → author robots/welds/objects → (filters) → play/settle
```

Also: **stop the timeline before any articulation-topology mutation** (PhysX parses
topology at play), and never flip topology on a carried-over live scene (wedged views
detach welds; the gripper free-falls).

## SPLIT recipe (the load-bearing details)

1. **Assets must be FLOATING-BASE**: `ArticulationRootAPI` on the tool's base LINK
   (e.g. `rg2_base_link`), no `fix_base` root joint. A bare export that kept the
   importer's `root_joint` anchors the tool to the WORLD — kill it with
   `jointEnabled=False` + `RemoveAppliedSchema` + **`SetActive(False)`**
   (`RemovePrim` CANNOT delete reference-composed prims — silent no-op).
2. **Mass-couple the articulation root**: a maximal weld to a zero-mass root is the
   infinite-mass-ratio extreme — it flexes (~4mm under finger reaction). Give the root
   real mass (0.5 kg) + inertia. The NVIDIA stability guide is about mass RATIOS, not
   "must be one articulation".
3. **Weld with schema APIs** (`UsdPhysics.FixedJoint.Define` + `CreateLocalPos0Attr`…)
   at frames computed from the CURRENT world poses (zero initial residual) — verify
   residual ≈ 0 pre-play.
4. **Filter the mount cluster** (see collision doctrine below).
5. Reference assets with an EXPLICIT source prim when they lack a `defaultPrim`
   (`AddReference(usd, "/onrobot_rg2")`) — a bare `add_reference_to_stage` composes null.

## BORN-MERGED recipe

One URDF of the full chain → importer (`merge_fixed_joints=False`, `fix_base=True`,
`parse_mimic=True`, `self_collision=False` or True+filters). Bake production tuning into
the asset at import: actuated drive gains, **zero the importer's default position drives
on mimic followers** (they LOCK the actuated joint), firm mimic springs, maxJointVelocity.
Commit the converter script — an asset without a committed reproducible converter strands
every future package update (both repos had exactly this gap). Load the cell AT the arm's
conventional prim path so name-based drivers work unchanged.

## Collision doctrine

- **Importer default = convexHull per link.** A hull FILLS concave pockets: a telescoping
  mount (QC-in-hand, ~40 cm³ hull overlap on 205 mm³ of real graze) jams instantly between
  separate articulations. This is why naive split "crashes on play" and why dimelab went
  merged-with-blanket-off — both are workarounds for missing filter metadata.
- **`enabledSelfCollisions=False` is a blanket that blinds the sim** (and only governs
  pairs WITHIN one articulation — useless across split articulations). The surgical tool
  is **`UsdPhysics.FilteredPairsAPI`**: pair-level, crosses articulation boundaries, works
  on free bodies. Adjacent (directly-jointed) pairs are auto-filtered by PhysX already.
  Rigidly-mated pairs (weld clusters) are filtered BY DEFINITION — their relative pose
  cannot change; their contact is pure noise.
- **Enumerate filter pairs from the LIVE scene, never from a cousin asset**: dump each
  rigid body's collider points + world transforms through the bridge, hull them, boolean
  pairwise (trimesh+manifold3d). Link frames differ between bakes of the same robot —
  the dime-frame list missed a 38 cm³ wrist↔hand pair present in the bare-export frames.
- **Cross-asset pairs can only be authored on the composed stage** (a rel can't target
  another file's prim) — put them in the loader; intra-asset filters can bake into the asset.
- **Export tolerance eats mate clearances**: CAD with 0.0 mm³ interpenetration can bake
  into meshes that graze (tessellation chord error ≥ design clearance → dozens of sliver
  contacts). Gate every collision bake with a pairwise-overlap check at the assembly pose.
  Watertight single-shell unions are the correct SOURCE (SDF/decompose/decimate all need
  volumes); fragmented per-body exports are unusable however small they are.

## Mimic / linkage verification (the parallelogram law)

PhysX mimic relation: **`follower = −gearing × reference`** (get the sign wrong and a
perfect linkage "fails" with dev = 2×θ — this exact bug produced a false "degraded sim"
alarm). Verify a mimic-driven gripper by commanding the actuated joint and asserting
`|follower + gearing×actuated| < 0.02` on EVERY follower. **A pad-gap swing or L/R
symmetry check cannot distinguish a symmetric dislocation from a coherent parallelogram**
— the historical merged "verification" passed on a dislocated linkage. Drive tuning does
not transfer between topologies: acceleration-type drives scale with the reflected
inertia of the owning tree.

## Debug playbook (each row cost real time)

| Symptom | Reality |
|---|---|
| Kit process dies at play, CUDA 700 | Lifecycle invariant violated (see above). Read the FIRST log error; everything after a poisoned context lies. |
| Edits/reloads have no effect inside Kit | Stale `.pyc` (launch Kit with `PYTHONDONTWRITEBYTECODE=1`; purge `__pycache__`); new modules invisible until `importlib.invalidate_caches()`; verify against the CODE OBJECT (`co_varnames`), not `inspect.getsource` (reads disk, lies). |
| Re-opened asset shows old content | Sdf layer cache — `Sdf.Layer.GetLoadedLayers()` + `Reload(force=True)` for layers under the asset dir, or inspect in a fresh process. |
| `is_homogeneous` on None / dead tensor view | Duplicate `SingleArticulation` on one articulation — REUSE cached handles (match `prim_path` by PREFIX: it resolves to the root-joint prim, not your constructor path). Fresh views after play need app-loop warmup (`await next_update_async()`, ~90 frames) — `world.step(render=False)` never pumps the loop that builds the sim view. |
| Physics attribute "set" but ignored | Bare attribute without its API schema in `apiSchemas` — the parser skips it. Always `Apply()` the API; audit with `prim.HasAPI(...)` or the live physics view, never composed-attribute dumps. |
| Traversal finds no colliders/joints | Instanceable assets — traverse with `Usd.PrimRange.Stage(st, Usd.TraverseInstanceProxies())`. |
| Gripper explodes on teleport | Never `set_joint_positions` across a maximal weld — drive TARGETS through the solver, or make the snap weld-aware (disable welds → move → re-seat → re-enable). |
| Weld "removed" but still active | `RemovePrim` on a referenced prim is a no-op — `SetActive(False)`. |

## Verification loop (done means all of these)

1. Settle: play N frames → arm `at_rest`, `max_qd ≈ 0`, no log errors.
2. Mimic parallelogram: residuals < 0.02 rad on all followers (see law above).
3. Weld rigidity: flange→tool-base distance constant through open/close/open (±0.01 mm).
4. Both topologies if both exist: the identical native pipeline (home → open → hover →
   descend → force-limited close → lift) passes in each; part lift > 50 mm proves grip.
5. The OTHER mode still works after your change (topology fixes love to break the sibling).

## Project integration

Locate the user's import scripts, scene loaders, driver interfaces, and USD
assets before editing. Apply the lifecycle and topology rules above to those
implementations. Keep minimal reproductions and verification records with the
project; do not assume a particular checkout, robot name, or workstation exists.

Companion skills: `/fusion:fusion (assemble workflow)` (CAD frames and mate proof),
`/fusion:fusion (cad-to-urdf workflow)` (mesh export), `../add-physics/workflow.md` (collider authoring),
and `../urdf-to-usd/workflow.md` (conversion and drive verification).
