# Omniverse OmniGraph Docs — Live Sources

Curated entry points. Every URL is an HTML URL — apply the `.md` suffix rewrite from `retrieval-rule.md`, with HTML fallback for `/kit/docs/omni.graph/` paths (they 403 on `.md`).

Verified 2026-04-23 against `/latest/`.

---

## Concepts & Getting Started

| Topic | URL | Extraction Prompt |
|---|---|---|
| OmniGraph landing | `https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html` | "Extract what OmniGraph is, the Action Graph vs Push Graph distinction, and the top-level sidebar structure (getting started, interface, node authoring, node library)." |
| Core concepts | `https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph/getting-started/core_concepts.html` | "Extract OmniGraph's core concepts — nodes, attributes, bundles, evaluators, scheduling, evaluation order, dirty propagation." |
| Interface | `https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph/interface.html` | "Extract the OmniGraph editor interface — how to create a graph, add nodes, wire attributes, and inspect evaluation." |

## Python API (HTML fallback — 403 on `.md`)

| Topic | URL | Extraction Prompt |
|---|---|---|
| `omni.graph` landing | `https://docs.omniverse.nvidia.com/kit/docs/omni.graph/latest/index.html` | "Extract `omni.graph.core` / `omni.graph.nodes` / `omni.graph.action` top-level structure. Use HTML fetch — `.md` returns 403." |
| Architecture guide | `https://docs.omniverse.nvidia.com/kit/docs/omni.graph.docs/latest/index.html` | "Extract OmniGraph architecture — evaluator types, graph contexts, push vs action semantics, compute threading. HTML fetch — `.md` returns 403." |
| Action Graph concept | `https://docs.omniverse.nvidia.com/kit/docs/omni.graph.docs/latest/concepts/ActionGraph.html` | "Extract Action Graph semantics — event-driven evaluation, On* trigger nodes, branching / looping patterns. HTML fetch." |

## Node Library

| Topic | URL | Extraction Prompt |
|---|---|---|
| Node library index | `https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph/node-library/node-library.html` | "List the node groups (omni-graph-action, omni-graph-nodes, drivesim-datastudio-base, UI-scene, etc.) with a one-line purpose each. Use as index to drill into specific nodes." |

**Constructing a specific node URL:** pattern is `.../ext_omnigraph/node-library/nodes/<group>/<name>-<version>.html`. Examples in the DriveSim tree: `drivesim-datastudio-base/egodynamics-1.html`, `/egotransform-1.html`, `/camerawwriter-1.html`. Scrape the index to confirm the group name before constructing URLs for novel nodes.

## AnimGraph (built on OmniGraph Action Graph)

| Topic | URL | Extraction Prompt |
|---|---|---|
| AnimGraph extension | `https://docs.omniverse.nvidia.com/extensions/latest/ext_animation-graph.html` | "Extract what AnimGraph is, its relationship to OmniGraph Action Graph, and how character-animation clips are authored as graphs." |
| AnimGraph user guide | `https://docs.omniverse.nvidia.com/extensions/latest/ext_animation-graph/user-guide.html` | "Extract the character-animation authoring workflow — clip loading, state machine, blending." |
| AnimGraph workflow lesson | `https://docs.omniverse.nvidia.com/extensions/latest/ext_animation-graph/lesson_animgraph-workflow.html` | "Extract the step-by-step AnimGraph lesson — loading a character, creating an AnimGraph, adding clips, blending, driving from keyboard events." |
| AnimGraph API | `https://docs.omniverse.nvidia.com/extensions/latest/ext_animation-graph/api.html` | "Extract the AnimGraph Python API surface." |

## Common Pages

| Topic | URL | Extraction Prompt |
|---|---|---|
| Glossary | `https://docs.omniverse.nvidia.com/extensions/latest/common/glossary-of-terms.html` | "Look up the specific term the user asked about." |

---

## Notes on extraction

- `.md` first for pages under `/extensions/latest/ext_omnigraph*`.
- **HTML fallback for `/kit/docs/omni.graph/` and `/kit/docs/omni.graph.docs/`.**
- Node-library URL **pattern**: `…/ext_omnigraph/node-library/nodes/<group>/<name>-<version>.html`.

## Exceptions

- **403 on `.md` for `/kit/docs/omni.graph/`**. HTML works.
- **Isaac Sim robot-specific OG nodes** (differential controllers, ROS 2 bridge, IMU publishers) live in the `isaac-sim` skill, not here.

## Version drift

Catalog targets `/latest/`. Node groups occasionally reorganize — re-scrape the node-library index after major Kit releases.
