# Isaac GR00T Docs

Reliable live access to Isaac GR00T documentation across the GitHub repo and HuggingFace model cards. Primary sources:

- `https://github.com/NVIDIA/Isaac-GR00T` — code + README + FAQ
- `https://huggingface.co/nvidia/GR00T-N1.5-3B` / `GR00T-N1-2B` — model cards with usage, license, training details
- `https://developer.nvidia.com/isaac/gr00t` — marketing overview + blog links

## When to use this sub-skill

Trigger on: NVIDIA Isaac GR00T (humanoid robot foundation models), GR00T N1 / N1.5 / Nx generalist policies, GR00T-Mimic (data generation / teleop retargeting), GR00T-Dreams (video-conditioned policy), the `gr00t` Python package (`gr00t.model`, `gr00t.data`, `gr00t.experiment`), humanoid fine-tuning with LeRobot datasets, cross-embodiment transfer, retargeting to specific humanoid platforms (Fourier GR1, Unitree G1, Hope Jr, etc.), or "foundation models for humanoid robots". Also triggers on adjacent use: Isaac Lab humanoid training envs (GR00T's backbone training runs on Isaac Lab), LeRobot `groot` policy integration, and humanoid dataset collection / augmentation workflows.

## Why this skill exists

GR00T is NVIDIA's generalist humanoid foundation model family (N1 / N1.5 / dreams) with matching data-generation (Mimic) and video-conditioning (Dreams) pipelines. It's built on Isaac Lab and LeRobot-compatible dataset formats. Recipes for fine-tuning to specific humanoid platforms, retargeting, and cross-embodiment transfer shift quickly. Live GitHub README + HF model cards are the canonical sources.

## The retrieval rule

**Pattern A — raw markdown via `raw.githubusercontent.com` and `huggingface.co/.../raw/main/`.**

| Source | Raw URL pattern | Fetch URL |
|---|---|---|
| GR00T repo file | `https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/<path>.md` | same (text/plain markdown) |
| HF model card | `https://huggingface.co/nvidia/<model>/raw/main/README.md` | same |

Rule: **use `raw.githubusercontent.com` for GitHub** (returns clean markdown); for HuggingFace model cards, use the `.../raw/main/README.md` path.

| HTML URL | Fetch URL |
|---|---|
| `https://github.com/NVIDIA/Isaac-GR00T/blob/main/README.md` | `https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/README.md` |
| `https://huggingface.co/nvidia/GR00T-N1.5-3B` | `https://huggingface.co/nvidia/GR00T-N1.5-3B/raw/main/README.md` |

## HTML exceptions

- **GitHub code pages** (`.py`, `.ipynb`, `.yaml`) — `raw.githubusercontent.com` still works; just note that notebooks return raw JSON.
- **NVIDIA developer portal** (`developer.nvidia.com/isaac/gr00t`) — plain HTML (Pattern D). Good for marketing / context; shallow on technical detail.
- **NVIDIA blog posts** on GR00T — plain HTML (Pattern D).

## Workflow

1. Classify — overview / getting-started (README), fine-tuning (README + getting_started notebooks), model detail (HF model card), deployment (repo scripts), dataset format (LeRobot-compatible — cross-ref `lerobot` skill).
2. Look up in `shared/live-sources.md`.
3. Fetch the raw markdown URL directly.
4. For notebook content, fetch the raw `.ipynb` and note that cells / outputs come through as JSON — ask a tight extraction prompt.
5. If the user asks about dataset format (LeRobotDataset v3) → cross-ref `lerobot`.
6. If the user asks about the Isaac Lab training side → cross-ref `isaac-lab`.
7. Cite the GitHub HTML URL (`github.com/.../blob/main/...`) or HF model page back to the user, not the raw URL.

## Reference files

- `shared/live-sources.md` — curated entry points: Repo root (README, FAQ) · Model Cards (HF) · Getting Started Notebooks · Developer Portal · Technical Blog.
- `shared/retrieval-rule.md` — rewrite rule, GitHub vs HF vs portal differences.

## Common pitfalls

- **GR00T N1 ≠ N1.5 ≠ Nx.** Different model sizes, different training data, different supported humanoids. Always confirm which version.
- **Dataset format is LeRobotDataset.** GR00T ingests LeRobotDataset (v3 in current releases). For format questions, route to `lerobot`.
- **Training runs on Isaac Lab.** The fine-tuning examples assume an Isaac Lab env. For Lab details, route to `isaac-lab`.
- **HuggingFace model cards may be gated.** Some GR00T variants require accepting the license via HF UI — the `raw/main/README.md` may return 401 if gated.
- **`developer.nvidia.com/isaac/gr00t` is marketing-leaning.** For code / config, go to the repo README, not the developer portal.
- **Notebooks in `getting_started/` are the canonical tutorials.** When the user wants "how do I fine-tune", fetch those notebook files via raw URL.
