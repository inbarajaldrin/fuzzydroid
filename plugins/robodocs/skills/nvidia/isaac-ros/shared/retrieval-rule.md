# Isaac ROS Docs — Retrieval Rule

## The rule

Pattern D — **plain HTML, WebFetch directly.** `https://nvidia-isaac-ros.github.io/*.html` is Sphinx-rendered full-body content on every page.

| HTML URL pattern | Fetch URL |
|---|---|
| `https://nvidia-isaac-ros.github.io/<path>.html` | same |

## Worked examples (verified 2026-04-23)

| HTML URL | Status |
|---|---|
| `/` | 200 · ~72 KB · 17 `<p>` |
| `/concepts/index.html` | 200 · plain HTML |
| `/getting_started/index.html` | 200 · plain HTML |
| `/reference_workflows/index.html` | 200 · plain HTML |
| `/index.md` | 404 — `.md` not supported |

## Versioning strategy

**Default: unversioned** — the GitHub Pages site tracks the current Isaac ROS release. No consistent `/v<ver>/` paths exposed. For historical versions, consult the `release_notes/` per-package pages.

**Verification date: 2026-04-23.**

## Exceptions

- **No sitemap.**
- **No `.md` suffix.**
- **`_sources/` not exposed.**

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://nvidia-isaac-ros.github.io/concepts/index.html" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/html
```

### Enumerate the sidebar

```sh
curl -s "https://nvidia-isaac-ros.github.io/" \
  | grep -oE 'href="[^"]*\.html[^"]*"' \
  | grep -v '^href="http' | grep -v '^href="#' \
  | sed 's/href="//;s/"$//' | grep -v '#' | sort -u
```

Sub-sections (concepts, reference_workflows, getting_started, repositories_and_packages, release_notes, troubleshooting) each have their own sidebar — scrape each for deep coverage.

### When the probe fails

If the body is <5 KB, the site moved to a SPA. Re-probe the root and the capability-specific URLs.
