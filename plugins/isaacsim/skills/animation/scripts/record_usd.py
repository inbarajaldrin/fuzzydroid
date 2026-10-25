"""record_usd - standalone animation video recorder via ``usdrecord`` (Hydra/Storm).

A no-Isaac-Sim alternative to ``record.py``. ``record.py`` captures the live Kit
viewport and therefore needs a running Isaac Sim; this renders a USD animation
(e.g. ``<asm>.anim.usda``) straight through ``usdrecord`` (Metal/GL Hydra) and
encodes an mp4 with ffmpeg. It works anywhere ``usdrecord`` + ``ffmpeg`` are on
PATH (macOS included), with no Kit runtime.

Two quirks of ``usdrecord`` this wraps for you:
  * The output path MUST contain a ``###`` frame placeholder, and the numbering
    only comes out clean with the ``###.###`` form (7-digit zero-pad); plain
    ``###`` emits broken scientific-notation names that collide. We render to
    ``f.###.###.png`` -> ``f.0000000.png`` and feed ffmpeg ``f.%07d.png``.
  * With no camera it re-frames the scene bbox EVERY frame, so an exploded-view
    subject "breathes" as parts converge. We fit ONE fixed look-at camera on the
    ASSEMBLED target (the sublayered <asm>.scene.usda at default time -- see
    _assembled_bbox for why start/end/union framing all pick a bad angle) so the
    movers simply fly in from off-screen. Pass --camera <primpath> to override.

Usage:
  uv run --no-project --with usd-core --with numpy python record_usd.py \
      <stage.usda> [--out DIR] [--mp4 PATH] [--fps 24] [--start N] [--end N] \
      [--width 800] [--camera PRIMPATH] [--elev 28] [--azim -58] [--margin 1.15] \
      [--stride-envelope 4] [--no-encode] [--loops 3]

Programmatic: ``render(stage, out=..., fps=..., ...) -> mp4_path | None``.
"""
import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile


def _look_at_matrix(eye, target, up):
    import numpy as np
    e = np.array(eye, float); t = np.array(target, float); u = np.array(up, float)
    z = e - t; z /= (np.linalg.norm(z) or 1.0)
    x = np.cross(u, z); x /= (np.linalg.norm(x) or 1.0)
    y = np.cross(z, x)
    from pxr import Gf
    return Gf.Matrix4d(
        float(x[0]), float(x[1]), float(x[2]), 0.0,
        float(y[0]), float(y[1]), float(y[2]), 0.0,
        float(z[0]), float(z[1]), float(z[2]), 0.0,
        float(e[0]), float(e[1]), float(e[2]), 1.0)


