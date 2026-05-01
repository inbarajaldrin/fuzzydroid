# Isaac Sim Docs — Live Sources

Curated entry points into NVIDIA Isaac Sim documentation at `https://docs.isaacsim.omniverse.nvidia.com/latest/`. Every URL is plain HTML — `WebFetch` directly per `retrieval-rule.md`.

Verified 2026-04-23 against Isaac Sim `/latest/` (5.1 stable).

---

## Getting Started

| Topic | URL | Extraction Prompt |
|---|---|---|
| Landing / TOC | `https://docs.isaacsim.omniverse.nvidia.com/latest/index.html` | "Extract the top-level section categories (Isaac Sim, Quick Start, Concepts, Base Applications, Development Components, Robot and Sensor Simulation, Utilities, API Documentation, Reference, Common) and any release-banner info." |
| Release notes | `https://docs.isaacsim.omniverse.nvidia.com/latest/overview/release_notes.html` | "Extract the most recent release notes — what shipped, breaking changes, API migrations, deprecated modules." |
| Requirements | `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html` | "Extract GPU / CPU / RAM / OS requirements and supported hardware matrix." |

## Installation

| Topic | URL | Extraction Prompt |
|---|---|---|
| Workstation install | `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_workstation.html` | "Extract the workstation install steps — launcher vs pip vs ZIP, post-install script, and the launch command." |
| Container install | `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_container.html` | "Extract the Docker run command, `nvcr.io/nvidia/isaac-sim` image tag, GPU flags, volume mounts, and X11 / WebRTC display options." |
| Cloud deployment | `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_cloud.html` | "Extract AWS / Azure / GCP deployment patterns and instance-type recommendations." |
| Pip install | `https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_pip.html` | "Extract `pip install isaacsim[...]` command variants and what each extra includes." |

## Python Scripting

| Topic | URL | Extraction Prompt |
|---|---|---|
| Python environment | `https://docs.isaacsim.omniverse.nvidia.com/latest/python_scripting/python_environment.html` | "Extract the Python environment setup — where python.sh / isaac-sim-python.sh live, how to activate it, and the Python version Isaac Sim ships with." |
| Standalone Python manual | `https://docs.isaacsim.omniverse.nvidia.com/latest/python_scripting/manual_standalone_python.html` | "Extract the SimulationApp(CONFIG) boilerplate — the CONFIG dict keys, import order (SimulationApp first, then everything else), update / render loop pattern, and cleanup." |
| Script Editor | `https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/omniverse_script_editor.html` | "Extract the in-Kit Script Editor workflow — where to open it, what's available without SimulationApp, and differences from standalone." |
| Jupyter notebook | `https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/jupyter_notebook.html` | "Extract the Jupyter setup for Isaac Sim and async-loop handling." |
| VSCode integration | `https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/vscode.html` | "Extract VSCode Python interpreter / debugger configuration for Isaac Sim scripts." |
| Carbonite settings | `https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/carb_settings.html` | "Extract how to read / set Isaac Sim carbonite settings from Python." |

## Core API Tutorials

| Topic | URL | Extraction Prompt |
|---|---|---|
| Core API index | `https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/index.html` | "List the core-API tutorials with their purpose." |
| Hello World (core) | `https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/tutorial_core_hello_world.html` | "Extract the minimal Python — open a stage, add a ground plane, add a robot, step simulation." |
| Hello Robot | `https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/tutorial_core_hello_robot.html` | "Extract adding a robot, setting joint positions, and commanding controllers." |
| Adding manipulator | `https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/tutorial_core_adding_manipulator.html` | "Extract adding a Franka / UR manipulator with gripper." |
| Adding props | `https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/tutorial_core_adding_props.html` | "Extract adding physics-enabled props (cubes, meshes) to a scene." |
| Adding multiple robots | `https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/tutorial_core_adding_multiple_robots.html` | "Extract multi-robot scene setup and per-robot controller wiring." |
| Multiple tasks | `https://docs.isaacsim.omniverse.nvidia.com/latest/core_api_tutorials/tutorial_core_multiple_tasks.html` | "Extract the Task class pattern for organizing multi-scene workflows." |

## Robot Simulation — Core

| Topic | URL | Extraction Prompt |
|---|---|---|
| Robot simulation index | `https://docs.isaacsim.omniverse.nvidia.com/latest/robot_simulation/index.html` | "Extract the robot-simulation section structure — robots, sensors, controllers, importers." |
| Robot policy example (RL inference) | `https://docs.isaacsim.omniverse.nvidia.com/latest/robot_simulation/ext_isaacsim_robot_policy_example.html` | "Extract how to load a trained Isaac Lab policy (ONNX / TorchScript) and run inference on a robot in Isaac Sim." |

