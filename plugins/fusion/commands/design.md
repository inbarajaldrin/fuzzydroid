---
description: Generate or modify CAD geometry in Fusion 360 from natural language descriptions or reference images. Writes parametric Python scripts and iterates based on visual feedback.
argument-hint: <description of what to create or modify>
allowed-tools: [Bash, Read, Write]
---

# /fusion:design

Generate CAD geometry in Fusion 360 from a text description or reference image. This command
drives the full design loop: understand the request, write a parametric script, execute it in
Fusion, capture a screenshot, and iterate on user feedback.

## Step 1: Understand the request

Parse the user's input to extract:
- **Shape description** (box, cylinder, cup, enclosure, bracket, etc.)
- **Dimensions** (width, height, depth, wall thickness, radii)
- **Features** (fillets, chamfers, holes, lips, domes, shells)
- **Multi-body** (cap, lid, mating parts — each gets its own component)
- **Reference images** (photos with dimensions — extract measurements from the image)

If dimensions or critical shape details are ambiguous, ask ONE round of clarifying questions
before generating code. Do not guess wall thickness or clearances without confirming.

## Step 2: Write a parametric script

Write the script to `/tmp/f360_design.py`. Every generated script MUST follow this structure:

```python
import adsk.core, adsk.fusion, math, json, traceback

app = adsk.core.Application.get()

# ============================================================
# CONFIG — all user-adjustable dimensions in mm
# ============================================================
CONFIG = {
    "width":       60,    # mm
    "depth":       60,    # mm
    "height":      50,    # mm
    "wallThickness": 1.5, # mm
    "cornerRadius":  8,   # mm
    # ... add parameters for every tunable dimension
}

def mm(v):
    """Convert mm to cm (Fusion internal unit). MANDATORY."""
    return v / 10.0

# ============================================================
# GEOMETRY HELPERS — include only what this design needs
# ============================================================

def draw_rect(sketch, hw, cr):
    """Draw a closed rounded rectangle centered at origin.
    hw = half-width (cm), cr = corner radius (cm)."""
    p = adsk.core.Point3D
    s = hw - cr
    ln = sketch.sketchCurves.sketchLines
    ar = sketch.sketchCurves.sketchArcs
    ln.addByTwoPoints(p.create(-s, -hw, 0), p.create(s, -hw, 0))
    ln.addByTwoPoints(p.create(hw, -s, 0), p.create(hw, s, 0))
    ln.addByTwoPoints(p.create(s, hw, 0), p.create(-s, hw, 0))
    ln.addByTwoPoints(p.create(-hw, s, 0), p.create(-hw, -s, 0))
    ar.addByCenterStartSweep(p.create(s, -s, 0), p.create(hw, -s, 0), -math.pi/2)
    ar.addByCenterStartSweep(p.create(s, s, 0), p.create(s, hw, 0), -math.pi/2)
    ar.addByCenterStartSweep(p.create(-s, s, 0), p.create(-hw, s, 0), -math.pi/2)
    ar.addByCenterStartSweep(p.create(-s, -s, 0), p.create(-s, -hw, 0), -math.pi/2)

def find_face(body, z_val, normal_z_sign, largest=True):
    """Find a planar face at z_val (cm) with given normal direction (+1 or -1)."""
    best = None
    for f in body.faces:
        geo = f.geometry
        if geo.classType() != 'adsk::core::Plane':
            continue
        bb = f.boundingBox
        if abs(bb.minPoint.z - z_val) > 0.02 or abs(bb.maxPoint.z - z_val) > 0.02:
            continue
        if normal_z_sign > 0 and geo.normal.z < 0.5:
            continue
        if normal_z_sign < 0 and geo.normal.z > -0.5:
            continue
        if best is None or (largest and f.area > best.area) or (not largest and f.area < best.area):
            best = f
    return best

def find_edges_at_z(body, z_val):
    """Collect all edges at a given Z level (cm) — useful for fillets."""
    edges = adsk.core.ObjectCollection.create()
    for i in range(body.edges.count):
        e = body.edges.item(i)
        bb = e.boundingBox
        if abs(bb.minPoint.z - z_val) < 0.02 and abs(bb.maxPoint.z - z_val) < 0.02:
            edges.add(e)
    return edges

# For loft-based shapes (tapered cups, organic forms):
# def mkprof(z, hw, cr):
#     """Create a sketch profile at offset Z for lofting."""
#     if z == 0:
#         plane = root.xYConstructionPlane
#     else:
#         pi = root.constructionPlanes.createInput()
#         pi.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(z))
#         plane = root.constructionPlanes.add(pi)
#     sk = root.sketches.add(plane)
#     draw_rect(sk, hw, cr)
#     return sk.profiles.item(0)
#
# def lerp(a, b, t):
#     return a + (b - a) * t

# ============================================================
# MAIN GEOMETRY
# ============================================================
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
design = adsk.fusion.Design.cast(app.activeProduct)
design.designType = adsk.fusion.DesignTypes.ParametricDesignType
root = design.rootComponent

try:
    C = {k: mm(v) for k, v in CONFIG.items()}

    # ... build geometry here using C['width'], C['height'], etc. ...

    app.activeViewport.fit()
    screenshot_path = '/tmp/fusion_design_result.png'
    app.activeViewport.saveAsImageFile(screenshot_path, 1920, 1080)

    result = {
        "status": "ok",
        "screenshot": screenshot_path,
        "config": CONFIG,
        "bodies": root.bRepBodies.count,
        "components": root.occurrences.count,
    }
    print(json.dumps(result, indent=2))

except Exception as e:
    print(json.dumps({
        "status": "error",
        "message": str(e),
        "traceback": traceback.format_exc()
    }))
```

