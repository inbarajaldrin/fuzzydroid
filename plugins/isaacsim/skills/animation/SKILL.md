---
name: animation
description: Author the non-baked ANIMATION layer for a CAD assembly — an EXPLODED-VIEW mating animation where the moving parts converge along their mate axis into their assembled poses, as time-sampled xformOps in a removable USD sublayer over the scene. Kinematic, not a physics sim: fix the upstream ROOT part (the one others connect to, not a ground part), converge the rest in the upstream mate order along the joint's axis (vertical for a tenon/socket, horizontal for a drawer slide), then prove the path with the bundled interpenetration gate before recording. The MOTION is discovered upstream — by hand, a parametric trajectory, the sequential exploded-view default, or an HTML/JS viewer — and this skill AUTHORS it into USD, then previews/records it (auto-framed camera). Distinct from /fusion:animation (a Fusion 360 ray-traced render) — this is USD scene authoring for Isaac Sim.
---

## Agent host compatibility

This skill works in Claude Code and Codex. Resolve symlinks on this file; the
plugin root is three parent directories above this `SKILL.md`. Use that absolute
root for `plugins/<plugin>/...` examples, regardless of the working directory.
When `CLAUDE_PLUGIN_ROOT` is unavailable, pass the resolved root under that name
to commands that use it. Use the host's equivalent tools for `Bash`, `Read`,
`WebFetch` and user questions. In Codex, `$plugin:skill` invokes the sibling skill
named by a `/plugin:skill` reference. Read sibling `SKILL.md` files directly when
needed; do not assume another host's slash commands exist.

# animation (USD assembly animation)

Author the **animation layer** for an assembly: the moving part(s) following a trajectory into (and out
of) their assembled poses, as **time-sampled `xformOp:translate` + `xformOp:orient` (+ visibility) in a
non-baked `<asm>.anim.usda` sublayer over the scene**. Delete the layer and the geometry is untouched.

The division of labour is deliberate: **you (or discovery) decide *what* the motion is; the skill
authors it.** The skill is not blind — it takes a motion you've discovered (a slider-tuned trajectory,
a parametric path, or the default sequential drop-in) and turns it into a clean, loopable USD layer.

## The mental model: this is an EXPLODED-VIEW mating animation (not a physics sim)

The default sequential motion is an **exploded assembly diagram in motion**, and framing it correctly is
what makes it look right. Internalize these four rules:

1. **Kinematic, not gravity.** Parts follow authored xform tracks to their seated target and **stop**.
   Nothing falls, nothing settles, there is no physics engine running during the anim. Do not reason
   about "which part rests on the ground" — reason about **which part everything else connects to**.
2. **Fix the ASSEMBLY ROOT, not a ground part.** The anchor (`base_part` in `assembly.json`) must be the
   **upstream reference part — index 0**, the part the others mate onto. For FurnitureBench that is
   `should_be_assembled`'s root: the tabletop for a table (legs mate into it), the seat for a stool, the
   central column/top for a pedestal, the cabinet box for a drawer. It is NOT the part that happens to
   rest on the floor. (A ground-resting `base_part` is a leftover from the settle pipeline — override it.)
3. **The target is the seated pose (`poses.json`); every mover converges to it along its MATE AXIS.**
   The explode direction is the axis the part separates along, read from the upstream relative pose —
   *vertical* for a leg/tenon into a socket (`--axis z`), *horizontal* for a drawer that slides in
   (`--axis y`/`x`). A part starts exploded off its seat along that axis and slides straight in. The
   mate axis is a property of the JOINT, not of gravity — legs "rising up" into a fixed tabletop is
   perfectly correct as an exploded view even though nothing rises under gravity.
4. **Prove the mate path with the collision gate.** `scripts/check_interpenetration.py` replays the anim
   off-sim and measures TRUE mesh overlap per frame. A clean mate slides to a ~0 mm clearance fit; a part
   that tunnels through another (wrong axis, wrong order, or a leg driven down *through* the top) shows
   deep sustained overlap. The gate must PASS before you record.

So the recipe for any multi-part FurnitureBench object: **extract the upstream root + mate order + mate
axis → fix the root → converge the rest in order along the axis → gate → record.**

## Requirements (external pipeline deps — real, not bundled)

