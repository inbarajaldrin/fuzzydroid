# Motion discovery — where the trajectory comes from

The skill authors motion; it doesn't invent it. Three ways to arrive at the keyframes/trajectory that
`author_anim.py` turns into a USD layer. Pick by how obvious the path is.

## 1. Sequential drop-in (computed) — the default for multi-part boards
A stacking/insertion board (FMB, furniture) doesn't need a hand-authored path: the anchor stays put and
each part appears and drops into its seated pose in assembly order. `sequential_motion.py` computes this
straight from `poses.json` + `assembly.json` (approach = seated + `lift_mm` along +Z; per-part time
window `[k/m, (k+1)/m]`; hidden until its turn). With `loop:true` the assemble reverses into a teardown.
Use this first for any board; only reach for a bespoke path when a part's motion isn't a straight drop.

## 2. Parametric / by-hand (mating pairs)
A two-part mate often has a specific path — drop-then-twist (bayonet), pure slide (dovetail), tilt-in-
then-rotate-flat about a pivot (hook-slot). Author the keyframes directly in the spec, or compute them
from a small parametric function and emit the keyframe list. Keep `t ∈ [0,1]` for the *engage* half; the
loop gives you disengage free. Quaternions are wxyz and get slerped, so two keyframes suffice for a pure
rotation (e.g. `[1,0,0,0] → [cos20°,0,0,sin20°]` for +40° about Z).

## 3. HTML/JS viewer (interactive) — best for a non-obvious mate
This is how the bayonet/dovetail/hook paths were originally found: `references/generate_example.py`
builds an **interactive HTML viewer** with a **scrub slider** bound to a JS `trajectory(t)` — you drag
the slider and watch the moving part thread into place, tuning offsets/angles/pivots live. It's far
easier to *find* a threading motion (a pivot that clears a wall, an approach offset) by eye than by
guessing numbers. Once it looks right, the trajectory is just a function of `t`; extract it:

- The JS `trajectory(t)` returns, per frame, the moving part's pose — e.g. `{ang, dx, dz, label}` for a
  revolute-about-pivot, or `{z, rot}` for a lower-then-twist. The Python side of the same `generate.py`
  usually mirrors it (`pose()/trajectory()` with the constants as CAD-exact values).
- To convert to keyframes: sample `trajectory(t)` at the phase boundaries (the `if t<…` breakpoints in
  the JS) and at the endpoints, compute the moving part's world transform at each (fold any pivot into
  the translate+quat — `world = T_translate · R_pivot`), and drop those `(t, translate_mm, quat_wxyz)`
  into the motion spec. Interpolation between them is `author_anim.py`'s job (lerp + slerp).
- Watch the convention: `generate.py`'s `pose_panel` composes **column-vector** `Tt.dot(_rot(angle))`
  (rotate about the Y-pivot first, then translate) — decompose the *net* 4×4, don't copy the raw dx/dz.

### Extraction recipe (JS trajectory → keyframes)
1. Read the phase breakpoints and constants from `generate.py` (`PIVOT`, `TILT_DEG`, `APPROACH`, seated
   heights, hook sweep, …).
2. For each breakpoint `t*`, build the moving part's world 4×4 the way `pose()` does, then decompose to
   `translate_mm` (m×1000) + `quat_wxyz`.
3. Emit `{t: t*, translate_mm, quat_wxyz}` (drop redundant fields — they carry forward).
4. `author_anim.py` sultures them into a seamless USD layer.

## Which to use
| assembly kind | discovery |
|---|---|
| stack / multi-part board (FMB, furniture) | **sequential_motion.py** (computed) |
| simple mate with an obvious path (pure slide, straight drop) | by-hand keyframes |
| mate with a threading/pivot path that must clear geometry | **HTML/JS viewer** → extract |

Whichever you use, the output is the same motion spec, and the authored `<asm>.anim.usda` is validated
the same way: play it against the `_physics` colliders (build the scene with `--ref-suffix _physics.usd`)
and confirm no interpenetration — a wrong path shows itself.
