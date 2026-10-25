"""Fusion 360 render-animation engine -- assembly-sequence videos via ray-traced frames.

WHY THIS EXISTS
---------------
Fusion's native Animation workspace (storyboards, "Publish Video") is NOT
authorable through the API -- `Storyboard` exposes only playback (`play`,
`playheadPosition`, `reverse`); there is no API to create transform/camera
keyframes (a scripted `transform2` move never records -- verified empirically).
So instead of fighting that wall, this engine OWNS the sequencing and lets
Fusion do the part it *can* do well: ray-tracing via
`RenderManager.inCanvasRendering`. Each frame is a pure function of its index
(part poses + camera), so any frame range re-renders independently and quality
is a single knob.

HOW IT RUNS
-----------
The engine runs INSIDE Fusion (via the bridge `exec`). The calling agent writes
a job file, then executes this script. The script reads the job, renders the
requested frame range to PNGs, and writes a result file. The agent stitches the
PNGs to MP4 with ffmpeg afterwards (client-side).

  Job file (default /tmp/fusion_anim_job.json):
  {
    "parts":          ["partA","partB","partC","partD"],  # component names, in assembly ORDER
    "always_visible": ["base"],           # foundation parts shown the whole time (optional)
    "raise_cm":       13.0,                # how far above its seat each part starts
    "intro":  6, "drop": 18, "settle": 4, "outro": 12,   # frame counts
    "camera": {"azimuth":[-55,20], "elevation":[45,22], "dolly":[1.25,0.92],
               "center_z": 3.0, "dist_mul": 1.4},
    "quality":  0.3,                       # in-canvas ray-trace quality 0..1 (0.75=Excellent,1.0=Final)
    "cap_s":    6.0,                       # max seconds to accumulate per frame
    "outdir":   "/tmp/anim_frames",
    "assembled_cache": "/tmp/anim_assembled.json",   # captured-once seat poses + camera calibration
    "range":    [0, 23]                    # frames to render this call; null/omitted => report TOTAL only
  }

  Invoke (per chunk):
    exec(open('.../scripts/render_animation.py').read())

  Result (/tmp/fusion_anim_result.json):
    {"status":"ok","total":90,"rendered":[0,...,22],"outdir":"...","total_frames_planned":90}

KEY FACTS / GOTCHAS
-------------------
- Run on Fusion's MAIN thread only (the bridge already marshals there).
- `saveImage` size == the Fusion VIEWPORT size, so the window size sets output
  resolution. Maximize Fusion for higher res; the aspect is whatever the window is.
- Moving a part RESETS ray-trace accumulation, so every frame re-accumulates
  (~3-12 s/frame depending on quality). That cost is inherent, not a bug.
- The "assembled" pose = the design's CURRENT state, captured ONCE to the cache
  file so chunked calls stay consistent even though earlier chunks leave parts
  mid-drop. Delete the cache to recapture (e.g. after editing the assembly).
- Direct design mode is forced so `transform2` sets are absolute + cheap. The
  document is never saved, so this is non-destructive.
- Raising in world Z = adding to the matrix translation's z (that's the part's
  world origin), which is correct regardless of the part's rotation.
"""

import adsk.core, adsk.fusion, traceback, time, os, json, math

JOB_PATH = os.environ.get("FUSION_ANIM_JOB", "/tmp/fusion_anim_job.json")
RESULT_PATH = "/tmp/fusion_anim_result.json"
ac = adsk.core


# ---------- easing ----------
def smoother(a, b, t):
    """smootherstep -- eased a->b; gentle start AND stop (no velocity discontinuity)."""
    u = max(0.0, min(1.0, t))
    return a + (b - a) * (u * u * u * (u * (u * 6 - 15) + 10))


def remap(t, t0, t1):
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return (t - t0) / (t1 - t0)