This skill authors USD but drives/records through an **external Isaac pipeline** that
must exist on the machine. These are genuine dependencies, documented here rather than
rewritten:

- **`~/Documents/isaacsim/`** — the pipeline root. The CAD/USD env runs as
  `cd ~/Documents/isaacsim && uv run python …` (trimesh, usd-core, pxr, …).
- **`~/Documents/isaacsim/scene_tools/`** — the sim-side module dir the bridge loads
  inside Isaac Kit. This skill's `scripts/view_stage.py` + `scripts/record.py` execute
  *there* as `scene_tools` (they `import omni.*` / `isaacsim.*` — not runnable on the
  Mac standalone). Keep the bundled copies in sync with `scene_tools/`; `bridge.py sync`
  copies that dir to the sim box.
- **`bridge.py`** at the pipeline root — the omni.kit.mcp bridge front-end
  (`python3 bridge.py {sync,view_stage,record,screenshot}`).
- **`usdrecord` + `ffmpeg` on PATH** — the ONLY deps of the standalone recorder
  (`scripts/record_usd.py`). This path needs NO Isaac Sim: `usdrecord` renders USD via
  Hydra/Storm (Metal/GL). Present wherever a USD build ships (e.g. `/usr/bin/usdrecord`
  on macOS). Use it when Isaac isn't available or for fast previews.
- **Upstream skill `/isaacsim:add-physics`** — produces the `<part>.collision.usda` /
  `<part>_physics.usd` layers this skill plays the animation against, and validates the
  assembly order first (see below).

## Operating environment
- Pipeline root `~/Documents/isaacsim/`; CAD env `cd ~/Documents/isaacsim && uv run python …`.
- Drive/preview Isaac with `python3 bridge.py {sync,view_stage,record,screenshot}`.
- Layers per part: geometry `<part>.usd` · collision `<part>.collision.usda` · physics `<part>_physics.usd`
  (all from **/isaacsim:add-physics**) · **animation `<asm>.anim.usda` ← THIS SKILL** (sublayers the scene).

