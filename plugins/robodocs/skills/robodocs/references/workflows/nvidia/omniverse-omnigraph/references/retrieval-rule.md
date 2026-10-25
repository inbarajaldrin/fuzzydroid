# Omniverse OmniGraph Docs — Retrieval Rule

## The rule

Pattern A — **append `.md` to any `.html` URL** under `docs.omniverse.nvidia.com`, with a **403 fallback to HTML** for the `/kit/docs/omni.graph/` Python-API tree.

| HTML URL pattern | `.md` status | Fetch strategy |
|---|---|---|
| `/extensions/latest/ext_omnigraph.html` | 200 | `.md` |
| `/extensions/latest/ext_omnigraph/<slug>.html` | 200 | `.md` |
| `/extensions/latest/ext_omnigraph/node-library/**` | 200 (per sampled pages) | `.md` |
| `/kit/docs/omni.graph/latest/**` | 403 | HTML |
| `/kit/docs/omni.graph.docs/latest/**` | 403 | HTML |

## Worked examples (verified 2026-04-23)

| HTML URL | `.md` URL | Status |
|---|---|---|
| `…/extensions/latest/ext_omnigraph.html` | append `.md` | 200 · text/markdown |
| `…/extensions/latest/ext_omnigraph/getting-started/core_concepts.html` | append `.md` | 200 · text/markdown |
| `…/kit/docs/omni.graph/latest/index.html` | append `.md` | **403** — use HTML |
| `…/kit/docs/omni.graph.docs/latest/index.html` | append `.md` | **403** — use HTML |

## Versioning strategy

**Default: `/latest/`** — OmniGraph docs track the current stable Kit release.

**Verification date: 2026-04-23.**

## Exceptions

- **Python-API pages at `/kit/docs/omni.graph/`** — 403 on `.md`. HTML fallback.
- **Architecture docs at `/kit/docs/omni.graph.docs/`** — 403 on `.md`. HTML fallback.
- **Node-library pages are numerous.** Individual node docs have URL pattern: `/extensions/latest/ext_omnigraph/node-library/nodes/<group>/<node-name>-<version>.html`. Construct on demand rather than catalog exhaustively.

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html.md" \
  | grep -iE "^(HTTP|content-type)"
# Expected: 200 + content-type: text/markdown; charset=UTF-8
```

### Enumerate OmniGraph sub-pages (sub-sections, not every node)

```sh
curl -s "https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html" \
  | grep -oE 'href="ext_omnigraph/[^"]*\.html"' \
  | sed 's/href="//;s/"$//' \
  | grep -v 'node-library/nodes/' \
  | sort -u
```

### Construct a specific node URL

When the user names a node like `DifferentialController` or `ReadIMUNode` in Isaac Sim (robot nodes), check the `isaac-sim` skill. For generic OG nodes like `Add`, `Branch`, `OnTick`, `OnImpulseEvent`:

1. Start at `node-library.html` index.
2. Follow to the group (`drivesim-datastudio-base`, `omni-graph-action`, `omni-graph-nodes`, etc.).
3. Node URL pattern: `…/ext_omnigraph/node-library/nodes/<group>/<name>-<version>.html`.

### When the probe fails

If `.md` returns 404 (not 403) on a known-good ext_omnigraph page, NVIDIA has changed URL structure. Re-probe the Omniverse root and update.
