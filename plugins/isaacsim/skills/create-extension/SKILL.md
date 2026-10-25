---
name: create-extension
description: Scaffold a NATIVE Isaac Sim control extension for a USD articulation — an omni-kit-mcp tool package (MCP_NAMESPACE + register(registrar)) that loads the robot into a live scene, plays physics, drives the joints (natively; ROS folds in later), animates a stroke, and shows an omni.ui control panel. Use whenever the user wants to "make an Isaac extension", "drive my robot in Isaac natively", "add a gripper/robot control panel to Isaac", "wrap my USD articulation as a tool package", or has a URDF-imported USD (see urdf-to-usd) ready to graduate into an interactive, agent-drivable Kit tool. Covers the load-bearing rules that are NOT obvious: articulation acquire order, the apply_action drive-target trap, the kinematic-drive fallback, view-identity rebuild across stop/play, hot-reload-safe omni.ui windows, headless viewport capture, and the tailnet-bound bridge host.
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

# Native Isaac Sim control extension (omni-kit-mcp tool package)

The last leg after `urdf-to-usd`: a USD articulation becomes an **interactive,
agent-drivable** Kit extension. The lab's "extension" is an **omni-kit-mcp tool
package** — a plain Python package (NOT a Kit `extension.toml` extension) that
declares `MCP_NAMESPACE` and one `register(registrar)` entrypoint. The bridge
autoloads it; every tool is dispatchable over the wire (`<namespace>.<tool>`) and
appears as a native MCP tool to an agent, and a panel click IS an agent call.

Build the control package in the user's project using the contract and lifecycle
rules below. Resolve USD paths, joint mappings, coupling parameters, bridge
endpoints, and ROS namespaces from that project. Keep machine-specific demos
and bring-up scripts with the project.

## The registration contract

```python
MCP_NAMESPACE = "myrobot"           # tools land as myrobot.<tool>
def register(registrar):            # the autoload entrypoint
    @registrar.tool("Human description.", {"arg": {"type": "number", "default": 0.0}})
    async def do_thing(arg: float = 0.0):
        import omni.usd               # Kit imports live INSIDE handlers (package stays
        ...                           #   importable off-Kit for tests)
        return {"ok": True}           # payload only — the bridge builds the envelope
```

Register per-launch with env knobs (no Kit restart, no `.toml`):
```
OMNI_KIT_MCP_PORT=<port> KIT_MCP_TOOL_PATHS=<parent-dir> KIT_MCP_TOOL_MODULES=myrobot_tools \
  isaacsim --ext-folder <omni-kit-mcp>/exts --enable omni.kit.mcp --no-window
```
Iterate without relaunch: `reload_tools {"module": "myrobot_tools"}`.

## Recommended control surface

| tool | does |
|---|---|
| `load_scene` | World + lights + reference the USD at `/World/<Robot>`; strip any ground plane for a fixed-base robot |
| `play` / `stop` | timeline play/stop; `stop` drops the cached articulation |
| `set_<cmd>` | drive to a commanded value (mm/θ/axis position) |
| `sweep` | animated, physics-stepped, starts from CURRENT pose, paced |
| `get_state` | read joint positions → domain units |
| `show_slider` | an `omni.ui` window that dispatches a drive tool on every tick |
| `capture` | fire-then-step viewport → PNG (frames a camera + lights once); the video-recipe primitive |
| `ros_start` / `ros_stop` | subscribe a namespaced joint-states topic + drive the articulation each physics step (see ROS section) |

## Load-bearing rules (the non-obvious ones that cost real debugging time)

1. **Reference the explicit source prim — the entry USD has NO default prim.**
   `stage.DefinePrim(P,"Xform").GetReferences().AddReference(usd, "/<robot_root>")`.
   `add_reference_to_stage` targets the (unset) default prim → hollow composition,
   no articulation root, and `SingleArticulation` dies later with
   `'NoneType' … 'is_homogeneous'`. (Or set `make_default_prim=True` at import.)
   Use an **absolute** USD path — a relative ref composes hollow silently.

2. **Acquire the articulation only AFTER physics is live.** `await world.play_async()`
   → a few `world.step(render=False)` → `SingleArticulation(art_path).initialize(
   world.physics_sim_view)`. Point it at the prim carrying `ArticulationRootAPI`
   (often `<robot>/root_joint`) — resolve by traversal, never assume.

3. **View-identity rebuild across stop/play.** A stop/play recreates
   `world.physics_sim_view`; an articulation cached against the old one silently
   NO-OPs `apply_action` while reads return the rest pose, and `handles_initialized`
   *lies* (remembers being true once). The honest detector: compare
   `id(world.physics_sim_view)` AND probe `articulation_view.is_physics_handle_valid()`;
   rebuild on either.

