---
name: nvidia
description: Meta-router over the NVIDIA Physical-AI stack — use whenever the user mentions OpenUSD / USD / `.usd` / `.usda` / `.usdc` / `.usdz`, NVIDIA Warp (`@wp.kernel`, GPU Python), Omniverse (Kit / ovrtx / ovphysx / XR / CloudXR / Vision Pro), Replicator (synthetic data generation), OmniGraph (Action / Push / AnimGraph), Isaac Sim (SimulationApp, URDF/MJCF import, sensors, cuMotion), Isaac Lab (RL/IL — rsl_rl / rl_games / skrl / sb3), Isaac ROS (CUDA-accelerated ROS 2 — cuVSLAM, Nvblox, FoundationPose, NITROS), Isaac GR00T (humanoid foundation models — N1 / N1.5 / Mimic), NVIDIA Cosmos (world foundation models), the NVIDIA NGC Catalog (`catalog.ngc.nvidia.com` / `nvcr.io` — container tags, manifests, hosted models, `docker pull nvcr.io/...`), or the NVIDIA Developer Forums (community Q&A across every NVIDIA product — CUDA / TensorRT / Jetson / DRIVE). Routes to the right sub-skill. Trigger liberally — NVIDIA's ecosystem evolves monthly; always consult live docs, NGC tags, or forum threads.
---

# NVIDIA Suite Docs — Meta Router

Meta-router over the NVIDIA Physical-AI stack. Twelve sub-skills, each a standalone docs / catalog wrapper for one surface. Use this skill to (a) figure out which sub-skill a user's question belongs to, (b) hand off multi-product questions, and (c) explain the hierarchy.

## How to use sub-skills (read this first)

**Sub-skills are subdirectories of this skill, NOT separately-registered skills.** The Skill tool only knows about `robodocs:nvidia` as a whole. Trying to invoke a sub-skill directly will fail:

```
Skill(robodocs:nvidia:isaac-sim)   ← ✗ Returns "Unknown skill"
Skill(isaac-sim)                   ← ✗ Returns "Unknown skill"
```

**Load sub-skills via the `Read` tool** on their files, treating them as reference material under this skill (progressive disclosure):

```
Read  <this-skill-path>/isaac-sim/router.md            ← sub-skill's description + workflow
Read  <this-skill-path>/isaac-sim/references/live-sources.md   ← curated URL catalog
Read  <this-skill-path>/isaac-sim/references/retrieval-rule.md ← rewrite rule (Pattern A/B/C/D)
Read  <this-skill-path>/isaac-sim/references/schema.md     ← Pattern B only (nvidia-forums has one)
```

Each sub-skill directory has the same 3-4 file shape: `router.md` (the product-specific description, workflow, and pitfalls — a plain markdown reference file, NOT a registered skill), `references/live-sources.md`, `references/retrieval-rule.md`, and `references/schema.md` (only sub-skills that consume a structured response shape — `nvidia-forums` and `nvidia-ngc`). Once you've Read the sub-skill's `live-sources.md`, apply its retrieval rule (`WebFetch` for HTML/markdown patterns, `Bash` with `curl` for the structured Docker Registry v2 + Discourse JSON patterns).

