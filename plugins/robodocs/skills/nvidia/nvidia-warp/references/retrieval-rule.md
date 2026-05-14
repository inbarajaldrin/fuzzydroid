# NVIDIA Warp Docs — Retrieval Rule

## The rule

Pattern D — **plain HTML**. `WebFetch` any `https://nvidia.github.io/warp/*.html` URL directly; no rewrite needed. The site is Sphinx-built (PyData theme) and server-renders full content.

| HTML URL pattern | Fetch URL pattern |
|---|---|
| `https://nvidia.github.io/warp/` | same (root redirects to `user_guide/installation.html`) |
| `https://nvidia.github.io/warp/<section>/<slug>.html` | same |
| `https://nvidia.github.io/warp/<slug>.html#<anchor>` | same — anchors are load-bearing on long pages |

## Worked examples (verified 2026-04-23)

| HTML URL | Probe result |
|---|---|
| `https://nvidia.github.io/warp/` | 200 · ~58 KB · 57 `<p>` · 7 `<h>` |
| `https://nvidia.github.io/warp/user_guide/basics.html` | 200 · plain HTML |
| `https://nvidia.github.io/warp/api_reference/warp.html` | 200 · plain HTML |
| `https://nvidia.github.io/warp/language_reference/builtins.html` | 200 · plain HTML · heavily anchored |

Pattern A (`.md` suffix) returns 404. Pattern B (JSON API) returns 404. Only Pattern D works.

### Partial Sphinx source exposure

Sphinx's `html_copy_source` is enabled for some pages. Top-level works; deep pages don't:

| URL | Status |
|---|---|
| `https://nvidia.github.io/warp/_sources/index.rst.txt` | 200 · text/plain |
| `https://nvidia.github.io/warp/_sources/modules/kernels.rst.txt` | 404 |

**Don't rely on `_sources/`**. It's unreliable. Use the rendered HTML instead.

## Versioning strategy

**Default: unversioned URLs (current main).**

GitHub Pages serves the `main` branch of the Warp repo. The project doesn't consistently publish `/vX.Y/` paths. If the user needs a specific version:

1. Check `user_guide/changelog.html` to find the release they want.
2. Fall back to reading the tagged version in the GitHub repo's `docs/` folder: `https://github.com/NVIDIA/warp/tree/v<version>/docs/`.

**Verification date: 2026-04-23.** Warp on that date was listed as v1.12-ish; re-run probes after major releases.

## Exceptions

- **Sitemaps don't exist** — `/sitemap.xml` and root `/sitemap.xml` both 404. Use the sidebar-scrape below.
- **`builtins.html` is very long** — hundreds of functions across ~15 anchored families. Always scope with an anchor.
- **`warp.sim` pages exist but mark the module as moving to Newton.** Treat `warp.sim` docs as legacy; check `changelog.html` before recommending its APIs.

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://nvidia.github.io/warp/user_guide/basics.html" | grep -iE "^(HTTP|content-type)"
# Expected: HTTP/2 200 + content-type: text/html; charset=utf-8
```

### Enumerate the sidebar (to refresh live-sources.md)

```sh
curl -s "https://nvidia.github.io/warp/" \
  | grep -oE 'href="[^"]*\.html[^"]*"' \
  | grep -v '^href="http' \
  | grep -v '^href="#' \
  | sed 's/href="//;s/"$//' \
  | grep -v '#' \
  | sort -u
```

Output is a flat slug list: `user_guide/basics.html`, `language_reference/builtins.html`, `api_reference/warp.html`, `domain_modules/fem.html`, `deep_dive/concurrency.html`, etc. Re-run after each Warp minor to pick up new pages.

### When the probe fails

If `curl -s https://nvidia.github.io/warp/user_guide/basics.html | wc -c` returns <5000 bytes:

1. Re-run the six probes from `docs-skill-builder/references/retrieval-patterns.md`.
2. Check whether NVIDIA/warp moved documentation hosting (possible — check `github.com/NVIDIA/warp` README for the canonical docs URL).
3. If the site shifted to a new location, update this file's URL root.