## Robot Importers

| Topic | URL | Extraction Prompt |
|---|---|---|
| URDF importer | `https://docs.isaacsim.omniverse.nvidia.com/latest/robot_setup/ext_omni_importer_urdf.html` | "Extract the URDF importer UI / CLI / Python invocation and known quirks (joint drive conversion, mesh path handling, collision primitives)." |
| MJCF importer | `https://docs.isaacsim.omniverse.nvidia.com/latest/robot_setup/ext_omni_importer_mjcf.html` | "Extract MJCF → USD conversion and MuJoCo compatibility notes." |

## Sensors

| Topic | URL | Extraction Prompt |
|---|---|---|
| RTX sensors overview | `https://docs.isaacsim.omniverse.nvidia.com/latest/robot_simulation/ext_isaacsim_sensors_rtx.html` | "Extract RTX-based sensors (camera, lidar, stereo, depth) — creation, configuration, and data extraction." |
| Physics sensors overview | `https://docs.isaacsim.omniverse.nvidia.com/latest/robot_simulation/ext_isaacsim_sensors_physics.html` | "Extract physics-based sensors (contact, IMU, force, articulation) — setup and data retrieval." |

## Physics / Collision / PhysX

Physics and collision authoring is distributed across three source domains: Isaac Sim's `/physics/` and `/sensors/` sections cover simulator-level behavior and physics sensor setup; the Omniverse `omni_physics` dev guide covers schema depth including `contactOffset`/`restOffset`, SDF mesh cooking, and collision approximation APIs; and OpenUSD's `UsdPhysics` module is the cross-ecosystem schema reference for physics primitives. Robotics users debugging contact offsets, articulation stability, or SDF collision approximation on a loaded robot usually need the `omni_physics` dev-guide pages first.

**Note:** The `omni_physics` doc paths at `docs.omniverse.nvidia.com/kit/docs/omni_physics/` return HTTP 403 on `.md` suffix — always fetch the `.html` URL directly for those entries.

### Isaac Sim physics

| Topic | URL | Extraction Prompt |
|---|---|---|
| Physics section landing | `https://docs.isaacsim.omniverse.nvidia.com/latest/physics/index.html` | "Extract the top-level structure of Isaac Sim's physics section — subsections, key topics, and how physics features map to the simulator runtime." |
| PhysX simulation fundamentals | `https://docs.isaacsim.omniverse.nvidia.com/latest/physics/simulation_fundamentals.html` | "Extract PhysX simulation fundamentals in Isaac Sim — time-stepping, substeps, scene settings, and how PhysX integrates with the Kit app loop." |
| New Newton-based engine overview | `https://docs.isaacsim.omniverse.nvidia.com/latest/physics/new_physics_engine.html` | "Extract the overview of the new Newton-based physics engine — what changed from PhysX-only, capability differences, and migration notes from the legacy engine." |
| Newton physics integration | `https://docs.isaacsim.omniverse.nvidia.com/latest/physics/newton_physics.html` | "Extract Newton physics integration details — APIs, configuration flags, contact model differences vs classic PhysX, and known limitations." |
| Physics learning resources | `https://docs.isaacsim.omniverse.nvidia.com/latest/physics/physics_resources.html` | "Extract the curated physics learning and reference resources — tutorials, external PhysX docs, and recommended reading for Isaac Sim physics users." |
| Static collision authoring | `https://docs.isaacsim.omniverse.nvidia.com/latest/physics/physics_static_collision.html` | "Extract static collision authoring in Isaac Sim — how to mark meshes as static colliders, supported collision shapes (convex hull, convex decomposition, SDF, mesh), USD prim configuration, and performance guidance." |
| Physics inspector extension | `https://docs.isaacsim.omniverse.nvidia.com/latest/physics/ext_isaacsim_inspect_physics.html` | "Extract the Physics Inspector extension — how to open it, what runtime physics state it exposes (contacts, applied forces, joint states), and how to use it for debugging." |

### Physics sensors

| Topic | URL | Extraction Prompt |
|---|---|---|
| Contact sensor | `https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_physics_contact.html` | "Extract the contact sensor setup — how to attach it to a rigid body, the Python API for reading contact force/impulse data each step, filtering by body pairs, and data schema returned." |
| IMU sensor | `https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_physics_imu.html` | "Extract IMU sensor setup — how to attach an IMU to a link, the Python API for reading linear acceleration and angular velocity, coordinate frame conventions, and noise model options." |

### Omniverse omni_physics dev guide