**Never guess URLs.** If the user's topic isn't covered in the sub-skill's `live-sources.md`, scrape the site's sidebar (per the sub-skill's `retrieval-rule.md`) or `WebSearch` for the canonical path. Do not fabricate URLs from training memory — the NVIDIA docs sites return 403 (not 404) for nonexistent paths, which makes dead-reckoning failures silent.

## The suite

```
skills/nvidia/
├── SKILL.md                    ← you are here
├── references/
│   └── overview.md             ← the hierarchy + routing principle
├── openusd/                    ← Pixar USD (foundation, not NVIDIA-owned)
├── nvidia-warp/                ← GPU Python framework (standalone)
├── omniverse-kit/              ← Omniverse app framework + unbundled libs
├── omniverse-replicator/       ← Synthetic data generation
├── omniverse-omnigraph/        ← Visual compute / action graphs
├── isaac-sim/                  ← Robotics simulator
├── isaac-lab/                  ← RL / IL on Isaac Sim
├── isaac-ros/                  ← CUDA-accelerated ROS 2 packages
├── isaac-groot/                ← Humanoid foundation models
├── nvidia-cosmos/              ← World foundation models (generative)
├── nvidia-ngc/                 ← NGC Catalog + nvcr.io Container Registry (containers / models / collections)
└── nvidia-forums/              ← NVIDIA Developer Forums (community Q&A, Discourse JSON)
```

## The hierarchy (why skills are organized this way)

Three peer platforms, with OpenUSD underneath and Warp off to the side:

- **OpenUSD** (Linux Foundation / Pixar) — the 3D scene format every Omniverse / Isaac product is built on. Not NVIDIA-owned.
- **NVIDIA Omniverse** — platform/SDK for 3D apps. Contains Kit, Replicator, OmniGraph. Unbundling into libraries (`ovrtx` / `ovphysx` / `ovstorage`) since 2025.
- **NVIDIA Isaac** — robotics **peer** platform (not a sub of Omniverse, despite using it). Contains Isaac Sim, Isaac Lab, Isaac ROS, Isaac GR00T.
- **NVIDIA Cosmos** — generative world models. Peer to Omniverse.
- **NVIDIA Warp** — standalone GPU Python framework. Used by Omniverse (as extension), Isaac Lab (reward / observation kernels), and many non-NVIDIA projects.

See `references/overview.md` for the full tree and the "parent skill owns the general tool, product skill owns its wrapped surface" routing principle.

## Routing table — pick the right sub-skill

| User said / is doing… | Sub-skill |
|---|---|
| `.usd` / `.usda` / stages / prims / references / payloads / LIVRPS / schemas (UsdLux / UsdGeom / UsdShade) / Pixar | **openusd** |
| `@wp.kernel` / GPU Python kernel / differentiable physics / tile primitives / autograd tape | **nvidia-warp** |
| `extension.toml` / Kit app / Carbonite / `carb.*` / `ovrtx` / `ovphysx` / `ovstorage` / building an Omniverse extension | **omniverse-kit** |
| Synthetic data / SDG / domain randomization / `rep.*` / annotators / writers (for non-robotics or generic CV) | **omniverse-replicator** |
| Action Graph / Push Graph / AnimGraph / OG nodes / visual compute graphs | **omniverse-omnigraph** |
| `SimulationApp` / robotics simulator / URDF or MJCF import / sensors / cuMotion / Isaac Sim controllers / `isaacsim.*` Python | **isaac-sim** |
| RL / PPO / SAC / parallel envs / Manager-Based vs Direct / rsl_rl / rl_games / skrl / sb3 / Hydra configs / Isaac Lab Mimic | **isaac-lab** |
| ROS 2 / NITROS / cuVSLAM / Nvblox / MoveIt + cuMotion / FoundationPose / Isaac ROS packages | **isaac-ros** |
| GR00T (N1 / N1.5 / Mimic / Dreams) / humanoid foundation models / retargeting | **isaac-groot** |
| Cosmos / generative video / world foundation models / cosmos-predict / -transfer / -reason / -rl | **nvidia-cosmos** |
| NGC / NGC Catalog / `catalog.ngc.nvidia.com` / `nvcr.io` / container tag lookup / "latest tag of X" / `docker pull nvcr.io/...` / hosted models on NGC / Helm charts / collections / NGC CLI / image labels (`com.nvidia.*`) | **nvidia-ngc** |
| "forum" / "forums" / community post / thread / known issue / workaround / "has anyone solved" / NVIDIA staff reply / cross-product compatibility question that docs miss | **nvidia-forums** |

## Multi-product questions

When a user's question spans multiple sub-skills, consult each in sequence:

- **"End-to-end: train in Isaac Lab, test in Isaac Sim, deploy via Isaac ROS"** → isaac-lab → isaac-sim → isaac-ros
- **"Generate synthetic data in Isaac Sim for a vision model, train, deploy"** → omniverse-replicator (or isaac-sim if using robot-wrapped SDG) → isaac-ros
- **"Humanoid fine-tune: GR00T + Isaac Lab + dataset format"** → isaac-groot → isaac-lab → `lerobot` (sibling skill in robodocs) for dataset
- **"Sim-to-real with Cosmos-generated video"** → nvidia-cosmos → isaac-sim → isaac-ros
- **"Write a Warp kernel that runs inside Isaac Lab"** → nvidia-warp (kernel) → isaac-lab (where it plugs in)
- **"Can I use product A with product B?"** (cross-product compatibility, often poorly covered in official docs) → the matching product skills for docs coverage, PLUS nvidia-forums for community Q&A and staff clarifications
- **"Is this a known issue / has anyone solved X?"** → nvidia-forums first, then the product skill for the current API / state
- **"What container should I pull for X?"** → nvidia-ngc (current tag + manifest) → the matching product skill for usage docs
- **"Is there a model checkpoint on NGC for X?"** → nvidia-ngc (sitemap-discovery) → the matching product skill for how to consume it (and `lerobot` if the dataset/checkpoint is mirrored on HuggingFace)
- **"Why is my `docker pull` saying unauthorized?"** → nvidia-ngc (probe whether the repo is anonymous-pullable or NVAIE-gated) → nvidia-forums for community context

## The routing principle — "parent skill owns the general tool, product skill owns its wrapped surface"

Every general tool has a parent skill. Every product that re-exposes that tool in a domain-specific way owns those wrappers **inside its own skill**.

| General (parent skill owns) | Wrapped (product skill owns) |
|---|---|
| `openusd` — USD API, composition, layers | `isaac-sim` → `isaacsim.core.utils.stage` (USD helpers for robot stages) |
| `omniverse-replicator` — randomizers, writers (any CV domain) | `isaac-sim` → `isaacsim.replicator` (robot-aware sensor writers) |
| `omniverse-omnigraph` — Action/Push graphs, node authoring | `isaac-sim` → robot-specific OG nodes (diff controllers, ROS bridge, sensor publishers) |
| `nvidia-warp` — `@wp.kernel`, autograd | `isaac-lab` → Lab-specific Warp reward / observation kernels |

So a question like "Replicator randomization for a Franka arm in Isaac Sim" routes to `isaac-sim` (robot-wrapped SDG), not `omniverse-replicator` (generic SDG). A question like "Replicator for PCB defect images" routes to `omniverse-replicator`.

## Shared retrieval patterns across the suite

| Pattern | Sub-skills using it |
|---|---|
| **A — `.md` suffix** (Omniverse docs site) | omniverse-kit · omniverse-replicator · omniverse-omnigraph |
| **A — raw markdown** (GitHub + HuggingFace) | isaac-groot · nvidia-cosmos |
| **B — Discourse JSON API** | nvidia-forums |
| **D — plain HTML** | openusd · nvidia-warp · isaac-sim · isaac-lab · isaac-ros |
| **E — Docker Registry v2 + sitemap** (anonymous `nvcr.io` token flow) | nvidia-ngc |

No sub-skill uses Pattern C (embedded JSON in HTML). Details per sub-skill live in each one's `references/retrieval-rule.md`. The two sub-skills with a `references/schema.md` file are the ones that consume structured response shapes: `nvidia-forums` (Discourse JSON — topic / search / category) and `nvidia-ngc` (Docker Registry v2 — token / tags / manifest v1+prettyjws + sitemap XML).

## Workflow

1. Parse the user's question for domain keywords (see routing table above).
2. If it's single-domain: `Read` the matching sub-skill's `router.md`, then `Read` its `references/live-sources.md`, apply the retrieval rule, `WebFetch` the URL. Do NOT use `Skill(...:...)` syntax — see "How to use sub-skills" above.
3. If it's multi-product, step through sub-skills in logical order (from general → specific, or training → sim → deploy) — reading each sub-skill's files as you go.
4. If the question is about the **relationship** between products ("what's the difference between Omniverse and Isaac Sim?"), answer from `references/overview.md` directly without fetching.
5. Cite the HTML URL of the source, per each sub-skill's convention.

## Reference files

- `references/overview.md` — the hierarchy, cross-skill relationships, and the general-vs-wrapped routing principle with examples.
- Twelve sub-skills, each self-contained with its own `router.md` + `references/live-sources.md` + `references/retrieval-rule.md` + `evals/evals.json` (plus `references/schema.md` for the two sub-skills that consume structured response shapes — `nvidia-forums` and `nvidia-ngc`).

## Common pitfalls

- **Don't use `Skill(robodocs:nvidia:<sub>)` or `Skill(<sub>)` syntax.** Sub-skills are directories, not registered skills. Load them via `Read`. This is the #1 failure mode — when the agent gets "Unknown skill" it silently falls back to guessing URLs from training memory, hitting 403/404s because it never loads the curated catalog.
- **Isaac Sim ≠ Omniverse.** They're peer platforms. Isaac *uses* Omniverse but has its own GitHub org, developer portal, release cadence.
- **Isaac Sim's docs site (`docs.isaacsim.omniverse.nvidia.com`) is NOT the same as the Omniverse docs site (`docs.omniverse.nvidia.com`)**, even though the subdomain suggests otherwise. The former uses plain HTML; the latter supports the `.md` suffix.
- **Routing the wrong Replicator question to the wrong skill is a common error.** Robot-flavored → isaac-sim. Anything else → omniverse-replicator.
- **GR00T training is on Isaac Lab, dataset format is LeRobotDataset.** For humanoid training questions, expect to hit isaac-groot + isaac-lab + `lerobot` (sibling skill in robodocs).
- **Cosmos is generative; Omniverse Replicator is deterministic.** Both produce training data, but through different mechanisms.
- **Warp is not Omniverse-specific.** Don't route Warp questions to omniverse-kit — they go to nvidia-warp.
- **`catalog.ngc.nvidia.com` ≠ `nvcr.io`.** The first is the browse UI (Next.js CSR — HTML is uninspectable); the second is the Container Registry (Docker Registry v2 — anonymous-queryable). When a user asks "what's on NGC", route to `nvidia-ngc` and use the registry, not WebFetch against the catalog HTML.
- **NGC container tags drift weekly.** A docs page saying "use `nvcr.io/nvidia/isaac-sim:4.5.0`" can be stale within days. For "what's the latest" questions, route to `nvidia-ngc` to probe the registry — don't quote tag names from product docs.
- **NGC hosted models are NOT Docker images.** They live behind `api.ngc.nvidia.com/v2/...` which is auth-gated. The `nvidia-ngc` sub-skill can only discover their URLs via the sitemap; the deep metadata needs an NGC API key. Be honest with the user when this gap kicks in.
