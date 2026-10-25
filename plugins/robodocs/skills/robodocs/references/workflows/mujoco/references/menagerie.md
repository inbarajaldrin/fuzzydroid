# MuJoCo Menagerie — robot model catalog

The Menagerie is DeepMind's curated zoo of high-quality MJCF models. Each robot lives in its own directory under `https://github.com/google-deepmind/mujoco_menagerie/tree/main/<dir>`.

This list is current as of MuJoCo Menagerie's `main` branch. When a user names a robot, route them to the directory and its README; the raw MJCF is at `<dir>/<robot>.xml`.

| Robot | Category | Directory | Raw model |
|---|---|---|---|
| Franka Emika Panda | Arm | `franka_emika_panda/` | `franka_emika_panda/panda.xml` |
| Franka FR3 | Arm | `franka_fr3/` | `franka_fr3/fr3.xml` |
| Universal Robots UR5e | Arm | `universal_robots_ur5e/` | `universal_robots_ur5e/ur5e.xml` |
| Universal Robots UR10e | Arm | `universal_robots_ur10e/` | `universal_robots_ur10e/ur10e.xml` |
| Kinova Gen3 | Arm | `kinova_gen3/` | `kinova_gen3/gen3.xml` |
| Kuka iiwa14 | Arm | `kuka_iiwa_14/` | `kuka_iiwa_14/iiwa14.xml` |
| Rethink Sawyer | Arm | `rethink_robotics_sawyer/` | varies |
| ABB IRB 1600 | Arm | `abb_irb1600/` | `abb_irb1600/irb1600_6_12.xml` |
| Trossen ViperX | Arm | `trossen_vx300s/` | varies |
| Shadow Hand E3M5 | Hand | `shadow_hand/` | `shadow_hand/right_hand.xml` |
| Shadow Dexterous Hand (DexHand) | Hand | `shadow_dexee/` | varies |
| Wonik Allegro Hand | Hand | `wonik_allegro/` | `wonik_allegro/right_hand.xml` |
| LEAP Hand | Hand | `leap_hand/` | varies |
| Robotiq 2F-85 gripper | Gripper | `robotiq_2f85/` | `robotiq_2f85/2f85.xml` |
| Robotiq 2F-85 V4 | Gripper | `robotiq_2f85_v4/` | varies |
| Boston Dynamics Spot | Quadruped | `boston_dynamics_spot/` | `boston_dynamics_spot/spot.xml` |
| ANYbotics ANYmal B | Quadruped | `anybotics_anymal_b/` | `anybotics_anymal_b/anymal_b.xml` |
| ANYbotics ANYmal C | Quadruped | `anybotics_anymal_c/` | `anybotics_anymal_c/anymal_c.xml` |
| Unitree A1 | Quadruped | `unitree_a1/` | `unitree_a1/a1.xml` |
| Unitree Go1 | Quadruped | `unitree_go1/` | `unitree_go1/go1.xml` |
| Unitree Go2 | Quadruped | `unitree_go2/` | `unitree_go2/go2.xml` |
| Google Barkour vB | Quadruped | `google_barkour_vb/` | `google_barkour_vb/barkour_vb.xml` |
| Google Barkour v0 | Quadruped | `google_barkour_v0/` | `google_barkour_v0/barkour_v0.xml` |
| Unitree H1 | Humanoid | `unitree_h1/` | `unitree_h1/h1.xml` |
| Unitree G1 | Humanoid | `unitree_g1/` | `unitree_g1/g1.xml` |
| Berkeley Humanoid | Humanoid | `berkeley_humanoid/` | varies |
| Robotis OP3 | Humanoid | `robotis_op3/` | `robotis_op3/op3.xml` |
| Agility Cassie | Bipedal | `agility_cassie/` | `agility_cassie/cassie.xml` |
| PAL Talos | Humanoid | `pal_talos/` | varies |
| Booster T1 | Humanoid | `booster_t1/` | varies |
| Apptronik Apollo | Humanoid | `apptronik_apollo/` | varies |
| Fourier GR-1 | Humanoid | `fourier_gr1/` | varies |
| Aloha (bimanual) | Multi-arm | `aloha/` | `aloha/aloha.xml` |
| Bitcraze Crazyflie 2 | Drone | `bitcraze_crazyflie_2/` | `bitcraze_crazyflie_2/cf2.xml` |
| Skydio X2 | Drone | `skydio_x2/` | `skydio_x2/x2.xml` |
| Realsense D435i | Sensor | `realsense_d435i/` | depth-camera asset for embedding |
| Hello Robot Stretch 3 | Mobile manipulator | `hello_robot_stretch_3/` | varies |
| Hello Robot Stretch (orig) | Mobile manipulator | `hello_robot_stretch/` | varies |
| Google Robot | Mobile manipulator | `google_robot/` | varies |

> **Source of truth**: `gh api repos/google-deepmind/mujoco_menagerie/contents | jq '.[] | select(.type=="dir") | .name'` will list every robot directory currently on `main`. The Menagerie expands roughly quarterly — re-run this when a user names a robot not on the table above.

## Per-robot fetch pattern

```bash
# README
curl -s "https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/<dir>/README.md"

# MJCF (find the exact filename via gh api contents on the dir)
gh api repos/google-deepmind/mujoco_menagerie/contents/<dir> --jq '.[] | select(.name | endswith(".xml")) | .name'

# Scene XML (includes lighting, ground, camera)
curl -s "https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/<dir>/scene.xml"
```

Most directories also include a `scene.xml` (the model embedded in a complete usable scene), `LICENSE`, and asset files (meshes in `assets/`).
