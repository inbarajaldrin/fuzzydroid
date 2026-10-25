# robodocs

Live-fetched documentation skills for the robotics stack — bundled inside the
[fuzzydroid](https://github.com/inbarajaldrin/fuzzydroid) marketplace.

## Main skill

| Internal workflow | Topics | Source |
|---|---|---|
| `lerobot` | HuggingFace LeRobot — policies (ACT, SmolVLA, Pi0, Diffusion, HIL-SERL), datasets (LeRobotDataset v3), supported hardware (SO-100/101, Koch, LeKiwi, Reachy2, Unitree G1, ...) | `huggingface.co/docs/lerobot` |
| `nvidia` | NVIDIA Physical-AI suite — Isaac Sim / Lab / ROS, GR00T, Cosmos, Warp, Omniverse (Kit / Replicator / OmniGraph), OpenUSD, NGC Catalog (`catalog.ngc.nvidia.com` / `nvcr.io`), NVIDIA Developer Forums | Per-product live fetch across NVIDIA + Pixar docs sites |
| `mujoco` | MuJoCo physics simulator — MJCF / mjModel / C++ + Python APIs, MJX (JAX/XLA backend), MJWarp / MuJoCo Warp (NVIDIA GPU backend), Menagerie (model zoo), Playground (RL envs), MPC (predictive control), dm_control, GitHub Discussions | `mujoco.readthedocs.io` + `github.com/google-deepmind/mujoco*` |

The NVIDIA workflow is a router over **twelve product surfaces** — Isaac Sim, Isaac Lab, Isaac ROS, Isaac GR00T, Cosmos, Warp, OpenUSD, Omniverse (Kit / Replicator / OmniGraph), NGC Catalog, and Developer Forums.

## Install

In Claude Code:

```
/plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
/plugin install robodocs@fuzzydroid
```

Once installed, the main skill can be selected automatically on relevant mentions ("LeRobot teleop",
"Isaac Lab PPO", "OpenUSD prim", "NVIDIA forums known issue", etc.) — no
explicit slash invocation required.

In Codex:

```bash
codex plugin marketplace add https://github.com/inbarajaldrin/fuzzydroid
codex plugin add robodocs@fuzzydroid
```

Start a new session and describe your question. The single entry point is
`$robodocs:robodocs` in Codex or `/robodocs:robodocs` in Claude Code. It loads
the relevant source workflows automatically; the same references serve both hosts.

## Requirements

Claude Code or Codex with web access. The skills use the host's web-fetch or shell
tools to pull live documentation — no Python deps, no API keys, no system packages.

## Why live-fetched?

LeRobot policies, the NVIDIA Isaac stack, and Omniverse Kit all evolve monthly
or faster. Cached training-data knowledge goes stale quickly. Each internal workflow teaches
the agent the right URL-rewrite rule for its source so answers come from current
documentation, not stale memory.

## Author

[Aldrin Inbaraj](https://github.com/inbarajaldrin)

## License

Apache-2.0 — see [fuzzydroid root LICENSE](../../LICENSE) and [NOTICES.md](../../NOTICES.md).
