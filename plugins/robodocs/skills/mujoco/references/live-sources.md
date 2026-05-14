# MuJoCo live-source URL catalog

Each row: **Topic** | **Canonical URL** | **What to extract**.

Default version path is `/en/stable/` on ReadTheDocs. Swap to `/en/latest/` only if the user asks about HEAD / unreleased features. Pin to e.g. `/en/3.5.0/` only if the user names a version.

---

## A. Core MuJoCo (C/C++ simulator) — `mujoco.readthedocs.io`

| Topic | URL | Extraction prompt |
|---|---|---|
| Landing / TOC | `https://mujoco.readthedocs.io/en/stable/` | Whole-site table of contents and feature list (note: bare-root may 403 — use `overview.html` as the practical landing) |
| Overview | `https://mujoco.readthedocs.io/en/stable/overview.html` | What MuJoCo is, design philosophy, what makes it different from Bullet/PhysX, the simulation pipeline at a high level |
| Installation | `https://mujoco.readthedocs.io/en/stable/programming/index.html` | C/C++ installation, library linking, dependencies, build flags |
| Computation pipeline | `https://mujoco.readthedocs.io/en/stable/computation/index.html` | Forward dynamics, inverse dynamics, kinematics, the order of operations in `mj_step`, what each stage of `mj_forward` computes |
| Constraint model | `https://mujoco.readthedocs.io/en/stable/computation/index.html#constraints` | Pyramidal vs elliptic friction cones, soft contacts, equality constraints, the unified soft-constraint formulation, `solref`/`solimp` tuning |
| MJCF XML reference | `https://mujoco.readthedocs.io/en/stable/XMLreference.html` | XML element and attribute definitions — `<body>`, `<joint>`, `<geom>`, `<actuator>`, `<sensor>`, `<equality>`, `<contact>`, `<default>`, `<asset>`, `<tendon>`, etc. Search for specific element by name. |
| URDF compatibility | `https://mujoco.readthedocs.io/en/stable/modeling.html#urdf-extensions` | URDF import, MuJoCo-specific URDF tags, the `mujoco` element in URDF |
| Modeling guide | `https://mujoco.readthedocs.io/en/stable/modeling.html` | How to build models: bodies, joints, geoms, inertia, mass, contact pairs, defaults, includes |
| Programming guide | `https://mujoco.readthedocs.io/en/stable/programming/index.html` | C/C++ programming: load model, allocate data, call `mj_step`, free, error handling, threading |
| Simulation programming | `https://mujoco.readthedocs.io/en/stable/programming/simulation.html` | `mj_step`, `mj_forward`, `mj_inverse`, sensor reading, control loop structure |
| Visualization API | `https://mujoco.readthedocs.io/en/stable/programming/visualization.html` | `mjvScene`, `mjrContext`, `mjvCamera`, `mjvOption`, abstract scene → rendered pixels |
| UI / mouse / keyboard | `https://mujoco.readthedocs.io/en/stable/programming/ui.html` | The built-in UI library, mouse interaction with the scene |
| Sample programs | `https://mujoco.readthedocs.io/en/stable/programming/samples.html` | The bundled `simulate`, `basic`, `record`, `compile` programs and what each does |
| Extensions / plugins | `https://mujoco.readthedocs.io/en/stable/programming/extensions.html` | The plugin SDK: sensor plugins, actuator plugins, elasticity plugins, custom physics |
| C API reference | `https://mujoco.readthedocs.io/en/stable/APIreference/index.html` | Function-by-function reference. Drill in via in-page anchors like `#mj-step`, `#mj-forward`, `#mjv-scene`. |
| API: types | `https://mujoco.readthedocs.io/en/stable/APIreference/APItypes.html` | `mjModel`, `mjData`, `mjOption`, `mjvScene`, `mjrContext` struct fields |
| API: functions | `https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html` | All `mj_*`, `mju_*`, `mjv_*`, `mjr_*`, `mjd_*` function signatures |
| API: macros | `https://mujoco.readthedocs.io/en/stable/APIreference/APImacros.html` | `mjMAXSZ`, `mjMINMU`, all `mj*` constants |
| Derivatives | `https://mujoco.readthedocs.io/en/stable/programming/derivatives.html` | Analytical and finite-difference derivatives, `mjd_transitionFD`, `mjd_inverseFD` |
| Changelog | `https://mujoco.readthedocs.io/en/stable/changelog.html` | Version-by-version release notes. Search for a feature or version (e.g. `3.5`, `keyframe`). |