4. **The drive-target trap — and the kinematic fallback.** The Isaac 5.x URDF
   importer's joint drives do not always track POSITION targets: on the RG2 build,
   `apply_action(joint_positions=…)`, `articulation_view.set_dof_position_targets`,
   AND direct USD `DriveAPI` target writes all NO-OP (gains/max-effort confirmed set,
   target readback correct) — only `set_joint_positions` (direct state) moved it.
   Diagnose in this order: (a) is the sim actually stepping? read
   `timeline.get_current_time()` across TWO bridge calls — inside one `run_python`
   the main-thread loop is blocked so `world.step()` increments the counter but sim
   time is frozen; physics advances between calls over wall-clock. (b) is gravity
   even a valid probe? if all joint axes are parallel to gravity (e.g. a gripper
   with vertical Z axes) there is zero gravity torque, so "no sag" is expected, not
   frozen. (c) if targets genuinely no-op, and the mechanism has no closed loops and
   self-collision is off, **drive kinematically**: interpolate `set_joint_positions`
   over N sub-steps. It is exact, smooth when paced,
   and holds (no gravity torque about vertical axes). Grasping an external object is
   the one thing kinematic drive can't do — flag it, don't fake it.

5. **When PD drive DOES work, use it, never `set_joint_positions`.** For force-driven
   articulations (e.g. Vention), `apply_action(ArticulationAction(...))` PD targets are
   correct; `set_joint_positions` teleports and explodes welded/constrained assemblies.
   Set gains PhysX-level via `articulation_view.set_gains` (runtime USD DriveAPI edits
   are unreliable). This is a per-robot decision — test both and pick what actually moves.

6. **Coupled DOFs: reproduce host-side unless the native coupling drives.** The RG2's
   9 mimic joints imported as native `PhysxMimicJointAPI` (structurally correct) but
   could not be driven (the whole 4-bar locked). Import with `parse_mimic=False` and
   reproduce the coupling host-side with the ±multiplier table — the same pattern as
   Vention's drag chain (`θᵢ(q)` computed once, sent as extra targets: one math, three
   runtimes). Derive the coupling table or pose engine from the current robot model.

7. **Hot-reload-safe `omni.ui` windows.** A window built by a previous module instance
   survives `reload_tools` with STALE closures. Declare the title in `register()` with
   `registrar.window("<title>")` — the bridge destroys the declared window when the
   owner unregisters (every reload), so the spawning tool just rebuilds fresh and reload
   self-heals eagerly. Keep a one-line destroy-by-title in the tool
   (`ui.Workspace.get_window(title).destroy()`) only as a re-invoke guard. (No
   `registrar.window`? Then destroy-by-title is your *only* guard — lazy, and the window
   shows stale until the next call.)

8. **Sweeps start from the CURRENT pose and are paced.** Reading the start pose then
   `linspace` (never a hardcoded start) avoids a teleport-yank on the first step; pace
   ≤ a small delta per step. For self-collision-free articulations, pacing IS the guard.

9. **Never pump Kit's loop from a handler — `await` the frame.** Your tool runs as a
   coroutine ON Kit's main event loop (the bridge hops it there — USD/PhysX are
   main-thread-only). A *synchronous* pump from inside it re-enters the running loop, and
   asyncio forbids that: a hard `RuntimeError: Cannot enter into task … while another task
   … is being executed`, cascading over every pending UI coroutine — under a live
   viewport (webrtc) it can take the process down. Culprits: `omni.kit.app.get_app()
   .update()`, `world.render()`, and `world.step(render=True)` (which calls `update()`).
   Instead make the handler `async def` and advance by awaiting, which yields to the loop
   AND (while playing) advances real sim time:
   ```python
   world = World.instance()
   if not world.is_playing():
       await world.play_async()
   for _ in range(n):
       await omni.kit.app.get_app().next_update_async()   # 1 dt + frame, no re-entry
   vel = art.get_joint_velocities()                       # real at-rest read
   ```
   Do NOT use `world.step_async` — Isaac's `World.step_async` is a broken override (sync
   `def`, takes `step_size` not `render`, runs only pre-step hooks, returns `None`; its
   docstring's `await world.step_async()` is misleading). Sync `world.step(render=False)`
   doesn't crash but freezes sim time inside the blocked call — `next_update_async` is the
   honest fix. (This is also why a settle loop and at-rest velocity reads only work in an
   async handler.)

## Headless evidence (screenshots without a window)

