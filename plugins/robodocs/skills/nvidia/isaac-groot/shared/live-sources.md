# Isaac GR00T Docs — Live Sources

Curated entry points for Isaac GR00T. Sources span GitHub repo, HuggingFace model cards, and NVIDIA developer portal. Apply the rewrite rule from `retrieval-rule.md` to fetch raw markdown.

Verified 2026-04-23.

---

## Repository Root (GitHub · NVIDIA/Isaac-GR00T)

| Topic | HTML URL (cite to user) | Fetch URL | Extraction Prompt |
|---|---|---|---|
| README | `https://github.com/NVIDIA/Isaac-GR00T/blob/main/README.md` | `https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/README.md` | "Extract the overview, supported humanoids, install commands, fine-tuning quickstart, model list (N1 / N1.5 / N variants), and dataset format (LeRobotDataset)." |
| FAQ | `https://github.com/NVIDIA/Isaac-GR00T/blob/main/FAQ.md` | `https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/FAQ.md` | "Look up the specific question the user asked." |
| AGENTS.md | `https://github.com/NVIDIA/Isaac-GR00T/blob/main/AGENTS.md` | `https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/AGENTS.md` | "Extract agent / tooling integration guidance." |
| CONTRIBUTING | `https://github.com/NVIDIA/Isaac-GR00T/blob/main/CONTRIBUTING.md` | `.../CONTRIBUTING.md` | "Extract contributor workflow, testing, PR checklist." |
| ATTRIBUTIONS | `https://github.com/NVIDIA/Isaac-GR00T/blob/main/ATTRIBUTIONS.md` | `.../ATTRIBUTIONS.md` | "Extract upstream attributions and third-party license notices." |

## Repository Subdirectories

The repo has directories `getting_started/`, `examples/`, `scripts/`, `docker/`, `demo_data/`, `gr00t/` (Python package), `tests/`. Notebooks in `getting_started/` are the canonical tutorial entry points.

| Topic | URL pattern | Extraction Prompt |
|---|---|---|
| Scrape repo tree | `https://github.com/NVIDIA/Isaac-GR00T/tree/main/<dir>` | "List the files in this directory (markdown / notebooks). Construct raw URLs as `https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/<dir>/<file>`." |
| Getting Started tree | `https://github.com/NVIDIA/Isaac-GR00T/tree/main/getting_started` | "List the getting_started notebooks / markdown. Each `.ipynb` is a tutorial; fetch via raw URL." |
| Examples tree | `https://github.com/NVIDIA/Isaac-GR00T/tree/main/examples` | "List the examples (fine-tuning configs, inference scripts)." |
| Scripts tree | `https://github.com/NVIDIA/Isaac-GR00T/tree/main/scripts` | "List the utility scripts (data conversion, eval, visualization)." |
| Docker tree | `https://github.com/NVIDIA/Isaac-GR00T/tree/main/docker` | "List the Dockerfiles and compose files." |
| `gr00t/` Python package | `https://github.com/NVIDIA/Isaac-GR00T/tree/main/gr00t` | "Scrape the package layout — model / data / experiment / utils submodules." |

**Constructing a raw URL** for any file you see:
`https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/<path>`

## HuggingFace Model Cards

| Topic | Model page (cite to user) | Fetch URL | Extraction Prompt |
|---|---|---|---|
| GR00T-N1.5-3B | `https://huggingface.co/nvidia/GR00T-N1.5-3B` | `https://huggingface.co/nvidia/GR00T-N1.5-3B/raw/main/README.md` | "Extract model description, usage snippet, training data, supported humanoids, license, and tokenizer." |
| GR00T-N1-2B | `https://huggingface.co/nvidia/GR00T-N1-2B` | `https://huggingface.co/nvidia/GR00T-N1-2B/raw/main/README.md` | "Extract the 2B variant details — size, capabilities, training recipe." |
| GR00T-N1-3B (gated) | `https://huggingface.co/nvidia/GR00T-N1-3B` | `https://huggingface.co/nvidia/GR00T-N1-3B/raw/main/README.md` (**401 — gated**) | "If accessible, extract model details; otherwise fall back to the GitHub README which lists N1-3B." |
| GR00T collection (HF) | `https://huggingface.co/collections/nvidia/isaac-gr00t` | `https://huggingface.co/collections/nvidia/isaac-gr00t` (HTML) | "Extract the full collection of GR00T models, checkpoints, and datasets published by NVIDIA on HuggingFace." |

## NVIDIA Developer Portal & Blog

| Topic | URL | Extraction Prompt |
|---|---|---|
| GR00T developer landing | `https://developer.nvidia.com/isaac/gr00t` | "Extract the product overview, release announcements, and links to technical blogs / models. Pattern D — plain HTML." |
| NVIDIA technical blog — GR00T N1.6 | `https://developer.nvidia.com/blog/building-generalist-humanoid-capabilities-with-nvidia-isaac-gr00t-n1-6-using-a-sim-to-real-workflow/` | "Extract the N1.6 architecture, sim-to-real workflow, and experimental results." |

## Related (cross-skill routing)

- **Dataset format (LeRobotDataset v3)** → `lerobot` skill.
- **Isaac Lab humanoid training envs** → `isaac-lab` skill.
- **Warp reward kernels for humanoid reward shaping** → `nvidia-warp` skill.

---

## Notes on extraction

- For **GitHub files**, the raw URL returns clean markdown (or notebook JSON for `.ipynb`).
- For **HF model cards**, `.../raw/main/README.md` is the canonical markdown.
- **Cite the HTML URL** (github.com/blob, huggingface.co/model_id) back to the user — they can open it in a browser.
- **Notebooks** (`*.ipynb`) come through as JSON; the extraction prompt should name "the cells about X" to help parse.

## Exceptions

- **Gated HF models** return 401. Note to user + fall back to GitHub README.
- **GitHub API** for directory listings may be rate-limited without auth — prefer HTML scrape of the tree page.

## Version drift

Catalog targets `main`. GR00T repo moves fast; when the user references a specific release (N1.6, etc.), substitute `main` with the matching tag, or scrape the Releases page for current tags.
