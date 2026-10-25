# NGC Catalog — Retrieval Rule

## The rule

Pattern E — **Docker Registry v2 with anonymous proxy_auth tokens, plus sitemap-grep for discovery.**

NGC is unique in this suite. Unlike the other ten product sub-skills, it does not have a single uniform fetch mechanism. Three surfaces, three behaviors:

| Surface | Mechanism | Anonymous? | What you get |
|---|---|---|---|
| Container tags, manifests, labels | `nvcr.io/v2/...` (Docker Registry v2) | ✅ — via `proxy_auth` token | Full structured metadata |
| URL discovery (everything in the catalog) | `catalog.ngc.nvidia.com/sitemap.xml` | ✅ — plain GET | One `<loc>` per page; ~3020 entries |
| Catalog UI HTML pages (`/orgs/.../containers/...`) | Next.js CSR | ⚠️ — citation-only | Bare shell; content hydrates in browser |
| Model / Helm / Resource / Collection deep metadata | `api.ngc.nvidia.com/v2/...` | ❌ — NGC API key required | (Not used by this skill) |

## URL translation table

| Goal | URL |
|---|---|
| Discover what exists | `https://catalog.ngc.nvidia.com/sitemap.xml` |
| Cite a container page to the user | `https://catalog.ngc.nvidia.com/orgs/<org>/(teams/<team>/)?containers/<image>` |
| Get anonymous registry token | `https://nvcr.io/proxy_auth?scope=repository:<repo>:pull&service=nvcr.io` |
| List image tags | `https://nvcr.io/v2/<repo>/tags/list` (Bearer required) |
| Read image manifest (layer digests) | `https://nvcr.io/v2/<repo>/manifests/<tag>` with `Accept: application/vnd.docker.distribution.manifest.v2+json` |
| Read image labels + arch + env (v1 fallback) | same URL with `Accept: application/vnd.docker.distribution.manifest.v1+prettyjws` |

The `<repo>` is the path **after** `nvcr.io/` — e.g., `nvidia/isaac-sim` or `nvidia/isaac/isaac-sim` depending on whether the image is org-level or team-scoped.

## Worked examples (verified 2026-05-13)

| URL | Status | Content-Type |
|---|---|---|
| `https://catalog.ngc.nvidia.com/sitemap.xml` | 200 | text/xml (459 KB) |
| `https://catalog.ngc.nvidia.com/` | 200 | text/html (Next.js CSR shell) |
| `https://catalog.ngc.nvidia.com/orgs/nvidia/teams/isaac/containers/isaac-sim` | 200 | text/html (CSR; no metadata in body) |
| `https://api.ngc.nvidia.com/v2/org/nvidia/repos/isaac-sim` | **401 Not Authenticated** | application/json |
| `https://api.ngc.nvidia.com/v2/search/catalog/resources/CONTAINER?q=isaac-sim` | **400** (well-formed but auth-gated) | application/problem+json |
| `https://nvcr.io/v2/nvidia/isaac-sim/tags/list` (no token) | 401 + `Www-Authenticate: Bearer realm="https://nvcr.io/proxy_auth"` | text/html |
| `https://nvcr.io/proxy_auth?scope=repository:nvidia/isaac-sim:pull&service=nvcr.io` | 200 | application/json (token) |
| `https://nvcr.io/v2/nvidia/isaac-sim/tags/list` (with token) | 200 | application/json — 79 tags |
| `https://nvcr.io/v2/nvidia/isaac-sim/manifests/4.5.0` (v1+prettyjws) | 200 | manifest with 68 history entries, full label set |

## Schema

See `references/schema.md` for the Docker Registry v2 response shapes — token, tags/list, manifest v2, manifest v1+prettyjws — and the NVIDIA-specific `com.nvidia.*` OCI label conventions.

## Versioning / freshness

- **Tags drift weekly.** A `tags/list` answer is only good until the next NVIDIA release. Always include the date when citing tag lists.
- **Sitemap updates within a day** of new catalog publications.
- **No version pinning** on either endpoint — they always serve the current state.

**Verification date: 2026-05-13.**

## Exceptions

