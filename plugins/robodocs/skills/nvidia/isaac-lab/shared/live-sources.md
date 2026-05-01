# Isaac Lab Docs — Live Sources

Curated entry points into NVIDIA Isaac Lab documentation at `https://isaac-sim.github.io/IsaacLab/main/`. Every URL is plain HTML — `WebFetch` directly per `retrieval-rule.md`.

Verified 2026-04-23 against `/main/`.

---

## Getting Started

| Topic | URL | Extraction Prompt |
|---|---|---|
| Welcome / landing | `https://isaac-sim.github.io/IsaacLab/main/index.html` | "Extract the top-level TOC and section overview (Setup, Tutorials, Workflows, RL, Mimic, Features, How-To, Deployment, API, Experimental, Refs)." |
| Installation index | `https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html` | "Extract the four install modes (pip+Sim-pip, pip+Sim-binary, source-build both, pip-only external) and system requirements." |
| Installation — pip (recommended) | `https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/pip_installation.html` | "Extract the pip-install flow — install Isaac Sim pip, clone IsaacLab, `./isaaclab.sh --install`, verify." |
| Installation — binary | `https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/binaries_installation.html` | "Extract the Isaac-Sim-binary + Lab-from-source flow." |
| Installation — source | `https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/source_installation.html` | "Extract the full source-build instructions for both Isaac Sim and Isaac Lab." |
| Developer setup | `https://isaac-sim.github.io/IsaacLab/main/source/setup/developer.html` | "Extract the developer workflow — pre-commit, docs build, testing." |

## Tutorials (core onboarding)

| Topic | URL | Extraction Prompt |
|---|---|---|
| Tutorials index | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/index.html` | "List the tutorial progression (Core, Environment, RL training) with prerequisites." |
| Create an empty scene | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/00_sim/create_empty.html` | "Extract the minimal Isaac Lab script — SimulationApp, stage, step loop." |
| Spawn prims | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/00_sim/spawn_prims.html` | "Extract `isaaclab.sim.spawners` — how to spawn rigid bodies, meshes, lights." |
| Add an articulation | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/01_assets/run_articulation.html` | "Extract how to load an articulated robot and step it." |
| Interacting with a rigid body | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/01_assets/run_rigid_object.html` | "Extract rigid-body manipulation from Python." |
| Create a scene with multiple robots | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/02_scene/create_scene.html` | "Extract the `InteractiveScene` class and multi-robot spawning." |
| Register an environment (Manager-Based) | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/create_manager_base_env.html` | "Extract the Manager-Based env authoring — `ManagerBasedEnvCfg`, observation / action / event / reward managers." |
| Register an environment (Direct) | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/create_direct_rl_env.html` | "Extract the Direct env authoring — custom env class inheriting `DirectRLEnv`, `_get_observations`, `_get_rewards`, `_reset_idx`." |
| Training an RL agent | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/run_rl_training.html` | "Extract the `./isaaclab.sh -p scripts/reinforcement_learning/<lib>/train.py` invocation and common flags." |

## Workflows — Manager-Based vs Direct

| Topic | URL | Extraction Prompt |
|---|---|---|
| Overview | `https://isaac-sim.github.io/IsaacLab/main/source/overview/core-concepts/task-workflows.html` | "Extract Manager-Based vs Direct trade-offs — composability, ease of use, performance, when to pick each." |
| Manager-Based envs (ManagerTermCfg patterns) | `https://isaac-sim.github.io/IsaacLab/main/source/overview/core-concepts/managers.html` | "Extract the Manager system — ObservationTermCfg, RewardTermCfg, EventTermCfg, ActionTermCfg, CurriculumTermCfg." |

## RL Libraries (integrations)

| Topic | URL | Extraction Prompt |
|---|---|---|
| RL overview (library comparison) | `https://isaac-sim.github.io/IsaacLab/main/source/overview/reinforcement-learning/index.html` | "Extract the four RL-library integrations (rsl_rl, rl_games, skrl, sb3) — strengths, supported algorithms, typical use cases." |
| rsl_rl | `https://isaac-sim.github.io/IsaacLab/main/source/overview/reinforcement-learning/rl_existing_scripts.html` | "Extract the rsl_rl train/play commands and config layout." |
| Wrapped RL envs | `https://isaac-sim.github.io/IsaacLab/main/source/overview/reinforcement-learning/wrapping_envs.html` | "Extract how Isaac Lab envs are wrapped to conform to each RL library's API." |
| Performance benchmark | `https://isaac-sim.github.io/IsaacLab/main/source/overview/reinforcement-learning/performance_benchmarks.html` | "Extract FPS numbers across envs, GPUs, and library choices." |

