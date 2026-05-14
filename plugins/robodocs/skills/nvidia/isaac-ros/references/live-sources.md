# Isaac ROS Docs — Live Sources

Curated entry points into NVIDIA Isaac ROS documentation at `https://nvidia-isaac-ros.github.io/`. Every URL is plain HTML — `WebFetch` directly.

Verified 2026-04-23.

---

## Getting Started

| Topic | URL | Extraction Prompt |
|---|---|---|
| Landing / TOC | `https://nvidia-isaac-ros.github.io/` | "Extract the top-level section structure (Getting Started, Concepts, Reference Workflows, Packages, Release Notes, Troubleshooting, About)." |
| Getting started index | `https://nvidia-isaac-ros.github.io/getting_started/index.html` | "Extract the onboarding flow — hardware requirements (Jetson vs x86), OS, ROS 2 distro, and first-run example." |
| Dev environment | `https://nvidia-isaac-ros.github.io/concepts/dev_env/index.html` | "Extract the recommended development environment — Docker image, host tools, CUDA / cuDNN / TensorRT versions." |
| Concepts index | `https://nvidia-isaac-ros.github.io/concepts/index.html` | "Extract the high-level capability index (perception, SLAM, manipulation, transport, DNN inference)." |
| Reference workflows | `https://nvidia-isaac-ros.github.io/reference_workflows/index.html` | "Extract the solution blueprints — Isaac for Manipulation and Isaac for Mobility overviews." |

## NITROS — Zero-Copy Transport

| Topic | URL | Extraction Prompt |
|---|---|---|
| NITROS index | `https://nvidia-isaac-ros.github.io/concepts/nitros/index.html` | "Extract what NITROS is, when to use it vs standard ROS 2 transport, and the message-type registry." |
| CUDA with NITROS | `https://nvidia-isaac-ros.github.io/concepts/nitros/cuda_with_nitros.html` | "Extract CUDA-aware message passing with NITROS — zero-copy GPU tensor sharing between nodes." |
| PyNITROS index | `https://nvidia-isaac-ros.github.io/concepts/nitros/pynitros/index.html` | "Extract the Python API for NITROS messages." |
| PyNITROS tutorial | `https://nvidia-isaac-ros.github.io/concepts/nitros/pynitros/tutorial_pynitros.html` | "Extract a working PyNITROS publisher/subscriber example." |
| NITROS Bridge — Isaac Sim | `https://nvidia-isaac-ros.github.io/concepts/nitros_bridge/tutorial_isaac_sim.html` | "Extract how NITROS Bridge connects Isaac Sim to on-robot ROS 2 nodes for sim-to-real testing." |

## Perception — Object Detection

| Topic | URL | Extraction Prompt |
|---|---|---|
| Detection overview | `https://nvidia-isaac-ros.github.io/concepts/object_detection/index.html` | "Extract the detection catalog (DetectNet, YOLOv8, RT-DETR, Grounding DINO) with use cases." |
| DetectNet | `https://nvidia-isaac-ros.github.io/concepts/object_detection/detectnet/index.html` | "Extract DetectNet usage — model format, topics, tuning." |
| DetectNet — Isaac Sim test | `https://nvidia-isaac-ros.github.io/concepts/object_detection/detectnet/tutorial_isaac_sim.html` | "Extract the Isaac Sim test harness for DetectNet." |
| DetectNet — custom model | `https://nvidia-isaac-ros.github.io/concepts/object_detection/detectnet/tutorial_custom_model.html` | "Extract how to train/deploy a custom DetectNet model." |
| YOLOv8 | `https://nvidia-isaac-ros.github.io/concepts/object_detection/yolov8/index.html` | "Extract the YOLOv8 package setup and inference usage." |
| RT-DETR | `https://nvidia-isaac-ros.github.io/concepts/object_detection/rtdetr/index.html` | "Extract RT-DETR package setup." |
| RT-DETR — Isaac Sim | `https://nvidia-isaac-ros.github.io/concepts/object_detection/rtdetr/tutorial_isaac_sim.html` | "Extract the Isaac Sim test flow for RT-DETR." |
| Grounding DINO | `https://nvidia-isaac-ros.github.io/concepts/object_detection/grounding_dino/index.html` | "Extract Grounding DINO open-vocabulary detection usage." |

## Perception — Pose Estimation