| Topic | URL | Extraction Prompt |
|---|---|---|
| Rigid bodies dev guide | `https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/rigid_bodies_articulations/rigid_bodies.html` | "Extract rigid body setup via omni_physics — PhysicsRigidBodyAPI application, mass/inertia overrides via PhysicsMassAPI, velocity damping, sleep thresholds, and Python snippet for enabling physics on a USD prim." |
| Collision authoring (contactOffset / restOffset / SDF) | `https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/rigid_bodies_articulations/collision.html` | "Extract the full collision authoring reference: contactOffset and restOffset attribute semantics (what each controls, default values, PhysxCollisionAPI location, and runtime-vs-authoring implications); all supported collision approximation types (convex hull, convex decomposition, SDF, mesh, primitive); SDF mesh cooking — when it runs, how to trigger offline baking, and the performance trade-offs; and the PhysxCollisionAPI / UsdPhysicsCollisionAPI Python attributes for setting these in code." |
| Articulation stability tuning | `https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/guides/articulation_stability_guide.html` | "Extract articulation stability tuning guidance — common instability causes (high mass ratios, stiff joints, small time steps), recommended solver iteration counts, contact offset tuning for robot links, joint drive stiffness/damping guidelines, and any articulation-specific PhysX flags." |

### OpenUSD physics schemas

| Topic | URL | Extraction Prompt |
|---|---|---|
| UsdPhysics schema overview | `https://openusd.org/release/api/usd_physics_page_front.html` | "Extract the UsdPhysics schema overview — the full list of applied API schemas (PhysicsRigidBodyAPI, PhysicsMassAPI, PhysicsArticulationRootAPI, PhysicsCollisionAPI, PhysicsJointAPI family), their attribute names and types, which schemas are combinable, and any authoring constraints noted in the spec." |

---

**Cross-skill routing for physics topics:**

- Pure Warp GPU kernel math for physics simulation (custom integrators, collision kernels) → `nvidia-warp` skill
- Pure USD schema authoring independent of robotics (generic UsdPhysics prim composition) → `openusd` skill
- Physics-based RL environment setup and Isaac Lab gym tasks → `isaac-lab` skill

---

## Synthetic Data (Isaac-wrapped Replicator)

| Topic | URL | Extraction Prompt |
|---|---|---|
| SDG with Isaac Sim | `https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/index.html` | "Extract how Isaac Sim wraps Omniverse Replicator — `isaacsim.replicator` module, robot-sensor writers, pose randomization on articulations." |

## cuMotion (GPU Motion Planning)

| Topic | URL | Extraction Prompt |
|---|---|---|
| cuMotion index | `https://docs.isaacsim.omniverse.nvidia.com/latest/cumotion/index.html` | "Extract cuMotion overview — GPU-accelerated motion planning on top of curobo." |
| Trajectory generator | `https://docs.isaacsim.omniverse.nvidia.com/latest/cumotion/tutorial_trajectory_generator.html` | "Extract the trajectory generator tutorial — joint-space and task-space planning calls." |
| Trajectory optimizer | `https://docs.isaacsim.omniverse.nvidia.com/latest/cumotion/tutorial_trajectory_optimizer.html` | "Extract the trajectory optimizer tutorial." |
| Graph planner | `https://docs.isaacsim.omniverse.nvidia.com/latest/cumotion/tutorial_graph_planner.html` | "Extract the global graph planner usage." |
| RMPflow | `https://docs.isaacsim.omniverse.nvidia.com/latest/cumotion/tutorial_rmpflow.html` | "Extract RMPflow reactive motion policy usage." |
| Robot configuration | `https://docs.isaacsim.omniverse.nvidia.com/latest/cumotion/tutorial_robot_configuration.html` | "Extract the robot config YAML format (kinematics, link spheres, self-collision)." |

## Cortex (decider networks)

| Topic | URL | Extraction Prompt |
|---|---|---|
| Cortex overview | `https://docs.isaacsim.omniverse.nvidia.com/latest/cortex_tutorials/tutorial_cortex_1_overview.html` | "Extract what Cortex is and the decider-network pattern for task-level decision making." |
| Decider networks | `https://docs.isaacsim.omniverse.nvidia.com/latest/cortex_tutorials/tutorial_cortex_2_decider_networks.html` | "Extract decider-network authoring — states, transitions, behaviors." |
| Franka block stacking | `https://docs.isaacsim.omniverse.nvidia.com/latest/cortex_tutorials/tutorial_cortex_4_franka_block_stacking.html` | "Extract the Franka block-stacking end-to-end example." |
| UR10 bin stacking | `https://docs.isaacsim.omniverse.nvidia.com/latest/cortex_tutorials/tutorial_cortex_5_ur10_bin_stacking.html` | "Extract the UR10 bin-stacking end-to-end example." |

