---
name: setup
description: Run the isaacsim setup workflow. Use when the user asks for isaacsim setup.
---

# isaacsim setup

Resolve symlinks on this file. The plugin root is three parent
directories above this `SKILL.md` (`<plugin>/skills/<skill>/SKILL.md`).
Use that absolute root in every command; pass it as
`CLAUDE_PLUGIN_ROOT` to child processes that use that variable.

Read `<plugin-root>/commands/setup.md` and follow its workflow.
Resolve its relative references from the paths it specifies.
Use the current host's shell, file, web and user-input tools for
`Bash`, `Read`, `WebFetch` and `AskUserQuestion` respectively.
In Codex, invoke sibling skills with `$plugin:skill`; slash-command
names in the workflow refer to the equivalent bundled skills.
