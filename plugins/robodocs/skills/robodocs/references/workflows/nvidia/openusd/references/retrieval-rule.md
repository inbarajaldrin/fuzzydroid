# OpenUSD Docs — Retrieval Rule

## The rule

Pattern D — **plain HTML**. `WebFetch` any `https://openusd.org/release/*.html` URL directly; no rewrite needed. The site is fully server-rendered static HTML (Doxygen + custom pages). WebFetch returns real body content, not an empty SPA shell.

| HTML URL pattern | Fetch URL pattern |
|---|---|
| `https://openusd.org/release/<slug>.html` | same |
| `https://openusd.org/release/user_guides/<slug>.html` | same |
| `https://openusd.org/release/user_guides/schemas/<domain>/<SchemaName>.html` | same |
| `https://openusd.org/release/api/<doxygen-path>.html` | same |

## Worked examples (verified 2026-04-23)

| HTML URL | Probe result |
|---|---|
| `https://openusd.org/release/index.html` | 200 · ~105 KB body · 28 `<p>` · 1 `<h>` |
| `https://openusd.org/release/tut_helloworld.html` | 200 · plain HTML |
| `https://openusd.org/release/user_guides/schemas/usdLux/SphereLight.html` | 200 · plain HTML |
| `https://openusd.org/release/glossary.html` | 200 · plain HTML |

Pattern A (`.md` suffix) and Pattern B (JSON API) both fail on this site (404 for all attempts).

## Versioning strategy

**Default: `/release/` (current-stable).**

Three addressing modes exist:

| URL form | When to use |
|---|---|
| `/release/<slug>.html` | **Default.** Current stable release. Use unless the user asks for something else. |
| `/dev/<slug>.html` | Development branch. Only use when the user explicitly asks about an upcoming feature or a recent change merged to dev. |
| `/v25.05/<slug>.html` (etc.) | Pinned version. Use when the user needs reproducibility against a specific historical release — API surface changes rarely but does change. |

**Verification date: 2026-04-23.** Re-run the probe commands below if any fetch returns unexpected content.

## Exceptions

- **Sitemaps don't exist** — `/sitemap.xml` and `/release/sitemap.xml` both return 404. Use sidebar scraping (below) for URL discovery.
- **API reference is Doxygen** — `/release/api/**` is machine-generated, deeply nested, and not well suited to narrative summarization. For API-level questions, prefer user-guide / tutorial pages when they exist; drop to the Doxygen page only for specific signatures.
- **Anchors are load-bearing** — many pages (like `usdfaq.html`) are one long page with ~30 anchored sections. When the user asks a specific question, include the anchor in your extraction prompt so you don't over-fetch.

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://openusd.org/release/tut_helloworld.html" | grep -iE "^(HTTP|content-type)"
# Expected: HTTP/2 200 + content-type: text/html
```

### Body-size sanity (confirms server-side render vs SPA shell)

```sh
curl -s "https://openusd.org/release/index.html" | wc -c
# Expected: > 50 KB. If ~2 KB, the site has shifted to a SPA and Pattern D is broken.
```

### Enumerate the sidebar (to refresh live-sources.md)

The left nav is server-rendered; scrape internal `.html` links from any page:

```sh
curl -s "https://openusd.org/release/index.html" \
  | grep -oE 'href="[^"]*\.html[^"]*"' \
  | grep -v '^href="http' \
  | sed 's/href="//;s/"$//' \
  | grep -vE '^#' \
  | sort -u
```

Output is a list of slugs like `tut_helloworld.html`, `user_guides/color_user_guide.html`, `spec_usdz.html`. Each becomes a catalog entry.

Pair with `user_guides/schemas/<domain>/` enumeration for schema-specific coverage:

```sh
curl -s "https://openusd.org/release/user_guides/schemas/usdLux/usdLux_toc.html" \
  | grep -oE 'href="[^"]*\.html"' | sed 's/href="//;s/"$//' | sort -u
```

### When the probe fails

If `curl -s https://openusd.org/release/tut_helloworld.html | wc -c` returns <5000 bytes:

1. Re-run the six probes from `docs-skill-builder/references/retrieval-patterns.md`.
2. Check whether the site has moved to a SPA — `grep -oE '__NEXT_DATA__|__INITIAL_STATE__|__NUXT__'` in the HTML.
3. If site structure changed, reclassify and update this file's rule.
