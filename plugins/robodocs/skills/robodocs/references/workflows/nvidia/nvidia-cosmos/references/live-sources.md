# NVIDIA Cosmos Docs — Live Sources

Curated entry points across the `nvidia-cosmos` GitHub organization and related HuggingFace model pages. Apply the rewrite rule from `retrieval-rule.md` before fetching.

Verified 2026-04-23.

---

## Organization & Product

| Topic | URL | Extraction Prompt |
|---|---|---|
| GitHub org listing | `https://github.com/orgs/nvidia-cosmos/repositories` | "List the current repos in the nvidia-cosmos org with a one-line description. Use this to discover new repos the catalog hasn't picked up." |
| Cosmos main product page | `https://www.nvidia.com/en-us/ai/cosmos/` | "Extract the product overview and the list of model families with their use cases. Plain HTML (Pattern D)." |
| NVIDIA technical blog (Cosmos category) | `https://developer.nvidia.com/blog/tag/cosmos/` | "Extract recent Cosmos blog posts with titles and summaries. Pattern D." |

## Prediction Models (video world models)

| Topic | HTML URL (cite) | Fetch URL | Extraction Prompt |
|---|---|---|---|
| cosmos-predict1 README | `https://github.com/nvidia-cosmos/cosmos-predict1/blob/main/README.md` | `https://raw.githubusercontent.com/nvidia-cosmos/cosmos-predict1/main/README.md` | "Extract cosmos-predict1 overview, architecture, install, inference, training, supported model sizes, and HF links." |
| cosmos-predict2 README | `https://github.com/nvidia-cosmos/cosmos-predict2/blob/main/README.md` | `.../cosmos-predict2/main/README.md` | "Extract cosmos-predict2 — what's new vs predict1, architecture, install, inference, fine-tuning." |
| cosmos-predict2.5 README | `https://github.com/nvidia-cosmos/cosmos-predict2.5/blob/main/README.md` | `.../cosmos-predict2.5/main/README.md` | "Extract cosmos-predict2.5 updates, scripts, and model checkpoints." |

## Transfer (physics-aware video-to-video)

| Topic | HTML URL | Fetch URL | Extraction Prompt |
|---|---|---|---|
| cosmos-transfer1 README | `https://github.com/nvidia-cosmos/cosmos-transfer1/blob/main/README.md` | `.../cosmos-transfer1/main/README.md` | "Extract cosmos-transfer1 — what it is (physics-aware video-to-video), typical use cases (style transfer, sim-to-real, condition control), inference / training commands, supported conditioners (Canny, depth, segmentation, etc.)." |

## Reasoning

| Topic | HTML URL | Fetch URL | Extraction Prompt |
|---|---|---|---|
| cosmos-reason1 README | `https://github.com/nvidia-cosmos/cosmos-reason1/blob/main/README.md` | `.../cosmos-reason1/main/README.md` | "Extract cosmos-reason1 — what is reasoning over video/world models, the task formulation, training data, and inference." |

## RL on World Models

| Topic | HTML URL | Fetch URL | Extraction Prompt |
|---|---|---|---|
| cosmos-rl README | `https://github.com/nvidia-cosmos/cosmos-rl/blob/main/README.md` | `.../cosmos-rl/main/README.md` | "Extract cosmos-rl — running RL on world models, environment wrappers, policies, training scripts." |

## Data Curation

| Topic | HTML URL | Fetch URL | Extraction Prompt |
|---|---|---|---|
| cosmos-curator README | `https://github.com/nvidia-cosmos/cosmos-curator/blob/main/README.md` | `.../cosmos-curator/main/README.md` | "Extract cosmos-curator — video data curation pipeline, filters, quality metrics, deduplication, output format." |
| cosmos-curate README | `https://github.com/nvidia-cosmos/cosmos-curate/blob/main/README.md` | `.../cosmos-curate/main/README.md` | "Extract cosmos-curate — check whether this is the active curation repo or a rename/sibling of cosmos-curator, and extract its specific scope." |

## Worked Recipes

| Topic | HTML URL | Fetch URL | Extraction Prompt |
|---|---|---|---|
| cosmos-cookbook README | `https://github.com/nvidia-cosmos/cosmos-cookbook/blob/main/README.md` | `.../cosmos-cookbook/main/README.md` | "Extract cosmos-cookbook — list of worked recipes, each one an end-to-end example for a Cosmos use case (e.g., generate sim training video, do style transfer, chain models)." |

## Evaluation

| Topic | HTML URL | Fetch URL | Extraction Prompt |
|---|---|---|---|
| cosmos-evaluator README | `https://github.com/nvidia-cosmos/cosmos-evaluator/blob/main/README.md` | `.../cosmos-evaluator/main/README.md` | "Extract the benchmark / evaluation harness — metrics, datasets, how to run, expected output format." |

## HuggingFace Model Cards (sample — many more in collection)

| Topic | HF URL | Fetch URL | Extraction Prompt |
|---|---|---|---|
| Cosmos HF collection | `https://huggingface.co/collections/nvidia/cosmos` | same (HTML) | "Extract the full list of Cosmos models on HuggingFace with sizes and gating status." |
| Cosmos-Predict2.1-2B-Text2Image (gated) | `https://huggingface.co/nvidia/Cosmos-Predict2.1-2B-Text2Image` | `.../raw/main/README.md` (**401**) | "Extract model card if accessible; otherwise fall back to the cosmos-predict2 README." |

## Cross-skill routing

- **Robotics training data from Cosmos** → cross-ref `isaac-lab` for how to consume in training.
- **Humanoid policies with Cosmos-conditioned video (GR00T-Dreams)** → cross-ref `isaac-groot`.
- **Simulation-side scene generation** → `omniverse-replicator` (deterministic) vs Cosmos (generative). Explain the difference when the user asks.

---

## Notes on extraction

- Raw markdown via `raw.githubusercontent.com` for repo READMEs.
- HF raw markdown via `.../raw/main/README.md`.
- Cite the **HTML** (github.com/blob, huggingface.co/model) back to the user.
- **When in doubt, fetch the org listing** to enumerate current repos — new ones land regularly.

## Exceptions

- **HF gated models** — 401. Fall back to GitHub README.
- **Repo renaming / reorg** — scrape the org listing periodically to refresh.

## Version drift

Cosmos is a fast-moving multi-repo family. Re-scrape the org listing each month, and check which `cosmos-predictN` / `cosmos-predictN.x` is the current recommended generation by reading the most recent repo's README.
