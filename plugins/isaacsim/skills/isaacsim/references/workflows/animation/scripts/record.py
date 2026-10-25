"""record — render the current stage's animation to a PNG sequence and encode an mp4. ASYNC.

Dispatched as a bridge tool, run() is a coroutine ON Kit's main loop, so it advances frames by
AWAITING them (`await app.next_update_async()`) — never a sync `app.update()` pump, which re-enters
the running loop and raises "Cannot enter into task … while another task … is being executed"
(under a live webrtc viewport it can crash the process). Fire-then-step: call
capture_viewport_to_file (returns immediately; never await the capture future itself — that
deadlocks), then await frames so the render + async write land. Typical flow: view_stage(path) to
open+frame the camera, then record() to capture start..end.
"""


async def run(path=None, out="/tmp/rec", fps=24.0, start=None, end=None, settle=3, warmup=20,
        encode=True, loops=3, **kwargs):
    import os, subprocess
    import omni.usd, omni.timeline, omni.kit.app
    from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file

    ctx = omni.usd.get_context()
    if path:
        ctx.open_stage(path)
    stage = ctx.get_stage()
    app = omni.kit.app.get_app()
    tl = omni.timeline.get_timeline_interface()
    vp = get_active_viewport()

    if start is None:
        start = int(stage.GetStartTimeCode())
    if end is None:
        end = int(stage.GetEndTimeCode())

    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith("frame_") and f.endswith(".png"):
            os.remove(os.path.join(out, f))

    for _ in range(warmup):
        await app.next_update_async()

    n = 0
    for fr in range(start, end + 1):
        tl.set_current_time(float(fr) / float(fps))
        for _ in range(3):
            await app.next_update_async()                   # render this timecode
        capture_viewport_to_file(vp, os.path.join(out, f"frame_{n:04d}.png"))
        for _ in range(settle):
            await app.next_update_async()                   # flush the capture to disk
        n += 1

    mp4 = None
    if encode and n > 0:
        mp4 = out + ".mp4"
        cmd = ["ffmpeg", "-y", "-framerate", str(int(fps))]
        if loops and loops > 1:
            cmd += ["-stream_loop", str(loops - 1)]         # repeat the clip for an obvious loop
        cmd += ["-i", os.path.join(out, "frame_%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", mp4]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("ffmpeg failed:\n" + r.stderr[-600:])
            mp4 = None

    return {"ok": True, "frames": n, "dir": out, "mp4": mp4, "start": start, "end": end}
