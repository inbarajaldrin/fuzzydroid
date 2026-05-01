# Omniverse Replicator Docs — Live Sources

Curated entry points. Every URL is an HTML URL — apply the `.md` suffix from `retrieval-rule.md` before `WebFetch`. HTML fallback on 403.

Verified 2026-04-23 against `/latest/`.

---

## Getting Started

| Topic | URL | Extraction Prompt |
|---|---|---|
| Replicator overview | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html` | "Extract what Replicator is, the core concept (programmatic SDG from USD scenes), the main workflow stages (scene setup → randomization → trigger → annotators → writer), and the sidebar TOC." |
| Getting started | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html` | "Extract the first-run example — minimal Python that spawns objects, randomizes, and writes output." |
| Basic functionalities | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html` | "Extract `rep.create.*`, `rep.modify.*`, `rep.randomizer`, `with rep.trigger.on_frame()`, and `rep.orchestrator` — the core building blocks." |
| APIs with fully developed scenes | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/apis_with_fully_developed_scene.html` | "Extract how to plug Replicator into an existing USD scene (as opposed to programmatic scene construction)." |
| Visualization | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/visualization.html` | "Extract how to visualize randomization / annotator output inside the Kit viewport." |
| Programmatic visualization | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html` | "Extract programmatic visualization APIs for debugging SDG runs." |

## Randomizers

| Topic | URL | Extraction Prompt |
|---|---|---|
| Randomizer details | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html` | "Extract `rep.randomizer.*` built-ins — color / rotation / texture / material / scatter / light — and the custom-randomizer authoring contract." |
| Distribution examples | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html` | "Extract the `rep.distribution.*` surface (uniform, normal, choice, sequence) with examples." |
| Advanced scattering | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/advanced_scattering.html` | "Extract scatter-on-surface / scatter-in-volume / physics-aware scattering usage." |
| Physics example | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/physics_example.html` | "Extract how to integrate Replicator with PhysX (drop objects, settle, then capture)." |
| Shrubs / worker example | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html` | "Extract the canonical vegetation-scattering example and worker-distribution pattern." |
| Camera examples | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html` | "Extract multi-camera setups, camera randomization, and frustum-aware positioning." |
| Subframes | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/subframes_examples.html` | "Extract subframe usage for motion blur / temporal supersampling." |

## Annotators (output label types)

| Topic | URL | Extraction Prompt |
|---|---|---|
| Annotator details (pointer page) | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotators_details.html` | "This page is a brief pointer — it tells you to go to the Replicator API's Default Annotators section. Extract the link it provides and follow it to the actual annotator catalog below." |
| **Default Annotators API** (the real annotator catalog) | `https://docs.omniverse.nvidia.com/py/replicator/latest/source/extensions/omni.replicator.core/docs/API.html#default-annotators` | "List every built-in annotator (rgb / depth / normals / semantic_segmentation / instance_segmentation / bounding_box_2d_tight / bounding_box_2d_loose / bounding_box_3d / pose / occlusion / distance_to_camera / distance_to_image_plane / skeleton_data / motion_vectors). For each: output format, shape, and typical downstream use. HTML fetch (`.md` returns 403 on /py/replicator/ paths)." |
| Annotations with transparency | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotations_with_transparency.html` | "Extract how annotators handle transparent / glass / alpha-mask geometry." |
| Semantics schema editor | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html` | "Extract how to apply semantic labels to USD prims so segmentation annotators produce correct output." |

## Writers

| Topic | URL | Extraction Prompt |
|---|---|---|
| Writer examples | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html` | "Extract the built-in writers (BasicWriter, KittiWriter, COCOWriter, PoseWriter, YoloWriter) with example usage." |
| Custom writer | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html` | "Extract the Writer class contract — `initialize`, `write`, `attach_to`, `detach` — and how to register a custom writer." |

## Augmentation & IO

| Topic | URL | Extraction Prompt |
|---|---|---|
| Augmentation examples | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html` | "Extract post-capture augmentation recipes (noise, blur, color jitter) applied to Replicator output." |
| IO guidelines | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/io_guidelines.html` | "Extract the expected directory layout for Replicator output, throughput tips, and cloud-storage considerations." |
| Using existing assets | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/using_existing_assets.html` | "Extract how to bring external USD / glTF / FBX assets into a Replicator run." |
| Replicator materials | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_materials.html` | "Extract OmniPBR / MDL material randomization patterns in Replicator." |
| Using layers | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_using_layers.html` | "Extract how to isolate Replicator modifications on their own USD layer (so the base scene stays clean)." |

## Headless / Container / AWS

| Topic | URL | Extraction Prompt |
|---|---|---|
| Headless example | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html` | "Extract the headless CLI invocation, `--no-window`, and how to run Replicator with no GUI." |
| Container setup | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html` | "Extract the Docker container image, mount patterns for input/output, and GPU passthrough flags." |
| AWS setup | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html` | "Extract AWS EC2 instance types (G5/G6), AMI choice, and the Siemens-style scaling pattern." |

## YAML Workflow

| Topic | URL | Extraction Prompt |
|---|---|---|
| YAML workflow | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html` | "Extract the YAML declarative SDG workflow — when to use it instead of the Python API." |
| YAML manual | `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_manual.html` | "Extract the YAML schema — every top-level key with its purpose and nested structure." |

## Python API (use HTML fallback — `.md` is 403)

| Topic | URL | Extraction Prompt |
|---|---|---|
| `omni.replicator.core` landing | `https://docs.omniverse.nvidia.com/py/replicator/latest/index.html` | "Extract the top-level `omni.replicator.core` modules (rep.create, rep.modify, rep.randomizer, rep.trigger, rep.orchestrator, rep.writers_default). Use HTML fetch — .md returns 403." |

---

## Notes on extraction

- `.md` URL first. Fall back to HTML for `/py/replicator/` paths.
- Cite HTML URL back to the user.
- Replicator pages often contain complete Python examples — extract the full snippet when the user wants to run it.

## Exceptions

- **`/py/replicator/` returns 403 on `.md`** — HTML fallback.
- **Isaac Sim's `isaacsim.replicator`** is a separate robot-aware wrapper — use the `isaac-sim` skill, not this one.

## Version drift

Catalog targets `/extensions/latest/`. Replicator versions move with Kit minor releases. Re-enumerate sub-pages after each release to pick up new annotators / writers.
