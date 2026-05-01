# Isaac Lab Docs

Reliable live access to NVIDIA Isaac Lab documentation at `https://isaac-sim.github.io/IsaacLab/main/`.

## When to use this sub-skill

Trigger on: NVIDIA Isaac Lab (the robot-learning framework on Isaac Sim), RL / IL training for robots, `isaaclab.*` Python modules (`isaaclab.envs`, `isaaclab.assets`, `isaaclab.managers`, `isaaclab.sensors`, `isaaclab.actuators`, `isaaclab.terrains`, `isaaclab.sim`, `isaaclab.scene`, `isaaclab.controllers`), Manager-Based vs Direct workflow, Hydra configs for Lab, parallel-env training, the four RL library integrations (rsl_rl, rl_games, skrl, stable-baselines3), Isaac Lab Mimic (imitation learning / teleop data generation), CloudXR teleoperation, multi-GPU training in Lab, Population Based Training, Ray integration, domain randomization in Lab, Isaac Lab Newton integration (experimental), or the `./isaaclab.sh` CLI wrapper. Also triggers on adjacent use: Isaac GR00T humanoid training (built on Isaac Lab), LeRobot EnvHub IsaacLab Arena integration, sim-to-real reward-shaping with Warp kernels, and "train a PPO policy on a custom robot".

## Why this skill exists

Isaac Lab is the learning framework on Isaac Sim — PPO/SAC/rl_games/skrl/sb3 integrations, Manager-Based vs Direct workflows, Hydra configs, parallel GPU envs, imitation learning (Mimic + SkillGen), and the CloudXR teleop stack. It's also the foundation under Isaac GR00T. APIs and workflow patterns churn release-to-release. Training decisions demand live docs.

## The retrieval rule

Pattern D — **plain HTML, WebFetch the URL directly.** `isaac-sim.github.io/IsaacLab/main/*.html` is Sphinx-rendered with full body content on every page.

| HTML URL | Fetch URL |
|---|---|
| `https://isaac-sim.github.io/IsaacLab/main/index.html` | same |
| `https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html` | same |
| `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.envs.html` | same |

## HTML exceptions

- **`.md` suffix returns 404** on all pages tested.
- **`_sources/*.rst.txt` returns 404** — not exposed.
- **Versioning** — docs live under `/main/` (tip of main branch). Tagged versions aren't consistently published on GitHub Pages; check the GitHub repo `docs/` folder if the user needs a pinned release.

## Workflow

1. Classify — installation / setup, workflow choice (Manager-Based vs Direct), RL lib (rsl_rl / rl_games / skrl / sb3), task / env authoring, sensor / actuator config, multi-GPU or cluster training, imitation-learning (Mimic), teleop (CloudXR / Haply), or Newton experimental integration.
2. Look up in `shared/live-sources.md`. For specific `isaaclab.*` APIs, go to `source/api/lab/isaaclab.<module>.html`.
3. `WebFetch` the HTML URL directly.
4. If the user asks about simulator basics (SimulationApp, URDF import) — route to `isaac-sim`.
5. If the user asks about custom Warp kernels — route to `nvidia-warp`.
6. If the user asks about humanoid foundation models — route to `isaac-groot`.
7. Cite the HTML URL.

## Reference files

- `shared/live-sources.md` — curated entry points across Setup · Tutorials · Workflows (Manager / Direct) · RL Libraries · Mimic & Imitation · Features (Hydra / multi-GPU / PBT / Ray) · How-To · Deployment · API Reference · Newton (experimental).
- `shared/retrieval-rule.md` — Pattern D rule, verification, versioning.

## Common pitfalls

- **Manager-Based vs Direct workflow is the top architectural decision.** Manager-Based uses `ManagerTermCfg` for observations/rewards/events (high-level, reusable). Direct lets you write the full env class. Pull the workflow pages before answering — users often pick the wrong one.
- **Hydra configs are load-bearing.** Isaac Lab uses Hydra + dataclasses. When answering "how do I override X", check `source/features/hydra.html`.
- **RL library choice matters.** rsl_rl is the NVIDIA-canonical fast trainer; rl_games is the legacy/performance benchmark; skrl is library-agnostic; sb3 is for baselines. Pick the one the user already uses.
- **`./isaaclab.sh` wraps `python`** inside the right Isaac Sim environment. Don't recommend bare `python` — the Isaac-Sim-bundled Python is what the Lab scripts expect.
- **Multi-GPU via torchrun.** Lab uses torchrun (previously `accelerate`). Check current guidance in `source/features/multi_gpu.html`.
- **Newton integration is experimental.** Under `source/experimental-features/newton-physics-integration/`. When the user asks about Newton in Lab, flag experimental status.
- **Warp reward kernels aren't documented in one place.** The Lab pattern is: observation / reward functions may be implemented as Warp kernels for speed. Point users at Warp docs when they need kernel authoring.
