# Isaac Sim URDF→USD→drive — failure catalog (symptom → cause → fix)

Use these failure signatures to diagnose conversion and control. The API names
reflect Isaac Sim 5.x; verify them against the installed release before applying
a remedy. Inputs and verification tolerances belong to the current project.

## Conversion

**Symptom:** `IndexError: list index out of range` deep in asyncio during
`from isaacsim import SimulationApp`.
**Cause:** script executed from a directory containing a stdlib-shadowing file
(`/tmp/inspect.py`); `sys.path[0]` = script dir.
**Fix:** run from a clean working directory. Never `/tmp`.

**Symptom:** conversion "succeeds" but prints nothing.
**Cause:** Kit teardown drops unflushed stdout.
**Fix:** `flush=True` on every print after `SimulationApp(...)`.

**Symptom:** docs page for the importer has no Python API.
**Cause:** genuinely undocumented.
**Fix:** `omni.kit.commands.get_commands()` → `URDFCreateImportConfig`,
`URDFParseAndImportFile(urdf_path, import_config, dest_path)`; `dir(config)`
for fields. Introspect, don't trust memory or docs.

**Symptom:** importer can't find meshes.
**Cause:** `package://` URIs; the ROS-package mapping is GUI-oriented.
**Fix:** pre-resolve to `file://` by string replacement in a working copy.

**Symptom:** the importer SEGFAULTS (breakpad dump in
`libisaacsim.asset.importer.urdf.plugin.so`) partway through a multi-mesh robot — reproduced on a
bare UR5e arm; a single-link coupler or the RG2 gripper alone import fine.
**Cause:** `URDFParseAndImportFile`'s **multi-layer `dest_path` writer** (the one that emits
`configuration/<name>_base.usd` + the instanceable split) crashes writing the UR5e visual DAEs. It is
NOT the meshes and NOT the mimic tree — it's the on-disk writer. On the composed workcell it dies right
after link/inertia parsing, leaving 492-byte stub layers.
**Fix:** import into the **in-memory stage** and export a flat file instead of using the multi-layer
writer: `omni.usd.get_context().new_stage()`, then `URDFParseAndImportFile(..., dest_path="")` (empty
dest = current stage), then `stage.Export(out.usd)`. Crash-free on the full UR5e + QC + RG2 workcell
(16 revolute DOFs, colored). Small single-part robots survive the `dest_path` writer either way; the
multi-DAE arm is what trips it — so reach for the flattened in-stage export for any full-robot import.

## Verification

**Symptom:** 0 meshes counted on a stage traverse of a 130 MB USD.
**Cause:** importer marks meshes instanceable; `Usd.Stage.Traverse()` skips
instance internals.
**Fix:** judge geometry by folder size / open in GUI; count joints and bodies
instead.

**Symptom:** `default prim: None` in the entry USD.
**Cause:** the importer doesn't set one.
**Fix:** not fatal — but it CAUSES the hollow-reference trap below. Record the
robot root prim path (e.g. `/robot_name`) for Phase 3.

## Scene loading

**Symptom:** referenced robot prim exists but stage has NO ArticulationRootAPI;
`SingleArticulation` later fails `'NoneType' object has no attribute 'is_homogeneous'`.
**Cause:** `add_reference_to_stage` references the file's default prim — which
is unset → hollow composition.
**Fix:** `prim.GetReferences().AddReference(usd_path, "/<robot_root_prim>")`.

## Driving

**Symptom:** `'NoneType' … is_homogeneous'` even with a solid reference.
**Cause:** articulation view constructed/initialized before physics exists.
**Fix:** `world.play_async()` → several `world.step(render=False)` →
`SingleArticulation(path).initialize(world.physics_sim_view)`. On `stop()`,
drop cached views (they die with the sim).

**Symptom:** robot explodes / welded parts separate when commanded.
**Cause:** `set_joint_positions` teleports state.
**Fix:** `apply_action(ArticulationAction(joint_positions=..., joint_indices=...))`
— PD targets resolved by the solver. (House rule inherited from the UR5e seeds.)

**Symptom:** passive joints sag below their commanded pose.
**Cause:** URDF-import default drive gains too weak vs gravity/lever arms.
**Fix:** raise `drive:*:physics:stiffness/damping` on those joints in the USD,
or accept cosmetically.

## ROS 2 bridge

