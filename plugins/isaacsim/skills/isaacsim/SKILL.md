---
name: isaacsim
description: Control NVIDIA Isaac Sim and manage its local or remote runtime. Use for setup and diagnostics, URDF-to-USD import, articulation assembly, collision authoring, physics validation, USD animation and recording, extension controls, WebRTC streaming, MCP, and the ROS 2 bridge. Detect existing installs and configure a macOS viewer when needed; load the relevant internal workflows automatically.
---

## Agent host compatibility

This skill works in Claude Code and Codex. Resolve symlinks on this file; the
plugin root is three parent directories above this `SKILL.md`. Use that absolute
root for plugin assets regardless of the working directory, and pass it as
`CLAUDE_PLUGIN_ROOT` to commands that use that variable. Use the current host's
equivalent shell, file, web, and user-input tools. Resolve links below from this
skill directory. Within an internal workflow, resolve its `references/`,
`scripts/`, and `evals/` from that workflow's directory; explicit
`skills/<plugin>/...` paths start at the plugin root.

# Isaac Sim plugin

Everything this plugin knows about a machine lives in
`~/.config/fuzzydroid/isaacsim.toml` — the state file `references/workflows/setup.md`
writes. Read it first; never guess venv names, install paths, or ports.

## Route internally

The public entry point is `/isaacsim:isaacsim` in Claude Code or
`$isaacsim:isaacsim` in Codex. Users can describe their goal in normal language.
Read the relevant workflow yourself and continue through verification. Combine
workflows when needed, retaining the same project, runtime, and output paths.
When setup is missing or a connection fails, follow setup or doctor within
the task and resume once the prerequisites hold. Ask for missing project facts
or required manual application steps.

| Goal | Internal workflow |
|---|---|
| Detect installs, record one, configure a bridge or macOS viewer | [setup](references/workflows/setup.md) |
| Check installation, bridge, ROS, or streaming health | [doctor](references/workflows/doctor.md) |
| Import a URDF and verify its drives | [urdf-to-usd/workflow](references/workflows/urdf-to-usd/workflow.md) |
| Compose articulations, collision filtering, and simulation lifecycle | [assemble/workflow](references/workflows/assemble/workflow.md) |
| Choose and validate colliders | [add-physics/workflow](references/workflows/add-physics/workflow.md) |
| Author USD motion, preview, or record an animation | [animation/workflow](references/workflows/animation/workflow.md) |
| Build project controls or an Isaac Sim extension | [create-extension/workflow](references/workflows/create-extension/workflow.md) |

## Ground rules

- **Strict delegation**: installs follow LIVE upstream docs (NVIDIA's Isaac
  Sim docs, the isaac-viewer-macos README, the omni-kit-mcp README) at
  execution time. This skill routes; it does not duplicate install steps.
- **State file is the source of truth** for: install `variant`
  (pip-standalone / pip-lab / binary / source / viewer), `isaac_root`,
  `isaac_bin`, `isaac_python`, `isaac_version`, `kit_config` (which
  user.config.json was edited), `mcp_port`, `omni_kit_mcp` (checkout used to
  script the bridge), `bind_host` (bridge bind address — localhost unless
  opened for remote access), ROS values (`ros_distro`,
  `rmw_implementation`, `ros_domain_id`, `ros_localhost_only`,
  `ros_bridge_ext`), `isaac_ctl`, `viewer_app`, and — on a Mac that drives a
  remote sim — `operate_client` (local `client.py` path), `sim_box_host`,
  `sim_box_port`.
- If the state file is missing, follow `references/workflows/setup.md`.
- Health questions → `references/workflows/doctor.md` (state-driven; N/A rows are normal).

## API questions: installed source vs live docs

The installed Isaac tree is a self-describing platform — 500+ extensions, each
shipping its own docs and source. Route by question shape:

| Question shape | Route |
|---|---|
| Exact signature / widget / kwarg / setting key / OGN node | **installed source** — read `references/installed-source-atlas.md` for the map (roots derived from the state file, never hardcoded) |
| Concept, tutorial, \"how should I\", deprecation | **live docs** (`/robodocs:robodocs (nvidia workflow)`) |
| They disagree | installed source wins — the runtime is the arbiter |

## Talking to a running sim

