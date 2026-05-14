---
name: mujoco
description: Live-fetch authoritative MuJoCo documentation, code, and community discussions across the full DeepMind ecosystem. Use when the user asks about MuJoCo, MJCF XML, mjModel/mjData, the C/C++ API, the Python bindings (mujoco), MJX (MuJoCo XLA / JAX backend), MJWarp / MuJoCo Warp (NVIDIA GPU backend), MuJoCo Menagerie (model zoo — Unitree, Franka, Shadow Hand, ANYmal, Spot, Allegro), MuJoCo Playground (RL environments, sim-to-real), MuJoCo MPC (predictive sampling, iLQG), dm_control (composer, suite, locomotion), constraint solvers, contact dynamics, soft contacts, tendons, actuators, sensors, rendering (mjvScene, mjrContext, EGL, GLFW, OSMesa), viewer (mjpython, simulate), derivatives (mjd_*), keyframes, plugins (elasticity, sensors, actuators), MuJoCo Warp/MJX install, kernel fusion, batched simulation, headless rendering, contact friction (solimp, solref, condim), GitHub Discussions (replaced mujoco.org/forum in 2022), release notes, version migration, or any MuJoCo 3.x feature.
---

# MuJoCo (live-fetch)

A live-fetch wrapper for the **MuJoCo physics simulator** ecosystem maintained by Google DeepMind. Routes the agent to authoritative, *currently-live* sources across nine surfaces — never returns stale cached content.

This skill does NOT cache MuJoCo content. It teaches you how to fetch the right page from the right source on demand.

## When to use this skill

The user is asking about:

- **MuJoCo core** — the C/C++ simulator, MJCF XML format, `mjModel` / `mjData`, computation pipeline, constraint solver, contact model
- **Python bindings** (`pip install mujoco`) — `mujoco.MjModel`, `mujoco.viewer`, GLFW/EGL rendering, the `simulate` viewer, `mjpython`
- **MJX** — the JAX/XLA reimplementation for GPU/TPU
- **MJWarp / MuJoCo Warp** — the NVIDIA Warp GPU backend (introduced as the high-perf path in MuJoCo 3.5+, broadly default-on by 3.7+)
- **Menagerie** — the curated zoo of high-quality MJCF models (Franka, Unitree Go2/G1/H1, Shadow Hand, Allegro, ANYmal, Spot, etc.)
- **MuJoCo Playground** — JAX/Warp RL environments + sim-to-real
- **MuJoCo MPC** — real-time model predictive control (predictive sampling, iLQG, gradient descent)
- **dm_control** — DeepMind Control Suite + Composer task framework
- **The community forum** — *NOTE: the old `mujoco.org/forum` was retired in 2022.* Modern discussion is on GitHub Discussions across the main repo and per-sub-project repos. See `references/forums.md`.

## How to use it

Always check `references/live-sources.md` first — it's the URL catalog mapping topic → canonical URL → extraction prompt for the agent.

1. **Identify the surface** — Is this a core-simulator question? MJX? Menagerie? A forum-style how-do-I question? Match the user's intent to the surface in `references/live-sources.md`.
2. **Pick the canonical URL** — Each row in the catalog has one. For deep topics, the catalog points at a hub page; navigate from there.
3. **Apply the retrieval rule** — Read `references/retrieval-rule.md` and follow it exactly. Different surfaces use different fetch mechanisms:
   - ReadTheDocs HTML pages → `WebFetch` with a browser User-Agent
   - GitHub repo files (`README.md`, source) → `gh api` or `raw.githubusercontent.com`
   - GitHub Discussions (forum posts, help threads) → `gh api repos/<org>/<repo>/discussions/<num>` or fetch the discussion URL with `WebFetch`
   - Raw `.rst` sources → `raw.githubusercontent.com/google-deepmind/mujoco/main/doc/<page>.rst` (cleaner than the rendered HTML for some queries)
4. **Cite the URL** — Always include the source URL when relaying content to the user.

## Forum / community queries — IMPORTANT

If the user is searching for an **answer to a question someone else has likely already asked** (sim instability, contact tuning, install errors, ROS integration, sim-to-real tips, performance tuning, MJX/Warp gotchas), the modern community surface is:

- `https://github.com/google-deepmind/mujoco/discussions` — main forum (Announcements / Asking for Help / General / Ideas / Polls / Show and tell)
- `https://github.com/google-deepmind/mujoco_playground/discussions` — Playground-specific
- `https://github.com/google-deepmind/mujoco_warp/discussions` — Warp-specific
- `https://github.com/google-deepmind/dm_control/discussions`
- `https://github.com/google-deepmind/mujoco_menagerie/discussions`

Use `gh search discussions --repo google-deepmind/<repo> "<keywords>"` to find threads, then `gh api repos/google-deepmind/<repo>/discussions/<number>` for the full content. **Note there is no "Q&A" category** on the main repo — "Asking for Help" is the help-question equivalent. Details in `references/forums.md`.

**Do not direct users to `mujoco.org/forum`** — it was deleted years ago and the URL no longer resolves to a community.

## Versioning

MuJoCo ReadTheDocs serves both `/en/stable/` (most recent release, default) and `/en/latest/` (development HEAD). Use `stable` unless the user specifically asks about an unreleased feature or main-branch code.

To pin a specific version: `https://mujoco.readthedocs.io/en/3.5.0/<page>.html`. The sitemap at `https://mujoco.readthedocs.io/sitemap.xml` enumerates all versioned roots. Current PyPI release as of 2026-05-13 is `mujoco==3.8.1`.

## Sibling skills inside robodocs

This skill is bundled in the **robodocs** plugin alongside:

- **`lerobot`** — HuggingFace LeRobot. When the user asks about MuJoCo Playground datasets, sim-to-real rollouts on real hardware, or LeRobotDataset format used by humanoid policies, cross-ref `lerobot`.
- **`nvidia`** (meta-router with twelve sub-skills) — when the user asks about MJWarp / MuJoCo Warp internals (the GPU backend uses NVIDIA Warp under the hood), cross-ref the `nvidia` skill's `nvidia-warp` sub-skill for the underlying `@wp.kernel` / GPU-Python framework. For NGC-hosted MuJoCo containers (if NVIDIA publishes any), the `nvidia-ngc` sub-skill is the right path.

## Reference files

- `references/live-sources.md` — the master URL catalog (topic | URL | extraction prompt) across all 9 surfaces
- `references/retrieval-rule.md` — the fetch mechanism (per-surface) and known gotchas
- `references/forums.md` — how to search and quote GitHub Discussions for community Q&A
- `references/menagerie.md` — model-by-model URL list for the Menagerie zoo
- `evals/evals.json` — portable verification tests

## What this skill does NOT do

- It does not enumerate every C function in the MuJoCo API — `XMLreference.html` and `APIreference.html` are huge; the catalog points at them and the agent drills in via in-page anchors.
- It does not mirror Menagerie model XML — file paths in `references/menagerie.md` resolve via `raw.githubusercontent.com`.
- It does not replace running MuJoCo locally — for actual simulation, the user runs `pip install mujoco` and code goes through the Python bindings or C API.
