# Retrieval rule (MuJoCo ecosystem)

The MuJoCo ecosystem spans **four host types**, each with a different fetch mechanism. Follow the rule for the host you're targeting.

## 1. `mujoco.readthedocs.io` (the canonical docs) — Pattern D, plain HTML

- **Use `WebFetch`** with a browser-class User-Agent.
- The root path (`/`) returns a 403 stub to bots — **do not start at the root**. Always fetch a specific page like `overview.html`, `computation.html`, `XMLreference.html`.
- The `.md` suffix trick **does not work** — `<page>.html.md` returns 404.
- The site is Cloudflare-fronted. If `WebFetch` is blocked, fall back to `Bash` with:
  ```bash
  curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
       "https://mujoco.readthedocs.io/en/stable/<page>.html"
  ```
- **Versioning**: use `/en/stable/` by default. Switch to `/en/latest/` for HEAD or `/en/3.5.0/` (etc.) for a pinned version.

### Cleaner alternative: raw RST source

For prose-heavy pages (overview, computation, modeling, programming guide), fetching the raw `.rst` source from GitHub is often cleaner than parsing rendered HTML. The Sphinx wrapper is stripped:

```bash
curl -s "https://raw.githubusercontent.com/google-deepmind/mujoco/main/doc/<page>.rst"
```

Known available: `overview.rst`, `computation.rst`, `modeling.rst`, `XMLreference.rst`, `APIreference.rst`, `mjx.rst`, `programming/*.rst`.

## 2. `github.com/google-deepmind/<repo>` (source code, READMEs) — `gh` CLI

For repo README, code files, or directory listings, prefer `gh` over `WebFetch`:

```bash
# README
gh api repos/google-deepmind/mujoco/readme --jq '.content' | base64 -d

# Raw file
curl -s "https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/franka_emika_panda/panda.xml"

# Directory listing
gh api repos/google-deepmind/mujoco_menagerie/contents | jq '.[] | .name'
```

Sub-repos covered: `mujoco`, `mujoco_menagerie`, `mujoco_mpc`, `mujoco_warp`, `mujoco_playground`, `dm_control`.

## 3. `github.com/.../<repo>/discussions` (community forum) — `gh` CLI

The MuJoCo forum migrated from `mujoco.org/forum` (now defunct) to **GitHub Discussions**.

```bash
# Search discussions across a repo
gh search discussions --repo google-deepmind/mujoco "contact instability"

# Get a specific discussion thread (number from the URL)
gh api repos/google-deepmind/mujoco/discussions/3094

# List recent discussions in a category
gh api 'repos/google-deepmind/mujoco/discussions?category_id=<id>&per_page=20'
```

Categories on the main repo: **Show and Tell**, **Q&A**, **Announcements** (where new releases like MuJoCo 3.5 are posted), **Ideas**.

If `gh` is unavailable, `WebFetch` on the discussion URL also works — discussions are server-rendered.

## 4. `mujoco.org` and `playground.mujoco.org` — Pattern D, plain HTML

Marketing / landing sites. `WebFetch` works directly. Limited content depth — usually link out to GitHub or ReadTheDocs.

## Common gotchas

- **403 on RTD root with `curl`** — RTD bot-filters the bare root. Always hit a specific `.html` page.
- **WebFetch caching** — the WebFetch tool caches for 15 minutes. If the user just changed a model and you're re-fetching, append a dummy query param or fetch via curl.
- **Stale discussions** — community threads can be years old; check the latest reply date before quoting an answer as current.
- **API stability** — MuJoCo's C API changed substantially in the 2.x → 3.x transition (Feb 2024). When citing function signatures, confirm the version match. Default to `stable` (currently 3.x).
- **MJX vs MJWarp** — these are sibling implementations. MJX-JAX runs on any XLA target; MJWarp is NVIDIA-specific. Don't confuse a question about one with docs for the other.