| Topic | URL | Extraction Prompt |
|---|---|---|
| Pose estimation overview | `https://nvidia-isaac-ros.github.io/concepts/pose_estimation/index.html` | "Extract the pose-estimation catalog (DOPE, CenterPose, FoundationPose)." |
| FoundationPose | `https://nvidia-isaac-ros.github.io/concepts/pose_estimation/foundationpose/index.html` | "Extract FoundationPose capabilities — 6D pose estimation from RGB + depth + object mesh." |
| FoundationPose — Isaac Sim | `https://nvidia-isaac-ros.github.io/concepts/pose_estimation/foundationpose/tutorial_isaac_sim.html` | "Extract the Isaac Sim FoundationPose test flow." |
| FoundationPose — create your own mesh | `https://nvidia-isaac-ros.github.io/concepts/pose_estimation/foundationpose/tutorial_create_your_own_mesh.html` | "Extract the mesh-preparation workflow for custom objects." |
| FoundationPose — tracking | `https://nvidia-isaac-ros.github.io/concepts/pose_estimation/foundationpose/tutorial_tracking.html` | "Extract the tracking mode that follows a pose across frames." |
| DOPE | `https://nvidia-isaac-ros.github.io/concepts/pose_estimation/dope/index.html` | "Extract DOPE usage for known-object 6D pose." |
| CenterPose | `https://nvidia-isaac-ros.github.io/concepts/pose_estimation/centerpose/index.html` | "Extract CenterPose category-level pose estimation usage." |

## Perception — Segmentation

| Topic | URL | Extraction Prompt |
|---|---|---|
| Segmentation overview | `https://nvidia-isaac-ros.github.io/concepts/segmentation/index.html` | "Extract the segmentation catalog (Segformer, Segment Anything, U-Net)." |
| Segformer | `https://nvidia-isaac-ros.github.io/concepts/segmentation/segformer/index.html` | "Extract Segformer usage." |
| Segformer — TensorRT | `https://nvidia-isaac-ros.github.io/concepts/segmentation/segformer/tutorial_tensorrt.html` | "Extract the TensorRT engine build and deploy flow." |
| Segment Anything | `https://nvidia-isaac-ros.github.io/concepts/segmentation/segment_anything/index.html` | "Extract Segment Anything usage." |

## Perception — Stereo Depth

| Topic | URL | Extraction Prompt |
|---|---|---|
| Stereo depth overview | `https://nvidia-isaac-ros.github.io/concepts/stereo_depth/index.html` | "Extract the stereo-depth catalog (ESS, SGM, FoundationStereo)." |
| ESS | `https://nvidia-isaac-ros.github.io/concepts/stereo_depth/ess/index.html` | "Extract ESS DNN stereo usage." |
| SGM | `https://nvidia-isaac-ros.github.io/concepts/stereo_depth/sgm/index.html` | "Extract SGM classic stereo usage." |
| FoundationStereo | `https://nvidia-isaac-ros.github.io/concepts/stereo_depth/foundationstereo/index.html` | "Extract FoundationStereo usage." |

## Perception — Fiducials / AprilTag

| Topic | URL | Extraction Prompt |
|---|---|---|
| AprilTag — Isaac Sim | `https://nvidia-isaac-ros.github.io/concepts/fiducials/apriltag/tutorial_isaac_sim.html` | "Extract AprilTag detection in Isaac Sim." |
| AprilTag — USB camera | `https://nvidia-isaac-ros.github.io/concepts/fiducials/apriltag/tutorial_usb_cam.html` | "Extract AprilTag with a real USB webcam." |

## SLAM & Localization

| Topic | URL | Extraction Prompt |
|---|---|---|
| Visual SLAM (cuVSLAM) index | `https://nvidia-isaac-ros.github.io/concepts/visual_slam/cuvslam/index.html` | "Extract cuVSLAM — NVIDIA's CUDA-accelerated visual / visual-inertial SLAM package." |
| Visual global localization (cuVGL) | `https://nvidia-isaac-ros.github.io/concepts/visual_global_localization/index.html` | "Extract cuVGL — visual global localization / relocalization against a map." |
| cuVGL tutorial | `https://nvidia-isaac-ros.github.io/concepts/visual_global_localization/tutorials/tutorial_cuvgl_localization.html` | "Extract the cuVGL end-to-end tutorial." |
| LiDAR localization (Isaac Sim) | `https://nvidia-isaac-ros.github.io/concepts/localization/lidar/tutorial_isaac_sim.html` | "Extract LiDAR-based localization in Isaac Sim." |

## Scene Reconstruction — Nvblox

| Topic | URL | Extraction Prompt |
|---|---|---|
| Nvblox index | `https://nvidia-isaac-ros.github.io/concepts/scene_reconstruction/nvblox/index.html` | "Extract Nvblox — GPU occupancy / ESDF mapping for navigation." |
| Nvblox technical details | `https://nvidia-isaac-ros.github.io/concepts/scene_reconstruction/nvblox/technical_details.html` | "Extract Nvblox internals — TSDF / ESDF / occupancy layers, voxel size, memory model." |
| Nvblox — Isaac Sim | `https://nvidia-isaac-ros.github.io/concepts/scene_reconstruction/nvblox/tutorials/tutorial_isaac_sim.html` | "Extract Isaac Sim + Nvblox end-to-end." |
| Nvblox — RealSense | `https://nvidia-isaac-ros.github.io/concepts/scene_reconstruction/nvblox/tutorials/tutorial_realsense.html` | "Extract real-robot Nvblox with Intel RealSense." |
| Nvblox — ZED | `https://nvidia-isaac-ros.github.io/concepts/scene_reconstruction/nvblox/tutorials/tutorial_zed.html` | "Extract Nvblox with a StereoLabs ZED camera." |

