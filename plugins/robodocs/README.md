# robodocs

Live-fetched documentation skills for the robotics stack — bundled inside the
[fuzzydroid](https://github.com/inbarajaldrin/fuzzydroid) marketplace.

## Skills

| Skill | Triggers on | Source |
|---|---|---|
| `robodocs:lerobot` | HuggingFace LeRobot — policies (ACT, SmolVLA, Pi0, Diffusion, HIL-SERL), datasets (LeRobotDataset v3), supported hardware (SO-100/101, Koch, LeKiwi, Reachy2, Unitree G1, ...) | `huggingface.co/docs/lerobot` (Pattern A — `.md` suffix) |
| `robodocs:nvidia` | NVIDIA Physical-AI suite — Isaac Sim / Lab / ROS, GR00T, Cosmos, Warp, Omniverse (Kit / Replicator / OmniGraph), OpenUSD, NVIDIA Developer Forums | Per-product live fetch (Patterns A, B, D) |

The `nvidia` skill is a meta-router over 11 product sub-skills (each its own
`router.md` + curated URL catalog) — it dispatches the user's question to the
right product surface and applies the correct retrieval rule.

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
