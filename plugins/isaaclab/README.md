# isaaclab

Isaac Lab setup, health, and project scaffolding, fuzzydroid-style: thin
commands delegating to a bundled Python module, with every machine fact
recorded in `~/.config/fuzzydroid/isaaclab.toml`.

## Commands

| command | what it does |
|---|---|
| `/isaaclab:setup` | delegates the install to the [official live docs](https://isaac-sim.github.io/IsaacLab), detects existing installs (pip venv or source checkout — never assuming `env_isaaclab`), records the confirmed choice + the omni-kit-mcp checkout |
| `/isaaclab:new-project` | clones [isaac-sim/IsaacLabExtensionTemplate](https://github.com/isaac-sim/IsaacLabExtensionTemplate) at a pinned commit (upstream has no tags), follows the template's own README, and drops in omni-kit-mcp's `examples/isaaclab_bridge_launch.py` fetched from its repo at invocation time |
| `/isaaclab:doctor` | state-file-driven health table; absent components read N/A, never FAIL; actively FAILs the static-TLS guard-rule violation |

## The launch shape and the guard rule

The canonical bridge+livestream launch (space-form kit args, explicit
`publicEndpointAddress`, no static-TLS tunable) is documented in
[`skills/isaaclab/references/bridge-launch.md`](skills/isaaclab/references/bridge-launch.md)
— including the three traps it avoids, each of which produced a
connected-but-broken state with no error message.

## Layout

```
commands/setup.md, doctor.md, new-project.md   thin command wrappers
skills/isaaclab/SKILL.md                       agent routing + symptom map
skills/isaaclab/references/bridge-launch.md    canonical launch shape + traps
lib/fuzzydroid_isaaclab/                    bundled Python (detect / setup / doctor)
```