## Imitation Learning — Isaac Lab Mimic

| Topic | URL | Extraction Prompt |
|---|---|---|
| Mimic overview | `https://isaac-sim.github.io/IsaacLab/main/source/overview/imitation-learning/index.html` | "Extract what Mimic is, the teleop → data-augmentation → demo-generation pipeline, and how it relates to SkillGen." |
| Teleoperation + Mimic data collection | `https://isaac-sim.github.io/IsaacLab/main/source/tutorials/04_teleoperation/teleop_and_imitation.html` | "Extract the teleop recording flow + SkillGen automated demo generation." |

## Features

| Topic | URL | Extraction Prompt |
|---|---|---|
| Hydra configs | `https://isaac-sim.github.io/IsaacLab/main/source/features/hydra.html` | "Extract Hydra overrides for Isaac Lab — CLI syntax, config composition, how envs and agents compose." |
| Multi-GPU | `https://isaac-sim.github.io/IsaacLab/main/source/features/multi_gpu.html` | "Extract torchrun launch for multi-GPU training in Isaac Lab and sharding strategy." |
| Population Based Training | `https://isaac-sim.github.io/IsaacLab/main/source/features/population_based_training.html` | "Extract PBT setup and the config for hyperparam search." |
| Ray integration | `https://isaac-sim.github.io/IsaacLab/main/source/features/ray.html` | "Extract Ray-cluster usage for distributed training." |
| Reproducibility | `https://isaac-sim.github.io/IsaacLab/main/source/features/reproducibility.html` | "Extract the seeding + deterministic-mode guidance." |

## How-To (recipes)

| Topic | URL | Extraction Prompt |
|---|---|---|
| Configure rendering | `https://isaac-sim.github.io/IsaacLab/main/source/how-to/configure_rendering.html` | "Extract rendering config — RTX real-time vs path-traced, sensor perf trade-offs." |
| Estimate camera count | `https://isaac-sim.github.io/IsaacLab/main/source/how-to/estimate_how_many_cameras_can_run.html` | "Extract the rule-of-thumb for how many sim cameras fit on one GPU." |
| Curriculums | `https://isaac-sim.github.io/IsaacLab/main/source/how-to/curriculums.html` | "Extract the CurriculumManager usage — how to ramp difficulty across training." |
| Draw markers (debug vis) | `https://isaac-sim.github.io/IsaacLab/main/source/how-to/draw_markers.html` | "Extract `VisualizationMarkers` usage — arrows, spheres, goal markers." |
| CloudXR teleoperation | `https://isaac-sim.github.io/IsaacLab/main/source/how-to/cloudxr_teleoperation.html` | "Extract CloudXR teleop setup for Apple Vision Pro / Quest." |
| Haply teleoperation | `https://isaac-sim.github.io/IsaacLab/main/source/how-to/haply_teleoperation.html` | "Extract Haply haptic-device teleop integration." |
| Add own library / extension | `https://isaac-sim.github.io/IsaacLab/main/source/how-to/add_own_library.html` | "Extract how to structure an external Lab extension." |

## Deployment

| Topic | URL | Extraction Prompt |
|---|---|---|
| Deployment index | `https://isaac-sim.github.io/IsaacLab/main/source/deployment/index.html` | "Extract the deployment options — Docker, HPC clusters, cloud." |
| Docker | `https://isaac-sim.github.io/IsaacLab/main/source/deployment/docker.html` | "Extract the Lab Docker image build and run." |
| HPC cluster | `https://isaac-sim.github.io/IsaacLab/main/source/deployment/cluster.html` | "Extract SLURM / PBS launch scripts for cluster training." |
| CloudXR teleop cluster | `https://isaac-sim.github.io/IsaacLab/main/source/deployment/cloudxr_teleoperation_cluster.html` | "Extract the CloudXR cluster deployment for multi-user teleop." |

## API Reference — `isaaclab.*`