## Runs AFTER /isaacsim:add-physics — and why
Author colliders + confirm the parts settle first. With physics, a wrong assembly **order** is rejected
(parts can't pass through each other), and playing an animation whose trajectory drives a part *through*
another exposes a bad path — the same signal the runtime agent uses. So lock the physical assembly
(/isaacsim:add-physics), then author the motion here. Point `build_scene.py --ref-suffix _physics.usd` at the
collision/physics layers when you want to play the motion against real colliders.

## Workflow
0. **Extract the assembly spec from upstream.** Read the object's upstream definition (for FurnitureBench:
   `furniture_bench/furniture/<obj>.py`) for the **root part (index 0)**, the **mate order**
   (`should_be_assembled`), and the **mate axis / direction** (from `assembled_rel_poses`). Set
   `assembly.json`'s `base_part` to the root and `assembly_order` to root-then-movers-in-mate-order; record
   an `upstream` provenance block. **Confirm the mate axis** (e.g. a drawer's slide direction) against the
   parametric source or by asking — don't assume vertical.
1. **Scene** — `scripts/build_scene.py <board_dir> [--ref-suffix _physics.usd]` → `<asm>.scene.usda`
   (references each part — by its `geometry` field, so N instances can share one mesh — at its seated pose
   + dome/key lights).
2. **Motion spec** (`<asm>.motion.json`). Three ways (see `references/motion-discovery.md`):
   - **Sequential exploded-view** (default): `scripts/sequential_motion.py <board_dir> --axis <x|y|z>
     --offset-mm <signed>` computes it from `poses.json` + `assembly.json` (root static; each mover starts
     exploded off its seat along the mate axis and converges in order; reverses on the loop for teardown).
     `--axis z --offset-mm -70` = converge upward (legs into a fixed tabletop). `--axis y --offset-mm -90`
     = slide in along +Y (a drawer that opens toward −Y). `--lift-mm` is the legacy z-only alias.
   - **Parametric / by-hand** (mating pairs — drop-then-twist, slide, tilt-then-rotate): write the
     keyframe list directly (`t ∈ [0,1]`, `translate_mm`, `quat_wxyz`, `visible`).
   - **HTML/JS extraction**: tune the trajectory in an interactive viewer, then read its keyframes.
3. **Author** — `scripts/author_anim.py <asm>.motion.json` → `<asm>.anim.usda` (time-sampled
   `xformOp:translate`/`orient` + `visibility`, `loop` wraps time with a triangle → seamless).
4. **Gate — MANDATORY before recording** — `scripts/check_interpenetration.py <asm>.anim.usda
   [--threshold-mm 1.0]` replays off-sim and measures true mesh overlap per frame. Must print **PASS**. A
   FAIL localizes the offending pair + frame (wrong axis/order/direction → the mover tunnels through a part).
5. **Preview / record** — two backends, pick per environment:
   - **Isaac (in-sim, live viewport):** `bridge.py sync`; `bridge.py view_stage '{"path":".../<asm>.anim.usda",
     "view":"front"}'`; `bridge.py record '{"out":"/tmp/<asm>","loops":2}'` → mp4. Highest-fidelity (RTX/materials);
     needs a running Isaac Sim.
   - **Standalone (no Isaac):** `scripts/record_usd.py` renders the anim through **`usdrecord`** (Hydra/Storm —
     Metal on macOS) + ffmpeg, no Kit runtime. `uv run --no-project --with usd-core --with numpy python
     scripts/record_usd.py <asm>.anim.usda --mp4 /tmp/<asm>.mp4 [--width 800] [--elev 28 --azim -58]` → mp4.
     It fits ONE fixed look-at camera over the whole-animation envelope (so the subject doesn't "breathe" as
     parts converge) and wraps two `usdrecord` quirks (mandatory `###` placeholder; only the `###.###` form
     numbers cleanly). Use it for quick previews / CI / any box without Isaac; use the Isaac backend for final
     lit renders.

   **Pick the view so the mate axis is NOT along the line of sight**: `front` (looks down −Y) for vertical/​X-axis
   mates; `iso` for a Y-slide (a drawer) so the motion reads diagonally. Both backends auto-frame the full motion
   envelope and scale to assembly size.

## Motion spec (the contract)
```json
{ "assembly":"bayonet-lock", "scene":"bayonet-lock.scene.usda", "fps":24, "frames":96, "loop":true,
  "parts":[ {"name":"plug", "keyframes":[
      {"t":0.0,"translate_mm":[0,0,65],"quat_wxyz":[1,0,0,0]},
      {"t":0.5,"translate_mm":[0,0,13]},
      {"t":1.0,"quat_wxyz":[0.9397,0,0,0.3420]} ]} ] }
```
`t ∈ [0,1]`; a missing `translate_mm`/`quat_wxyz`/`visible` **carries from the previous keyframe**.
translate is mm→m; quat is wxyz (slerped); `visible` steps (appear/disappear). Poses are the part's
**world** pose (the anim overrides `/World/<part>`'s xform, which the scene set to the seated pose).

## Guardrails — what NOT to do
- **Don't fix a ground part as the anchor.** The anchor is the upstream ROOT (part 0), the thing others
  mate onto — override a settle-era ground `base_part`. A stool anchors on the *seat*, not a leg; a
  round-table pedestal on the *top*, not the base.
- **Don't reason about gravity.** No physics runs during the anim. "Legs can't rise from the floor" is the
  wrong instinct — this is an exploded view; parts converge along the mate axis regardless of up/down.
- **Don't assume a vertical drop.** Read the mate axis from the upstream relative pose. A drawer slides
  horizontally (`--axis y`); driving it down with `--lift-mm` tunnels it through the cabinet.
- **Don't look down the mate axis.** If the slide is along −Y, a `front` view (also along −Y) hides the
  motion — use `iso`. Match the camera to the motion.
- **Don't invent the trajectory blind.** The path is discovered/guided; the skill authors it. For a
  non-trivial mate, prototype it (HTML viewer or parametric) and *watch* it before committing keyframes.
- **Don't bake motion into the geometry or scene.** It lives ONLY in `<asm>.anim.usda`; removing the
  sublayer must leave a clean static scene.
- **Don't mismatch the xformOp order.** The scene authors `[translate, orient]` on `/World/<part>`; the
  anim overrides those same ops — don't add a differently-ordered op set.
- **Don't record before the gate passes.** `check_interpenetration.py` must print PASS. It measures TRUE
  signed-distance overlap (not fcl contact-margin noise), so a clearance fit reads ~0 and only a real
  tunnel fails — no excuse to skip it.
- **Don't trust a PASS with a `[WARN] NON-WATERTIGHT` line.** That result is UNVERIFIED — a non-watertight
  part can hide a real overlap as a false 0. Fix the mesh first (re-tessellate via Fusion STL, above), or
  run `--require-watertight` so it fails loudly. A "clean" reading you can't sign is not clean.
- **Don't fight the loop.** `loop:true` triangle-wraps time (assemble → disassemble). Author keyframes
  for the forward (assemble) half only; the reverse is free and seamless.
- **Units/axis:** metres, Z-up, `metersPerUnit=1` (the scene enforces it); keyframe translate is mm.

## Tools this skill packages
- `scripts/build_scene.py` — the seated-pose scene layer (+ optional `_physics` refs for collider play).
  References each part by its `geometry` field, so shared-mesh instances (leg1..leg4 → one leg.usd) work.
- `scripts/sequential_motion.py` — the sequential exploded-view motion spec from a board. `--axis {x,y,z}`
  + `--offset-mm` set the mate axis and explode distance/direction (root stays fixed).
- `scripts/author_anim.py` — the core: motion spec → time-sampled `<asm>.anim.usda`.
- `scripts/check_interpenetration.py` — the **no-pass-through gate** (run before recording). Off-sim,
  per-frame TRUE overlap: fcl's collision BOOLEAN picks which pairs actually touch (a precise pre-filter —
  a bounding-box test is far too coarse for nested parts), then exact SIGNED-DISTANCE gives the depth
  (fcl's own contact-depth is margin noise, unused). Meshes built once + re-transformed per frame. PASS/FAIL
  + worst pair/frame. `--stride N` for nested/detailed parts (a real tunnel spans many frames). Needs
  `--with trimesh --with python-fcl --with rtree`.
  **Watertight is REQUIRED for a trustworthy result:** signed-distance has no inside/outside sign on a
  non-watertight mesh, so a pair involving one can read a **false 0** (silently clean). The gate now
  prints a loud `[WARN] NON-WATERTIGHT parts: …` and marks the verdict `UNVERIFIED`; pass
  `--require-watertight` to turn that into a hard FAIL. If a part is non-watertight it's almost always a
  **STEP→OpenCASCADE tessellation defect** (non-manifold edges where a pocket meets a curved face) — a
  fresh STEP re-export reproduces it deterministically, and mesh-surgery (pymeshfix) drifts geometry.
  The shape-preserving fix: **re-tessellate the same solid via Fusion's own STL exporter**
  (`createSTLExportOptions`, high refinement), then swap that clean mesh into the geometry USD (points +
  triangles, keep the USD's material/prim structure). Same shape, watertight topology.
- `references/motion-discovery.md` — direct vs parametric vs HTML/JS-extracted, and how to pull a
  trajectory out of a JS viewer.
- `references/generate_example.py` — a bundled `generate.py` (bayonet-lock): the interactive HTML/JS
  viewer + `trajectory(t)` pattern, as the discovery option.
- `scripts/view_stage.py` + `scripts/record.py` — **bundled** sim-side tools (open + frame a stage;
  play + capture frames → ffmpeg mp4). They execute *inside* Isaac as `scene_tools` — i.e. you invoke
  them with `bridge.py view_stage '{...}'` / `bridge.py record '{...}'` after `bridge.py sync` (which
  copies `scene_tools/` to the box). Bundled here so the skill carries its own recorder; keep them in
  sync with `~/Documents/isaacsim/scene_tools/` (that's the copy the bridge actually loads).
- `scripts/record_usd.py` — the **standalone (no-Isaac) recorder**: renders the anim via `usdrecord`
  (Hydra/Storm) + ffmpeg on the local machine, no Kit runtime. Auto-fits a fixed look-at camera over the
  animation envelope so the subject doesn't "breathe" as parts converge. CLI `python record_usd.py
  <asm>.anim.usda --mp4 out.mp4` or programmatic `record_usd.render(stage, mp4=...)`. The complement to
  `record.py`: same job (anim → looping mp4), different backend — reach for it when Isaac isn't running or
  for a fast preview; `record.py` for final RTX-lit output. Mirror at `~/Documents/isaacsim/record_usd.py`.
