# isaacsim setup

Set up Isaac Sim for this machine and record the result in
`~/.config/fuzzydroid/isaacsim.toml`.

## Binding principles

- **Strict delegation.** This plugin contains NO install knowledge that a
  target repo's README or NVIDIA's docs own. You clone/invoke and follow the
  LIVE docs at execution time. If upstream docs are wrong, the fix goes
  upstream — never write compensating steps here.
- **Pre-existing installs are the norm.** Run the detection ladder BEFORE
  proposing any install. Never assume a venv name (`env_isaacsim` /
  `env_isaaclab` are NVIDIA doc examples, not facts), a Python minor version,
  or that an `activate` script exists.
- **Machine facts live in the state file**, never in plugin content. Record
  everything the recorder accepts.

## Branch: macOS — Isaac Viewer install

Isaac Sim itself does not run on macOS; the macOS role is the native WebRTC
viewer.

1. Clone the viewer repo and follow **its** README's "macOS (the viewer)"
   section exactly (build, copy to /Applications, open):

   ```bash
   git clone https://github.com/inbarajaldrin/isaac-viewer-macos.git
   ```

   **If the clone 404s** (repo not yet published), ask the operator for the
   local path to their isaac-viewer-macos checkout and clone/copy from there
   instead. Do not reconstruct the install steps from memory — read the
   README you just cloned and follow it.
