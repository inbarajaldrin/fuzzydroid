# fuzzydroid-isaacsim

Bundled Python for the fuzzydroid `isaacsim` plugin. Stdlib only.

| module | role |
|---|---|
| `fuzzydroid_isaacsim.detect` | detection ladder for pre-existing Isaac Sim installs (running process > PATH with symlinks resolved and wrapper scripts refused > pip venvs > `~/.local/share/ov/pkg` binaries > source checkouts) |
| `fuzzydroid_isaacsim.setup` | non-interactive recorder: validates the confirmed install choice, optionally enables the ROS 2 bridge persistently, writes `~/.config/fuzzydroid/isaacsim.toml` |
| `fuzzydroid_isaacsim.ros_bridge` | versioned `isaacsim.ros2.bridge` enable in Kit's `user.config.json` (backup, idempotent, collapses stale variants) |
| `fuzzydroid_isaacsim.doctor` | state-file-driven health table; absent components read N/A, never FAIL |

Run via `uv run --with-editable . python -m fuzzydroid_isaacsim.<module>`;
the `/isaacsim:setup` and `/isaacsim:doctor` commands do this for you.
