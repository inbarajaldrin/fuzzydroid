# CAD → URDF Workflow

The canonical recipe for turning a Fusion 360 design into a working ROS 2 URDF
package. Distilled from `plugins/fusion/scripts/export_urdf.py` (the live exporter)
plus the practical gotchas surfaced while rigging real robots (e.g. bunker_mini).

## When to use this

User asks any of:
- "export this as a URDF / ROS package"
- "make a URDF from the Fusion design"
- "rig this CAD for ROS"
- "give me a robot description that loads in RViz / Gazebo / Isaac Sim"

## Two flavours

| Flavour | Use when | Entry point |
|---|---|---|
| **One-shot from a clean Fusion design** | The Fusion design already has joints + a component named `base_link` | `cli-anything-fusion export urdf` (wraps `scripts/export_urdf.py`) |
| **From a flattened STEP** | User provides a `.STEP` file with no assembly hierarchy (single component, hundreds of nameless bodies) | Multi-step: import → cluster bodies by spatial signature → export merged STLs → hand-write the URDF |

The one-shot flavour is preferred. The flattened-STEP flavour is for when the
upstream CAD ships without a real assembly tree.

---

## Flavour A — one-shot URDF export from Fusion

### Required design conventions (script enforces these)

1. **A root component named `base_link`** — the script walks `rootComponent.occurrences`
   looking for it by name. If absent, the export fails with a clear error.
2. **Clean component identifiers**: `motor_1`, `link_1`, `wrist_yaw` — no spaces, no
   special characters. These become URDF link names verbatim.
3. **Joints modelled as Fusion as-built joints or regular joints** (revolute or rigid).
4. **Optionally, an `ee_link` component** — can be a real joint-connected link or an
   orphan occurrence. If orphan, the exporter emits a sphere primitive of radius 0.04 m.

### Run the export

```bash
# Defaults: ./outputs/<doc_name>_urdf, pkg=<doc>_pkg, robot=<doc>
cli-anything-fusion --json export urdf

# Or be explicit:
cli-anything-fusion --json export urdf \
  --path ./outputs/scara_urdf \
  --pkg-name scara_description \
  --robot-name scara_arm
```

### Output structure

```
<path>/
├── CMakeLists.txt
├── package.xml
├── meshes/<link_name>.stl              # one STL per link
├── urdf/
│   ├── <robot>.urdf                    # base — package:// mesh paths
│   ├── <robot>_rviz.urdf               # + world link + joint0_fixed
│   └── <robot>_gazebo.urdf             # + damping + ros2_control + gazebo plugin
├── config/
│   ├── <robot>_gazebo.yaml             # controller config
│   └── <robot>_config.rviz             # rviz scene
└── launch/
    ├── <robot>_rviz.launch.py
    └── <robot>_gazebo.launch.py
```

### Key formulas the exporter uses

These are the load-bearing equations in `export_urdf.py`. They are correct — do not
hand-tweak the output unless you understand them.

```
Visual origin    = -(joint_global_position_where_link_is_child) × 0.01
Joint origin     = (this_joint_global - parent_link_frame_global) × 0.01
Inertia values   = body.getXYZMomentsOfInertia() × 1e-6   # kg·cm² → kg·m²
```

The `× 0.01` is the **cm → m** conversion (Fusion's internal length unit is cm; URDF
is m). The `× 1e-6` is **kg·cm² → kg·m²** because inertia scales as length².

### Joint type discrimination

Fusion models some "fixed" connections as revolute joints with rotation limits set
to a single value. The exporter follows this rule:

| Fusion joint shape | URDF type |
|---|---|
| Rigid joint | `fixed` |
| Revolute with `lower == upper` (or any rotation limits) | `fixed` |
| Revolute with no limits | `continuous` |

Override after export if you need `revolute` with real limits.

### STL export technique (avoiding Fusion's "(1)" suffix)

`exportManager.execute(stlOptions)` adds a `(1)` suffix to the filename if a body
with that name already exists. The exporter sidesteps this with the **rename-before-copy**
pattern:

1. Create a temp component at the root.
2. Copy the target body into the temp component (`bodies.copy(body)` → returns a new body).
3. Rename the copy to the link name.
4. Export the temp component as STL.
5. Delete the temp component (or skip-save).

### Cleanup after export

The script creates temp components inside the design. **Close the Fusion document
without saving** to discard them, or undo manually. The exporter prints a warning
when temps remain.

---

## Flavour B — rigging from a flattened STEP

When upstream CAD ships as a single STEP file with no preserved assembly hierarchy
(AgileX Bunker Mini's `bunker mini2.0对外模型-20221118.STEP` is the canonical
example), you can't use the one-shot exporter. Instead:

### Step 1 — import the STEP

```python
import adsk.core, adsk.fusion
app = adsk.core.Application.get()
opts = app.importManager.createSTEPImportOptions("/path/to/file.STEP")
new_doc = app.importManager.importToNewDocument(opts)
```

Send via `cli-anything-fusion exec -` with the code piped in.

**STEP imports usually flatten to one component with N nameless bodies** (`Body1`,
`Body2`, ..., `BodyN`). The supplier strips the assembly tree before export. You
have to recover semantic structure from geometry.

### Step 2 — classify bodies by spatial signature

Walk `rootComponent.bRepBodies`, record bounding boxes, and cluster:

