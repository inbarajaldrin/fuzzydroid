# Copy-paste recipes for joint authoring

Use these skeletons with the current document's geometry, dimensions, and
joint convention. All run via
`cat script.py | ~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json exec -`.
Every script starts with the document-activation preamble (api-gotchas.md).

## 1. Measure joint axis lines from cylinders

```python
# For each candidate axis: collect cylinder faces with axis ∥ expected direction whose
# axis line passes near the expected point. Radius/area filters keep out fasteners.
for occ in root.occurrences:
    for b in occ.bRepBodies:
        for f in b.faces:
            g = f.geometry
            if g and g.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType \
               and g.radius > 2.5 and f.area > 40:
                o, a = g.origin, g.axis   # line = point o + t*a (o's position ALONG a is arbitrary)
```
Compare found lines to targets by (perpendicular distance, |dot|−1). For a URDF target, compute
frame targets with numpy FK at your chosen zero pose OUTSIDE Fusion.

## 2. Corrective transform application (parametric-safe)

```python
des.designType = adsk.fusion.DesignTypes.ParametricDesignType   # BEFORE any move
cm = adsk.core.Matrix3D.create(); cm.setWithArray(row_major_16_translation_in_cm)
t = occ.transform2.copy(); t.transformBy(cm); occ.transform2 = t   # new = corr @ old
des.snapshots.add()
```

## 3. Gated regular-joint builder (the heart of the method)

```python
def mk(flip, angle, offset):
    e0, e1 = find_coincident_circle_pair()          # RE-FIND fresh every attempt
    g0 = adsk.fusion.JointGeometry.createByCurve(e0, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
    g1 = adsk.fusion.JointGeometry.createByCurve(e1, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
    inp = root.joints.createInput(g0, g1)           # (child_geo, parent_geo)
    inp.isFlipped = flip
    if angle:  inp.angle  = adsk.core.ValueInput.createByReal(angle)
    if offset: inp.offset = adsk.core.ValueInput.createByReal(offset)
    inp.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
    jt = root.joints.add(inp); adsk.doEvents()
    return jt, measure_child_displacement()         # rotation about axis + translation, FROM GEOMETRY

# search: for flip in (False, True): create; if clean keep; else delete (restores pose),
# retry with angle = -measured_rotation (both signs), offset = -measured_axial (both signs).
# Convergence metric = a LANDMARK CIRCLE on the child vs its target position, never the
# group occurrence transform.
```

Landmark-converging variant (when the child must land at a known pose, e.g. re-zeroing a
joint to a convention): measure the signed angle from landmark to target about the axis,
`angle += that`, iterate ≤5; keeps only if error < 0.15 mm.

## 4. Motion links with empirical sign search

```python
def link(j1, j2, rev):
    inp = root.motionLinks.createInput(jnt(j1), jnt(j2))
    inp.linkValueOne = adsk.core.ValueInput.createByReal(1.0)
    inp.linkValueTwo = adsk.core.ValueInput.createByReal(1.0)
    inp.isReversed = rev
    return root.motionLinks.add(inp)
# For each sign combo: create links, drive the master a little, measure LOOP-CLOSURE ERROR
# (distance between the two coincident-pivot circles at the open end), drive back, delete links.
# Keep the combo whose error stays ~0. Requires rigid groups first, else all combos tie.
```

## 5. Full-body validation sweep

Drive the master joint through its range in steps; at each step measure the mechanism's output
from live face geometry (e.g., pad-to-pad gap from plane-face origins) and compare against the
analytic model / URDF FK. Also do a ONE-TIME whole-assembly z-audit via the copy-export bounds —
per-body world bounds expose axial slides that kinematic checks cannot see.

## 6. World-baked per-body mesh export → link frames

```python
tmp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
for each body (skip vertices.count < 3):
    cp = body.copyToComponent(tmp)                 # bakes WORLD coords
    em.execute(em.createSTLExportOptions(cp, f"{out}/b{idx:04d}.stl"))  # mm, MeshRefinementMedium
    cp.deleteMe()
tmp.deleteMe()
# manifest: file → link. Post-process (trimesh): world → link frame AT THE EXPORT POSE, scale 0.001.
# Budget ~1-2 s/body; use a 10 min timeout and poll for the manifest file.
```

## 7. Limits (after all joints exist)

```python
TWO_PI = 6.28318
lo = max(cur - half_range, -TWO_PI + 1e-4); hi = min(cur + half_range, TWO_PI - 1e-4)
lim = rm.rotationLimits
lim.isMinimumValueEnabled = True; lim.minimumValue = lo
lim.isMaximumValueEnabled = True; lim.maximumValue = hi
# read-back may show mod-2π-normalized values; verify the SPAN.
```

## 8. Save into a cloud project folder

```python
proj = <iterate app.data.dataProjects by name>
folder = proj.rootFolder.dataFolders  # itemByName or .add("hardware")
app.activeDocument.saveAs("name", folder, "description", "")
# Drive VALUES persist through save/reopen — the doc reopens at the saved pose.
# Park the canonical pose BEFORE saving. (See api-gotchas.md: an earlier note
# claiming "save resets drives to 0" was wrong; the model had been saved off-pose.)
```