---

## B. Python bindings (`pip install mujoco`)

| Topic | URL | Extraction prompt |
|---|---|---|
| Python overview | `https://mujoco.readthedocs.io/en/stable/python.html` | The `mujoco` PyPI package, `MjModel.from_xml_path`, `MjData`, `mj_step`, GLFW/EGL/OSMesa rendering |
| Python tutorial colab | `https://github.com/google-deepmind/mujoco/blob/main/python/tutorial.ipynb` | End-to-end notebook covering load → step → render → control |
| `mujoco.viewer` | `https://mujoco.readthedocs.io/en/stable/python.html#interactive-viewer` | The passive viewer, the managed viewer, `mjpython` (required on macOS) |
| Rendering off-screen | `https://mujoco.readthedocs.io/en/stable/python.html#rendering` | EGL on Linux headless, OSMesa fallback, the `mujoco.Renderer` class |
| Python API reference | `https://github.com/google-deepmind/mujoco/blob/main/python/README.md` | The bindings README — install, viewer modes, GLFW/EGL/OSMesa selection, mocap |
| PyPI page | `https://pypi.org/project/mujoco/` | Current PyPI version, install command, project links |

---

## C. MJX (MuJoCo XLA / JAX backend)

| Topic | URL | Extraction prompt |
|---|---|---|
| MJX docs landing | `https://mujoco.readthedocs.io/en/stable/mjx.html` | What MJX is, JAX vs Warp backend split, supported features vs limitations vs core MuJoCo |
| MJX API reference | `https://mujoco.readthedocs.io/en/stable/mjx_api.html` | `mjx.Model`, `mjx.Data`, `mjx.step`, `mjx.put_model`, `mjx.get_data` |
| MJX tutorials | `https://mujoco.readthedocs.io/en/stable/mjx_tutorials.html` | Brax integration, batched simulation, training RL policies on TPU |
| MJX source / README | `https://github.com/google-deepmind/mujoco/tree/main/mjx` | The MJX subtree of the main repo, install instructions, contribution notes |

---

## D. MuJoCo Warp (`mujoco_warp` / MJWarp) — NVIDIA GPU backend

| Topic | URL | Extraction prompt |
|---|---|---|
| Repo + README | `https://github.com/google-deepmind/mujoco_warp` | Install, supported features, the relationship to MJX, NVIDIA Warp dependency |
| Issues (known limitations) | `https://github.com/google-deepmind/mujoco_warp/issues` | Open issues for unsupported features, GPU kernel bugs |
| Discussions | `https://github.com/google-deepmind/mujoco_warp/discussions` | Community Q&A for the Warp backend |
| MuJoCo 3.5 announcement (where Warp went GA) | `https://github.com/google-deepmind/mujoco/discussions/3094` | The official 3.5 release post — what made Warp the canonical GPU path |

---

## E. MuJoCo Menagerie (model zoo)

| Topic | URL | Extraction prompt |
|---|---|---|
| Repo + index | `https://github.com/google-deepmind/mujoco_menagerie` | The full list of robots — table of model name, manufacturer, DoF, source, version |
| Per-model READMEs | `https://github.com/google-deepmind/mujoco_menagerie/tree/main/<robot_dir>` | Each robot has its own dir with its own README. See `references/menagerie.md` for the full robot list and direct links. |
| Per-model MJCF | `https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/<robot_dir>/<robot>.xml` | Raw MJCF XML — the actual model used in simulation |

---

## F. MuJoCo MPC (`mujoco_mpc`)

| Topic | URL | Extraction prompt |
|---|---|---|
| Repo + README | `https://github.com/google-deepmind/mujoco_mpc` | What MJPC is, predictive sampling, iLQG, gradient descent planners, the GUI |
| Paper | `https://arxiv.org/abs/2212.00541` | The MJPC paper — algorithmic details |
| Tasks index | `https://github.com/google-deepmind/mujoco_mpc/tree/main/mjpc/tasks` | Built-in tasks: cartpole, swimmer, humanoid, manipulation, walker |
| Discussions | `https://github.com/google-deepmind/mujoco_mpc/discussions` | Community Q&A for MJPC |

---

## G. MuJoCo Playground (`mujoco_playground`)