def _assembled_bbox(stage_path, start, end):
    """(center, radius) of the ASSEMBLED target, for a stable fixed camera.

    An anim spec authored by author_anim.py with loop=true PING-PONGS: it wraps time
    with a triangle so frame 0 == frame N are the EXPLODED state and the fully assembled
    peak is the MIDDLE frame. So neither the start nor the end frame is the assembled
    target, and the union of all frames includes the parts flung far out along their mate
    axes -- both give the camera a bad, zoomed-out, near-top-down angle (the "lying on its
    side" look). The correct framing subject is the SEATED scene.

    We compute it from the anim's first sublayer -- the sublayered <asm>.scene.usda, whose
    DEFAULT (non-time-sampled) poses ARE the assembled arrangement -- at default time.
    Falls back to the anim's middle frame (the loop's assembled peak), then the end frame.
    """
    import numpy as np
    from pxr import Usd, UsdGeom, Sdf

    def _union(stage, timecode):
        cache = UsdGeom.BBoxCache(timecode,
                                  [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        mn = np.array([1e30] * 3); mx = np.array([-1e30] * 3)
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Camera):
                continue
            if not (prim.IsA(UsdGeom.Boundable) or prim.IsA(UsdGeom.Xformable)):
                continue
            try:
                b = cache.ComputeWorldBound(prim).ComputeAlignedRange()
            except Exception:
                continue
            if b.IsEmpty():
                continue
            mn = np.minimum(mn, np.array(b.GetMin()))
            mx = np.maximum(mx, np.array(b.GetMax()))
        return mn, mx

    # 1) prefer the sublayered assembled scene at default time
    try:
        layer = Sdf.Layer.FindOrOpen(stage_path)
        subs = list(layer.subLayerPaths) if layer else []
        if subs:
            scene_path = subs[0]
            if not os.path.isabs(scene_path):
                scene_path = os.path.normpath(
                    os.path.join(os.path.dirname(stage_path), scene_path))
            scene = Usd.Stage.Open(scene_path)
            mn, mx = _union(scene, Usd.TimeCode.Default())
            if np.isfinite(mn).all():
                return (mn + mx) / 2.0, float(np.linalg.norm(mx - mn) / 2.0) or 1.0
    except Exception:
        pass
    # 2) fall back to the anim's assembled peak (middle frame for a triangle loop)
    stage = Usd.Stage.Open(stage_path)
    for f in ((int(start) + int(end)) // 2, int(end)):
        mn, mx = _union(stage, Usd.TimeCode(f))
        if np.isfinite(mn).all():
            return (mn + mx) / 2.0, float(np.linalg.norm(mx - mn) / 2.0) or 1.0
    return np.zeros(3), 1.0


def _build_camera_stage(src, start, end, elev, azim, margin, stride, up_axis):
    """Wrapper stage that sublayers ``src`` and adds a fixed look-at camera.

    Returns (wrapper_path, camera_primpath).
    """
    import numpy as np
    from pxr import Usd, UsdGeom, Gf
    center, radius = _assembled_bbox(src, start, end)

    focal = 50.0
    dist = radius * 3.4
    el = math.radians(elev); az = math.radians(azim)
    if up_axis == "Z":
        d = np.array([math.cos(el) * math.cos(az),
                      math.cos(el) * math.sin(az),
                      math.sin(el)])
        up = [0, 0, 1.0]
    else:  # Y-up
        d = np.array([math.cos(el) * math.cos(az),
                      math.sin(el),
                      math.cos(el) * math.sin(az)])
        up = [0, 1.0, 0]
    eye = np.array(center) + d * dist
    aperture = 2.0 * focal * (radius / dist) * margin

    wrapper = os.path.join(tempfile.mkdtemp(prefix="record_usd_"), "camera_stage.usda")
    st = Usd.Stage.CreateNew(wrapper)
    st.GetRootLayer().subLayerPaths.append(os.path.abspath(src))
    st.SetStartTimeCode(start); st.SetEndTimeCode(end)
    UsdGeom.SetStageUpAxis(st, getattr(UsdGeom.Tokens, up_axis.lower()))
    cam = UsdGeom.Camera.Define(st, "/RecordCam")
    cam.AddTransformOp().Set(_look_at_matrix(eye, center, up))
    cam.CreateFocalLengthAttr(focal)
    cam.CreateHorizontalApertureAttr(float(aperture))
    cam.CreateVerticalApertureAttr(float(aperture * 0.75))
    # generous clip: movers fly out along their mate axes during the explode, so a
    # tight near/far around the assembled radius would clip them mid-flight.
    cam.CreateClippingRangeAttr(Gf.Vec2f(max(1e-3, dist * 0.02), dist * 20.0))
    st.GetRootLayer().Save()
    return wrapper, "/RecordCam"


def _stage_frame_range(stage_path):
    from pxr import Usd
    s = Usd.Stage.Open(stage_path)
    return int(s.GetStartTimeCode()), int(s.GetEndTimeCode())


def _detect_up_axis(stage_path):
    """Up-axis of the ASSET, not the anim wrapper.

    An anim layer authored without an explicit upAxis defaults to Y even though its
    sublayered scene is Z-up (the scene's opinion does not always compose up into the
    root's stage metadata) -- a Y-up camera on a Z-up asset renders it tipped/flipped.
    So resolve the first sublayer (the scene) first, falling back to the stage itself.
    """
    from pxr import Usd, UsdGeom, Sdf
    try:
        layer = Sdf.Layer.FindOrOpen(stage_path)
        subs = list(layer.subLayerPaths) if layer else []
        if subs:
            sp = subs[0]
            if not os.path.isabs(sp):
                sp = os.path.normpath(os.path.join(os.path.dirname(stage_path), sp))
            ax = UsdGeom.GetStageUpAxis(Usd.Stage.Open(sp))
            if ax:
                return ax
    except Exception:
        pass
    return UsdGeom.GetStageUpAxis(Usd.Stage.Open(stage_path)) or "Z"


def render(stage, out=None, mp4=None, fps=24.0, start=None, end=None, width=800,
           camera=None, elev=22.0, azim=-58.0, margin=1.2, stride_envelope=4,
           encode=True, loops=3):
    """Render ``stage`` (a USD anim) to a PNG sequence + mp4 via usdrecord.

    Returns the mp4 path (or the frame dir when ``encode`` is False).
    """
    stage = os.path.abspath(os.path.expanduser(stage))
    if not shutil.which("usdrecord"):
        raise RuntimeError("usdrecord not found on PATH")
    s0, s1 = _stage_frame_range(stage)
    start = s0 if start is None else int(start)
    end = s1 if end is None else int(end)
    out = out or (os.path.splitext(stage)[0] + "_frames")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith(".png"):
            os.remove(os.path.join(out, f))

    render_stage, cam_path = stage, camera
    if camera is None:
        up = _detect_up_axis(stage)
        render_stage, cam_path = _build_camera_stage(
            stage, start, end, elev, azim, margin, stride_envelope, up)

    pattern = os.path.join(out, "f.###.###.png")
    cmd = ["usdrecord", "--imageWidth", str(int(width)),
           "--frames", f"{start}:{end}"]
    if cam_path:
        cmd += ["--camera", cam_path]
    cmd += [render_stage, pattern]
    r = subprocess.run(cmd, capture_output=True, text=True)
    frames = sorted(f for f in os.listdir(out) if f.endswith(".png"))
    if r.returncode != 0 and not frames:
        raise RuntimeError("usdrecord failed:\n" + r.stderr[-2000:])
    if not frames:
        raise RuntimeError("usdrecord produced no frames")

    if not encode:
        return out
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")
    mp4 = mp4 or (os.path.splitext(stage)[0] + ".mp4")
    # frames are f.0000000.png .. -> ffmpeg glob-safe via the 7-digit pattern
    first = frames[0]
    prefix = first.split(".")[0]  # "f"
    # Encode the PNG sequence to a single clip. NOTE: -stream_loop BEFORE an image2
    # input silently yields zero frames on macOS ffmpeg, so we never loop at this
    # stage -- a triangle-loop anim already reads as a seamless cycle in one pass.
    base = mp4 if (not loops or loops <= 1) else mp4 + ".base.mp4"
    cmd = ["ffmpeg", "-y", "-framerate", str(int(fps)),
           "-start_number", "0",
           "-i", os.path.join(out, f"{prefix}.%07d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", base]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + r.stderr[-2000:])
    if loops and loops > 1:
        # -stream_loop works on a real video-file input (unlike image2 above).
        r = subprocess.run(["ffmpeg", "-y", "-stream_loop", str(loops - 1),
                            "-i", base, "-c", "copy", mp4],
                           capture_output=True, text=True)
        os.remove(base)
        if r.returncode != 0:
            raise RuntimeError("ffmpeg loop failed:\n" + r.stderr[-2000:])
    return mp4


def main():
    ap = argparse.ArgumentParser(description="Standalone usdrecord animation video recorder (no Isaac Sim).")
    ap.add_argument("stage", help="USD animation stage (e.g. <asm>.anim.usda)")
    ap.add_argument("--out", default=None, help="frame dir (default <stage>_frames)")
    ap.add_argument("--mp4", default=None, help="output mp4 (default <stage>.mp4)")
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--camera", default=None, help="existing camera prim path; else auto look-at")
    ap.add_argument("--elev", type=float, default=22.0, help="auto-camera elevation deg")
    ap.add_argument("--azim", type=float, default=-58.0, help="auto-camera azimuth deg")
    ap.add_argument("--margin", type=float, default=1.2, help=">1 = more padding around subject")
    ap.add_argument("--stride-envelope", type=int, default=4, help="frame stride when fitting the camera")
    ap.add_argument("--no-encode", action="store_true")
    ap.add_argument("--loops", type=int, default=3)
    a = ap.parse_args()
    result = render(a.stage, out=a.out, mp4=a.mp4, fps=a.fps, start=a.start, end=a.end,
                    width=a.width, camera=a.camera, elev=a.elev, azim=a.azim,
                    margin=a.margin, stride_envelope=a.stride_envelope,
                    encode=not a.no_encode, loops=a.loops)
    print(f"[record_usd] {result}")


if __name__ == "__main__":
    sys.exit(main())
