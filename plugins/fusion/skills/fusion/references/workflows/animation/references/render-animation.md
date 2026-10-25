# Render Animations in Fusion 360

Produce **rendered animation videos** from a Fusion design — assembly/disassembly
sequences, exploded views, turntables, joint motion — by keyframing the scene
ourselves and ray-tracing each frame, then stitching to MP4.

## Contents
- [Why this approach (the API wall)](#why-this-approach)
- [The render API (what Fusion *does* expose)](#the-render-api)
- [Workflow](#workflow)
- [Job file schema](#job-file-schema)
- [The camera rig](#the-camera-rig)
- [Stitching to MP4 (ffmpeg)](#stitching-to-mp4)
- [Quality and timing](#quality-and-timing)
- [Tuning the look](#tuning-the-look)
- [Gotchas](#gotchas)
- [Animation taxonomy and roadmap](#animation-taxonomy-and-roadmap)

---

## Why this approach

Fusion has an **Animation workspace** (storyboards, "Publish Video"). It is
**not authorable through the API.** The `Storyboard` object exposes only playback
(`play`, `playheadPosition`, `reverse`, `end`) — there is **no API to create
transform/camera keyframes**. A scripted `transform2` move never records into the
storyboard (verified: a moved part stays constant across all playhead times and
`storyboard.end` never leaves `0.0`). Recording only happens from the interactive
Transform-Components dialog, which the bridge cannot drive headlessly.

So we don't use the storyboard at all. Instead:

> **We own the sequencing; Fusion owns the rendering.** Each frame is a pure
> function of its index — `frame_state(idx)` sets part poses + visibility,
> `camera_state(idx)` sets the camera — and Fusion ray-traces that frame via
> `RenderManager.inCanvasRendering`. We `saveImage` each frame and `ffmpeg` the
> PNGs into a video.

Because frames are pure functions of the index, any frame range re-renders
independently (so we can chunk the render across bridge calls and avoid one giant
blocking call), and **quality is a single knob** — draft now, re-render clean later
with zero changes to the motion.

The engine is `scripts/render_animation.py`. This doc is how to drive it.

---

## The render API

`design.renderManager` (all introspected live, not guessed):

| Need | API | Notes |
|---|---|---|
| Enter render env | `renderManager.activateRenderWorkspace()` | required before in-canvas |
| Advanced ray-trace | `inCanvasRendering.isAdvanced = True` then `.start(quality)` | `quality` 0–1: `0.75`=Excellent, `1.0`=Final; **auto-stops** at quality |
| Fast preview | `isAdvanced = False` then `.start(0)` | runs forever until `.stop()`; flatter look |
| Save a frame | `inCanvasRendering.saveImage(fullpath)` | `.png/.jpg/.tiff`; **size = the viewport size** |
| Progress | `.iterations`, `.elapsedTime`, `renderComplete` event | poll `iterations` inside a `doEvents()` loop |
| Lock view | `.lockView = True` | prevents drift mid-accumulation |
| Gallery render | `renderManager.rendering.startLocalRender(...)` + `resolutionWidth/Height`, `renderQuality` | highest quality, slower; not used by the engine (in-canvas is better for many frames) |
| Scene look | `renderManager.sceneSettings`: `backgroundType`, `brightness`, `cameraExposure`, `isGroundReflections`, `groundRoughness`, `lightAngle`, depth-of-field | global environment/lighting |

Output **resolution = the Fusion viewport size**, so maximize the Fusion window
before a final render for higher-res frames.

---

## Workflow

1. **Open the assembly.** `fzd-fusion project open --project ... --folder ... --file ...`
2. **Inspect parts.** `fzd-fusion --json design components` → component base-names.
3. **Get the assembly ORDER.** From the assembly manual image (read it via GPT —
   `/ask-gpt`, never Claude's own image read), or ask the user. Order = the
   sequence parts seat into the build. The foundation part(s) go in `always_visible`.
4. **Write the job file** (`/tmp/fusion_anim_job.json`, schema below). Start with
   `"range": null` — a **planning call** that captures the seat poses + camera
   calibration to the cache and returns the total frame count.
5. **Planning call:**
   ```bash
   SCRIPT="skills/fusion/references/workflows/animation/scripts/render_animation.py"
   printf 'exec(open("%s").read())\n' "$SCRIPT" > /tmp/anim_driver.py   # or write the path literally
   fzd-fusion --json exec - < /tmp/anim_driver.py
   ```
   Read `total` from the result. Confirm the parts are at their **assembled** state
   when this first runs (the engine captures "current pose = seat" once, into the
   `assembled_cache`). Delete that cache to recapture after editing the assembly.
6. **Render in chunks.** Set `"range": [a, b]` (~20–25 frames per call) and exec the
   driver again per chunk. Each chunk writes `frame_%04d.png` into `outdir`.
   Chunking keeps any single bridge call short.
7. **Stitch to MP4** with ffmpeg (below).
8. **Verify** a few frames / the video via GPT before declaring done.

**Tip:** validate motion + camera with a *fast/low* quality pass first
(`quality: 0.3`), then re-render clean (`0.75`) once the timing looks right —
same job, just bump `quality`.

---

## Job file schema

`/tmp/fusion_anim_job.json` (override path with env `FUSION_ANIM_JOB`):

```json
{
  "parts":          ["partA","partB","partC","partD"],
  "always_visible": ["base"],
  "raise_cm":       13.0,
  "intro": 6, "drop": 18, "settle": 4, "outro": 12,
  "camera": {"azimuth":[-55,20], "elevation":[45,22], "dolly":[1.25,0.92],
             "center_z": 3.0, "dist_mul": 1.4},
  "quality":  0.3,
  "cap_s":    6.0,
  "outdir":   "/tmp/anim_frames",
  "assembled_cache": "/tmp/anim_assembled.json",
  "range":    [0, 23]
}
```

| Field | Meaning |
|---|---|
| `parts` | component base-names in **assembly order** (these animate, one drop each) |
| `always_visible` | foundation parts shown the whole time (don't animate) |
| `raise_cm` | how far above its seat each part starts its drop |
| `intro`/`drop`/`settle`/`outro` | frame counts; total = `intro + len(parts)*drop + outro` |
| `camera.azimuth/elevation/dolly` | `[start, end]` for orbit angle / elevation angle / distance multiplier |
| `camera.center_z` | height of the orbit target (assembly mid-height, cm) |
| `camera.dist_mul` | base distance = (iso-fit distance) × this |
| `quality` | in-canvas ray-trace quality 0–1 |
| `cap_s` | max seconds to accumulate per frame (safety cap) |
| `range` | `[a,b)` frames to render this call; `null` ⇒ planning-only (capture cache, report total) |

---

## The camera rig

The camera is a keyframed function too — eye placed on a sphere around the
assembly center, three independently-eased channels (all `smootherstep`, so no
velocity discontinuities):

- **Azimuth** sweeps `azimuth[0]→[1]` across the whole timeline → continuous parallax.
- **Elevation** descends `elevation[0]→[1]` over the first ~70% (start high to
  establish the empty base, lower so drops are seen entering from above), with a
  small hero rise at the very end.
- **Dolly** (radius ×) establishes wide, pushes in over the first third, with a
  final beauty push at the end.

`isSmoothTransition=False` so each frame is placed exactly (no Fusion tween
fighting the keyframe). Target stays at the assembly center so the build stays
composed. To change the feel, edit the `camera` ranges in the job; for a full
turntable use `azimuth:[0,360]` with a static `frame_state` (see taxonomy).

---

## Stitching to MP4

```bash
ffmpeg -y -framerate 20 -start_number 0 -i <outdir>/frame_%04d.png \
  -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p" \
  -c:v libx264 -crf 19 -movflags +faststart <out>.mp4
```

- `-framerate` sets pace; lower = slower/more watchable (18–24 typical).
- The `scale=trunc(...)` makes dimensions even (h264/yuv420p requires it).
- Ask the user where to save the final MP4 — keep throwaway drafts in `/tmp`.

---

## Quality and timing

| quality | look | ~time/frame | use |
|---|---|---|---|
| `0.3` | grainy but readable | ~3–5 s | draft to validate motion/camera |
| `0.75` (Excellent) | clean, near-photoreal | ~10–30 s | final deliverable |
| `1.0` (Final) | max | 30 s–1 min+ | hero shot only |

Moving a part **resets accumulation**, so every frame re-accumulates from scratch
— that per-frame cost is inherent. A ~90-frame board at `0.75` is roughly a
20–40 min render. Budget accordingly; render overnight for Final.

---

## Tuning the look

- **Pace:** `-framerate` in ffmpeg, or `drop`/`settle`/`outro` frame counts.
- **Hang time:** higher `raise_cm` + the ease-in-out drop already makes parts hang
  high before a soft landing.
- **Camera drama:** widen `azimuth` for more orbit; lower `elevation[1]` for a more
  side-on, dramatic build; `dolly` end < 1.0 for a push-in finish.
- **Resolution:** maximize the Fusion window (output = viewport size).
- **Environment:** `sceneSettings` for background, brightness, ground reflections,
  light angle — set once before rendering for a different mood.

---

## Gotchas

- **Run on Fusion's main thread.** The bridge marshals there; never thread into the API.
- **Seats captured once.** "Assembled" = the design's current state at first run,
  cached so chunks stay consistent. If parts aren't assembled at first run, the
  cache is wrong — delete it and recapture with the assembly seated.
- **Direct mode is forced** so `transform2` sets are absolute and cheap. The doc is
  never saved → non-destructive.
- **Raising in world Z** = adding to the matrix translation's `z` (the part's world
  origin), correct regardless of the part's rotation.
- **Window size = output size.** Don't resize Fusion mid-render.
- **Don't `saveAsImageFile` (viewport grab) for finals** — use
  `inCanvasRendering.saveImage` so you get the ray-traced result, not the shaded view.

---

## Animation taxonomy and roadmap

Everything below renders through the **same pipeline** (per-frame scene state →
in-canvas ray-trace → ffmpeg). What changes is *what `frame_state(idx)` drives*.
That's the extension point — adding an animation type means adding a state
function, not new rendering.

**Axis 1 — what's being animated:**

| Type | What moves per frame | Status |
|---|---|---|
| **Assembly / disassembly** | part transforms toward/away from seats, in order | ✅ built (`render_animation.py`) |
| **Exploded view** | part transforms OUTWARD along radial/axis vectors (static pose or animated explode/collapse) | 🔜 small variant — replace the Z-drop with a per-part explode vector |
| **Turntable / camera-only** | nothing; camera orbits 360° around a static (assembled) model | 🔜 trivial — static `frame_state`, `azimuth:[0,360]` |
| **Flythrough** | camera follows a path/spline; model static | 🔜 camera path sampler |
| **Joint actuation / mechanism** | drive Fusion **joints** (revolute/slider `jointValue`) or child-occurrence transforms about an axis — gripper opening, hinge, arm sweep | 🔜 joints ARE scriptable; add a joint-driver state fn |
| **Appearance / highlight** | per-part opacity/color (ghosting, highlight the active part, fade-in) via the Appearance API | 🔜 appearance-swap state fn |
| **Parameter morph** | drive `userParameters` over frames on a parametric design (telescoping, configurator sweep), recompute, render | 🔜 needs parametric (not direct) mode |
| **Section / cutaway** | animate a section plane sweeping through to reveal internals | 🔜 investigate section API support |
| **Path / trajectory follow** | move an object along a sampled path (tool on toolpath, part on conveyor) | 🔜 path sampler + transform |

**Axis 2 — composition (combine any of the above):**
- Camera trajectory is **orthogonal** and already layered on every type.
- On-frame callouts / labels / leader lines are best **composited in post**
  (ffmpeg/overlay), since Fusion render text is limited.

**Out of scope (be honest about the walls):**
- Native Fusion storyboard / "Publish Video" — API can't author it.
- Physics (gravity, collisions, contact) — not a Fusion design capability; that's
  simulation (e.g. Isaac Sim) territory.
- FEA result playback (Simulation workspace) — separate, limited API.

When folding a new type in: add its `frame_state`-style function to
`render_animation.py` (selected by a job `mode` field), document its job fields
here, and add a row above with status ✅.
