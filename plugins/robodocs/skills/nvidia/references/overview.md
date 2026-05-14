# NVIDIA Physical-AI Stack — Overview

The hierarchy, cross-skill relationships, and routing principle behind this suite.

---

## The tree (ground truth, 2026)

```
OpenUSD (Pixar / Linux Foundation — foundation, not NVIDIA)
  └── used by everything below

NVIDIA Omniverse ─────────────────┐   NVIDIA Isaac ─────────────────┐   NVIDIA Cosmos
  Platform/SDK for 3D + sim       │   Robotics platform             │   World foundation
  • Kit (app framework)           │   • Isaac Sim    (simulator)    │   models (generative
  • ovrtx / ovphysx / ovstorage   │   • Isaac Lab    (RL / IL)      │    video for physical AI)
    (standalone libs, 2025+)      │   • Isaac ROS    (ROS 2 GPU)    │
  • Replicator (Kit extension)    │   • Isaac GR00T  (humanoid FMs) │
  • OmniGraph (Kit extension)     │                                 │
                                  │                                 │

NVIDIA Warp — standalone Python GPU framework, used across Omniverse / Isaac / external
```

## Three non-obvious facts

1. **Isaac is a peer to Omniverse, not a child.** Separate developer portal (`developer.nvidia.com/isaac` vs `nvidia.com/en-us/omniverse`), separate GitHub org (`isaac-sim/*` vs Omniverse extensions), separate release cadence. Isaac *uses* Omniverse, but it's a peer product line.
2. **OpenUSD is not NVIDIA-owned.** It's the Linux Foundation AOUSD standard (originally Pixar). Used by Omniverse, Apple RealityKit, Houdini, Maya, Blender, Unreal, and many VFX/CAD pipelines. An openusd skill should answer cross-ecosystem questions, not just NVIDIA ones.
3. **Warp is standalone.** Not an Omniverse component. Ships as a Kit extension AND as a pip package. Used in Isaac Lab (reward/observation kernels), Newton physics engine, and many projects with no NVIDIA stack at all.

## The routing principle

> **The parent skill owns the general tool. The product skill owns its own wrapped surface of that tool.**

Every general tool has a parent skill. Every product that re-exposes that tool in a domain-specific way owns those wrappers **inside its own skill**. This keeps boundaries clean and prevents skill overlap.

### Applied examples

| General (parent skill) | Product-specific wrapper (product skill) |
|---|---|
| `openusd` — USD Python API, layers, composition | `isaac-sim` → `isaacsim.core.utils.stage` (robot-stage USD helpers) |
| `omniverse-replicator` — randomizers, annotators, writers (generic CV) | `isaac-sim` → `isaacsim.replicator` (sensor-aware robotic SDG) |
| `omniverse-omnigraph` — Action/Push graphs, node authoring | `isaac-sim` → differential / holonomic controllers, ROS bridge, sensor publishers |
| `omniverse-kit` — Kit SDK, Carbonite, extension.toml | (Isaac Sim is a Kit app; kit-level questions go up; Isaac-specific extensions stay in isaac-sim) |
| `nvidia-warp` — `@wp.kernel`, autograd | `isaac-lab` → Lab-specific reward / observation kernels, env-step kernels |

### Cross-skill routing examples

- User says "use Replicator to label images of a Franka arm" → **`isaac-sim`** (robot context) — the `isaacsim.replicator` wrapper lives there.
- User says "use Replicator for PCB defect detection" → **`omniverse-replicator`** (generic CV context).
- User says "USD composition arcs — references vs payloads" → **`openusd`** (pure USD, any context).
- User says "load a URDF into Isaac Sim and check its USD stage" → **`isaac-sim`** (the Isaac-side stage utilities) with a pointer to `openusd` for composition details.
- User says "write a reward in Warp for Isaac Lab" → **`nvidia-warp`** (kernel authoring) + **`isaac-lab`** (where it plugs in).

