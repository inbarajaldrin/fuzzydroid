---
name: isaaclab
description: Manage a machine's Isaac Lab (NVIDIA's RL/imitation-learning framework on Isaac Sim) footprint — detect and record the Lab install (pip venv or source, never assuming a venv name), scaffold extension projects from the pinned template, and run Lab standalone scripts with the omni.kit.mcp bridge + WebRTC livestream. Use when the user asks to set up, verify, or troubleshoot Isaac Lab, run/stream a training script, create an Isaac Lab project, or debug a Lab reset() hang or a stream that connects without frames. Triggers on "isaac lab setup", "isaaclab training", "lab standalone", "stream the training", "new isaac lab project".
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

# Isaac Lab plugin

Everything this plugin knows about a machine lives in
`~/.config/fuzzydroid/isaaclab.toml`. Read it first; never guess venv names
(`env_isaaclab` is a doc example, not a fact), Lab paths, or ports.

## Ground rules

- **Strict delegation**: installs follow the LIVE official docs
  (https://isaac-sim.github.io/IsaacLab) at execution time; project
  scaffolding follows the template repo's own README. This skill routes.
- **State file fields**: `variant` (pip/source), `lab_root`, `lab_python`,
  `lab_version`, `isaac_version`, `omni_kit_mcp` (checkout used for bridge
  launches), `mcp_port` (Lab-side OMNI_KIT_MCP_PORT, default 9010).
- Missing state file → `/isaaclab:setup`. Health → `/isaaclab:doctor`.
  New project → `/isaaclab:new-project`.

## Launching with bridge + livestream

The canonical launch shape, its placeholders, and the three traps (silent
`=`-form kit args, `publicEndpointAddress` vs the non-functional `PUBLIC_IP`
env, and the static-TLS tunable that hangs reset()) are in
**`references/bridge-launch.md`** — read it before composing ANY Lab launch
command. The one rule to never violate even in a quick one-off:

> Isaac Lab standalone runs MUST NOT export the GLIBC static-TLS tunable
> (`glibc.rtld.optional_static_tls`). It starves the PhysX GPU dispatcher
> thread's stack — `pthread_create` fails and `PxThreadImpl::start` spins
> forever. That tunable is full-app-launcher business only.

## Symptom → cause quick map

| symptom | cause |
|---|---|
| `reset()` hangs forever, CPU spinning | static-TLS tunable exported into the run (check `activate`, wrapper scripts) |
| stream "connects" but no frames | `publicEndpointAddress` kit arg missing → SDP without ICE candidates |
| bridge never binds, no error | `--enable=omni.kit.mcp` written with `=` — silently ignored; use space form |
| viewer cycles reconnect at launch | first frame of a training run can exceed the viewer's 8s acquire timeout |

## Related

- Isaac Sim install/bridge/viewer: the `isaacsim` plugin.
- Doc lookups (Isaac Lab APIs, rsl_rl/skrl/sb3 workflows): the `robodocs` plugin.\n
## API questions: installed source vs live docs

Route by question shape: API-exact (signature / cfg field / task id) -> read
the installed source; the map lives in `references/installed-source-atlas.md`
(roots derived from the state file, never hardcoded). Concepts, workflow
choices, deprecations -> live docs (`/robodocs:nvidia`). When they disagree,
the installed source wins — the runtime is the arbiter.
