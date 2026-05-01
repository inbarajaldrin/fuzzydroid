# Isaac Sim Docs — Retrieval Rule

## The rule

Pattern D — **plain HTML, WebFetch directly.** `https://docs.isaacsim.omniverse.nvidia.com/latest/*.html` returns substantial server-rendered content on every page.

| HTML URL pattern | Fetch URL |
|---|---|
| `https://docs.isaacsim.omniverse.nvidia.com/<version>/<path>.html` | same |

**Note:** the `.md` suffix used by `docs.omniverse.nvidia.com` does NOT work on this subdomain. Any `.html.md` returns 404.

## Worked examples (verified 2026-04-23)

| HTML URL | Status |
|---|---|
| `…/latest/index.html` | 200 · ~99 KB · 46 `<p>` · 9 `<h>` |
| `…/latest/installation/install_workstation.html` | 200 · plain HTML |
| `…/latest/python_scripting/manual_standalone_python.html` | 200 · plain HTML |
| `…/latest/reference_python_api.html` | 200 · plain HTML |
| `…/latest/index.html.md` | **404** — `.md` suffix not supported |

## Versioning strategy

**Default: `/latest/`** — redirects to current stable.

| URL form | When to use |
|---|---|
| `/latest/<path>.html` | **Default.** Current stable (Isaac Sim 5.1 at time of verification). |
| `/5.1.0/<path>.html` | Pinned version. Use when the user needs reproducibility. |
| `/5.0.0/<path>.html` | Previous stable. |
| `/6.0.0/<path>.html` | Early developer preview. Only use when user asks about upcoming features. |

**Verification date: 2026-04-23.** Latest Isaac Sim at time of verification: 5.1 (with 6.0 in early preview).

## Exceptions

- **`objects.inv` (Sphinx intersphinx inventory)** — `…/latest/objects.inv` returns 200. Not directly readable via WebFetch (binary format) but usable via intersphinx-enabled tooling for symbol→URL mapping.
- **`searchindex.js`** — 200 OK but large JS file; not useful for direct extraction.
- **`_sources/*.rst.txt`** — 404. Not exposed on this site.
- **No `/sitemap.xml`** — both `/latest/sitemap.xml` and `/sitemap.xml` 404. Use sidebar scraping (below) for URL discovery.

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_workstation.html" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/html
```

### Body-size sanity

```sh
curl -s "https://docs.isaacsim.omniverse.nvidia.com/latest/index.html" | wc -c
# Expected: > 50 KB. <5 KB means the site switched to a SPA shell.
```

### Enumerate the sidebar

```sh
curl -s "https://docs.isaacsim.omniverse.nvidia.com/latest/index.html" \
  | grep -oE 'href="[^"]*\.html[^"]*"' \
  | grep -v '^href="http' | grep -v '^href="#' \
  | sed 's/href="//;s/"$//' | grep -v '#' | sort -u
```

Run from any page to get internal slugs. Individual pages expose their sub-tree via the same scrape — e.g., scrape `robot_simulation/index.html` for the full robot-simulation subtree.

### When the probe fails

If the HTML body is <5 KB, the site moved to a SPA — re-run the six probes. If `.md` suddenly works, Isaac Sim has adopted the Omniverse-root `.md` behavior; update this rule.
