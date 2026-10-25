# Chain rigging — script skeletons

All run via `cat script.py | ~/.local/share/fuzzydroid/fusion/venv/bin/fzd-fusion --json exec -`
(never printf — it eats `%`). Start every script with the document-activation
preamble (rig-joints). Long jobs: `export FUSION_BRIDGE_TIMEOUT=540`, Bash timeout
600000, and log progress to a file. Derive all geometry, part names, and
calibration data from the current assembly before applying these skeletons.

## 1. Adjacency discovery

```python
def circle_edges(o, rmin, rmax):            # rmin/rmax bracket the pin radius (cm)
    out=[]
    for b in o.bRepBodies:
        for e in b.edges:
            g=e.geometry
            if g and g.curveType==adsk.core.Curve3DTypes.Circle3DCurveType and rmin<=g.radius<=rmax:
                out.append((e,(g.center.x,g.center.y,g.center.z),g.radius))
    return out
# adjacency: same-radius (<0.02) + coincident center (<0.06) between two parts
# graph walk from the anchored bracket -> ordered edges [(parent, child, pivot), ...]
# widen rmin/rmax if an end bracket is missing from the graph (degree-0 node)
```

## 2. Gate ladder (regular revolute per edge)

```python
# per attempt: REFETCH pairs (proxies die on create/delete), pick pairs[pi]
gc=adsk.fusion.JointGeometry.createByCurve(ec, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
gp=adsk.fusion.JointGeometry.createByCurve(ep, adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
inp=root.joints.createInput(gc,gp); inp.isFlipped=flip
if angle: inp.angle=adsk.core.ValueInput.createByReal(angle)
inp.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
j=root.joints.add(inp); adsk.doEvents()
disp = dist(far_landmark_now, far_landmark_before)      # far = circle center farthest from pivot
# accept < 0.08cm (mating clearance ~0.05 reads as "displacement" — don't gate at 0.05 exactly)
# ladder order: (pair0,noflip,angle-iter) -> other pairs -> flips -> SWAPPED child/parent geometry
# angle compensation: signed atan2 rotation of far-landmark about pivot in chain plane; angle -= dang
# delete failures with j.deleteMe() / entity.deleteMe() — NEVER timelineItem.deleteMe() in direct mode
```

## 3. Create-once + heal (bridging joints / any corruption)

```python
def heal_joint(parent, child, joint, target, pivot, tries=4):
    for _ in range(tries):
        e0=err(child)
        if e0<0.1: return
        dang = signed_angle_about(pivot, landmark(child), target)   # chain plane
        base=joint.jointMotion.rotationValue
        best=(e0,base)
        for sgn in (+1,-1):
            drive_to(joint, base+sgn*dang)
            if err(child)<best[0]: best=(err(child), base+sgn*dang)
            drive_to(joint, base)
        drive_to(joint, best[1])
# walk proximal->distal, 2-4 full rounds. drive_to steps <=0.25 rad with doEvents().
# Rigid-move a DANGLING segment first (transform2 premultiply, conjugated through the
# parent occurrence: local' = Pinv @ C_world @ P @ local) — works in direct mode.
```

## 4. Calibration dump

Measure per edge: fresh pivot (coincident pair center), `r0 = rotationValue`, sign
(drive +0.06 → measure child rotation direction → restore). Fit path params (see
math reference). Dump one JSON: edges, r0, signs, pins, z_top/z_bot/R, pitch,
anchor, tail. This file + the pose function IS the chain driver — keep it with the
project (and port it to the ROS side unchanged).

## 5. Pose application

```python
def apply_pose(q):
    drive_slider(slider_value_for(q))        # know your slideValue<->world sign!
    d = deltas(q)                            # from the path model
    for k, jn in enumerate(edge_names):
        J[jn].jointMotion.rotationValue = r0[jn] + signs[jn]*wrap(d[k]-d0[k])
    adsk.doEvents()
# park FIRST in every sweep script (a crashed previous run leaves the model posed;
# baselines captured on a displaced model poison every measurement afterward)
# restore = drive slider to park + set r0 values DIRECTLY; verify residual ~0.0000
```

## 6. Sweep → GIF

Fixed camera (fit ONCE at the widest pose, reassign saved camera per frame),
`saveAsImageFile`, forward+reverse frame order, `ffmpeg -framerate 5 -loop 0`.
Full recipe: `../making-gifs.md`.

## Failure quick-reference

| Symptom | Cause → fix |
|---|---|
| child thrown ~8 cm laterally at creation | wrong coincident pair → brute-force pairs |
| compensation diverges (error doubles) | bridging joint → swap geometry sides |
| "A joint in system exists" forever | phantom joint → entity.deleteMe(), check timeline |
| poses regress after each retry | driven-pose create/delete churn → create once, heal |
| whole segment off by former-attempt residue | deletion didn't restore segment → rigid-move + heal |
| heal stalls at a constant offset on a whole run | joint pinned on wrong PIN END → recreate that joint |
| solver "articulates" then everything corrupts | you closed the loop → don't; scripted poses |
```
