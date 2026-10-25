# Package architecture: the Robotiq-precedent split

The biggest structural lesson: **do not bake the adapter or its clocking into the gripper
description.** Split the robot into independent packages that compose. This is exactly how
Robotiq's `robotiq_description` is structured, and it is the pattern to follow.

## The three packages

```
workspace / bringup  (composes the chain)
   └─ arm description (e.g. ur_description: ur5e)  -> flange frame tool0
        └─ adapter description (onrobot_quick_changer_description)  -> child mount frame
             └─ gripper description (onrobot_rg2_description)  -> rg2_base_link
```

1. **Gripper-only description** — rooted at its OWN `base_link`, mounted via a
   `parent` + `*origin` block, with NO adapter and NO clocking baked in. The gripper macro
   is *pure*: it knows its native reach axis and nothing about how it attaches to a robot.
2. **Adapter description** — a SEPARATE package on the Robotiq `ur_to_robotiq_adapter`
   pattern. The adapter owns the reach-axis remap, the clocking, and the coaxial standoff.
3. **Workspace / bringup** — composes arm + adapter + gripper. It picks the arm, calls the
   adapter macro with a `rotation`, and parents the gripper onto the adapter's `child` frame.

Why: any gripper can then mount on any adapter on any arm, and the coupling is defined
once, in the adapter, where it physically lives.

## Required outputs of a CAD→URDF pass

A pass is not done when the meshes exist. It ships THREE artifacts (the QC pass shipped
only the third until 2026-07-10, when the user caught the gap):

1. **A saved standalone rigged/reframed Fusion doc**, in the link/datasheet frame — the
   pristine vendor part live-linked and placed by the feature-derived link-frame matrix so
   the link IS the doc frame at identity (parallel to `rg2_rigged`, `quick_changer_rigged`).
   This is the canonical, reliable PRUNE / re-bake source.
   - It MUST be NATIVE, not live-linked: **break the live link** (`Occurrence.breakLink()`)
     so the B-Rep is embedded and the doc is self-contained. A live-linked doc's `.f3d`
     export is a hollow ~33 KB stub (geometry only in the cloud xref); a native doc's is
     multi-MB. Breaking the link copies geometry IN — it does not touch the pristine source.
   - Guard-verify extents (thin-axis + magnitudes) BEFORE saving; breakLink embeds current
     geometry as-is, so pre/post extents must be identical.
2. **A STEP export from that same (native) doc** — the portable, self-contained B-Rep.
   Verify it by re-import (extents + solid count). CAVEAT: after `breakLink`, a direct
   assembly STEP export silently drops bodies (nested-occurrence bug) — export via a
   flatten (TBM-copy all world bodies into one temp base-feature component, STEP that).
   See `references/fusion-cautions.md`.
3. **The baked URDF meshes** (visual `.dae` per color group + collision `.stl` per link).

Record all three in the package/`cad/` README with their verified extents. The `.f3d`
is a reference archive of the doc; the STEP is the portable geometry — say which is which.

## The Robotiq precedent (cite the real files)

Robotiq's `robotiq_description` ships `ur_to_robotiq_adapter.xacro` with the macro
signature:

```
params="prefix parent child rotation"
```

The clocking lives on the **adapter**, via the `rotation` arg. The Robotiq gripper macro
(`robotiq_2f_85_macro.xacro` / `robotiq_2f_140`) is pure — it takes a `prefix` and a
mount, and knows nothing about the UR flange indexing. Mirror this exactly. Upstream:
`ros-industrial`/`PickNikRobotics` `robotiq_description` (package `robotiq_description`,
`urdf/ur_to_robotiq_adapter.xacro`).

## The gripper macro (pure)

Root the gripper at its own base with a `parent` + `*origin`, so the caller decides where
it mounts. Real signature from `onrobot_rg2_description/urdf/onrobot_rg2_macro.xacro`:

```xml
<xacro:macro name="onrobot_rg2" params="prefix parent *origin ...">
  <joint name="${prefix}rg2_base_joint" type="fixed">
    <xacro:insert_block name="origin"/>
    <parent link="${parent}"/>
    <child  link="${prefix}rg2_base_link"/>
  </joint>
  <!-- ... links, drive joint, cover/bumper mimic sub-macro ... -->
</xacro:macro>
```