## Manipulation

| Topic | URL | Extraction Prompt |
|---|---|---|
| Manipulation index | `https://nvidia-isaac-ros.github.io/concepts/manipulation/index.html` | "Extract the manipulation stack overview — cuMotion + MoveIt, isaac_grasp, pick_and_place, XRDF." |
| cuMotion + MoveIt — Isaac Sim | `https://nvidia-isaac-ros.github.io/concepts/manipulation/cumotion_moveit/tutorial_isaac_sim.html` | "Extract cuMotion running through MoveIt in Isaac Sim." |
| cuMotion + MoveIt — custom manipulator | `https://nvidia-isaac-ros.github.io/concepts/manipulation/cumotion_moveit/tutorial_custom_manipulator.html` | "Extract how to add cuMotion support for a custom robot." |
| Isaac Grasp | `https://nvidia-isaac-ros.github.io/concepts/manipulation/isaac_grasp.html` | "Extract the isaac_grasp package — grasp pose authoring and selection." |
| Pick and place | `https://nvidia-isaac-ros.github.io/concepts/manipulation/pick_and_place.html` | "Extract the end-to-end pick-and-place reference workflow." |
| XRDF (extended robot description) | `https://nvidia-isaac-ros.github.io/concepts/manipulation/xrdf.html` | "Extract the XRDF YAML format — collision spheres, self-collision, joint groups." |
| Orchestration | `https://nvidia-isaac-ros.github.io/concepts/manipulation/orchestration.html` | "Extract the orchestration pattern for multi-step manipulation tasks." |

## DNN Inference

| Topic | URL | Extraction Prompt |
|---|---|---|
| DNN inference index | `https://nvidia-isaac-ros.github.io/concepts/dnn_inference/index.html` | "Extract the DNN-inference abstraction — TensorRT vs Triton choice, engine caching, input/output topics." |
| TensorRT & Triton info | `https://nvidia-isaac-ros.github.io/concepts/dnn_inference/tensorrt_and_triton_info.html` | "Extract TensorRT engine build workflow and Triton serving integration." |
| Model preparation | `https://nvidia-isaac-ros.github.io/concepts/dnn_inference/model_preparation.html` | "Extract the ONNX export → TensorRT engine → deployment flow for custom models." |

## Cloud Control

| Topic | URL | Extraction Prompt |
|---|---|---|
| Cloud control index | `https://nvidia-isaac-ros.github.io/concepts/cloud_control/index.html` | "Extract Isaac Mission Client + Mission Dispatch architecture for fleet orchestration." |
| Isaac ROS Mission Client | `https://nvidia-isaac-ros.github.io/concepts/cloud_control/isaac_ros_mission_client.html` | "Extract the robot-side Mission Client package usage." |
| Isaac Cloud MCP Mission Control | `https://nvidia-isaac-ros.github.io/concepts/cloud_control/tutorial_isaac_cloud_mcp_mission_control.html` | "Extract the Mission Control tutorial via Isaac Cloud." |

## Benchmarking & Jetson

| Topic | URL | Extraction Prompt |
|---|---|---|
| Benchmarking | `https://nvidia-isaac-ros.github.io/concepts/benchmarking/index.html` | "Extract the Isaac ROS benchmark harness — how to measure end-to-end latency / throughput of a graph." |
| Jetson stats | `https://nvidia-isaac-ros.github.io/concepts/jetson_stats/index.html` | "Extract Jetson-specific monitoring (jtop, power modes, thermal)." |

---

## Notes on extraction

- Plain HTML, no rewrite.
- Most capability sections have a `tutorial_isaac_sim.html` page — use it for sim-first testing before real-robot deployment.
- For specific ROS 2 package names, check `repositories_and_packages/` sub-tree (scrape from sidebar).

## Exceptions

- **Isaac Sim simulator questions** (setting up robots, sensors in sim) → `isaac-sim` skill.
- **RL training** → `isaac-lab` skill.
- **Raw Omniverse Replicator** → `omniverse-replicator` skill.

## Version drift

Catalog reflects current Isaac ROS (2026-04-23). New packages land frequently — re-scrape the sidebar for new perception / manipulation additions. Isaac ROS release numbering (3.x) is separate from Isaac Sim.
