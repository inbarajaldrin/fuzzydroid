---
name: lerobot
description: Use whenever the user is working with HuggingFace LeRobot or asks about robot imitation learning, real-world robotics in PyTorch, LeRobot policies (ACT, SmolVLA, Pi0, Diffusion, HIL-SERL), LeRobot datasets / LeRobotDataset v3, or LeRobot-supported hardware (SO-100, SO-101, Koch, LeKiwi, Reachy2, Unitree G1, Hope Jr, Omx, Open-Arm, Earthrover, Damiao, Feetech). Also triggers on "LeRobot tutorial", "LeRobot teleop", "record a dataset with LeRobot", "train a LeRobot policy", "LeRobot calibration", or "push LeRobot model to the Hub". Fetches LeRobot's documentation reliably via the `.md` suffix rule (Pattern A). Trigger liberally — LeRobot's APIs, policy list, and dataset format evolve rapidly and cached knowledge is frequently stale; always consult the live docs before answering.
---

# LeRobot Docs

Reliable live access to HuggingFace LeRobot's documentation at `https://huggingface.co/docs/lerobot/`.

## Why this skill exists

LeRobot is a fast-moving robotics library: policies are added monthly, the dataset format has gone through v1 → v2 → v3, and hardware support keeps expanding. Training knowledge goes stale fast. This skill teaches the agent the right URL-rewrite rule and gives it a curated map of entry points so it can always pull current content from the source.

## The retrieval rule

Pattern A — **append `.md` to any LeRobot docs URL**. HuggingFace serves a clean `text/markdown` response next to the HTML.

| HTML URL | Markdown URL |
|---|---|
| `https://huggingface.co/docs/lerobot/index` | `https://huggingface.co/docs/lerobot/index.md` |
| `https://huggingface.co/docs/lerobot/installation` | `https://huggingface.co/docs/lerobot/installation.md` |
| `https://huggingface.co/docs/lerobot/smolvla` | `https://huggingface.co/docs/lerobot/smolvla.md` |

Rule: strip any trailing slash, then append `.md`. For the root, use `index.md`.

**Versioning note (verified 2026-04-22):** LeRobot docs currently resolve unversioned paths (`/docs/lerobot/<slug>.md`) to the latest. At time of verification that was `v0.5.1`. Versioned variants like `/docs/lerobot/v0.5.1/en/<slug>.md` and `/docs/lerobot/main/en/<slug>.md` **404** — only the unversioned slug supports `.md`. Strategy is always-latest because only one URL form works (decision forced per `docs-skill-builder` Step 3 criteria). See `references/retrieval-rule.md` for the verified probes and full rationale.

## HTML exceptions

None observed — every sidebar page tested returns `text/markdown` via the unversioned `.md` suffix. If a page 404s on `.md`, fall back to `WebFetch` of the HTML URL.

## Workflow

1. Identify the topic (install, a specific policy, a specific robot, dataset format, teleop, training loop, etc.).
2. Look up the entry point in `references/live-sources.md`. If the user's question mentions a slug not catalogued, apply the rewrite rule to `https://huggingface.co/docs/lerobot/<slug>.md`.
3. `WebFetch` the `.md` URL with a tight extraction prompt — name the section you want (install command, config flags, policy hyperparameters, dataset schema field, etc.).
4. If the page references another page the user needs, rewrite that URL the same way and fetch it.
5. Cite the HTML URL (not the `.md` URL) back to the user so they can open it in a browser.

## Reference files

- `references/live-sources.md` — curated entry points grouped by topic (Get Started, Tutorials, Policies, Datasets, Hardware, Integrations, Advanced, Contributing).
- `references/retrieval-rule.md` — the exact rewrite rule, probe commands, and verified examples.

## Common pitfalls

- **Do not prefix with `v0.5.1/en/` when fetching `.md`.** That path returns HTML for the page and 404 for the `.md` — opposite of Apple/Claude docs behaviour. Use the bare slug.
- **`sitemap.xml` is unreliable — use sidebar scrape for URL discovery.** `/docs/lerobot/sitemap.xml` returns an HTML notice saying to use `/docs/lerobot/main/en/sitemap.xml`, but that URL also 404s. The authoritative page list is the left sidebar of any rendered doc page. This matches step 2 of the URL discovery hierarchy in `docs-skill-builder/references/retrieval-patterns.md` — for LeRobot, jump straight to sidebar scrape; see the re-enumeration command in `references/retrieval-rule.md`.
- **Policy naming drift.** New policies land frequently (pi0, pi05, pi0fast, smolvla, xvla, ...). If the user asks about a policy not in `live-sources.md`, try `https://huggingface.co/docs/lerobot/<policy-name>.md` directly.
- **Dataset format versions.** LeRobot has shipped v1, v2, and v3 of the dataset format. When answering dataset questions, check which version the user is on — `lerobot-dataset-v3.md` and `porting_datasets_v3.md` are the current-version references.
- **Always-latest versioning.** This skill pins the **concept** of latest (v0.5.1 as of 2026-04-21). If HuggingFace ever stops resolving unversioned URLs, re-run the probe in `references/retrieval-rule.md` and switch to an explicit version segment.
