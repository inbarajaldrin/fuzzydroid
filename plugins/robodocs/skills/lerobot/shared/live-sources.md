# LeRobot Docs — Live Sources

Curated entry points into HuggingFace LeRobot's documentation. Every URL below is an **HTML URL** — apply the rewrite rule (`append .md`, strip trailing slash) from `retrieval-rule.md` before calling `WebFetch`.

When the user's question points at a slug not listed here, construct `https://huggingface.co/docs/lerobot/<slug>.md` directly. The `<slug>` list is discoverable from the left sidebar of any doc page (see `retrieval-rule.md` for the enumeration command).

Verified against latest (`v0.5.1`) on 2026-04-21.

---

## Get Started

| Topic | URL | Extraction Prompt |
|---|---|---|
| Overview / landing | `https://huggingface.co/docs/lerobot/index` | "Extract the high-level description of LeRobot and the top-level sidebar sections." |
| Installation | `https://huggingface.co/docs/lerobot/installation` | "Extract the pip / source install commands, Python version requirements, and any platform-specific notes." |
| Notebooks | `https://huggingface.co/docs/lerobot/notebooks` | "List the official example notebooks with their purpose and Colab links." |
| Contributing | `https://huggingface.co/docs/lerobot/contributing` | "Extract the contributor workflow — branch conventions, testing requirements, and PR checklist." |
| Backward compatibility | `https://huggingface.co/docs/lerobot/backwardcomp` | "Extract breaking changes between LeRobot versions and migration steps." |

## Tutorials — Imitation Learning & Teleop

| Topic | URL | Extraction Prompt |
|---|---|---|
| IL with real robots (main tutorial) | `https://huggingface.co/docs/lerobot/il_robots` | "Extract the end-to-end flow: teleoperate, record dataset, train policy, evaluate. Include every CLI command." |
| Phone teleop | `https://huggingface.co/docs/lerobot/phone_teleop` | "Extract setup instructions for controlling a LeRobot arm from an iOS/Android phone." |
| HIL data collection | `https://huggingface.co/docs/lerobot/hil_data_collection` | "Extract the human-in-the-loop recording workflow and the data format it produces." |
| HIL-SERL (real robot) | `https://huggingface.co/docs/lerobot/hilserl` | "Extract the HIL-SERL training recipe, including reward labeling and interactive fine-tuning." |
| HIL-SERL in simulation | `https://huggingface.co/docs/lerobot/hilserl_sim` | "Extract sim setup, environment list, and hyperparameters for HIL-SERL in sim." |
| Async inference / RTC | `https://huggingface.co/docs/lerobot/async` | "Extract the async inference architecture and how to enable it at runtime." |
| Real-time control (RTC) | `https://huggingface.co/docs/lerobot/rtc` | "Extract the real-time control loop diagram and latency budget." |

## Policies (algorithms)

| Topic | URL | Extraction Prompt |
|---|---|---|
| ACT (Action Chunking Transformer) | `https://huggingface.co/docs/lerobot/act` | "Extract ACT's architecture summary, default hyperparameters, and the train/eval CLI." |
| SmolVLA | `https://huggingface.co/docs/lerobot/smolvla` | "Extract SmolVLA's model size, input modality (vision-language-action), and fine-tuning recipe." |
| Pi0 | `https://huggingface.co/docs/lerobot/pi0` | "Extract Pi0's policy description, training config, and supported robots." |
| Pi0.5 | `https://huggingface.co/docs/lerobot/pi05` | "Extract what changed in Pi0.5 vs Pi0 and the updated recipe." |
| Pi0-FAST | `https://huggingface.co/docs/lerobot/pi0fast` | "Extract the FAST tokenizer description and how it speeds up Pi0 inference." |
| xVLA | `https://huggingface.co/docs/lerobot/xvla` | "Extract the xVLA policy description and usage." |
| Groot | `https://huggingface.co/docs/lerobot/groot` | "Extract the Groot integration — what it is and how to use it inside LeRobot." |
| Bring your own policy | `https://huggingface.co/docs/lerobot/bring_your_own_policies` | "Extract the interface a custom policy class must implement (forward, select_action, config keys)." |
| Action representations | `https://huggingface.co/docs/lerobot/action_representations` | "Extract the supported action spaces (joint, EE pose, delta, absolute) and how to configure each." |
| Wall-clock loss | `https://huggingface.co/docs/lerobot/walloss` | "Extract what wall-clock loss is and when to enable it." |

## Datasets

| Topic | URL | Extraction Prompt |
|---|---|---|
| LeRobotDataset v3 | `https://huggingface.co/docs/lerobot/lerobot-dataset-v3` | "Extract the v3 schema — keys, chunking, episode layout, metadata fields." |
| Porting datasets to v3 | `https://huggingface.co/docs/lerobot/porting_datasets_v3` | "Extract the migration script usage and field-by-field mapping from v2 to v3." |
| Dataset subtask labeling | `https://huggingface.co/docs/lerobot/dataset_subtask` | "Extract how subtask annotations are stored and used during training." |
| Using dataset tools | `https://huggingface.co/docs/lerobot/using_dataset_tools` | "Extract the CLI commands for inspecting, visualizing, and editing a LeRobotDataset." |
| Streaming video encoding | `https://huggingface.co/docs/lerobot/streaming_video_encoding` | "Extract the supported codecs, ffmpeg flags, and when to use streaming vs pre-encoded video." |
| Rename map | `https://huggingface.co/docs/lerobot/rename_map` | "Extract how to remap feature names between dataset and policy." |

## Hardware — Supported Robots

