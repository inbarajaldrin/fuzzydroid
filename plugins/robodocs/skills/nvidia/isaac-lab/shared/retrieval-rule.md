# Isaac Lab Docs — Retrieval Rule

## The rule

Pattern D — **plain HTML, WebFetch directly.** GitHub Pages serves the Sphinx-built docs at `https://isaac-sim.github.io/IsaacLab/main/`.

| HTML URL pattern | Fetch URL |
|---|---|
| `https://isaac-sim.github.io/IsaacLab/main/<path>.html` | same |

## Worked examples (verified 2026-04-23)

| HTML URL | Status |
|---|---|
| `…/main/index.html` | 200 · ~78 KB · 48 `<p>` · 8 `<h>` |
| `…/main/source/setup/installation/index.html` | 200 · plain HTML |
| `…/main/source/api/lab/isaaclab.envs.html` | 200 · plain HTML |
| `…/main/index.html.md` | 404 — `.md` suffix not supported |

## Versioning strategy

**Default: `/main/`** — tracks the main branch of the IsaacLab repo. GitHub Pages does not consistently publish tagged releases at `/v<ver>/` paths.

| URL form | When to use |
|---|---|
| `/main/<path>.html` | **Default.** Current main. |
| Repo at tagged ref | If the user needs a pinned version, fall back to `https://github.com/isaac-sim/IsaacLab/tree/v<ver>/docs/` and read the RST/MD source there. |

**Verification date: 2026-04-23.**

## Exceptions

- **No sitemap** — `/sitemap.xml` 404s. Use sidebar scraping.
- **No `_sources/*.rst.txt`** — 404. Only rendered HTML is exposed.
- **`.md` suffix does not work.**

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/index.html" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/html
```

### Enumerate the sidebar

```sh
curl -s "https://isaac-sim.github.io/IsaacLab/main/index.html" \
  | grep -oE 'href="[^"]*\.html[^"]*"' \
  | grep -v '^href="http' | grep -v '^href="#' \
  | sed 's/href="//;s/"$//' | grep -v '#' | sort -u
```

Sub-sections (e.g., tutorials, api, how-to) have their own sidebars — scrape each to get deep coverage.

### When the probe fails

Isaac Lab publishes docs on GitHub Pages tied to `main`. If pages move, check the IsaacLab repo for a new docs URL in the README.