```python
for i in range(root.bRepBodies.count):
    b = root.bRepBodies.item(i)
    bb = b.boundingBox
    size = (bb.maxPoint.x - bb.minPoint.x,
            bb.maxPoint.y - bb.minPoint.y,
            bb.maxPoint.z - bb.minPoint.z)
    center = ((bb.minPoint.x + bb.maxPoint.x) / 2, ...)
```

Wheel signature: **roundish in one plane, thin in the perpendicular axis**, centered
near the track Y-position. Chassis signature: **large rectangular envelope, central**.
Debris (screws/bolts): **< 50 vertices**.

### Step 3 — export each body as a separate STL via Fusion bridge

```python
em = design.exportManager
for i in body_indices:
    b = root.bRepBodies.item(i)
    opts = em.createSTLExportOptions(b, f"/tmp/out/body_{i:03d}_{b.name}.stl")
    opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
    em.execute(opts)
```

Refinement choices: `MeshRefinementLow` (~5× smaller files, fine for visualization);
`MeshRefinementMedium` (the default for rotating parts that need smooth edges);
`MeshRefinementHigh` (rarely needed for URDF).

### Step 4 — merge bodies into per-link STLs

For each URDF link, concatenate the bodies that belong to it. Use `trimesh`:

```python
import trimesh
meshes = [trimesh.load(p) for p in body_files_for_this_link]
merged = trimesh.util.concatenate(meshes)
merged.apply_scale(0.001)   # IMPORTANT — see unit table below
if recenter:                # for rotating links: centre mesh on joint axis
    c = (merged.bounds[0] + merged.bounds[1]) / 2
    merged.apply_translation(-c)
    joint_origin_world = c   # use as the URDF joint <origin xyz="...">
merged.export(f"meshes/{link_name}.STL")
```

### Step 5 — author the URDF by hand

Mirror an existing rigged URDF's topology (e.g. `bunker_description.urdf`). Substitute
geometry references and joint origins from Step 4.

---

## CRITICAL — unit conventions (single source of truth)

Three units coexist; mixing them is the #1 cause of "the wheels are 100× too big":

| Source | Unit | Convert to URDF metres by |
|---|---|---|
| `body.boundingBox` from Fusion's Python API | **centimetres** | × `0.01` |
| `body.physicalProperties.volume` | **cm³** | × `1e-6` for m³ |
| Inertia from `getXYZMomentsOfInertia()` | **kg·cm²** | × `1e-6` for kg·m² |
| **STL exported by `exportManager`** | **millimetres** | × `0.001` |
| **STEP files from external suppliers** | mm (by convention) | × `0.001` |

Mismatched scales come from forgetting that **Fusion's Python API is in cm** but
**Fusion's STL export is in mm**. Pick one (m, in trimesh) and convert at every
boundary.

---

## Common gotchas (chronological — the order they bite)

1. **STEP imports lose component names.** Bodies become `Body1`, `Body2`, … —
   classify by geometry, not by name.
2. **`getXYZMomentsOfInertia()` returns 6 values** (`ixx, iyy, izz, ixy, iyz, ixz`)
   in that order, in **kg·cm²**. The exporter handles this; if you reuse the API,
   so must you.
3. **Wheel meshes that rotate must be recentered on the rotation axis** before
   saving — otherwise the wheel orbits the joint origin instead of spinning in place.
4. **`urdf-loader` (the JS viewer library) needs `three/examples/jsm/` aliased
   separately from `three/addons/`** in import maps. The plugin's bundled viewer
   handles this — but if you hand-roll a viewer, both prefixes must resolve.
5. **`viewer/urdf/serve_urdf.py` uses ONE `viewer/robot` symlink** — two parallel
   viewer instances need separate copies of the urdf/ scripts dir. See
   `references/urdf-viewer.md`.
6. **Coordinate frame in the Fusion CAD origin may not be REP-103.** Inspect wheel
   positions: if right-side wheels have **negative** Y and left-side **positive** Y,
   you're on REP-103 (X forward, Y left, Z up). Otherwise rotate the whole model
   in the URDF root link's RPY.
7. **`base_link` mesh should NOT include rotating wheel geometry.** If the CAD's
   chassis mesh has tracks/wheels baked in, you'll see the static silhouette plus
   the rotating wheel meshes overlaid (Z-fighting). Either: (a) cut wheels out of
   the chassis mesh, or (b) accept the visual overlap as bunker_description does.

---

## Reference URDFs in this repo / common families

When the user provides a reference URDF and asks for "the same thing on robot X":

- **Mirror the joint topology where it physically applies.** Don't add wheels the
  new robot doesn't have.
- **Mirror joint names** so existing launch files / controllers / configs carry over
  without rewrites.
- **Substitute geometry from the new model's CAD.** Don't scale the reference's
  meshes — they're a different robot.
- **Mirror what's `base_link` vs separate links.** AgileX `bunker_description` puts
  tracks inside `BUNKER.STL` and wheels as separate revolute links; `scout_mini`
  uses 4 continuous wheel joints + transmissions + Gazebo plugin. Pick the reference
  that matches the user's runtime needs (visualization-only vs sim-driveable).

---

## Where things live

- Exporter source: `plugins/fusion/scripts/export_urdf.py` (25 KB, full docstring
  + working implementation)
- Variants: `export_single_urdf.py` (single-link), `export_multi_link_urdf.py`
- CLI wiring: `cli-anything-fusion export urdf` (in `shared/fuzzydroid/fuzzydroid/fusion/cli.py`)
- USD post-process (separate tool): `plugins/fusion/scripts/export_usd.py` —
  standalone STL → USD via `pxr`, not a Fusion-runtime export.
