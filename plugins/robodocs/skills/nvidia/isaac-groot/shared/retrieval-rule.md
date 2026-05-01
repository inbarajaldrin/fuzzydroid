# Isaac GR00T Docs — Retrieval Rule

## The rule

**Pattern A — raw markdown from GitHub + HuggingFace.**

| Source | Rewrite |
|---|---|
| GitHub `github.com/NVIDIA/Isaac-GR00T/blob/main/<path>` | `raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/<path>` |
| HuggingFace model page `huggingface.co/nvidia/<model>` | `huggingface.co/nvidia/<model>/raw/main/README.md` |
| NVIDIA developer portal `developer.nvidia.com/isaac/gr00t` | same (Pattern D — plain HTML) |

## Worked examples (verified 2026-04-23)

| HTML URL | Fetch URL | Status |
|---|---|---|
| `github.com/NVIDIA/Isaac-GR00T/blob/main/README.md` | `raw.githubusercontent.com/.../main/README.md` | 200 · text/plain |
| `github.com/NVIDIA/Isaac-GR00T/blob/main/FAQ.md` | `.../main/FAQ.md` | 200 · text/plain |
| `huggingface.co/nvidia/GR00T-N1.5-3B` | `.../raw/main/README.md` | 200 · text/plain |
| `huggingface.co/nvidia/GR00T-N1-3B` | `.../raw/main/README.md` | **401** — gated model, accept license in HF UI |

## Versioning strategy

**Default: `main` branch** on GitHub, latest model tag on HuggingFace.

| URL form | When |
|---|---|
| `raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/<file>` | Default — tracks main. |
| `raw.githubusercontent.com/NVIDIA/Isaac-GR00T/<tag>/<file>` | Pinned release — substitute `main` with a git tag. |

**Verification date: 2026-04-23.**

## Exceptions

- **Gated HF models** return 401. Fall back to the GitHub README (which often describes the model) or the NVIDIA blog / developer portal.
- **Jupyter notebooks (`*.ipynb`)** — `raw.githubusercontent.com` returns the raw JSON notebook. Extract cells via prompt; don't try to render.
- **GitHub directory listings** don't expose file lists via raw URL — scrape the HTML tree or use the GitHub API (may be rate-limited).

## Detection / verification

### Verify raw markdown works

```sh
curl -sI "https://raw.githubusercontent.com/NVIDIA/Isaac-GR00T/main/README.md" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/plain; charset=utf-8
```

### Enumerate repo files (limited without auth)

```sh
# Scrape HTML for top-level files + dirs
curl -s "https://github.com/NVIDIA/Isaac-GR00T" \
  | grep -oE 'title="[^"]*\.(md|ipynb|py|yaml|toml)"' \
  | sed 's/title="//;s/"$//' | sort -u
```

### Enumerate Cosmos-style org repos (for future maintenance)

```sh
curl -s "https://github.com/orgs/nvidia-cosmos/repositories" \
  | grep -oE 'href="/nvidia-cosmos/[^"/]*"' \
  | sed 's|href="/nvidia-cosmos/||;s/"$//' | sort -u
```

### When the probe fails

If the raw URL 404s after a release, the file may have been renamed — scrape the repo HTML for the new filename. If HF returns 401, the model is gated; the user must accept the license on HF.
