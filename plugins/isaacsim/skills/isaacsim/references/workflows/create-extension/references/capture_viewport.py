#!/usr/bin/env python3
"""Headless offscreen viewport screenshot for a bridged Isaac Sim (--no-window).

This is the body of an `async` bridge TOOL (or anything `run_coroutine`'d on Kit's
loop) — NOT a sync `run_python` payload. Capture must advance frames, and a handler
runs as a coroutine ON Kit's main loop: a synchronous pump (`app.update()` /
`world.step(render=True)`) from inside it re-enters the running loop and raises
`RuntimeError: Cannot enter into task … while another task … is being executed`
(cascading, and under a live webrtc viewport it can crash the process). So we AWAIT
frames via `next_update_async()` instead — the async yield lets the frames the render
and the file write need actually happen. Register `capture` as a tool, then `get_file`
the PNG back. An UNLIT scene renders BLACK — the dome + distant light are load-bearing.

Parameterize CAM_EYE / CAM_TARGET to frame your robot (metres, world frame).
"""
OUT = "/tmp/shot.png"


async def capture(out: str = OUT):
    import omni.usd, omni.kit.app
    from pxr import UsdGeom, UsdLux, Gf
    from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file
    from omni.kit.viewport.utility.camera_state import ViewportCameraState

    CAM_EYE = Gf.Vec3d(0.14, -0.30, 0.20)     # camera position, world m
    CAM_TARGET = Gf.Vec3d(0.14, 0.0, -0.01)   # look-at point, world m

    app = omni.kit.app.get_app()
    stage = omni.usd.get_context().get_stage()

    # lighting (unlit -> black frame)
    if not stage.GetPrimAtPath("/World/DomeLight").IsValid():
        UsdLux.DomeLight.Define(stage, "/World/DomeLight").CreateIntensityAttr(1000.0)
    if not stage.GetPrimAtPath("/World/KeyLight").IsValid():
        key = UsdLux.DistantLight.Define(stage, "/World/KeyLight")
        key.CreateIntensityAttr(3000.0)
        UsdGeom.Xformable(key.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-45, 10, 0))

    vp = get_active_viewport()
    cam = "/OmniverseKit_Persp"
    vp.camera_path = cam
    cs = ViewportCameraState(cam, vp)
    cs.set_position_world(CAM_EYE, True)
    cs.set_target_world(CAM_TARGET, True)

    for _ in range(80):                        # warm the RTX render (await, never pump)
        await app.next_update_async()
    capture_viewport_to_file(vp, out)          # fire; do NOT await this call itself
    for _ in range(40):                        # let the async write finish
        await app.next_update_async()
    return {"ok": True, "path": out}
