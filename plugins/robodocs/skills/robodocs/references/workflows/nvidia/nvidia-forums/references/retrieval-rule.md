# NVIDIA Forums — Retrieval Rule

## The rule

Pattern B — **Discourse JSON API**. Append `.json` to any forum URL and Discourse returns the same page's data as structured JSON (`application/json`).

| HTML URL pattern | JSON URL pattern |
|---|---|
| `https://forums.developer.nvidia.com/t/<slug>/<id>` | `…/t/<slug>/<id>.json` |
| `https://forums.developer.nvidia.com/c/<path>/<cat-id>` | `…/c/<path>/<cat-id>.json` |
| `https://forums.developer.nvidia.com/latest` | `…/latest.json` |
| `https://forums.developer.nvidia.com/categories` | `…/categories.json` |
| `https://forums.developer.nvidia.com/search?q=<Q>` | `…/search.json?q=<Q>` |
| `https://forums.developer.nvidia.com/tag/<tag>` | `…/tag/<tag>.json` |
| `https://forums.developer.nvidia.com/u/<user>` | `…/u/<user>.json` |

## Worked examples (verified 2026-04-23)

| URL | Status | Content-Type |
|---|---|---|
| `/categories.json` | 200 | application/json |
| `/latest.json` | 200 | application/json |
| `/t/integration-between-isaacsim-and-create-xr/229108.json` | 200 | application/json |
| `/t/can-i-use-createxr-with-isaacsim/232462.json` | 200 | application/json |
| `/search.json?q=CreateXR%20IsaacSim` | 200 | application/json |
| `/c/omniverse/isaac-sim/69.json` | 200 | application/json |
| `/c/omniverse/xr-spatial-computing/707.json` | 200 | application/json |

## Schema

See `references/schema.md` for the full Discourse JSON schema — topic, post_stream, search response, category listing.

## Versioning / freshness

Discourse always serves the current state. There's no version pinning. Pay attention to the thread's `last_posted_at` field — threads that haven't been active in 2+ years may reference deprecated APIs.

**Verification date: 2026-04-23.**

## Exceptions

- **Admin endpoints** (`/admin/*`, some `/u/<user>/messages*`) return 401/403 — auth-gated. Skip.
- **Sitemap** (`/sitemap.xml`) works and is useful for bulk URL enumeration.
- **Gated categories** (staff-only) return a topic list but posts may 403 inside — rare, mostly announcements-level threads.
- **Stale category slugs return JSON body with `text/html` content-type.** Example: `/c/omniverse/isaac-sim/69.json` returns a 301 redirect to `/c/omniverse/simulation/69.json` (new canonical slug), and the redirected response's body IS valid JSON — but the `Content-Type` header says `text/html`. **Parse the body as JSON anyway, but prefer the canonical slug.** To find the current slug: `curl -sI https://forums.developer.nvidia.com/c/<id>.json | grep -i ^location` resolves the ID to its current slug.
- **Rule of thumb:** always include the numeric category ID in URLs. Discourse slugs are cosmetic; the ID is stable.

## Detection / verification

### Verify the JSON API still works

```sh
curl -sI "https://forums.developer.nvidia.com/categories.json" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: application/json; charset=utf-8
```

### Search for a topic

```sh
curl -s "https://forums.developer.nvidia.com/search.json?q=<QUERY>" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{t[\"id\"]:>8}  {t[\"title\"]}') for t in d.get('topics',[])[:10]]"
```

### Fetch a topic + extract posts

```sh
curl -s "https://forums.developer.nvidia.com/t/<slug>/<id>.json" \
  | python3 -c "
import json, sys, re
d = json.load(sys.stdin)
print(f'Title: {d[\"title\"]}')
print(f'Views: {d[\"views\"]}  Posts: {d[\"posts_count\"]}  Last: {d[\"last_posted_at\"]}')
for p in d['post_stream']['posts']:
    body = re.sub(r'<[^>]+>', '', p['cooked'])[:500]
    staff = ' [STAFF]' if p.get('admin') or p.get('moderator') else ''
    print(f'\n--- #{p[\"post_number\"]} by @{p[\"username\"]}{staff} on {p[\"created_at\"][:10]} ---')
    print(body)
"
```

### Enumerate all top-level categories

```sh
curl -s "https://forums.developer.nvidia.com/categories.json" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d['category_list']['categories']:
    print(f'  [{c[\"id\"]:4d}] {c[\"slug\"]:40s}  {c[\"name\"]}')
"
```

### When the probe fails

- **404** on `.json` after a slug change — the slug is cosmetic; re-fetch with just `/t/<id>.json` (Discourse accepts IDs alone).
- **429** — rate limited. Back off and retry.
- **Discourse version bump** — schema is stable but occasional fields get added. Treat as additive; existing keys keep working.

## Rate limits

Discourse default is ~60 requests/minute unauth'd. For this skill's typical usage (a few topic fetches per question), we won't hit it. For bulk enumeration (e.g., scraping an entire category for training data), use the `/sitemap.xml` path and stagger.