The QC chain was REMOVED from this macro when the gripper was stripped to gripper-only —
that coupling now lives entirely in the adapter package. `*origin` (a xacro block
parameter) lets the caller inject an arbitrary mount transform.

## The adapter macro (owns the coupling + clocking)

Real signature from `onrobot_quick_changer_description/urdf/onrobot_quick_changer_macro.xacro`:

```xml
<xacro:macro name="onrobot_quick_changer"
    params="prefix:='' parent:=tool0 child:=quick_changer_tool
            rotation:=${pi/2} io:=false
            mesh_pkg:=onrobot_quick_changer_description">
  <xacro:property name="standoff" value="${0.0237 if io else 0.01810}"/>

  <!-- pure clock about the approach axis (+Z) -->
  <joint name="${prefix}quick_changer_joint" type="fixed">
    <parent link="${parent}"/>
    <child  link="${prefix}quick_changer_link"/>
    <origin rpy="0 0 ${rotation}" xyz="0 0 0"/>
  </joint>
  <link name="${prefix}quick_changer_link"> <!-- neutral datasheet-frame mesh --> </link>

  <!-- coaxial standoff -> gripper mount frame -->
  <joint name="${prefix}quick_changer_coupler_joint" type="fixed">
    <parent link="${prefix}quick_changer_link"/>
    <child  link="${child}"/>
    <origin rpy="${-pi/2} ${-pi/2} 0" xyz="0 0 ${standoff}"/>
  </joint>
  <link name="${child}"/>
</xacro:macro>
```

Two joints do the work:
- **joint 1** (`quick_changer_joint`) is a PURE `Rz(rotation)` clock about the approach
  axis. This is the single tunable that indexes the adapter on the flange. Nothing about
  the clocking is in the mesh.
- **joint 2** (`quick_changer_coupler_joint`) is the FIXED coupler→gripper seating:
  `rpy(-pi/2,-pi/2,0)` remaps the gripper's native reach axis onto the approach +Z, and
  `xyz 0 0 standoff` is the coaxial coupling distance (measured from physical faces — see
  `references/coupling-measurement.md`).

## Boolean variant selector

Model real hardware variants with a boolean arg driving a xacro property, not an enum
string. The QC uses `io:=false` (default → QC-R v3, item 109498, the user's part) vs
`io:=true` (→ QC-R I/O, item 102326), selecting the standoff:

```xml
<xacro:property name="standoff" value="${0.0237 if io else 0.01810}"/>
```

The non-IO standoff is **0.01810 m (18.10 mm)** — the coupling read from the CAD's
mating faces (flange → `rg2_base`), per `references/coupling-measurement.md`. The
`io:=true` branch's `0.0237` is carried from an earlier note and has NOT been
re-verified against the QC-R I/O datasheet; confirm it from the I/O part's mating
faces before trusting it.

Document the io→item-number map in the macro header and README so the boolean is
traceable to a real SKU. Do not model discontinued variants unless referenced.

## Neutral mesh frame (see also below)

Export the adapter mesh in the manufacturer DATASHEET's canonical frame — for the QC:
origin at the coupler disc, +Z out of the coupler face (the approach axis), X/Y in the
disc plane (datasheet v1.7 p4 coordinate figure). Keep clocking/indexing in the `rotation`
joint arg, NOT frozen in the mesh. A caller changes `rotation` and the whole adapter+gripper
re-clocks about +Z. This is what makes the mesh reusable across every clocking a robot
integrator needs.

A subtlety worth recording in the header: the CAD you export from may be labelled a
different revision than the user's hardware (the QC STEP was labelled v2; the user's part
is v3). If the COUPLING INTERFACE is standardised (ISO-9409-1-50-4-M6, disc diameter,
coupler height, dowel) and matches across revisions, the coupling is valid even though the
housing appearance differs cosmetically. State this explicitly rather than silently
shipping a v2 mesh as v3.