**Symptom:** wondering which OmniGraph nodes to use.
**Fix (verified names, 5.0):** `omni.graph.action.OnPlaybackTick`,
`isaacsim.ros2.bridge.ROS2Context`, `isaacsim.ros2.bridge.ROS2SubscribeJointState`
(input `topicName`), `isaacsim.core.nodes.IsaacArticulationController`
(input `robotPath`). Connect tick→sub exec, ctx→sub context, sub's
jointNames/position/velocity/effortCommand → controller. On failure, dump
`og.get_registered_nodes()` filtered — never guess.

**Symptom:** `RTPS_TRANSPORT_SHM Error … open_and_lock_file failed` on `ros2 topic` /
bridge startup.
**Cause:** FastRTPS shared-memory transport on a multi-user box.
**Fix:** cosmetic — UDP transport carries the traffic. Ignore.

**Symptom:** two publishers on the command topic fight (e.g. a GUI at 20 Hz and a
test `ros2 topic pub`).
**Fix:** expected last-writer-wins interleave; for tests, publish faster than the
GUI or stop it. Design one authoritative commander.

## Remote ops

**Symptom:** SSH command exits 255 and everything died mid-script.
**Cause:** `pkill -f <word>` matched the remote bash's own command line (the
script text contains the word — e.g. in the relaunch line).
**Fix:** `[b]racketed` patterns AND split kill / launch into separate SSH calls.

**Symptom:** tkinter GUI survives pkill.
**Cause:** SIGTERM ignored mid-mainloop.
**Fix:** `pkill -9`.

**Symptom:** freshly-registered Kit config vanishes.
**Cause:** a running Kit app overwrites `user.config.json` on graceful exit.
**Fix:** register while stopped, or `kill -9` (no config flush) then relaunch.

## Live-control layer (added after the drive-debugging round)

**Symptom:** robot pinned at exact 0.0 on every DOF; `set_axis` returns ok but nothing
moves; earlier there was PD jitter, now perfectly flat readings.
**Cause (three stacked, disambiguate in this order):**
1. *Competing commander* — a ROS graph applying `/joint_states` every tick stomps any
   native target within one frame (a GUI publishing its parked zero counts!).
2. *Stale physics view* — stop/play recreates `world.physics_sim_view`; a cached
   articulation bound to the OLD view: `apply_action` logs
   `Physics Simulation View is not created yet` and NO-OPS, while position reads return
   the rest pose with no error. **`handles_initialized` LIES on stale objects** (it
   remembers being initialized once), and after a GUI stop/play even
   `id(world.physics_sim_view)` can be unchanged while the underlying PhysX view is
   dead. The honest detector is a VALIDITY PROBE:
   `articulation_view.is_physics_handle_valid()` (fall back to checking the view's
   `_physics_view`/`is_valid`), combined with the id check; rebuild on either.
3. *Sag vs drives* — gravity beating weak imported drive gains (droop, not pinning).
**Fixes:** one authoritative commander (see below); view-identity rebuild; gravity off +
gains via `articulation_view.set_gains` (PhysX-level — runtime USD DriveAPI edits are
unreliable and helped cause #2's confusion).

**Symptom:** deactivating the ROS graph prim (`prim.SetActive(False)`) changes nothing —
targets still stomped every tick.
**Cause:** OmniGraph keeps evaluating a LOADED graph whose prim is deactivated.
**Fix:** `stage.RemovePrim(graph_path)` to disable; rebuild the graph to re-enable.
Design the toggle as remove/rebuild, never SetActive.

**Symptom:** measuring sim-time advancement with `time.sleep` inside a bridge
`run_python` always reads 0.
**Cause:** run_python executes on Kit's MAIN thread — the sleep blocks the run loop you
are measuring.
**Fix:** measure across two separate bridge calls (wall time passes outside Kit).

**Symptom:** after `reload_tools`, bridge tools behave new but an on-screen
`omni.ui` window still runs OLD code.
**Cause:** windows built by the previous module instance survive reload with stale
closures.
**Fix:** declare the window in `register()` with `registrar.window("<title>")` — the
bridge destroys the declared window when the owner unregisters (every reload), so the
tool rebuilds fresh and reload self-heals eagerly. A manual destroy-by-title
(`ui.Workspace.get_window(name).destroy()`) then rebuild is the fallback when the
package doesn't declare its window — but it heals only lazily, on the next call.

**Symptom:** a "sweep" tool yanks the robot violently to its start point (and fast
transients swing chain links through geometry, since articulation self-collision is
off by import design).
**Cause:** ramping from a HARDCODED start while the robot is elsewhere — the first
PD target teleports the goal.
**Fix:** sweeps start from the CURRENT joint position (read it, then linspace), and
pace steps (≤~2 mm per physics step). Pacing IS the collision guard for
self-collision-free articulations.