- **NVAIE-entitled repos** (NVIDIA AI Enterprise) — `proxy_auth` rejects the scope request even for anonymous probes. Symptom: 401 from `proxy_auth` itself, not from `v2/...`. Tell the user the repo needs entitlement.
- **Pre-staged catalog entries** — sometimes a `/containers/<image>` URL exists in the sitemap before the registry has any tags. `tags/list` returns 404. NVIDIA publishes catalog UI entries before the binary lands.
- **Multi-platform manifests** — newer NVIDIA containers return a manifest list (`application/vnd.docker.distribution.manifest.list.v2+json`) when fetched without a specific platform `Accept`. To inspect a single arch's labels, follow the list to the per-arch manifest digest.
- **`latest` is not always semantically "newest"** — NVIDIA sometimes pins `latest` to the previous stable while newer tags are staged. If the user wants "the newest version", filter the tag list and pick the highest semver, don't pull `latest`.
- **Manifest v1+prettyjws is upstream-deprecated.** OCI dropped it from the spec. `nvcr.io` still serves it as of 2026-05-13, but plan a fallback path (fetch v2 manifest, then GET the config blob → read `config.Labels` from the OCI image config JSON).
- **CI-test org noise.** Every sitemap response includes ~30-50 lines under `orgs/0615409268808334/` (e.g., `test_collection_20251229_070044_285_eld_production`). Filter these — they're NVIDIA's own automated test fixtures.
- **Catalog UI HTML is Next.js client-side-rendered.** `curl` returns a 25 KB shell containing only `<title>NVIDIA NGC</title>`, the meta description "GPU-optimized AI, Machine Learning, & HPC Software", and the bundled JS chunks. Don't parse it for content.

## Detection / verification

### Verify the sitemap still works

```sh
curl -sI "https://catalog.ngc.nvidia.com/sitemap.xml" \
  | grep -iE "^(HTTP|content-type|content-length)"
# Expected: 200 + content-type: text/xml + content-length: ~450000+
```

### Get an anonymous registry token

```sh
TOKEN=$(curl -s "https://nvcr.io/proxy_auth?scope=repository:nvidia/isaac-sim:pull&service=nvcr.io" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
# token length ~1100-1200 chars; expires in 300s
```

### List tags for a repo

```sh
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://nvcr.io/v2/nvidia/isaac-sim/tags/list" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'name: {d[\"name\"]}')
print(f'tags ({len(d[\"tags\"])} total):')
for t in d['tags'][-10:]: print(f'  {t}')
"
```

### Inspect a manifest for labels + arch + env

```sh
curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.v1+prettyjws" \
  "https://nvcr.io/v2/nvidia/isaac-sim/manifests/4.5.0" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
h = d.get('history', [])
print(f'history entries: {len(h)}')
if h:
    c = json.loads(h[0]['v1Compatibility'])
    cfg = c.get('config', {})
    print(f'arch: {c.get(\"architecture\")}')
    print(f'env ({len(cfg.get(\"Env\", []))}):')
    for e in cfg.get('Env', [])[:8]: print(f'  {e}')
    print(f'labels ({len(cfg.get(\"Labels\", {}) or {})}):')
    for k, v in (cfg.get('Labels') or {}).items(): print(f'  {k} = {v}')
"
```

### Discover what NGC has for a product

```sh
# One-time sitemap cache per session
curl -s "https://catalog.ngc.nvidia.com/sitemap.xml" > /tmp/ngc.sitemap.xml

# Find everything related to "cosmos"
grep -oE '<loc>[^<]+</loc>' /tmp/ngc.sitemap.xml \
  | sed -E 's|<loc>||; s|</loc>||' \
  | grep -v '/orgs/0615409268808334/' \
  | grep -i cosmos
```

### When the probe fails

- **401 on `proxy_auth`** — the repo is NVAIE-gated. Tell the user.
- **404 on `tags/list`** — the catalog page exists but the registry path doesn't. Could be pre-staged (binary not yet published) or could be a registry-path mismatch (try with vs without the team segment).
- **403 on `manifests/<tag>`** — rare; usually means the tag was yanked. Re-list tags.
- **`proxy_auth` returns `{"errors":[...]}` instead of `{"token":"..."}`** — the scope syntax was wrong. Must be `repository:<repo>:pull` exactly; missing the `repository:` prefix or `:pull` suffix breaks it.
- **Manifest media-type confusion** — if you send a v2-only Accept and the registry has a manifest list, you get back the list, not a manifest. Set Accept to include all four media types and dispatch based on the `mediaType` field of the response.

## Rate limits

- **`nvcr.io`**: ~60 req/min anonymous for read operations. Token requests are cheap; reuse a token across multiple manifest reads (token TTL is 300 seconds per the `expires_in` field).
- **`catalog.ngc.nvidia.com/sitemap.xml`**: no enforced limit observed; treat as cacheable for a session.

## Why we don't use the auth-gated `api.ngc.nvidia.com`

Three reasons:

1. **Privacy / portability.** Requiring an NGC API key would make this skill tied to a user's NGC account; the rest of the suite is anonymous-first.
2. **Most useful queries don't need it.** Container tag discovery and label inspection cover the majority of "what's published on NGC" questions, and both work anonymously via `nvcr.io`.
3. **Forum fallback exists.** For deeply gated queries (model contents, dataset files, collection composition), `nvidia-forums` covers the community-knowledge angle without auth.

If a user explicitly wants to use their own NGC API key, point them at NGC's CLI (`ngc registry`, `ngc collection`) which is the supported path — this skill stays anonymous.
