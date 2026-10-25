# isaacsim

NVIDIA Isaac Sim setup and health for robotics workstations, fuzzydroid-style:
thin `/isaacsim:setup` + `/isaacsim:doctor` commands delegating to a bundled
Python module, with every machine fact recorded in
`~/.config/fuzzydroid/isaacsim.toml`.

## What setup does

**Linux (the sim box):**
1. Runs the detection ladder for pre-existing installs — running process >
   PATH (symlinks resolved, shell-wrapper launchers refused) > pip venvs
   containing `isaacsim` > `~/.local/share/ov/pkg` binaries > source
   checkouts — presents the inventory, recommends, and asks you to confirm.
2. Fresh installs (only when needed) are delegated to NVIDIA's live docs; the
   plugin bakes in no install steps.
3. Registers the [omni.kit.mcp](https://github.com/inbarajaldrin/omni-kit-mcp)
   bridge permanently via that repo's own `scripts/install.py`.
4. Optionally enables the ROS 2 bridge persistently (versioned
   `isaacsim.ros2.bridge-<ver>` in the Kit app's `user.config.json`; backed
   up, idempotent) and records the ask-once ROS values
   (RMW_IMPLEMENTATION / ROS_DOMAIN_ID / ROS_LOCALHOST_ONLY).

**macOS (the viewer box):** installs the native
[Isaac Viewer](https://github.com/inbarajaldrin/isaac-viewer-macos) WebRTC
app by following that repo's README, and records it.

## Doctor

State-file-driven: components setup did not install read `N/A — not
installed`, never FAIL. Probes include a `list_tools` round-trip against the
bridge port and `isaac-ctl status` where recorded.

## Layout

```
commands/setup.md, doctor.md      thin command wrappers (the interactive flow)
skills/isaacsim/SKILL.md          agent routing + guard rules
lib/fuzzydroid_isaacsim/       bundled Python (detect / setup / ros_bridge / doctor)
```
\n\n> **Isaac Sim runs fully without MCP.** Extensions, UI, ROS, and standalone\n> Python are independent of the bridge; omni-kit-mcp is an optional layer that\n> adds agent access. Setup treats it as a distinct, skippable step.\n