The omni.kit.mcp bridge is an NDJSON-over-TCP server. Script it with
omni-kit-mcp's stdlib-only **reference client** — `omni_kit_mcp` (the checkout)
comes from the state file, never hardcode it. A lone running bridge is
auto-discovered from its runtime portfile, so you usually pass **no port**:

```bash
# omni_kit_mcp from ~/.config/fuzzydroid/isaacsim.toml
PYTHONPATH=<omni_kit_mcp> python3 -m kit_mcp.client list_tools
PYTHONPATH=<omni_kit_mcp> python3 -m kit_mcp.client run_python '{"code":"result = 1"}'
# several Kit processes up (e.g. the app on 9009 + a Lab run on 9010)? list, then pin:
PYTHONPATH=<omni_kit_mcp> python3 -m kit_mcp.client --list-bridges
PYTHONPATH=<omni_kit_mcp> python3 -m kit_mcp.client list_tools --port <mcp_port>
# exit codes: 0 success · 1 bridge answered an error · 2 unreachable/ambiguous
```

`import kit_mcp.client` is stdlib-only (no `mcp` SDK needed). Discovery reads
`$XDG_RUNTIME_DIR/omni-kit-mcp/`; pass `--port <mcp_port>` (recorded) to pin a
specific process when discovery is ambiguous. `run_python` executes Python on
Kit's main thread. For the full protocol, the `BridgeClient` persistent-
connection API, and the `kit-mcp` MCP front-end, read the omni-kit-mcp repo's
README ("Scripting the bridge").

If `omni_kit_mcp` is not in the state file, re-run `references/workflows/setup.md` with
`--omni-kit-mcp <checkout>` to record it.

## Operate from another machine (e.g. the macOS viewer box)

The Mac's role isn't only *viewing* the WebRTC stream — it can *drive* the sim
too. The reference client is a single stdlib-only file, so operating a remote
sim needs nothing on the Mac beyond a copy of it. `references/workflows/setup.md` (macOS
branch) offers to drop `client.py` + a short README into `~/Documents/isaacsim`
and records `operate_client` + `sim_box_host` (+ optional `sim_box_port`) in
the state file; read them there, never hardcode a box or IP.

Reach the sim box two ways (its bridge binds `localhost` unless `bind_host`
opened it):

```bash
# A) SSH tunnel — zero config on the box; forward a local port to the bridge
ssh -f -N -L 19009:127.0.0.1:<box_bridge_port> <user>@<box>
python3 <operate_client> list_tools --host 127.0.0.1 --port 19009

# B) Direct — only if the box ran omni-kit-mcp install.py --bind-host <tailnet-ip>
python3 <operate_client> --list-bridges --host <box_ip> --port <box_bridge_port>   # what's running there
python3 <operate_client> run_python '{"code":"result = 1"}' --host <box_ip> --port <box_bridge_port>
```

`<box>` / `<box_ip>` / `<box_bridge_port>` come from `sim_box_host` (+
`sim_box_port` if pinned) in the state file. A remote caller can't read the
box's portfiles, so `--list-bridges` — asked of any reachable bridge (typically
the installed app's stable port) — is how you enumerate every bridge on that
box, including ephemeral-port Lab runs. **Security:** the bridge serves
`run_python` (remote code execution) — expose it beyond loopback (option B)
only on a trusted tailnet/LAN, never `0.0.0.0` on a public host; the SSH tunnel
(option A) needs no such exposure.

## Launch guard rule (do not violate)

Env guards (GLIBC_TUNABLES static-TLS bump, nvjitlink LD_PRELOAD) are
**per-profile and launcher-scoped** (isaac-ctl):

- full-app Isaac Sim profile: tunable + preload — both fine.
- Isaac Lab standalone runs: **never export the static-TLS tunable** — glibc
  carves static TLS out of each new thread's stack, the PhysX GPU dispatcher's
  pthread_create fails, and `PxThreadImpl::start` spins forever (the classic
  "reset() hang"). Preload at most.
- Guards never go in venv `activate`, blanket env files, or Kit config
  (ld.so consumes them before the process exists).

## Related

- Isaac Lab (RL/IL on top of Isaac Sim): the separate `isaaclab` plugin.
- Doc lookups across the NVIDIA stack: the `robodocs` plugin.

## Assembly and validation

Use `references/workflows/assemble/workflow.md` for articulation topology, scene lifecycle, collision
filtering, gravity validation, and mimic verification. Keep robot-specific
bring-up scripts, recordings, and investigation logs in the user's project.