# ---------- design access ----------
def get_design(app):
    d = adsk.fusion.Design.cast(app.activeProduct)
    if d:
        return d
    return adsk.fusion.Design.cast(
        app.activeDocument.products.itemByProductType("DesignProductType"))


def occ_map(design):
    """Map component base-name (version suffix stripped) -> root occurrence."""
    return {o.component.name.split(" v")[0]: o for o in design.rootComponent.occurrences}


def set_z(occ, z):
    m = occ.transform2.copy()
    v = m.translation
    v.z = z
    m.translation = v
    occ.transform2 = m


class Animator:
    def __init__(self, job):
        self.parts = job["parts"]
        self.always = job.get("always_visible", [])
        self.raise_cm = float(job.get("raise_cm", 13.0))
        self.intro = int(job.get("intro", 6))
        self.drop = int(job.get("drop", 18))
        self.settle = int(job.get("settle", 4))
        self.outro = int(job.get("outro", 12))
        cam = job.get("camera", {})
        self.az = cam.get("azimuth", [-55, 20])
        self.el = cam.get("elevation", [45, 22])
        self.dolly = cam.get("dolly", [1.25, 0.92])
        self.center_z = float(cam.get("center_z", 3.0))
        self.dist_mul = float(cam.get("dist_mul", 1.4))
        self.quality = float(job.get("quality", 0.3))
        self.cap_s = float(job.get("cap_s", 6.0))
        self.outdir = job["outdir"]
        self.cache_path = job.get("assembled_cache", "/tmp/fusion_anim_assembled.json")
        self.n = len(self.parts)
        self.ddrop = max(self.drop - self.settle, 1)
        self.total = self.intro + self.n * self.drop + self.outro
        self.seat = {}      # part -> [x,y,z] assembled translation
        self.center = [0.0, 0.0, self.center_z]
        self.base_dist = None

    # -- per-frame part poses --
    def frame_state(self, idx):
        if idx < self.intro:
            active, local = -1, 0
        elif idx >= self.intro + self.n * self.drop:
            active, local = self.n, 0
        else:
            active = (idx - self.intro) // self.drop
            local = (idx - self.intro) - active * self.drop
        st = {}
        for j, name in enumerate(self.parts):
            if j < active:
                st[name] = (0.0, True)
            elif j == active:
                r = min(local / max(self.ddrop - 1, 1), 1.0)
                p = smoother(0.0, 1.0, r)             # ease-in-out drop -> hangs high, lands soft
                st[name] = (self.raise_cm * (1 - p), True)
            else:
                st[name] = (self.raise_cm, False)     # not yet placed -> hidden
        return st

    # -- per-frame camera --
    def camera_state(self, idx):
        t = idx / max(self.total - 1, 1)
        az = smoother(self.az[0], self.az[1], t)                                   # full-length orbit
        el = (smoother(self.el[0], self.el[1], remap(t, 0.0, 0.7))                 # descend to establish drops
              + smoother(0.0, 6.0, remap(t, 0.82, 1.0)))                           # small hero rise at end
        dm = (smoother(self.dolly[0], self.dolly[1], remap(t, 0.0, 0.33))          # establish wide, push in
              + smoother(0.0, -0.08, remap(t, 0.85, 1.0)))                         # final beauty push
        azr, elr = math.radians(az), math.radians(el)
        R = self.base_dist * dm
        cx, cy, cz = self.center
        eye = ac.Point3D.create(cx + R * math.cos(elr) * math.cos(azr),
                                cy + R * math.cos(elr) * math.sin(azr),
                                cz + R * math.sin(elr))
        return eye, ac.Point3D.create(cx, cy, cz), ac.Vector3D.create(0, 0, 1)

    # -- one-time calibration: seats + camera distance (cached for chunk consistency) --
    def calibrate(self, app, design, occ):
        if os.path.exists(self.cache_path):
            data = json.load(open(self.cache_path))
            self.seat = {k: v for k, v in data["seat"].items()}
            self.center = data["center"]
            self.base_dist = data["base_dist"]
            return
        for name in self.parts:
            tr = occ[name].transform2.translation
            self.seat[name] = [tr.x, tr.y, tr.z]
        vp = app.activeViewport
        cam = vp.camera
        cam.cameraType = ac.CameraTypes.PerspectiveCameraType
        cam.viewOrientation = ac.ViewOrientations.IsoTopRightViewOrientation
        cam.isFitView = True
        vp.camera = cam
        vp.fit()
        adsk.doEvents()
        cam = vp.camera
        e, g = cam.eye, cam.target
        dist = math.sqrt((e.x - g.x) ** 2 + (e.y - g.y) ** 2 + (e.z - g.z) ** 2)
        self.center = [0.0, 0.0, self.center_z]
        self.base_dist = dist * self.dist_mul
        json.dump({"seat": self.seat, "center": self.center, "base_dist": self.base_dist},
                  open(self.cache_path, "w"))

    def setup(self, app, design):
        if design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
            design.designType = adsk.fusion.DesignTypes.DirectDesignType
        rm = design.renderManager
        if not rm.isRenderWorkspaceActive:
            rm.activateRenderWorkspace()
            adsk.doEvents()
        occ = occ_map(design)
        self.calibrate(app, design, occ)
        for name in self.always:
            if name in occ:
                occ[name].isLightBulbOn = True
        return occ, app.activeViewport, rm

    def apply_frame(self, occ, vp, idx):
        for name, (dz, vis) in self.frame_state(idx).items():
            o = occ[name]
            o.isLightBulbOn = vis
            set_z(o, self.seat[name][2] + dz)
        eye, tgt, up = self.camera_state(idx)
        cam = vp.camera
        cam.cameraType = ac.CameraTypes.PerspectiveCameraType
        cam.eye, cam.target, cam.upVector = eye, tgt, up
        cam.isSmoothTransition = False     # place exactly; no tween fighting us
        cam.isFitView = False
        vp.camera = cam

    def render_range(self, app, design, a, b):
        occ, vp, rm = self.setup(app, design)
        icr = rm.inCanvasRendering
        icr.isAdvanced = True              # advanced => stops at the requested quality
        try:
            icr.lockView = True            # no view drift mid-accumulation
        except Exception:
            pass
        os.makedirs(self.outdir, exist_ok=True)
        done = []
        for idx in range(a, b):
            self.apply_frame(occ, vp, idx)
            vp.refresh()
            adsk.doEvents()
            icr.start(self.quality)
            t0, last, stable = time.time(), -1, 0
            while True:
                adsk.doEvents()
                el = time.time() - t0
                it = icr.iterations
                stable = stable + 1 if it == last else 0
                last = it
                if el > self.cap_s:
                    break
                if el > 1.2 and stable > 40 and it > 0:
                    break
                time.sleep(0.02)
            icr.saveImage(os.path.join(self.outdir, "frame_%04d.png" % idx))
            icr.stop()
            adsk.doEvents()
            done.append(idx)
        return done


def main():
    out = {"status": "error"}
    try:
        job = json.load(open(JOB_PATH))
        app = ac.Application.get()
        design = get_design(app)
        anim = Animator(job)
        rng = job.get("range")
        if not rng:
            # planning call: report TOTAL and warm the cache
            occ, vp, rm = anim.setup(app, design)
            out = {"status": "ok", "total": anim.total, "rendered": [],
                   "outdir": anim.outdir, "total_frames_planned": anim.total}
        else:
            done = anim.render_range(app, design, int(rng[0]), int(rng[1]))
            out = {"status": "ok", "total": anim.total, "rendered": done,
                   "outdir": anim.outdir, "total_frames_planned": anim.total}
    except Exception:
        out = {"status": "error", "message": traceback.format_exc()}
    json.dump(out, open(RESULT_PATH, "w"))
    print(json.dumps(out))


main()
