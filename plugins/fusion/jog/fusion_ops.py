# Fusion-side operations for the robot jog server.
#
# Each op is Python source executed inside Fusion's runtime on the MAIN thread
# via the bridge's exec_python command; results come back as one JSON line.
# Fusion internal units: revolute joint values are radians, slider values cm.

import json

try:
    from . import bridge_client
except ImportError:  # run as a plain script (serve_jog.py adds this dir to sys.path)
    import bridge_client


SCAN_CODE = r'''
import adsk.core, adsk.fusion, json
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
out = {"doc": None, "joints": []}
if design:
    out["doc"] = app.activeDocument.name
    seen = set()
    def add(j, context):
        try:
            tok = j.entityToken
        except Exception:
            return
        if tok in seen:
            return
        seen.add(tok)
        e = {"token": tok, "name": j.name, "context": context}
        try:
            m = j.jointMotion
            jt = m.jointType
            if jt == adsk.fusion.JointTypes.RevoluteJointType:
                e["kind"] = "revolute"
                e["value"] = m.rotationValue
                lim = m.rotationLimits
                e["min"] = lim.minimumValue if lim.isMinimumValueEnabled else None
                e["max"] = lim.maximumValue if lim.isMaximumValueEnabled else None
            elif jt == adsk.fusion.JointTypes.SliderJointType:
                e["kind"] = "slider"
                e["value"] = m.slideValue
                lim = m.slideLimits
                e["min"] = lim.minimumValue if lim.isMinimumValueEnabled else None
                e["max"] = lim.maximumValue if lim.isMaximumValueEnabled else None
            else:
                e["kind"] = "other"
                e["jointType"] = jt
        except Exception as ex:
            e["kind"] = "error"
            e["error"] = str(ex)
        out["joints"].append(e)
    root = design.rootComponent
    for j in root.joints:
        add(j, "root")
    # As-built joints are a separate collection with the same motion API
    # (the rg2 v27 rig is all as-built revolutes).
    for j in root.asBuiltJoints:
        add(j, "root")
    # Joints defined inside (possibly externally referenced) components must be
    # driven through their assembly-context proxy, not the native object.
    for occ in root.allOccurrences:
        try:
            for j in occ.component.joints:
                try:
                    add(j.createForAssemblyContext(occ), occ.fullPathName)
                except Exception:
                    pass
            for j in occ.component.asBuiltJoints:
                try:
                    add(j.createForAssemblyContext(occ), occ.fullPathName)
                except Exception:
                    pass
        except Exception:
            pass
print(json.dumps(out))
'''


SET_CODE_TEMPLATE = r'''
import adsk.core, adsk.fusion, json
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
sets = json.loads(%(sets_json)r)
out = {"applied": 0, "errors": [], "actual": {}}
targets = []
for tok, value in sets:
    try:
        ents = design.findEntityByToken(tok)
        if not ents:
            out["errors"].append({"token": tok[:24], "error": "token not found"})
            continue
        j = ents[0]
        m = j.jointMotion
        if m.jointType == adsk.fusion.JointTypes.RevoluteJointType:
            m.rotationValue = float(value)
        elif m.jointType == adsk.fusion.JointTypes.SliderJointType:
            m.slideValue = float(value)
        else:
            out["errors"].append({"token": tok[:24], "error": "unsupported joint type"})
            continue
        out["applied"] += 1
        targets.append((tok, m))
    except Exception as ex:
        out["errors"].append({"token": tok[:24], "error": str(ex)})
try:
    adsk.doEvents()
    app.activeViewport.refresh()
except Exception:
    pass
# Read back post-solve values: near joint limits the solver may clamp (or on a
# failed solve revert), so the caller must learn what Fusion actually did.
for tok, m in targets:
    try:
        if m.jointType == adsk.fusion.JointTypes.RevoluteJointType:
            out["actual"][tok] = m.rotationValue
        else:
            out["actual"][tok] = m.slideValue
    except Exception:
        pass
print(json.dumps(out))
'''


PALETTE_CODE_TEMPLATE = r'''
import adsk.core, json
app = adsk.core.Application.get()
ui = app.userInterface
pid = 'fzdRobotJog'
existing = ui.palettes.itemById(pid)
if existing:
    existing.deleteMe()
p = ui.palettes.add(pid, 'Robot Jog', %(url)r, True, True, True, %(width)d, %(height)d)
p.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
print(json.dumps({"palette": pid, "url": %(url)r}))
'''


READ_CODE_TEMPLATE = r'''
import adsk.core, adsk.fusion, json
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
tokens = json.loads(%(tokens_json)r)
out = {}
for tok in tokens:
    try:
        ents = design.findEntityByToken(tok)
        if not ents:
            continue
        m = ents[0].jointMotion
        if m.jointType == adsk.fusion.JointTypes.RevoluteJointType:
            out[tok] = m.rotationValue
        elif m.jointType == adsk.fusion.JointTypes.SliderJointType:
            out[tok] = m.slideValue
    except Exception:
        pass
print(json.dumps(out))
'''


def scan(timeout=120.0):
    """Enumerate the active document's joints. Returns {doc, joints:[...]}"""
    return bridge_client.exec_json(SCAN_CODE, timeout=timeout)


def set_joints(sets, timeout=120.0):
    """Apply [(token, value), ...] — radians for revolute, cm for slider."""
    code = SET_CODE_TEMPLATE % {'sets_json': json.dumps(list(sets))}
    return bridge_client.exec_json(code, timeout=timeout)


def read_values(tokens, timeout=30.0):
    """Read current native values for known joint tokens: {token: value}."""
    code = READ_CODE_TEMPLATE % {'tokens_json': json.dumps(list(tokens))}
    return bridge_client.exec_json(code, timeout=timeout)


def open_palette(url, width=390, height=640, timeout=60.0):
    """Create (or replace) the Robot Jog palette docked on the right."""
    code = PALETTE_CODE_TEMPLATE % {'url': url, 'width': width, 'height': height}
    return bridge_client.exec_json(code, timeout=timeout)
