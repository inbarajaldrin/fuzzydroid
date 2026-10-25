---
name: robodocs
description: Fetch current robotics documentation for HuggingFace LeRobot, MuJoCo and its ecosystem, and the NVIDIA Physical-AI stack (Isaac Sim, Lab, ROS, GR00T, Cosmos, Warp, Omniverse, OpenUSD, NGC, and developer forums). Use for API questions, installation guidance, training workflows, simulation, datasets, and troubleshooting in these ecosystems.
---

# RoboDocs

Answer robotics questions from live sources. This is the single entry point for
RoboDocs in Claude Code (`/robodocs:robodocs`) and Codex (`$robodocs:robodocs`).
No local runtime or setup is needed.

Resolve symlinks on this file. The plugin root is three parent directories above
this `SKILL.md`. Resolve links below relative to this skill directory. Use the
current host's file, web, shell, and user-input tools for the equivalent tool names
in the workflows.

## Select the source workflow

Read the relevant workflow and follow it within the current task. Load additional
workflows when a question spans ecosystems; users do not need to invoke them.

| Question | Workflow |
|---|---|
| LeRobot hardware, teleoperation, calibration, datasets, policies, or training | [LeRobot](references/workflows/lerobot/workflow.md) |
| MuJoCo, MJCF, Python/C APIs, MJX, MJWarp, Menagerie, Playground, MPC, or dm_control | [MuJoCo](references/workflows/mujoco/workflow.md) |
| Isaac Sim/Lab/ROS, GR00T, Cosmos, Warp, OpenUSD, Omniverse, NGC, or NVIDIA forums | [NVIDIA](references/workflows/nvidia/workflow.md) |

Each workflow retains its own source catalog, retrieval rules, and supporting
references. Resolve its local paths from that workflow's directory. The NVIDIA
workflow routes further to product `router.md` files within its own directory.

Fetch the relevant source at execution time and cite the original page in the
answer. Check the user's installed version when it changes the answer; distinguish
official documentation, source code, and community advice. If a fetch fails,
report it and use the workflow's fallback rather than presenting memory as a live
result. Do not load unrelated catalogs or every product reference by default.

For local Fusion, KiCad, Isaac Sim, or Isaac Lab operations, use that plugin's
main skill when available. Documentation lookup alone does not require installing
an application or running its setup.
