# Omniverse Kit Docs — Retrieval Rule

## The rule

Pattern A — **append `.md` to any `.html` URL** under `docs.omniverse.nvidia.com`. The Omniverse Sphinx infrastructure serves clean `text/markdown` next to every HTML page.

| HTML URL pattern | Fetch URL pattern |
|---|---|
| `https://docs.omniverse.nvidia.com/<path>.html` | `https://docs.omniverse.nvidia.com/<path>.html.md` |

**Do not strip `.html`.** The `.md` suffix appends after `.html`. URLs that end in `/` do not support the rewrite.

## Worked examples (verified 2026-04-23)

| HTML URL | `.md` URL | Status |
|---|---|---|
| `…/kit/docs/kit-manual/latest/index.html` | `…/kit/docs/kit-manual/latest/index.html.md` | 200 · text/markdown |
| `…/kit/docs/carbonite/latest/index.html` | `…/kit/docs/carbonite/latest/index.html.md` | 200 · text/markdown |
| `…/extensions/latest/ext_replicator.html` | `…/extensions/latest/ext_replicator.html.md` | 200 · text/markdown |
| `…/kit/docs/omni.graph/latest/index.html` | `…/kit/docs/omni.graph/latest/index.html.md` | **403** — fall back to HTML |
| `…/py/replicator/latest/index.html` | `…/py/replicator/latest/index.html.md` | **403** — fall back to HTML |

## 403 fallback

When `.md` returns 403 (observed on some `/kit/docs/<ext>/` and `/py/<pkg>/` paths):

1. Fetch the HTML URL directly (`WebFetch` handles HTML→markdown conversion for Pattern D).
2. Content is still reachable — the 403 is on the `.md` alias, not the underlying page.
3. Document the exception in `live-sources.md` if you encounter it.

## Versioning strategy

**Default: `latest/` in the URL path.**

Most Kit docs publish under `/latest/`, which redirects/serves the current stable. Pinned versions exist (e.g., `/106.0/`) but are inconsistent across sub-products. Default to `/latest/` unless the user asks for a specific version.

**Verification date: 2026-04-23.**

## Exceptions

- **Sitemap exists and works**: `https://docs.omniverse.nvidia.com/sitemap.xml` returns 200. Use it for authoritative URL discovery across the whole Omniverse docs tree.
- **Some nested paths 403 on `.md`** — see the fallback above.
- **Trailing-slash URLs fail** — always target a specific `.html` page.

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/index.html.md" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/markdown; charset=UTF-8
```

### Use the sitemap for URL discovery

```sh
curl -s "https://docs.omniverse.nvidia.com/sitemap.xml" | grep -oE '<loc>[^<]+</loc>' \
  | sed 's/<loc>//;s|</loc>||' | grep -E 'kit-manual|carbonite|kit/docs|extensions' | sort -u
```

### When the probe fails

If `.md` returns 404 (not 403) on a known-good page, Omniverse has changed its URL scheme. Re-run the six probes from `docs-skill-builder/references/retrieval-patterns.md` and update this file.
