"""view_stage — open a USD stage, frame the camera on the FULL MOTION ENVELOPE, and set a timecode.

For previewing authored scenes / animation layers (e.g. the mating-assembly *.anim.usda). ASYNC
(awaits frames on Kit's loop).

The camera is framed DYNAMICALLY on the assembly's size: it unions the world bounding box over
`sample` timecodes across the whole clip, so the approach/insertion travel (parts that start off their
seated pose) is fully in-frame, not just the assembled bounds. Distance scales with that envelope, so
a small knob and a large table both fill the frame the same way.

  view="front" : camera looks along -Y (Z up in image) — vertical insertion motion reads clearly.
  view="iso"   : three-quarter isometric.

Not part of the fmb add/assemble flow — a standalone previewer so `bridge.py screenshot` / record can
capture any layer at any frame.
"""


async def run(path, frame=0, fps=24.0, view="front", margin=1.3, sample=9, **kwargs):
    import omni.usd, omni.timeline, omni.kit.app
    from pxr import Usd, UsdGeom

    ctx = omni.usd.get_context()
    ctx.open_stage(path)
    app = omni.kit.app.get_app()
    for _ in range(20):
        await app.next_update_async()
    stage = ctx.get_stage()
    start = int(stage.GetStartTimeCode())
    end = int(stage.GetEndTimeCode())
    dp = stage.GetDefaultPrim() or stage.GetPseudoRoot()

    # ---- MOTION ENVELOPE: union world bbox over sampled timecodes across the clip ----
    # (a single timecode misses the approach extent; the assembled frame is the smallest box).
    tcs = [start] if end <= start else [
        start + round(i * (end - start) / (sample - 1)) for i in range(max(2, sample))]
    mn = [float("inf")] * 3
    mx = [float("-inf")] * 3
    for tc in tcs:
        bbc = UsdGeom.BBoxCache(Usd.TimeCode(tc), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        rng = bbc.ComputeWorldBound(dp).ComputeAlignedRange()
        a, b = rng.GetMin(), rng.GetMax()
        if not rng.IsEmpty():
            for i in range(3):
                mn[i] = min(mn[i], a[i]); mx[i] = max(mx[i], b[i])
    if mn[0] == float("inf"):                      # nothing visible at any sample -> fall back
        mn, mx = [-0.15, -0.15, 0.0], [0.15, 0.15, 0.15]

    c = [(mn[i] + mx[i]) / 2.0 for i in range(3)]
    dx, dy, dz = (mx[i] - mn[i] for i in range(3))

    # ---- dynamic distance: fit the in-view extent, scaled by assembly size ----
    K = 1.6                                         # perspective pull-back (~35 deg half-fov equiv)
    if view == "front":                             # near-front: frame plane is (X wide, Z tall)
        dist = margin * K * max(dx, dz, 1e-3)
        # A PURE -Y look (eye differing from target only in Y) degenerates set_camera_view's up
        # (view dir parallel to a reference axis -> broken camera, blank render). Tilt a hair off
        # axis: small +X azimuth and +Z elevation. Still reads as a front view; vertical (Z)
        # insertion motion stays clearly visible.
        eye = [c[0] + dist * 0.06, c[1] - dist, c[2] + dist * 0.14]
    elif view == "side":                            # near-side: frame plane is (Y wide, Z tall)
        # look along -X; both a vertical (Z) insert and a front-back (Y) slide read in-plane. Tilt a
        # hair off pure -X (small -Y azimuth + Z elevation) to avoid the degenerate-up blank render.
        dist = margin * K * max(dy, dz, 1e-3)
        eye = [c[0] - dist, c[1] - dist * 0.06, c[2] + dist * 0.14]
    else:                                           # iso three-quarter
        diag = (dx * dx + dy * dy + dz * dz) ** 0.5 or 0.3
        d = margin * K * diag
        eye = [c[0] + d * 0.55, c[1] - d * 0.7, c[2] + d * 0.45]

    try:
        from isaacsim.core.utils.viewports import set_camera_view
        set_camera_view(eye=eye, target=c)
    except Exception as e:
        print(f"view_stage camera set skipped: {e}")

    tl = omni.timeline.get_timeline_interface()
    tl.set_current_time(float(frame) / float(fps))
    for _ in range(30):
        await app.next_update_async()
    return {"ok": True, "path": path, "frame": frame, "end": end, "view": view,
            "envelope_mm": [round(dx * 1000, 1), round(dy * 1000, 1), round(dz * 1000, 1)],
            "center": [round(v, 4) for v in c], "eye": [round(v, 4) for v in eye]}
