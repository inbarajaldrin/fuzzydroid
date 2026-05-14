# robodocs

Live-fetched documentation skills for the robotics stack — bundled inside the
[fuzzydroid](https://github.com/inbarajaldrin/fuzzydroid) marketplace.

## Skills

| Skill | Triggers on | Source |
|---|---|---|
| `robodocs:lerobot` | HuggingFace LeRobot — policies (ACT, SmolVLA, Pi0, Diffusion, HIL-SERL), datasets (LeRobotDataset v3), supported hardware (SO-100/101, Koch, LeKiwi, Reachy2, Unitree G1, ...) | `huggingface.co/docs/lerobot` |
| `robodocs:nvidia` | NVIDIA Physical-AI suite — Isaac Sim / Lab / ROS, GR00T, Cosmos, Warp, Omniverse (Kit / Replicator / OmniGraph), OpenUSD, NGC Catalog (`catalog.ngc.nvidia.com` / `nvcr.io`), NVIDIA Developer Forums | Per-product live fetch across NVIDIA + Pixar docs sites |
| `robodocs:mujoco` | MuJoCo physics simulator — MJCF / mjModel / C++ + Python APIs, MJX (JAX/XLA backend), MJWarp / MuJoCo Warp (NVIDIA GPU backend), Menagerie (model zoo), Playground (RL envs), MPC (predictive control), dm_control, GitHub Discussions | `mujoco.readthedocs.io` + `github.com/google-deepmind/mujoco*` |

The `nvidia` skill is a meta-router over **twelve product surfaces** — Isaac Sim, Isaac Lab, Isaac ROS, Isaac GR00T, Cosmos, Warp, OpenUSD, Omniverse (Kit / Replicator / OmniGraph), NGC Catalog, and Developer Forums.

## Install

In Claude Code:

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
/plugin install robodocs@fuzzydroid
```

Once installed, the skills auto-trigger on relevant mentions ("LeRobot teleop",
"Isaac Lab PPO", "OpenUSD prim", "NVIDIA forums known issue", etc.) — no
explicit slash invocation required.

## Requirements

None beyond Claude Code itself. The skills use Claude Code's built-in `WebFetch`
tool to pull live documentation — no Python deps, no API keys, no system packages.

## Why live-fetched?

LeRobot policies, the NVIDIA Isaac stack, and Omniverse Kit all evolve monthly
or faster. Cached training-data knowledge goes stale quickly. Each skill teaches
the agent the right URL-rewrite rule for its source so answers come from current
documentation, not stale memory.

## Author

[Aldrin Inbaraj](https://github.com/inbarajaldrin)

## License

Apache-2.0 — see [fuzzydroid root LICENSE](../../LICENSE) and [NOTICES.md](../../NOTICES.md).
