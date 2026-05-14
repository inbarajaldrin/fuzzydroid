# Discourse JSON Schema (NVIDIA Forums)

Discourse — the software powering `forums.developer.nvidia.com` — serves a documented JSON API alongside every HTML page. This file documents the three most-used response shapes: **topic JSON**, **search JSON**, and **category JSON**.

## Topic JSON — `/t/<slug>/<id>.json`

Returned when fetching a single thread. This is the most-common shape for answering user questions.

### Top-level keys

| Key | Purpose |
|---|---|
| `title` | Thread title (plain). |
| `fancy_title` | Thread title with HTML-encoded entities. |
| `id` | Topic ID (stable — use this for cache keys). |
| `slug` | URL slug (cosmetic — can change). |
| `posts_count` | Total posts including replies. |
| `reply_count` | Replies to the original post specifically. |
| `like_count` | Aggregate likes across the thread. |
| `views` | View count. |
| `created_at` | ISO 8601 timestamp of thread creation. |
| `last_posted_at` | ISO 8601 of most recent post — **critical for freshness judgment**. |
| `category_id` | Numeric ID of the containing category. |
| `tags` | Array of tag slugs. |
| `closed` | Boolean — can be "solved" OR "abandoned", read posts to tell. |
| `archived` | Boolean — read-only (usually ancient threads). |
| `visible` | Boolean — `false` means soft-deleted. |
| `word_count` | Total word count across all posts. |
| `post_stream` | **The content** — dict with `posts` (array) and `stream` (array of post IDs in order). |
| `participant_count` | Unique posters. |
| `related_topics` | Pre-resolved list of similar threads (follow for context). |
| `suggested_topics` | Other threads Discourse thinks are related. |
| `timeline_lookup` | Array of `[post_number, timestamp]` pairs for timeline navigation. |

### `post_stream.posts[i]` — individual post

| Key | Purpose |
|---|---|
| `id` | Unique post ID. |
| `post_number` | 1-indexed position in the thread. `post_number: 1` is the original question. |
| `username` | Poster's username. |
| `name` | Display name (often empty). |
| `created_at` | ISO 8601 timestamp. |
| `updated_at` | If edited, differs from created_at. |
| `cooked` | **Rendered HTML body** — the actual content. Strip `<[^>]+>` for plain text. |
| `raw` | *Not included by default.* Request with `?include_raw=true`. |
| `reads` | How many users read this post. |
| `score` | Composite engagement score. |
| `reply_to_post_number` | If this is a reply to a specific post, its number. |
| `post_type` | 1 = regular, 3 = staff message, 4 = small action (user joined / closed / etc.). |
| `moderator` | Boolean — the poster is a forum moderator. |
| `admin` | Boolean — the poster is an admin / NVIDIA staff. |
| `staff` | Boolean — true if moderator OR admin. |
| `user_title` | Title-style label ("NVIDIA Employee", "Community Member"). |
| `accepted_answer` | Boolean — this post is marked as the solution. If any post has this, read it first. |
| `incoming_link_count` | How many other threads link here. |
| `wiki` | Boolean — community-editable. |

## Search JSON — `/search.json?q=<query>`

| Key | Purpose |
|---|---|
| `topics` | Array of topic stubs matching the query. |
| `posts` | Array of post stubs — **these include topic_id** for following to the full thread. |
| `users` | Matched users (rarely useful). |
| `categories` | Matched categories. |
| `tags` | Matched tags. |
| `grouped_search_result` | Aggregated facets — `more_posts`, `more_topics`, etc. for pagination. |

### `topics[i]` — topic stub (not the full topic)

Shape is a subset of the full topic JSON: `id`, `title`, `slug`, `posts_count`, `reply_count`, `highest_post_number`, `created_at`, `last_posted_at`, `bumped`, `pinned`, `unseen`, etc. **No `post_stream`.** To get content, follow to `/t/<slug>/<id>.json`.

### `posts[i]` — post stub with topic context

Has the post body (`blurb` — truncated plaintext) and `topic_id` so you can resolve to the full thread.

## Category JSON — `/c/<path>/<cat-id>.json`

| Key | Purpose |
|---|---|
| `topic_list` | Dict with `topics` (array). |
| `users` | Users with recent activity. |
| `primary_groups` | Group memberships (rarely useful). |

### `topic_list.topics[i]` — same shape as search topic stubs

Use this to browse "recent threads in category X".

## Categories listing — `/categories.json`

| Key | Purpose |
|---|---|
| `category_list.categories` | Array of top-level categories (subcategories listed via `subcategory_ids`). |

### `category_list.categories[i]`

| Key | Purpose |
|---|---|
| `id` | Stable numeric ID. |
| `slug` | URL slug. |
| `name` | Human name. |
| `description` | Short description. |
| `parent_category_id` | If this is a sub, points to parent. |
| `subcategory_ids` | Array of direct subcategory IDs. |
| `topic_count` | Total threads in the category. |
| `post_count` | Total posts. |

## Common extraction patterns

### "What did the user ask, and what did NVIDIA staff answer?"

```python
# From /t/<slug>/<id>.json
posts = data['post_stream']['posts']
op = posts[0]  # original poster — post_number: 1
question = re.sub(r'<[^>]+>', '', op['cooked'])
staff_replies = [p for p in posts if p.get('admin') or p.get('moderator')]
accepted = [p for p in posts if p.get('accepted_answer')]
```

### "Is this thread still current?"

Check `last_posted_at`. If older than ~18 months and the product has had major releases since, flag staleness to the user.

### "Find threads about X across the forum"

```
GET /search.json?q=<query>
→ iterate topics[] for ID + title
→ follow top N to /t/<slug>/<id>.json for full content
```

### "What's hot in Isaac Sim right now?"

```
GET /c/omniverse/isaac-sim/69.json
→ topic_list.topics — sorted by recent activity by default
```

### "Is this post the answer or just the original question?"

- `post_number: 1` → original question
- `accepted_answer: true` → marked solution (rare on this forum)
- `admin / moderator / staff: true` → NVIDIA reply (high-signal but not always the answer)
- Look at `reply_count` and `like_count` on individual posts for crowd-validation

## Tips

- **Filter before reading.** A thread with 30 posts is noisy. Read post 1 (question) + the first staff reply + the most-liked reply + the last post (often the resolution).
- **`cooked` contains HTML.** Strip tags for plain text; keep them (especially `<a>`) when the user asks for links.
- **`related_topics[]` is gold.** If the first thread doesn't fully answer, follow related_topics before running a new search.
- **Old NVIDIA Employee advice can still be correct.** Date alone doesn't make a post wrong, but a 2021 post about a 2024 API is suspect.
- **IDs are stable, slugs aren't.** Cache by ID.