## Retrieval patterns used across the suite

| Pattern | Mechanism | Sub-skills |
|---|---|---|
| **A — `.md` suffix** | Append `.md` to `.html` URL; site serves native markdown | `omniverse-kit`, `omniverse-replicator`, `omniverse-omnigraph` |
| **A — raw markdown** | Use `raw.githubusercontent.com` or `huggingface.co/.../raw/` | `isaac-groot`, `nvidia-cosmos` |
| **B — Discourse JSON API** | Append `.json` to any forum URL; get structured topic / search / category data | `nvidia-forums` |
| **D — plain HTML** | WebFetch the HTML URL directly (Sphinx / custom server-rendered) | `openusd`, `nvidia-warp`, `isaac-sim`, `isaac-lab`, `isaac-ros` |

**No sub-skill uses Pattern C (embedded JSON in HTML).** Only `nvidia-forums` is Pattern B — it's the only skill with a `references/schema.md` file documenting the structured response shape. Each sub-skill's `references/retrieval-rule.md` documents verified probe commands and the rewrite rule specific to its source.

## Why two peer-platform docs sites behave differently

Both `docs.omniverse.nvidia.com` and `docs.isaacsim.omniverse.nvidia.com` are Sphinx-rendered NVIDIA sites under the same corporate infra, but:

- `docs.omniverse.nvidia.com` — serves `text/markdown` when you append `.md` to any `.html` URL (with some 403 gaps under `/kit/docs/<ext>/` paths).
- `docs.isaacsim.omniverse.nvidia.com` — returns 404 for `.md` on every page tested. Only the rendered HTML is exposed.

This is why each sub-skill probes its own site and documents its own rule. Don't assume siblings behave the same.

## Cross-references to sibling skills outside this suite

- **`lerobot`** — HuggingFace LeRobot. LeRobotDataset v3 is the dataset format used by Isaac GR00T and increasingly by Isaac Lab Mimic. When the user asks about dataset format in any of those contexts, cross-ref lerobot.

## The forums sub-skill — why it's shaped differently from the others

All ten product sub-skills in this suite wrap **official documentation** for one product. `nvidia-forums` is the only one that wraps **community Q&A** and covers all NVIDIA products at once (CUDA, TensorRT, Jetson, DRIVE, etc.) — not just Omniverse / Isaac / Cosmos.

Why it's separate rather than folded into each product skill:

- **Shared infrastructure.** All NVIDIA forums run on one Discourse instance. One skill, one retrieval rule, one schema file.
- **Different content shape.** Product-docs skills catalog stable entry-point URLs. The forums skill catalogs **categories** and teaches the agent to **search-first** — forum content is query-driven, not URL-driven.
- **Covers gaps.** Cross-product compatibility questions, "is this a known issue", staff corrections of stale docs — these live in forums but not in product docs. The forums skill is the fallback when product docs don't cover a user's specific situation.
- **Different retrieval pattern.** Discourse's JSON API (Pattern B) is structurally different from the `.md` suffix / plain HTML patterns used elsewhere. Putting it in its own skill keeps the schema file contained.

## Maintenance

Each sub-skill's `retrieval-rule.md` has a **verification date** and **re-probe commands**. When re-validating the suite:

1. Re-run `retrieval-rule.md` probes in each sub-skill.
2. Re-scrape sidebars to find new pages.
3. Update the verification date.
4. If a retrieval rule changes (e.g., NVIDIA adds `.md` to Isaac Sim's subdomain), update the rule + live-sources accordingly.

For the meta-router itself (this file and `SKILL.md`), update when:

- NVIDIA adds a new peer product (next to Omniverse / Isaac / Cosmos) or a new sub-product under an existing platform.
- The routing table needs new keywords (new product line, new terminology).
- The hierarchy shifts (e.g., Isaac Sim moves fully off Kit to unbundled libs).

Last verified: 2026-04-23.
