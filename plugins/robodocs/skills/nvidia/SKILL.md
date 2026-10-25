---
name: nvidia
description: Fetch live NVIDIA robotics and Physical-AI documentation. Route questions about Isaac Sim, Isaac Lab, Isaac ROS, GR00T, Cosmos, Warp, Omniverse, OpenUSD, Replicator, NGC containers and NVIDIA developer forums.
---

# robodocs nvidia

Resolve symlinks on this file. The plugin root is three parent
directories above this `SKILL.md` (`<plugin>/skills/<skill>/SKILL.md`).
Use that absolute root in every command; pass it as
`CLAUDE_PLUGIN_ROOT` to child processes that use that variable.

Read `<plugin-root>/commands/nvidia.md` and follow its workflow.
Resolve its relative references from the paths it specifies.
Use the current host's shell, file, web and user-input tools for
`Bash`, `Read`, `WebFetch` and `AskUserQuestion` respectively.
In Codex, invoke sibling skills with `$plugin:skill`; slash-command
names in the workflow refer to the equivalent bundled skills.