| Topic | URL | Extraction Prompt |
|---|---|---|
| API index | `https://isaac-sim.github.io/IsaacLab/main/source/api/index.html` | "Extract the top-level `isaaclab.*` module list with one-line purpose each." |
| `isaaclab.app` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.app.html` | "Extract `AppLauncher` — the Lab equivalent of SimulationApp boilerplate." |
| `isaaclab.envs` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.envs.html` | "Extract env base classes — ManagerBasedEnv, ManagerBasedRLEnv, DirectRLEnv, DirectMARLEnv." |
| `isaaclab.envs.mdp` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.envs.mdp.html` | "Extract MDP term library — observations, rewards, events, terminations that ship built-in." |
| `isaaclab.managers` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.managers.html` | "Extract the Manager classes and term configs." |
| `isaaclab.scene` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.scene.html` | "Extract InteractiveScene + scene config patterns." |
| `isaaclab.assets` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.assets.html` | "Extract Articulation, RigidObject, DeformableObject asset classes." |
| `isaaclab.sensors` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sensors.html` | "Extract Sensor base + TiledCamera, RayCaster, ContactSensor, FrameTransformer." |
| `isaaclab.actuators` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.actuators.html` | "Extract ImplicitActuator / IdealPDActuator / DCMotor / ActuatorNetLSTM configs." |
| `isaaclab.controllers` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.controllers.html` | "Extract differential IK controller, joint-position controller, and operational-space controller." |
| `isaaclab.devices` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.devices.html` | "Extract teleop devices — SpaceMouse, gamepad, keyboard." |
| `isaaclab.markers` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.markers.html` | "Extract VisualizationMarkers for debug arrows / spheres / frames." |
| `isaaclab.terrains` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.terrains.html` | "Extract procedural terrain generation — sub-terrain configs (slope, stairs, rough, pyramid, plane)." |
| `isaaclab.sim` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sim.html` | "Extract `SimulationContext` and low-level sim config." |
| `isaaclab.sim.spawners` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sim.spawners.html` | "Extract the spawner catalog — UsdFileCfg, MeshCfg, light spawners, rigid / deformable spawners." |
| `isaaclab.sim.schemas` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sim.schemas.html` | "Extract USD schema wrappers." |
| `isaaclab.sim.converters` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sim.converters.html` | "Extract URDF / MJCF / Mesh converters." |
| `isaaclab.utils` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.utils.html` | "Extract math utilities, timer, dict tools." |
| `isaaclab_rl` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab_rl/isaaclab_rl.html` | "Extract the RL-library wrappers surface." |
| `isaaclab_mimic` (envs) | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab_mimic/isaaclab_mimic.envs.html` | "Extract Mimic env base classes." |
| `isaaclab_mimic` (datagen) | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab_mimic/isaaclab_mimic.datagen.html` | "Extract the Mimic data-generation pipeline (DataGenerator, source demo selection, augmentation)." |
| `isaaclab_tasks.utils` | `https://isaac-sim.github.io/IsaacLab/main/source/api/lab_tasks/isaaclab_tasks.utils.html` | "Extract task registry, env-id lookup, and hydra helpers." |

## Experimental — Newton Physics

| Topic | URL | Extraction Prompt |
|---|---|---|
| Newton integration index | `https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/index.html` | "Extract what Newton-in-Lab is, current status, and scope." |
| Installation | `https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/installation.html` | "Extract Newton-in-Lab install steps." |
| Training environments | `https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/training-environments.html` | "Extract which envs currently support Newton backend." |
| Sim-to-sim (PhysX→Newton) | `https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/sim-to-sim.html` | "Extract sim-to-sim behavior comparison between PhysX and Newton." |
| Sim-to-real | `https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/sim-to-real.html` | "Extract Newton sim-to-real results." |
| Solver transitioning | `https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/solver-transitioning.html` | "Extract how to switch solver backend mid-project." |
| Limitations | `https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/limitations-and-known-bugs.html` | "Extract known limitations of the Newton integration." |

---

## Notes on extraction

- Plain HTML — no rewrite.
- For specific `isaaclab.*` symbols, land at the module page and drill in via the auto-generated class docs.

## Exceptions

- **Simulator / SimulationApp / URDF import questions** → `isaac-sim` skill.
- **Custom Warp kernels for rewards** → `nvidia-warp` skill.
- **Humanoid foundation models (GR00T)** → `isaac-groot` skill.
- **Newton is experimental — flag when recommending.**

## Version drift

Catalog tracks `/main/`. When tagged versions are published to GitHub Pages, swap `/main/` → `/v<ver>/`. If URL structure breaks, re-enumerate the sidebar.
