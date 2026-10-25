---
name: urdf-to-usd
description: Convert a URDF and its meshes into an Isaac Sim USD articulation, verify the imported structure and geometry, and establish native or ROS 2 drive control. Use for URDF imports, empty USD references, articulation initialization, mimic coupling, material preservation, and drive troubleshooting.
---

## Agent host compatibility

This skill works in Claude Code and Codex. Resolve symlinks on this file; the
plugin root is three parent directories above this `SKILL.md`. Use that absolute
root for `plugins/<plugin>/...` examples, regardless of the working directory.
When `CLAUDE_PLUGIN_ROOT` is unavailable, pass the resolved root under that name
to commands that use it. Use the host's equivalent tools for `Bash`, `Read`,
`WebFetch` and user questions. In Codex, `$plugin:skill` invokes the sibling skill
named by a `/plugin:skill` reference. Read sibling `SKILL.md` files directly when
needed; do not assume another host's slash commands exist.

# URDF to a driven USD articulation

Use the user's robot description, meshes, installed Isaac version, and machine
state. Keep generated conversion scripts and robot-specific control packages in
that project. Do not assume a particular robot, venv name, source prim, or GPU box.

## Convert

1. Resolve every `package://` mesh URI from the actual package roots. Write a
   working URDF with importer-resolvable paths; preserve the source file.
2. Run from a clean project directory with Isaac's own Python environment. Avoid
   directories containing files that shadow stdlib modules such as `inspect.py`.
3. Start `SimulationApp` before importing Kit modules, then enable the installed
   URDF importer extension. Discover command names and config fields from that
   installation. Isaac 5.x exposes `URDFCreateImportConfig` and
   `URDFParseAndImportFile(urdf_path, import_config, dest_path)`.
4. Choose fixed-base behavior, fixed-joint merging, inertia handling, mimic
   parsing, self-collision, units, and drives from the current mechanism. Record
   those choices rather than reusing another robot's preset.
5. Flush progress output and retain the importer's status and output paths.

Keep the output's entry USD and configuration layers together. Mesh payloads
may live in referenced layers rather than directly in the entry file.

## Verify structure and geometry

Run the bundled audit with Isaac's interpreter:

```bash
<isaac-python> <skill-dir>/scripts/verify_usd.py <robot.usd>
```

Compare its joint counts, rigid-body count, articulation roots, and default-prim
status to the source URDF. The helper checks structural presence; additionally
verify expected link extents, visual colors, collision coverage, and the actual
composed scene. Traverse instance proxies when inspecting instanceable meshes.

A watertight repair can discard open-shell geometry. Compare per-link source
and output extents; a prim's existence alone does not prove a complete mesh.
For importer material limitations, split visual meshes into single-color groups
and verify their bound USD materials after composition.

## Compose the robot

An entry USD without a default prim can produce an empty reference. Inspect the
source stage and reference the intended source prim explicitly when needed:

```python
prim = stage.DefinePrim("/World/Robot", "Xform")
prim.GetReferences().AddReference(absolute_usd_path, source_prim_path)
```

Resolve the composed prim carrying `ArticulationRootAPI` by traversal. Do not
assume it is the reference's top-level prim. Ground planes and base fixation are
scene decisions; a fixed-base floating tool does not automatically need a floor.
For multi-robot composition and simulation lifecycle, use `/isaacsim:assemble`.

## Establish native drive control

Use `/isaacsim:create-extension` to expose a project-specific control namespace.
Initialize the articulation after physics starts, against the current physics
view. Rebuild cached handles after stop/play invalidates that view.

Prefer physical drive targets (`ArticulationAction`) when force-driven behavior
is required. Confirm simulation time advances and inspect actual positions over
multiple frames; target readback alone does not prove motion. Inside Kit async
handlers, await frame updates instead of synchronously pumping the event loop.

Validate native mimics over the full stroke. If imported coupling locks the
mechanism, investigate follower drives and joint topology. Host-side coupling
can reproduce the model only after its signs, offsets, and limits are verified.
A kinematic interpolation fallback must be labeled as kinematic and cannot serve
as evidence of force-controlled grasping or contact behavior.

## Collision and ROS integration

Use `/isaacsim:add-physics` to choose colliders from geometry and required
contacts. De-instance editable collision scopes when necessary, apply the
physics APIs explicitly, and validate settling and the intended collision pairs.

For ROS 2 control, discover the installed bridge's supported nodes. A direct
path uses a joint-state subscriber feeding an articulation controller. Verify
ROS domain, middleware, topic namespace, joint names, units, and observed motion
end to end; do not infer interoperability from the graph merely existing.

If the installed ROS bridge cannot interoperate, a project ROS node can call the
native control tools through the bridge client and publish the same verified
joint model for RViz. Keep command and state semantics explicit, and namespace
project topics to avoid disturbing unrelated robot stacks.

## References

- `references/isaac-gotchas.md` — conversion, composition, and initialization
  failure signatures and remedies.
- `scripts/verify_usd.py` — structural articulation audit.
- `/fusion:rig-joints` and `/fusion:cad-to-urdf` — upstream CAD and mesh export.
- `/isaacsim:create-extension`, `/isaacsim:assemble`, and `/isaacsim:add-physics`
  — control tooling, scene assembly, and contact validation.