### Script rules

- **All dimensions in CONFIG are in mm.** The `mm()` function converts to cm for the API.
  Fusion's internal unit is centimeters. Forgetting this is the most common bug.
- **CONFIG must contain every tunable dimension.** The user can ask "make it taller" and
  you just change one CONFIG value and re-run.
- **Name every feature** (`extrude.name = 'ContainerExtrude'`). This makes the timeline
  readable and debugging easier.
- **Name every body** (`body.name = 'ContainerBody'`). Multi-body designs get confusing fast.
- **Use components for separate parts** (cap, lid, base). Create via
  `root.occurrences.addNewComponent(adsk.core.Matrix3D.create())`.
- **Always call `app.activeViewport.fit()`** before the screenshot.

### Geometry technique selection

Choose the right technique for the shape:

| Shape | Technique |
|-------|-----------|
| Prismatic (box, enclosure, bracket) | Sketch + Extrude |
| Tapered (cup, vase, funnel) | Multi-section Loft with 8+ profiles |
| Round (cylinder, dome) | Sketch circle + Extrude, or Revolve |
| Hollow | Shell (with cut-extrude fallback) |
| Rounded edges | Fillet after all other operations |
| Multi-part (container+cap) | Separate components + transform positioning |
| Trim/cutout | Sketch profile + Cut extrude (not boolean body copy) |

### Shell fallback

Shell operations fail on complex geometry. Always wrap in try/except:

```python
try:
    shell_feat = comp.features.shellFeatures.add(shell_input)
except:
    # Fallback: cut-extrude the inner profile
    inner_sk = comp.sketches.add(plane)
    draw_rect(inner_sk, inner_hw, inner_cr)
    ci = comp.features.extrudeFeatures.createInput(
        inner_sk.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    ci.setDistanceExtent(False, adsk.core.ValueInput.createByReal(depth))
    comp.features.extrudeFeatures.add(ci)
```

### Loft straight-side fix

When lofting tapered shapes, 2-4 sections cause spline-interpolated concave curves.
Use 8+ intermediate sections with linearly interpolated dimensions:

```python
N_SECTIONS = 8
step = height / N_SECTIONS
for i in range(N_SECTIONS + 1):
    z = step * i
    hw = lerp(bot_hw, top_hw, z / height)
    cr = lerp(bot_cr, top_cr, z / height)
    profiles.append(mkprof(z, hw, cr))
```

## Step 3: Execute via the bridge

```bash
VENV_PYTHON=$(python3 -c "
import tomllib, os, sys
from pathlib import Path
cfg = (Path(os.environ['APPDATA']) / 'fuzzydroid' / 'fusion.toml') if os.name == 'nt' \
      else Path.home() / '.config' / 'fuzzydroid' / 'fusion.toml'
if not cfg.exists():
    sys.exit(1)
state = tomllib.loads(cfg.read_text())
venv = Path(state['venv_path'])
print(venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))
")

if [ -z "$VENV_PYTHON" ]; then
    echo "fusion plugin is not set up - run /fusion:setup first"
    exit 1
fi

printf 'exec(open("/tmp/f360_design.py").read())' \
  | "$VENV_PYTHON" -m fuzzydroid.fusion.cli --json exec -
```

## Step 4: Show the result

1. Parse the JSON output. Check `status` is `"ok"`.
2. Read the screenshot: `Read /tmp/fusion_design_result.png`
3. Present the image to the user with a brief summary of what was created
   (dimensions, body count, feature list).
4. If the script errored, read the traceback, diagnose the issue, fix the script,
   and re-execute. Common errors:
   - Shell compute failure -> use cut-extrude fallback
   - Feature validation error -> reorder operations (fillet before shell often helps)
   - Profile not found -> check sketch is closed and has exactly one profile

## Step 5: Iterate

When the user requests changes:

- **Dimension change** ("make it taller", "wider corners"): update CONFIG values only,
  re-run the same script.
- **Feature change** ("add a fillet", "remove the lip", "hollow it out"): modify the
  geometry section of the script, keep CONFIG intact.
- **Shape change** ("make it round instead of square"): rewrite the geometry section,
  possibly switch technique (extrude -> revolve).
- **Multi-version**: Save each version to `/tmp/f360_design_v2.py`, `v3.py`, etc.
  so the user can go back.

After each change, re-execute and show the updated screenshot. Continue until the user
is satisfied.

## Step 6: Save

When the user says "save this" or "looks good":
1. Ask which Fusion project/folder to save to (or save to current if already open).
2. Use `app.activeDocument.save("name")` or `saveAs` via exec.
3. Optionally export to `./outputs/` via `/fusion:export`.
