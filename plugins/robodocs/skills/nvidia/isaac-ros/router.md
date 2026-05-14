# Isaac ROS Docs

Reliable live access to NVIDIA Isaac ROS documentation at `https://nvidia-isaac-ros.github.io/`.

## When to use this sub-skill

Trigger on: NVIDIA Isaac ROS (CUDA-accelerated ROS 2 packages), `isaac_ros_*` packages, NITROS zero-copy transport, cuVSLAM (visual SLAM), cuVGL (visual global localization), Nvblox (occupancy mapping / scene reconstruction), cuMotion on ROS 2 (+ MoveIt integration), FoundationPose / CenterPose / DOPE (pose estimation), RT-DETR / YOLOv8 / Grounding DINO (object detection), Segformer / Segment Anything / U-Net (segmentation), ESS / SGM / FoundationStereo (stereo depth), AprilTag fiducials on ROS, Isaac Mission Client / Mission Dispatch (cloud control), Jetson deployment of ROS packages, DNN Inference with TensorRT / Triton on ROS, Isaac Sim ↔ ROS 2 bridge (via NITROS Bridge), Isaac for Manipulation / Isaac for Mobility reference workflows. Also triggers on adjacent use: Nova Carter with Isaac ROS, Jetson Orin as the compute for Isaac ROS packages, and sim-to-real testing where Isaac Sim feeds synthetic data through the same NITROS pipeline deployed on-robot.

## Why this skill exists

Isaac ROS is NVIDIA's collection of CUDA-accelerated ROS 2 packages for on-robot deployment — visual SLAM (cuVSLAM), occupancy mapping (Nvblox), motion planning (cuMotion + MoveIt), foundation-model perception (FoundationPose, FoundationStereo, Grounding DINO, Segment Anything), and zero-copy transport (NITROS). Package coverage and naming shifts between releases, and the Isaac Sim ↔ real-robot bridge is fiddly. Live docs keep recommendations grounded.

## The retrieval rule

Pattern D — **plain HTML, WebFetch the URL directly.** GitHub Pages serves the full Sphinx-rendered HTML.

| HTML URL | Fetch URL |
|---|---|
| `https://nvidia-isaac-ros.github.io/` | same |
| `https://nvidia-isaac-ros.github.io/concepts/visual_slam/cuvslam/index.html` | same |
| `https://nvidia-isaac-ros.github.io/concepts/scene_reconstruction/nvblox/index.html` | same |

## HTML exceptions

- **`.md` suffix returns 404.**
- **No sitemap** — use sidebar scraping.
- **Per-package release notes** live at `https://nvidia-isaac-ros.github.io/release_notes/<package>.html`; URL patterns are consistent.

## Workflow

1. Classify — which capability? Perception (detection / segmentation / pose / stereo), SLAM / localization (cuVSLAM / cuVGL), mapping (Nvblox), manipulation (cuMotion + MoveIt, isaac_grasp, pick_and_place), transport (NITROS), cloud control (Mission Client / Dispatch), or DNN inference (TensorRT / Triton).
2. Look up in `references/live-sources.md`. Each capability usually has an `index.html` overview + per-model / per-sensor tutorials.
3. `WebFetch` the HTML URL directly.
4. For Isaac Sim testing of an Isaac ROS package, use the `tutorial_isaac_sim.html` page for that capability (common across perception/SLAM/mapping docs).
5. If the user is asking about robot simulation (not ROS-deploy), route to `isaac-sim`.
6. Cite the HTML URL.

## Reference files

- `references/live-sources.md` — curated entry points: Getting Started · Perception (detection / segmentation / pose / stereo / fiducials) · SLAM & Localization · Scene Reconstruction (Nvblox) · Manipulation (cuMotion + MoveIt) · NITROS Transport · DNN Inference · Cloud Control · Isaac Sim Integration · Getting Started on Jetson.
- `references/retrieval-rule.md` — Pattern D rule + verification.

## Common pitfalls

- **NITROS vs NITROS Bridge.** NITROS = zero-copy transport for ROS 2 messages on NVIDIA HW. NITROS Bridge = connector between Isaac Sim and real ROS 2 nodes. Don't conflate.
- **`tutorial_isaac_sim.html` pages are load-bearing.** Almost every perception / SLAM capability has a sim-first tutorial. Start there when the user wants to try before deploying.
- **MoveIt integration is version-pinned.** cuMotion + MoveIt works against specific ROS 2 distros / MoveIt versions. Check the current support matrix.
- **FoundationPose needs a mesh.** Custom objects require `.obj` / USD meshes. Route to the `tutorial_create_your_own_mesh.html` page.
- **Jetson vs x86.** Some packages are optimized for Jetson (aarch64); confirm target compute before recommending.
- **Isaac ROS packages are separate from Isaac Sim packages.** `isaacsim.ros2.bridge` in Isaac Sim publishes to ROS 2; Isaac ROS consumes from ROS 2 on-robot. They meet in the middle (via NITROS Bridge) but are different codebases / docs.
- **Release cadence is fast.** The capability index in `live-sources.md` may miss new packages — scrape the sidebar when in doubt.
