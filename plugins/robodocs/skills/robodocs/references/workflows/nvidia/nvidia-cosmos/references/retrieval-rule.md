# NVIDIA Cosmos Docs — Retrieval Rule

## The rule

**Pattern A — raw markdown, multi-repo across the `nvidia-cosmos` GitHub organization.**

| Source | Rewrite |
|---|---|
| `github.com/nvidia-cosmos/<repo>/blob/main/<path>` | `raw.githubusercontent.com/nvidia-cosmos/<repo>/main/<path>` |
| `huggingface.co/nvidia/<model>` | `huggingface.co/nvidia/<model>/raw/main/README.md` |
| `nvidia.com/en-us/ai/cosmos/` (marketing) | same (Pattern D plain HTML) |

## Worked examples (verified 2026-04-23)

| HTML URL | Fetch URL | Status |
|---|---|---|
| `github.com/nvidia-cosmos/cosmos-predict1/blob/main/README.md` | `raw.githubusercontent.com/nvidia-cosmos/cosmos-predict1/main/README.md` | 200 · text/plain |
| `github.com/nvidia-cosmos/cosmos-predict2/blob/main/README.md` | `.../cosmos-predict2/main/README.md` | 200 · text/plain |
| `github.com/nvidia-cosmos/cosmos-predict2.5/blob/main/README.md` | `.../cosmos-predict2.5/main/README.md` | 200 · text/plain |
| `github.com/nvidia-cosmos/cosmos-transfer1/blob/main/README.md` | `.../cosmos-transfer1/main/README.md` | 200 · text/plain |
| `github.com/nvidia-cosmos/cosmos-reason1/blob/main/README.md` | `.../cosmos-reason1/main/README.md` | 200 · text/plain |
| `github.com/nvidia-cosmos/cosmos-rl/blob/main/README.md` | `.../cosmos-rl/main/README.md` | 200 · text/plain |
| `github.com/nvidia-cosmos/cosmos-cookbook/blob/main/README.md` | `.../cosmos-cookbook/main/README.md` | 200 · text/plain |
| `huggingface.co/nvidia/Cosmos-Predict2.1-2B-Text2Image` | `.../raw/main/README.md` | **401** — gated |

## Versioning strategy

**Default: `main` branch** on GitHub. Different repos = different generations (predict1/2/2.5). Pick the newest matching the user's intent unless they specify.

**Verification date: 2026-04-23.**

## Exceptions

- **Gated HF model cards** — 401 on `.../raw/main/README.md` until the license is accepted.
- **Marketing site** (`nvidia.com/en-us/ai/cosmos/`) — plain HTML. Good for product context, shallow on code.
- **Repo naming generations.** `cosmos-predict1` → `cosmos-predict2` → `cosmos-predict2.5` — evolving repos, not branches.

## Detection / verification

### Verify raw markdown works for a repo

```sh
curl -sI "https://raw.githubusercontent.com/nvidia-cosmos/cosmos-predict2/main/README.md" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/plain; charset=utf-8
```

### Enumerate current repos in the org

```sh
curl -s "https://github.com/orgs/nvidia-cosmos/repositories" \
  | grep -oE 'href="/nvidia-cosmos/[^"/]*"' \
  | sed 's|href="/nvidia-cosmos/||;s/"$//' \
  | sort -u
```

Use this to refresh the catalog when new repos land.

### When the probe fails

- **404 on raw URL** — the repo may have been archived/renamed. Scrape the org listing to find the current repo name.
- **401 on HF** — model is gated. Direct the user to accept the license; fall back to the GitHub README.
- **Marketing page changed** — `nvidia.com/en-us/ai/cosmos/` is plain HTML; it can restructure any time. Look for a linked docs page.