| Topic | URL | Extraction prompt |
|---|---|---|
| Repo + README | `https://github.com/google-deepmind/mujoco_playground` | What Playground is, the JAX/Warp backends, environment list, training APIs |
| Site | `https://playground.mujoco.org/` | Marketing/landing — links into the repo and demos |
| Paper | `https://arxiv.org/abs/2502.08844` | The Playground paper — design rationale, benchmarks |
| Environments | `https://github.com/google-deepmind/mujoco_playground/tree/main/mujoco_playground/_src` | Locomotion / manipulation env source — Cartpole, Unitree Go2, Franka, Berkeley Humanoid, etc. |
| Discussions | `https://github.com/google-deepmind/mujoco_playground/discussions` | Community Q&A — training tips, sim-to-real, Madrona rendering |
| Warp integration announcement | `https://github.com/google-deepmind/mujoco_playground/discussions/197` | Beta notice for Playground-on-MJWarp |
| DeepWiki mirror | `https://deepwiki.com/google-deepmind/mujoco_playground` | Third-party indexed view of the repo for cross-search |

---

## H. dm_control (DeepMind Control Suite + Composer)

| Topic | URL | Extraction prompt |
|---|---|---|
| Repo + README | `https://github.com/google-deepmind/dm_control` | dm_control overview, Suite vs Composer vs Locomotion, the PyMJCF builder, the MuJoCo Python wrapper origins |
| Suite environments | `https://github.com/google-deepmind/dm_control/tree/main/dm_control/suite` | The classic 30 RL tasks (cartpole, cheetah, humanoid, walker, etc.) |
| Composer framework | `https://github.com/google-deepmind/dm_control/tree/main/dm_control/composer` | Task composition, entities, observables, arenas |
| Discussions | `https://github.com/google-deepmind/dm_control/discussions` | Community Q&A |

---

## I. Community / forum (GitHub Discussions)

**The historical `mujoco.org/forum` was retired in 2022.** All community Q&A moved to GitHub Discussions.

| Topic | URL | Extraction prompt |
|---|---|---|
| Main forum | `https://github.com/google-deepmind/mujoco/discussions` | The primary discussion hub for the core simulator |
| Asking for Help | `https://github.com/google-deepmind/mujoco/discussions/categories/asking-for-help` | User questions — the closest analog to a Stack Overflow tag (verified live: this is the actual category name, not "Q&A") |
| Show and tell | `https://github.com/google-deepmind/mujoco/discussions/categories/show-and-tell` | Community projects, models, integrations |
| Announcements | `https://github.com/google-deepmind/mujoco/discussions/categories/announcements` | Release announcements, official updates from DeepMind maintainers |
| Ideas | `https://github.com/google-deepmind/mujoco/discussions/categories/ideas` | Feature requests, open design questions |
| General | `https://github.com/google-deepmind/mujoco/discussions/categories/general` | Open-ended discussion |
| Polls | `https://github.com/google-deepmind/mujoco/discussions/categories/polls` | Community polls (lower volume) |
| Playground forum | `https://github.com/google-deepmind/mujoco_playground/discussions` | Playground-specific |
| Warp forum | `https://github.com/google-deepmind/mujoco_warp/discussions` | MJWarp-specific |
| Menagerie forum | `https://github.com/google-deepmind/mujoco_menagerie/discussions` | Model-zoo-specific (asset bugs, new robot requests) |
| dm_control forum | `https://github.com/google-deepmind/dm_control/discussions` | Suite/Composer-specific |
| MPC forum | `https://github.com/google-deepmind/mujoco_mpc/discussions` | MJPC-specific |

For how to search and quote these threads via `gh`, see `references/forums.md`.

---

## J. Marketing / homepage

| Topic | URL | Extraction prompt |
|---|---|---|
| MuJoCo homepage | `https://mujoco.org/` | High-level pitch, links to docs/repo |
| Playground homepage | `https://playground.mujoco.org/` | Playground pitch, demos |

---

## K. Third-party integrations (notable)

| Topic | URL | Extraction prompt |
|---|---|---|
| MuJoCo Simulink Blockset (MathWorks) | `https://github.com/mathworks-robotics/mujoco-simulink-blockset` | MATLAB/Simulink integration — how to drive MuJoCo from Simulink models |
| Unity plugin | `https://mujoco.readthedocs.io/en/stable/unity.html` | Official Unity bindings: how to install, asset import, prefab generation, runtime stepping |
