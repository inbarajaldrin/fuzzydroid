# LeRobot Docs — Retrieval Rule

## The rule

Strip any trailing slash from the HTML docs URL, then **append `.md`**. Use the **unversioned** path (`/docs/lerobot/<slug>`), not the versioned variant (`/docs/lerobot/v0.5.1/en/<slug>`).

| HTML URL pattern | Fetch URL pattern |
|---|---|
| `https://huggingface.co/docs/lerobot/` | `https://huggingface.co/docs/lerobot/index.md` |
| `https://huggingface.co/docs/lerobot/<slug>` | `https://huggingface.co/docs/lerobot/<slug>.md` |
| `https://huggingface.co/docs/lerobot/<slug>/` | `https://huggingface.co/docs/lerobot/<slug>.md` |

## Worked examples

| HTML URL | Fetch URL | Verified |
|---|---|---|
| `https://huggingface.co/docs/lerobot/index` | `https://huggingface.co/docs/lerobot/index.md` | 200 text/markdown |
| `https://huggingface.co/docs/lerobot/installation` | `https://huggingface.co/docs/lerobot/installation.md` | 200 text/markdown |
| `https://huggingface.co/docs/lerobot/smolvla` | `https://huggingface.co/docs/lerobot/smolvla.md` | 200 text/markdown |
| `https://huggingface.co/docs/lerobot/lerobot-dataset-v3` | `https://huggingface.co/docs/lerobot/lerobot-dataset-v3.md` | 200 text/markdown |

## Versioning strategy

**Verification date: 2026-04-22.** Latest LeRobot version at time of probe: `v0.5.1`. Re-verify with the probe commands below if it has been more than ~3 months since this date, or if any `.md` fetch returns 404.

Three addressing modes exist:

| URL form | `.md` works? | Notes |
|---|---|---|
| `/docs/lerobot/<slug>` (unversioned) | YES | **Preferred** — resolves to latest, verified 200 for every slug tested 2026-04-22. |
| `/docs/lerobot/v0.5.1/en/<slug>` (pinned) | NO (404) | Only `index.md` works under this prefix; leaf pages 404. |
| `/docs/lerobot/main/en/<slug>` (main branch) | NO (404) | Same — only `index.md` works. |

**Strategy chosen: always-latest (unversioned).**

Decision rationale per `docs-skill-builder` Step 3 criteria: **only one URL form works.** Versioned leaf paths 404 for `.md`, so the decision is forced — there is no "both work, pick one" tradeoff here. If both forms had worked, always-latest would still be appropriate (LeRobot users generally want current APIs on a fast-moving library), but that consideration is moot given the probe result.

When HuggingFace cuts a new LeRobot version, `/docs/lerobot/<slug>.md` will silently switch to the new content. Re-enumerate the sidebar (below) after every minor release to refresh `live-sources.md`.

**If your probe contradicts this file:** trust the probe. HuggingFace's URL routing has changed before and may change again. Update this file's verification date and rewrite rule, then flag `docs-skill-builder/references/case-studies.md` if the HuggingFace entry needs a corresponding update.

If always-latest ever stops working (HuggingFace changes routing), fall back to versioning by capturing the current version in this file and expanding the rewrite rule.

## Exceptions

- **None observed for `.md` suffix on unversioned paths.** Every sidebar slug tested returned `200 text/markdown`.
- `sitemap.xml` endpoints are **not usable** (verified 2026-04-22):
  - `https://huggingface.co/docs/lerobot/sitemap.xml` returns HTML with a "doesn't exist in v0.5.1" notice.
  - `https://huggingface.co/docs/lerobot/main/en/sitemap.xml` returns 404.
  - **Future maintainers:** per the URL discovery hierarchy in `docs-skill-builder/references/retrieval-patterns.md` (sitemap → sidebar scrape → hub pages → GitHub repo), skip step 1 for this site and go directly to **step 2, sidebar scrape** (see next section). Do not waste time re-probing sitemap.xml unless you have reason to believe HuggingFace has fixed it.

## Detection / verification

### Verify pattern still works

```sh
curl -sI "https://huggingface.co/docs/lerobot/installation.md" | grep -iE "^(HTTP|content-type)"
# Expected: HTTP/2 200 + content-type: text/markdown; charset=utf-8
```

### Re-enumerate the sidebar (to refresh live-sources.md)

The HTML sidebar of any rendered doc page lists every other page. Extract the slugs:

```sh
curl -s "https://huggingface.co/docs/lerobot/index" -H "Accept: text/html" \
  | grep -oE 'href="/docs/lerobot/[^"]*"' \
  | grep -v '/_app/' \
  | grep -v 'v0\.5\.' \
  | sort -u
```

Output is a list like `href="/docs/lerobot/<slug>"`. Each slug becomes a catalog entry with rewrite target `/docs/lerobot/<slug>.md`.

### When the probe fails

If `curl -sI .../installation.md` returns anything other than `200 text/markdown`:

1. Re-run the six probes from `docs-skill-builder/references/retrieval-patterns.md` against `https://huggingface.co/docs/lerobot/`.
2. If pattern A still holds with a different prefix (e.g., versioned path now works), update this file's rewrite rule.
3. If pattern A no longer works at all, reclassify — LeRobot might have moved to a new routing scheme.
