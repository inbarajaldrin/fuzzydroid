# isaaclab

Isaac Lab setup, health, project scaffolding, and bridge launches from Claude
Code or Codex. Machine facts are recorded in `~/.config/fuzzydroid/isaaclab.toml`.

## Main skill

Describe your task, or use `/isaaclab:isaaclab` in Claude Code or
`$isaaclab:isaaclab` in Codex. The agent selects the internal workflow:

| Workflow | Purpose |
|---|---|
| Setup | Follow live official installation docs, detect existing pip/source installs, and record the selected install and bridge checkout. |
| New project | Scaffold from the pinned IsaacLabExtensionTemplate and fetch the bridge launch example from its source. |
| Doctor | Check recorded installation health and detect launch guard violations. |

## The launch shape and the guard rule

The canonical bridge+livestream launch (space-form kit args, explicit
`publicEndpointAddress`, no static-TLS tunable) is documented in
[`skills/isaaclab/references/bridge-launch.md`](skills/isaaclab/references/bridge-launch.md)
— including the three traps it avoids, each of which produced a
connected-but-broken state with no error message.

## Layout

```text
skills/isaaclab/SKILL.md                       main skill and symptom map
skills/isaaclab/references/workflows/          setup, doctor, and new-project workflows
skills/isaaclab/references/bridge-launch.md    canonical launch shape and traps
lib/fuzzydroid_isaaclab/                       bundled Python runtime
```
