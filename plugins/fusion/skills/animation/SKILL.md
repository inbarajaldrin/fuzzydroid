---
name: animation
description: Render animation videos and ray-traced frames from an Autodesk Fusion 360 design via the fuzzydroid fzd-fusion bridge — assembly / disassembly sequences, exploded views, turntables, and joint-motion clips. Because Fusion's Animation workspace is not authorable through the API, this skill OWNS the sequencing (each frame is a pure function of its index — part poses + camera) and lets Fusion ray-trace each frame with RenderManager.inCanvasRendering, then stitches the PNGs to MP4 with ffmpeg. Use whenever the user wants to "animate the assembly", "render a build/disassembly video", "make an exploded-view animation", "turntable render", "ray-trace / photoreal frames of this Fusion design", "show the parts dropping into place", or a rendered clip of a CAD mechanism moving. This is the FUSION-render animation (ray-traced frames); for USD/Isaac scene assembly animation see /isaacsim:animation.
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

# Fusion render animation

Produce rendered animation videos from a Fusion design by keyframing the scene
ourselves and ray-tracing each frame, then stitching to MP4. Fusion's Animation
workspace (storyboards, "Publish Video") is **not authorable through the API**, so we
don't use it: **we own the sequencing; Fusion owns the rendering.** Each frame is a
pure function of its index — `frame_state(idx)` sets part poses + visibility,
`camera_state(idx)` sets the camera — and Fusion ray-traces it via
`RenderManager.inCanvasRendering`. Because frames are index-pure, any range re-renders
independently (chunk the render across bridge calls), and quality is a single knob
(draft now, re-render clean later with no motion changes).

## Prerequisites

- fuzzydroid fusion plugin installed; bridge alive:
  `~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json ping`.
- The assembly open in Fusion at its **assembled** state before the first (planning)
  run — the engine captures "current pose = seat" once into the `assembled_cache`.
- ffmpeg on the host for the PNG → MP4 stitch.

## Hard rules

- **Run on Fusion's main thread** — go through the bridge (`fzd-fusion --json exec -`);
  never thread into the API.
- **Output resolution = the Fusion viewport size.** Maximize the Fusion window before a
  final render; don't resize mid-render.
- **Use `inCanvasRendering.saveImage`, not `saveAsImageFile`** for finals — the former is
  the ray-traced result, the latter is the flat shaded viewport.
- **The doc is never saved** (direct mode forced so `transform2` sets are absolute and
  cheap) — the render is non-destructive.
- **Draft first.** Validate motion + camera at `quality: 0.3`, then re-render at `0.75`
  (Excellent) once the timing looks right — same job, just bump `quality`.

## The engine

`scripts/render_animation.py` is the render-animation engine (run it through the bridge
with `exec`). It reads a JSON job file (default `/tmp/fusion_anim_job.json`, override via
`FUSION_ANIM_JOB`), renders a frame range to PNGs, and writes a result file; a planning
call (`"range": null`) captures the seat poses + camera calibration and reports the total
frame count. Full workflow, the job-file schema, the camera rig, ffmpeg stitch, quality/
timing table, and the animation-type taxonomy/roadmap are in
`references/render-animation.md`.
