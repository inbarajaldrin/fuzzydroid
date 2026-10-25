# Making animation GIFs from a rigged Fusion design

Turn joint drives into a looping GIF: pose → screenshot → pose → screenshot → ffmpeg.
All screenshots via the bridge (`app.activeViewport.saveAsImageFile`) — never OS-level
capture (window chrome, focus, scaling all bite).

## The recipe

```python
vp = app.activeViewport
cam = vp.camera
cam.viewOrientation = adsk.core.ViewOrientations.FrontViewOrientation  # or Iso*
cam.isSmoothTransition = False           # never animate camera moves in a script
vp.camera = cam; adsk.doEvents()

# 1) FRAME THE CAMERA ONCE at the widest pose, then hold it fixed
apply_pose(q_widest); vp.fit(); adsk.doEvents()
saved_cam = vp.camera                    # capture AFTER fit

for i, q in enumerate(sweep):
    apply_pose(q)
    vp.camera = saved_cam; adsk.doEvents()   # re-assert; do NOT call fit() per frame
    vp.saveAsImageFile(f"/tmp/frame_{i:02d}.png", 1400, 875)
    adsk.doEvents()

restore_park()                           # drive everything back; verify residual ~0
```

Then assemble (forward + reverse frames = seamless loop):

```bash
i=0
for f in 00 01 .. 12 11 .. 01; do cp "frame_$f.png" "seq_$(printf %02d $i).png"; i=$((i+1)); done
ffmpeg -y -framerate 5 -i seq_%02d.png -vf "scale=900:-1" -loop 0 out.gif
```

## Rules that came from real failures

1. **Fixed camera or jumpy GIF.** `vp.fit()` per frame re-zooms to the changing
   bounding box — the background lurches every frame. Fit exactly once at the pose
   with the largest extent, save `vp.camera`, reassign it every frame.
2. **`adsk.doEvents()` after every camera assignment and before every
   `saveAsImageFile`** — otherwise you screenshot the previous state.
3. **Park before and after.** Drive values persist through saves; a sweep that ends
   mid-pose becomes the document's pose. End with an exact restore (set recorded
   values directly, don't re-drive incrementally) and print the residual.
4. **Crash-proof baselines.** If the script dies mid-sweep, the model is left posed.
   Start every sweep script by driving to the canonical park FIRST, then capture
   reference landmarks. (A crashed run once left a slider at −10 cm; the rerun
   measured every "error" offset by exactly that.)
5. Frame size: 1400–1600 px wide is plenty; scale down in ffmpeg (`scale=900:-1`).
   13 poses × forward-reverse at `-framerate 5` reads well for mechanism motion.
6. Fusion draws joint glyphs/annotations for selected/driven joints — they show in
   screenshots. Deselect (`ui.activeSelections.clear()`) if you want clean frames,
   or keep them to visualize joint values (they read nicely in tutorials).
7. **The Fusion window must be on screen.** `saveAsImageFile` needs Fusion to draw its
   viewport. If the window is off-screen (another Space, the Stage Manager strip,
   minimized), the call blocks the bridge's main-thread queue: the bridge still answers
   `ping`, but every later `exec` times out until the window comes back. This is the
   wrong recipe for a machine someone is using.
   When the motion is analytic (a known screw, slide, or revolute path), render offscreen
   from exported meshes instead, with no Fusion involved. Apply the analytic
   transforms in an offscreen renderer such as PyVista, and cap any section cuts
   before capturing frames.
   Keep this Fusion recipe for motion only Fusion can solve, such as multi-joint drapes and
   contact-driven poses.

## Acceptance

Check that the camera stays fixed, frame order produces the intended loop, and
all driven joints return exactly to their recorded starting values. Keep the
frames and pose readbacks with the user's project.
