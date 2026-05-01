# Omniverse Replicator Docs — Retrieval Rule

## The rule

Pattern A — **append `.md` to any `.html` URL** under `docs.omniverse.nvidia.com`. Verified 200 `text/markdown` for the Replicator extension page and every sub-page under `ext_replicator/`.

| HTML URL pattern | Fetch URL pattern |
|---|---|
| `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html` | append `.md` |
| `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/<slug>.html` | append `.md` |

## Worked examples (verified 2026-04-23)

| HTML URL | `.md` URL | Status |
|---|---|---|
| `…/extensions/latest/ext_replicator.html` | `…/ext_replicator.html.md` | 200 · text/markdown |
| `…/extensions/latest/ext_replicator/getting_started.html` | (append `.md`) | 200 · text/markdown |
| `…/py/replicator/latest/index.html` | `…/index.html.md` | **403** — fall back to HTML |

## 403 fallback

The `/py/replicator/latest/` Python API tree returns 403 on `.md`. For those pages:

1. Fetch the HTML URL directly (`WebFetch` converts HTML→markdown on its own).
2. Prefer the `ext_replicator/` overview pages (which cover the same APIs in context) when possible.

## Versioning strategy

**Default: `/extensions/latest/`.** Omniverse Replicator publishes docs at `/latest/` which tracks the current stable Kit / Replicator release. There are no widely-published pinned version URLs for Replicator — if the user needs pinned content, check the Kit release notes or the NGC container manifest.

**Verification date: 2026-04-23.**

## Exceptions

- **Python API (`/py/replicator/`)** — 403 on `.md`. HTML works.
- **Sitemap coverage** — Replicator pages appear under the root `https://docs.omniverse.nvidia.com/sitemap.xml`. Filter for `/ext_replicator` to enumerate.

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html.md" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/markdown; charset=UTF-8
```

### Enumerate Replicator sub-pages

```sh
curl -s "https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html" \
  | grep -oE 'href="ext_replicator/[^"]*\.html"' \
  | sed 's/href="//;s/"$//' | sort -u
```

### When the probe fails

If `.md` returns 404 (not 403) on a known-good page, NVIDIA changed the URL scheme. Re-probe the whole `docs.omniverse.nvidia.com` root and update the rule.