| Topic | URL | Extraction Prompt |
|---|---|---|
| SO-100 arm | `https://huggingface.co/docs/lerobot/so100` | "Extract BOM, calibration, and first-teleop steps for SO-100." |
| SO-101 arm | `https://huggingface.co/docs/lerobot/so101` | "Extract BOM, calibration, and first-teleop steps for SO-101." |
| Koch arm | `https://huggingface.co/docs/lerobot/koch` | "Extract Koch setup — assembly, driver install, calibration." |
| LeKiwi mobile base | `https://huggingface.co/docs/lerobot/lekiwi` | "Extract LeKiwi's hardware description and teleop setup." |
| Reachy2 | `https://huggingface.co/docs/lerobot/reachy2` | "Extract Reachy2 integration — connection, calibration, teleop." |
| Hope Jr | `https://huggingface.co/docs/lerobot/hope_jr` | "Extract Hope Jr setup and recording instructions." |
| Unitree G1 | `https://huggingface.co/docs/lerobot/unitree_g1` | "Extract Unitree G1 integration steps and safety notes." |
| OpenArm | `https://huggingface.co/docs/lerobot/openarm` | "Extract OpenArm assembly and usage." |
| OMX | `https://huggingface.co/docs/lerobot/omx` | "Extract OMX configuration and teleop flow." |
| Earthrover Mini Plus | `https://huggingface.co/docs/lerobot/earthrover_mini_plus` | "Extract Earthrover Mini Plus setup and supported demos." |
| SARM | `https://huggingface.co/docs/lerobot/sarm` | "Extract SARM description and integration notes." |
| Damiao motors | `https://huggingface.co/docs/lerobot/damiao` | "Extract Damiao driver setup and supported commands." |
| Feetech motors | `https://huggingface.co/docs/lerobot/feetech` | "Extract Feetech motor driver usage — port detection, calibration, torque commands." |
| Cameras | `https://huggingface.co/docs/lerobot/cameras` | "Extract supported camera backends (OpenCV, RealSense, Phone) and configuration examples." |
| Integrate new hardware | `https://huggingface.co/docs/lerobot/integrate_hardware` | "Extract the Robot / Teleop abstract classes to implement when adding a new platform." |

## Integrations — Envs & Benchmarks

| Topic | URL | Extraction Prompt |
|---|---|---|
| EnvHub | `https://huggingface.co/docs/lerobot/envhub` | "Extract what EnvHub is and how to browse / install new envs." |
| EnvHub — Isaac Lab Arena | `https://huggingface.co/docs/lerobot/envhub_isaaclab_arena` | "Extract the Isaac Lab Arena integration usage." |
| EnvHub — LeIsaac | `https://huggingface.co/docs/lerobot/envhub_leisaac` | "Extract the LeIsaac integration usage." |
| Libero | `https://huggingface.co/docs/lerobot/libero` | "Extract how to run Libero benchmarks inside LeRobot." |
| MetaWorld | `https://huggingface.co/docs/lerobot/metaworld` | "Extract MetaWorld integration and task list." |
| Adding benchmarks | `https://huggingface.co/docs/lerobot/adding_benchmarks` | "Extract the interface for adding a new benchmark env." |

## Advanced — Processors, Training, Performance

| Topic | URL | Extraction Prompt |
|---|---|---|
| Processors intro | `https://huggingface.co/docs/lerobot/introduction_processors` | "Extract the processor concept and the lifecycle hooks." |
| Env processor | `https://huggingface.co/docs/lerobot/env_processor` | "Extract how env processors transform observations / actions." |
| Robot + teleop processors | `https://huggingface.co/docs/lerobot/processors_robots_teleop` | "Extract where processors attach on the robot and teleop sides." |
| Implement your own processor | `https://huggingface.co/docs/lerobot/implement_your_own_processor` | "Extract the abstract class contract and a minimal example." |
| Debug processor pipeline | `https://huggingface.co/docs/lerobot/debug_processor_pipeline` | "Extract the debugging tools / logging hooks for processors." |
| Multi-GPU training | `https://huggingface.co/docs/lerobot/multi_gpu_training` | "Extract the accelerate / torchrun launch command and sharding strategy." |
| Multi-task DiT | `https://huggingface.co/docs/lerobot/multi_task_dit` | "Extract the multi-task DiT policy config and dataset layout." |
| PEFT / LoRA fine-tuning | `https://huggingface.co/docs/lerobot/peft_training` | "Extract the PEFT config keys and which policies support LoRA." |
| Torch accelerators | `https://huggingface.co/docs/lerobot/torch_accelerators` | "Extract the supported accelerator backends (cuda, mps, xla) and fallbacks." |

---

## Notes on extraction

- All rows above are **HTML URLs**. Append `.md` before calling WebFetch (see `retrieval-rule.md`).
- Extraction prompts are deliberately specific (e.g., "extract the CLI command", "extract the schema fields"). Generic prompts like "summarize" under-utilize the markdown fidelity.
- When citing back to the user, show the HTML URL — it opens in a browser; the `.md` URL dumps raw text.

## Exceptions

- `index` is the **only** path verified to work with every URL variant (`/index.md`, `/v0.5.1/en/index.md`, `/main/en/index.md`). For all other slugs, only the unversioned `/docs/lerobot/<slug>.md` returns 200.
- If a page 404s on `.md`, WebFetch the HTML URL as a fallback (pattern D for that one page).

## Version drift

The catalog above reflects LeRobot `v0.5.1` (latest as of 2026-04-21). When LeRobot ships a new minor, re-run the sidebar enumeration in `retrieval-rule.md` to pick up new policies / robots; the rewrite rule itself should remain valid.