Headless (`--no-window`) has no X11 window to grab. Capture the offscreen viewport
from an **`async` tool** (never a sync `run_python` payload — capture needs to advance
frames, and pumping the loop from a handler re-enters it and crashes, see rule 9):
add a `UsdLux.DomeLight` + a `DistantLight` (an unlit scene renders BLACK), frame a
camera (`ViewportCameraState.set_position_world/set_target_world`), warm the render
with ~60–80 `await omni.kit.app.get_app().next_update_async()`, then
`capture_viewport_to_file(vp, path)`, then ~40 more `await …next_update_async()` so the
async write lands; `get_file` it back. Never `await capture_viewport_to_file` itself
(it waits for a frame the loop can't produce while you hold it — deadlock) and never
sync-`update()`/`world.step(render=True)` to warm (re-entry crash). See
`references/capture_viewport.py`.

**Video = kinematic stroke → viewport frames → ffmpeg.** Expose a `capture(path)` tool
(fire-then-step; sets the camera + lights once). To record actuation, drive the stroke and
capture a frame per step: `for th in linspace(open, closed): set_pose(th); capture(frame_%04d)`,
then `ffmpeg -framerate N -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p -vf
"pad=ceil(iw/2)*2:ceil(ih/2)*2" out.mp4`. This end-to-end recipe (no authored anim layer) is what
the `/isaacsim:animation` recorder can't do — that one drives authored xformOp timecodes, not a
live articulation. For a ROS-driven video, publish the width ramp and capture in the subscriber
and store the recording script in the project.

## Driving from ROS (host-side bridge — the robust path when Isaac's internal DDS won't interop)

Isaac 5.0 ships its own bundled ROS2 (Humble + CycloneDDS). In practice its OmniGraph subscriber
would not receive from a **system-Humble** publisher on a non-default `ROS_DOMAIN_ID` (the
`ROS2Context.domainId` didn't propagate to the internal DDS), so the "canonical" graph
`ROS2SubscribeJointState → IsaacArticulationController` was a dead end (and that controller applies
PD targets, which no-op per rule 4 anyway). The path that ships reliably:

- **A system-Humble ROS node bridges ROS → Isaac over the omni-kit-mcp bridge** (NDJSON, not DDS):
  it subscribes the command topic and calls a drive tool (`myrobot.set_width`) via the reference
  client (`kit_mcp.client.BridgeClient`), and republishes `/joint_states` so an RViz
  `robot_state_publisher` follows the same command. **One command → sim + RViz together.**
- **Namespace it** (`/<robot>/*`) and use your own domain so you never disturb a running lab stack on
  `/joint_states` / domain 0.
- Keep a `ros_start`/`ros_stop` extension tool with the OmniGraph subscribe + a physics-step
  `set_joint_positions` callback **wired but optional** — it's the direct-subscribe path for when
  the internal-DDS interop is fixed; the bridge path is what you demo today.
- **Persistent ROS nodes over SSH are the flaky part, not the ROS.** Launch them in **tmux**
  (survives disconnect); an exiting demo script runs fine backgrounded, a forever-node does not.
Keep the ROS adapter, robot-state-publisher configuration, RViz configuration,
and process launcher in the user's project.

## Ops (remote bridge)

- The bridge often binds the **tailnet IP**, not localhost — `ss -ltnp | grep <port>`;
  dial that host (`--host <tailnet-ip>`), or let the client discover it from the portfile
  (endpoint discovery resolves host+port together, so a no-arg `call()` dials the
  advertised host).
- One bridge per Kit process; run a second instance on its own `OMNI_KIT_MCP_PORT`
  so you never disturb another agent's Isaac.
- `run_python` executes on Kit's MAIN thread — a `time.sleep`/`world.step` loop there
  blocks the run loop; measure sim-time or let physics advance across SEPARATE calls.
- **Driving a box from another machine?** The tool code + assets must live on the
  *box's* disk (imports/USD paths resolve there). Ship them over the bridge's file data
  plane instead of rsync/scp: `stat_file` (verify by sha256, skip unchanged), `put_file`
  (push; a `.py` push purges the sibling `__pycache__`), then `reload_tools` — and
  `get_file` to pull results (screenshots, exports) back. `<omni-kit-mcp>/examples/
  remote_driver.py` is the copyable ensure→reload→dispatch driver.

## References and companion skills

- `references/capture_viewport.py` — reusable headless lit-camera capture helper.
- `/isaacsim:urdf-to-usd` — import, verify, compose, and diagnose an articulation.
- `/isaacsim:assemble` — topology, collision filtering, and scene lifecycle.
- `/isaacsim:add-physics` — collider selection and contact validation.