## Isaac Lab Integration

| Topic | URL | Extraction Prompt |
|---|---|---|
| Isaac Lab tutorials index | `https://docs.isaacsim.omniverse.nvidia.com/latest/isaac_lab_tutorials/index.html` | "Extract how Isaac Lab relates to Isaac Sim — link out to the Isaac Lab docs. For deep RL training questions, route to the `isaac-lab` skill." |

## Isaac ROS / ROS 2 Bridge

| Topic | URL | Extraction Prompt |
|---|---|---|
| ROS 2 tutorials | `https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/index.html` | "Extract ROS 2 bridge setup, topic mapping, TF publishing, and common robot bring-up patterns in sim." |
| Isaac ROS (nvidia_isaac_ros tutorials) | `https://docs.isaacsim.omniverse.nvidia.com/latest/nvidia_isaac_ros/isaac_ros_tutorials.html` | "Extract how Isaac ROS packages (cuVSLAM, Nvblox, FoundationPose) integrate with Isaac Sim for sim-to-real testing. For deep Isaac ROS questions, route to the `isaac-ros` skill." |

## Digital Twin

| Topic | URL | Extraction Prompt |
|---|---|---|
| Digital twin index | `https://docs.isaacsim.omniverse.nvidia.com/latest/digital_twin/index.html` | "Extract the digital-twin workflows — occupancy mapping, warehouse logistics, conveyor simulation." |
| Warehouse creator | `https://docs.isaacsim.omniverse.nvidia.com/latest/digital_twin/warehouse_logistics/ext_omni_warehouse_creator.html` | "Extract the warehouse creator extension — parametric warehouse scene generation." |

## Assets

| Topic | URL | Extraction Prompt |
|---|---|---|
| USD asset overview | `https://docs.isaacsim.omniverse.nvidia.com/latest/assets/usd_assets_overview.html` | "Extract the Isaac Sim asset library structure — where assets live, Nucleus vs local, and how to discover." |
| Robots | `https://docs.isaacsim.omniverse.nvidia.com/latest/assets/usd_assets_robots.html` | "Extract the list of shipped robots (Franka, UR, Nova Carter, Jetbot, Transporter, humanoids, etc.)." |
| Environments | `https://docs.isaacsim.omniverse.nvidia.com/latest/assets/usd_assets_environments.html` | "Extract the shipped environments (warehouse, hospital, office, outdoor)." |
| Camera / depth sensors | `https://docs.isaacsim.omniverse.nvidia.com/latest/assets/usd_assets_camera_depth_sensors.html` | "Extract the shipped camera and depth sensor models with intrinsics." |

## API Reference

| Topic | URL | Extraction Prompt |
|---|---|---|
| Python API reference | `https://docs.isaacsim.omniverse.nvidia.com/latest/reference_python_api.html` | "Extract the top-level `isaacsim.*` Python module list — isaacsim.core, isaacsim.robot, isaacsim.sensors, isaacsim.replicator, isaacsim.ros2, isaacsim.storage, isaacsim.util, etc." |
| Reference architecture | `https://docs.isaacsim.omniverse.nvidia.com/latest/reference_architecture.html` | "Extract the Isaac Sim reference architecture — Kit apps, isaacsim.* extensions, dependency on Omniverse libraries." |
| Reference materials (conventions, glossary) | `https://docs.isaacsim.omniverse.nvidia.com/latest/reference_conventions.html` | "Extract Isaac Sim's naming / coordinate / unit conventions." |
| Glossary | `https://docs.isaacsim.omniverse.nvidia.com/latest/reference_glossary.html` | "Look up the specific term the user asked about." |

---

## Notes on extraction

- Plain HTML — no rewrite.
- For specific `isaacsim.*` Python symbols, start at `reference_python_api.html` and drill into the relevant module page.
- Sidebar scrape is your friend when the user names a sub-topic not in this catalog.

## Exceptions

- **`.md` suffix does NOT work** on this subdomain. Always fetch the `.html`.
- **Raw Replicator questions** (non-robot SDG) → `omniverse-replicator` skill.
- **RL training questions** → `isaac-lab` skill.
- **ROS 2 GPU-accelerated packages (cuVSLAM, Nvblox)** → `isaac-ros` skill.

## Version drift

Catalog tracks `/latest/`. Isaac Sim had a major API rename in 4.x → 5.x (`omni.isaac.*` → `isaacsim.*`) — if pages reference old APIs, check release notes for the migration path.
