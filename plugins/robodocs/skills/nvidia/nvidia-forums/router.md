# NVIDIA Developer Forums Docs

Reliable live access to the NVIDIA Developer Forums at `https://forums.developer.nvidia.com/`. The forums run **Discourse**, so every topic / category / search page is available as structured JSON alongside the rendered HTML.

## When to use this sub-skill

Trigger on: NVIDIA Developer Forums (`forums.developer.nvidia.com`), real-world user problems and NVIDIA staff answers across Omniverse, Isaac Sim / Lab / ROS / GR00T, NVIDIA Cosmos, CloudXR, DRIVE, Jetson, CUDA, TensorRT, Triton, cuDNN, DeepStream, Metropolis, Riva, Omniverse Replicator, Omniverse Kit, or any NVIDIA developer product. Also triggers on "forum", "forums", "known issue", "has anyone solved", "anyone running into", "community post", "thread", "bug report", "workaround", "NVIDIA staff answer", or cross-product compatibility questions that official docs don't cover well (e.g., "does product A work with product B", "can I use X in Y", "is Z supported on W"). This is the ONLY sub-skill in the suite that covers community-sourced content — official-docs sub-skills should defer here for user-experience / "in the wild" questions that can't be answered from product docs alone.

## Why this skill exists

Official product docs (what the other sub-skills in this suite cover) are pristine but often miss: real-world error messages, cross-product compatibility ("can I use X with Y"), staff corrections of older docs, "known issue" acknowledgements, and unofficial workarounds. The NVIDIA Developer Forums are where those live — indexed by Discourse, searchable, with staff-tagged replies.

## The retrieval rule

Pattern B — **Discourse JSON API**. Every HTML URL on `forums.developer.nvidia.com` has a `.json` counterpart that returns structured data (topic metadata + posts + participants + references).

| HTML URL | JSON URL |
|---|---|
| `/t/<slug>/<topic-id>` | `/t/<slug>/<topic-id>.json` |
| `/c/<path>/<cat-id>` | `/c/<path>/<cat-id>.json` |
| `/latest` | `/latest.json` |
| `/categories` | `/categories.json` |
| `/search?q=<query>` | `/search.json?q=<query>` |

Rule: **append `.json`** to any forum URL. No path rewrite needed (unlike Apple's insert-before-path rule). Discourse serves `application/json` with a well-documented schema — see `references/schema.md`.

## HTML exceptions

- **User profile pages** (`/u/<username>.json`) work but are rarely useful for technical questions.
- **Some admin-only endpoints** (like `/admin/*`) require auth and will 401/403 — skip.
- **Rate limits** exist on the JSON API — space out requests. For bulk enumeration, prefer the sitemap (`/sitemap.xml` returns 200) over scraping.

## Workflow

1. Classify the question — is it a known-thread lookup, a product category browse, a cross-product compatibility question, or a search across multiple products?
2. **For a search**: hit `/search.json?q=<query>` first. It returns a `topics[]` and `posts[]` array; grab the top matches' IDs and fetch topic JSON.
3. **For a specific thread the user mentions**: fetch `/t/<slug>/<id>.json` directly.
4. **For "what's happening in category X"**: fetch `/c/<path>/<cat-id>.json?page=0`. See `references/live-sources.md` for the category catalog.
5. Extract the user's original question from `post_stream.posts[0].cooked`, NVIDIA staff answers by filtering posts where `user_title` or `moderator: true`, and the resolution from the last post or a post marked as solution.
6. Cite the **HTML URL** (`/t/<slug>/<id>`) back to the user, optionally with the post anchor (`#post_<N>`).

## Reference files

- `references/live-sources.md` — category catalog (Omniverse / Isaac / Robotics / AV / AI-DS / Developer Tools + IDs) and search-first workflow.
- `references/retrieval-rule.md` — full Discourse `.json` rule, rate-limit notes, verification commands.
- `references/schema.md` — **Discourse JSON schema** (topic, post_stream, search response) with extraction patterns — the only schema file in the suite because this is the only Pattern B skill.

## Common pitfalls

- **`post.cooked` is rendered HTML, not markdown.** Each post's body is in `post_stream.posts[i].cooked`. Strip HTML tags if you want clean text; keep them if you want links preserved.
- **Staff vs user posts.** Check `user_title` (e.g., "NVIDIA Employee") or `moderator: true` / `admin: true` on the post. Don't quote a random user as an authoritative answer.
- **Old threads can be stale.** Posts from 2021-2023 may reference deprecated APIs. Always check `last_posted_at` — a thread with recent activity is more likely current. When citing old advice, flag the date.
- **`/search.json` results are paginated.** Default returns top matches, not all. If the user needs deep search, explicitly page through or use a more specific query.
- **Topic IDs are stable, slugs aren't.** Discourse preserves the ID forever but renames the slug if the title changes. When caching a URL, include the ID so you can always resolve.
- **"Closed" doesn't mean "answered".** `closed: true` can mean solved OR abandoned. Read the last couple of posts to tell which.
- **Cross-linked threads exist.** `related_topics[]` at the bottom of topic JSON is pre-populated — follow it when the first thread doesn't fully answer the user, before running a fresh search.
- **The forum covers more than Omniverse/Isaac.** CUDA, TensorRT, Jetson, DRIVE, cuDNN, DeepStream all live here too. Don't route to `omniverse-kit` or `isaac-sim` skills for a CUDA compiler error — that's a forum-only question.