2. Run the README's verify line and confirm both halves succeed.
3. **Offer the operate-from-Mac path (optional).** The Mac can also *drive* a
   remote sim, not just view it. Ask the user if they want it. If yes:
   - Obtain omni-kit-mcp's single-file, stdlib-only reference client and drop
     it somewhere stable (convention: `~/Documents/isaacsim/client.py`), plus a
     short README next to it (SSH-tunnel vs direct + the `run_python`/RCE note):

     ```bash
     mkdir -p ~/Documents/isaacsim
     git clone https://github.com/inbarajaldrin/omni-kit-mcp.git /tmp/omni-kit-mcp
     cp /tmp/omni-kit-mcp/kit_mcp/client.py ~/Documents/isaacsim/client.py
     ```

     The repo is public (https://github.com/inbarajaldrin/omni-kit-mcp). If the
     box is offline or already has a checkout, copy `kit_mcp/client.py` from
     that local checkout instead.
   - Ask which Linux sim box this Mac operates (hostname / tailnet name) and, if
     they want to pin one, its bridge port (else discovery / `--list-bridges`
     finds it). These are recorded facts — never hardcode them in content.
4. Record (drop the operate flags if the user declined step 3):

   ```bash
   CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
     uv run --python 3.11 \
       --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaacsim" \
       python -m fuzzydroid_isaacsim.setup --variant viewer \
       --viewer-app "/Applications/Isaac Viewer.app" \
       --operate-client "$HOME/Documents/isaacsim/client.py" \
       --sim-box-host <sim box hostname/tailnet name> \
       --sim-box-port <port if pinned>
   ```

Done — point the user at the skill's "Operate from another machine" section and
read [doctor](doctor.md), run the checks, and resume the original request.

## Branch: Linux — Isaac Sim install + bridge + optional ROS

### 1. Detection ladder first

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaacsim" \
    python -m fuzzydroid_isaacsim.detect --json
```

The ladder is strongest-evidence-first: running process → PATH (symlinks
resolved; shell-wrapper launchers are classified `launcher` and REFUSED as
installs) → pip venvs containing the `isaacsim` package → `~/.local/share/ov/pkg`
binaries → source checkouts. If the user mentions a venv or checkout in an
unusual place, re-run with `--scan-dir <dir>`.

**Present the full inventory to the user as a table**, including refused
launchers (so they understand why a PATH `isaacsim` was not chosen), state the
recommendation (running > newest pip > newest binary), and ask the user to
confirm the recommendation, pick another entry, or request a fresh install.

### 2. Fresh install (only if none exists or the user asks)

Delegate entirely to NVIDIA's LIVE documentation — fetch it now, follow it
exactly, never work from memory:

- pip install: https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_python.html
- binary (workstation) install: https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_workstation.html

Ask the user which variant they want before starting. After the install
completes, **re-run the detection ladder** so the new install is discovered
and classified like any other.

### 3. omni.kit.mcp bridge registration

Register the bridge permanently via omni-kit-mcp's own installer:

```bash
git clone https://github.com/inbarajaldrin/omni-kit-mcp.git
cd omni-kit-mcp && python3 scripts/install.py
```

The repo is public (https://github.com/inbarajaldrin/omni-kit-mcp); if the box
is offline or already has a checkout, use that local path instead. Follow its
README; use
`--dry-run` first if unsure, and `--config <path>` if the box has multiple Kit
app-data dirs. Note WHICH `user.config.json` it edited (it prints the path;
a box can have many app-data dirs, so this is a recorded fact, not a guess) and
which port it set (default 9009). Also note the **checkout path** — it is
recorded (`--omni-kit-mcp` in step 5) so doctor can script the bridge through
its reference client and skills can read it from the state file.

**Optional — remote access (bind host).** By default the bridge binds
`localhost`; remote callers reach it via an SSH tunnel (zero config). If the
user instead wants the bridge reachable directly on this box's tailnet/LAN IP,
run the installer with `--bind-host <ip>` and record it (`--bind-host` in step
5). Print this verbatim before offering it:

> **SECURITY:** the bridge serves `run_python` — arbitrary remote code
> execution by design. Binding beyond loopback exposes that to the whole
> network. Only bind a **trusted tailnet/LAN IP**, never `0.0.0.0` and never a
> public host. When in doubt, keep localhost and tunnel over SSH.

### 4. Optional ROS 2 branch

Ask the user whether this box should have the ROS 2 bridge persistently
enabled. If yes, the values fall in three classes:

1. **Auto-detected silently** — ROS_DISTRO (from `/opt/ros`, else the Ubuntu
   release map); library paths are always derived at runtime from recorded
   facts, never stored as literals. Don't ask about these.
2. **Ask once, with defaults, record** — present these with their defaults
   and let the user accept or override:
   - `RMW_IMPLEMENTATION` — default `rmw_cyclonedds_cpp`
   - `ROS_DOMAIN_ID` — default `0`
   - `ROS_LOCALHOST_ONLY` — default `1`
3. **Computed** — everything else. Never ask, never store.

### 4b. Optional — Python-matched ROS 2 workspace (in-cell `rclpy` + custom packages)

Only offered if step 4 enabled ROS. Ask the user whether anything on this box needs to
`import rclpy` **inside Isaac's own interpreter** — a custom message type, or a stock ROS package
Isaac does not bundle. If nothing does, skip: Isaac's internal ROS libraries are the default and
adding a workspace that is not needed is a tree to keep in step with every Isaac upgrade.

**What this is.** NVIDIA's `IsaacSim-ros_workspaces` builds a minimal ROS 2 core, in Docker,
against the Python version Isaac itself runs, plus a second workspace for your own packages. It
is neither a rebuild of Isaac nor a rebuild of the system ROS — it is a third tree, sourced
before Isaac starts. Docker is required.

1. **Read the LIVE docs now and follow them exactly** — never from memory, and never reconstruct
   the build steps here:

   - https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_ros_other_platforms.html
   - https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/tutorial_ros2_custom_message_python.html

2. **Check the Python before building, and stop if it does not match.** The docs at `/latest/`
   describe the newest Isaac; the workspaces repository is tagged **per Isaac release**
   (`IsaacSim-<version>`), and the tag is what decides the Python. Clone the tag matching the
   `--isaac-version` recorded in step 5, then read `build_ros.sh` and confirm the dockerfile it
   selects targets the same Python minor as this box's Isaac (`<isaac-python> -V`). If they
   differ, **stop and tell the user**: a workspace built for another Python fails at the first
   in-cell `import rclpy` with a missing `_rclpy_pybind11.cpython-3NN…so` — nothing is absent, the
   wrong build is being offered. Do not improvise a build for a Python the tag does not target.

3. **Add whatever the user needs, in the place the docs name**, and build with the vendor's own
   script — no vendor file is edited:

   ```bash
   # custom and non-bundled packages go in <distro>_ws/src/ ; build_ros.sh does the rest
   ./build_ros.sh -d <distro> -v <ubuntu version>
   ```

   **Build optimized — the vendor default is not.** The dockerfile passes no `CMAKE_BUILD_TYPE`,
   so the tree builds `-O0` (measured 2026-08-26 on the 5.0.0 tag: 124 of 130 packages, including
   `rclpy`, `rmw_cyclonedds_cpp` and the serialization path — +36–39% per frame and ~35% worse
   tracking until fixed). Add `-DCMAKE_BUILD_TYPE=Release` to the dockerfile's two colcon
   invocations before building, keep the pristine dockerfile beside it as `.vendor-unmodified`,
   and tell the user this is a recorded two-line deviation from the vendor tree.

   Pin any stock package the user adds to **the version this box's `/opt/ros` holds** (read it
   out of `/opt/ros/<distro>/share/<pkg>/package.xml`) — the two ends of an action have to carry
   the same definition, and "a `control_msgs`" is not the same fact as "the host's `control_msgs`".

4. **Record the facts, never the recipe.** The build's output paths and what it was built for are
   machine facts and belong in the state file:

   ```bash
   ... python -m fuzzydroid_isaacsim.setup ... \
     --ros-workspace <the build_ws/<distro> directory build_ros.sh produced> \
     --ros-workspace-isaac-version <the tag it was built from> \
     --ros-workspace-python <the Python that tag targets>
   ```

   *(These three flags do not exist in the recorder yet. Until they do, print the values and ask
   the user where they want them kept — do not write them into plugin content.)*

5. **Print to the user, verbatim rule:**

   > This workspace REPLACES Isaac's internal ROS libraries rather than joining them — NVIDIA
   > loads its own only "if no other ROS libraries are sourced". Source it (both `local_setup.bash`
   > files, minimal core first) in the shell that launches Isaac, and nowhere else. It must be
   > rebuilt from the matching tag on every Isaac upgrade that moves the Python.
   >
   > It is also not the system ROS: `/opt/ros` stays on the host side of the wire, for the real
   > robot stack, and must never reach Isaac's interpreter.

### 5. Record

One call with everything confirmed (drop the `--ros*` flags if ROS was
declined; `--isaac-python`/`--isaac-bin` only where the variant has them;
`--isaac-ctl` only if `isaac-ctl` is installed on this box):

```bash
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" \
  uv run --python 3.11 \
    --with-editable "${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_isaacsim" \
    python -m fuzzydroid_isaacsim.setup \
    --variant <pip-standalone|pip-lab|binary|source> \
    --isaac-root <venv-dir|pkg-dir|checkout> \
    --isaac-bin <launch-entry> \
    --isaac-python <venv-python> \
    --isaac-version <version> \
    --kit-config <the user.config.json from step 3> \
    --mcp-port <port from step 3> \
    --omni-kit-mcp <the omni-kit-mcp checkout from step 3> \
    --bind-host <ip if the bridge was bound beyond localhost; omit otherwise> \
    --isaac-ctl <path if present> \
    --ros --rmw <answer> --ros-domain-id <answer> --ros-localhost-only <answer>
```

The recorder validates paths, refuses wrapper scripts, performs the
persistent `isaacsim.ros2.bridge` enable (versioned ext id, backup,
idempotent), and writes the state file.

### 6. Guard notes (print to the user, verbatim rule)

Env guards are **per-profile, launcher-scoped** (isaac-ctl) — never venv
`activate` blocks, never blanket env files, never Kit config:

- full-app profile: exports the GLIBC_TUNABLES static-TLS bump + nvjitlink preload.
- Isaac Lab standalone profile: **MUST NOT export the static-TLS tunable** —
  it starves the PhysX GPU dispatcher thread's stack (pthread_create fails,
  `PxThreadImpl::start` spins forever). The nvjitlink preload is fine either way.

Finish by reading [doctor](doctor.md), running the checks, and resuming the original request.
