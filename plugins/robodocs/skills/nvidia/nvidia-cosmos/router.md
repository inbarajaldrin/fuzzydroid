# NVIDIA Cosmos Docs

Reliable live access to NVIDIA Cosmos documentation across the `nvidia-cosmos` GitHub organization (`https://github.com/orgs/nvidia-cosmos/repositories`) and related HuggingFace model pages.

## When to use this sub-skill

Trigger on: NVIDIA Cosmos (world foundation models for physical AI), `cosmos-predict1` / `cosmos-predict2` / `cosmos-predict2.5` (video prediction world models), `cosmos-transfer1` (physics-aware video-to-video), `cosmos-reason1` (reasoning world models), `cosmos-rl` (RL on world models), `cosmos-curator` / `cosmos-curate` (video data curation), `cosmos-cookbook` (worked recipes), `cosmos-evaluator` (benchmark harness), generative video for simulation data / robotics data augmentation, or "world foundation models" generally. Also triggers on use with Omniverse (Cosmos complements simulation by generating physical-AI training video) and Isaac GR00T (GR00T-Dreams uses Cosmos for video-conditioned policy generation).

## Why this skill exists

Cosmos is NVIDIA's world-foundation-model family — generative models that produce physically-plausible video for training physical AI (robotics, AVs, humanoids). Unlike Isaac Sim (deterministic simulation) or Omniverse (rendering / physics), Cosmos generates **imagined** future video conditioned on scene / action / language. The family spans multiple repos (predict / transfer / reason / rl / curator / cookbook / evaluator) and HF model checkpoints. No single docs site covers it — the GitHub org is the source of truth.

## The retrieval rule

**Pattern A — raw markdown, multi-repo.**

Cosmos is an **organization** with many repos. The rewrite pattern is:

| Source | Rewrite |
|---|---|
| `github.com/nvidia-cosmos/<repo>/blob/main/<path>` | `raw.githubusercontent.com/nvidia-cosmos/<repo>/main/<path>` |
| HuggingFace `huggingface.co/nvidia/<model>` | `huggingface.co/nvidia/<model>/raw/main/README.md` |

Use `raw.githubusercontent.com` for any repo file; use `huggingface.co/.../raw/main/README.md` for model cards.

**Routing across repos** — when the user doesn't say which Cosmos model, pick based on intent:
- Video prediction → `cosmos-predict1` / `cosmos-predict2` / `cosmos-predict2.5`
- Physics-aware video-to-video (e.g., style transfer, sim-to-real) → `cosmos-transfer1`
- Reasoning over video → `cosmos-reason1`
- RL on world models → `cosmos-rl`
- Data curation → `cosmos-curator` / `cosmos-curate`
- Worked examples → `cosmos-cookbook`
- Benchmarks → `cosmos-evaluator`

## HTML exceptions

- **HuggingFace gated models** — some Cosmos model cards require accepting the license (401 without).
- **GitHub organization page** (`github.com/nvidia-cosmos`) is plain HTML — scrape for the current repo list (the org adds repos frequently).
- **NVIDIA main Cosmos page** (`nvidia.com/en-us/ai/cosmos/`) is plain HTML (Pattern D) — marketing-leaning but good for product context.

## Workflow

1. Identify the task — prediction / transfer / reasoning / RL / curation / cookbook / eval.
2. Pick the matching repo in `references/live-sources.md`. If unsure, fetch the org listing via HTML scrape.
3. Fetch the raw README from `raw.githubusercontent.com/nvidia-cosmos/<repo>/main/README.md`.
4. For model-specific details, follow to the HF model card linked in the README.
5. For end-to-end recipes, go to `cosmos-cookbook`.
6. Cite the GitHub repo URL (not raw) and the HF model page back to the user.

## Reference files

- `references/live-sources.md` — curated entry points per repo in the `nvidia-cosmos` org + key HF model cards + main product page.
- `references/retrieval-rule.md` — rewrite rules for the multi-repo layout.

## Common pitfalls

- **`cosmos-curator` vs `cosmos-curate`** — both exist in the org. Check the README of each to see which is active / canonical for the user's use case.
- **Repo naming evolves.** `cosmos-predict1` → `cosmos-predict2` → `cosmos-predict2.5` reflects generations. Always use the most recent unless the user asks for a specific version.
- **HF model cards vs repo READMEs.** Repo README often has install / script / training details; HF card has model architecture, eval numbers, license. Fetch both for complete answers.
- **Some models are gated on HF.** Route to the GitHub README if the HF card returns 401.
- **NVIDIA main cosmos page** is marketing — don't treat as technical truth. Always cross-reference with repo README.
- **Cookbook is worked recipes, not reference docs.** If the user needs a canonical API surface, go to the specific repo's README; the cookbook is for "how do I achieve X end-to-end" scenarios.
