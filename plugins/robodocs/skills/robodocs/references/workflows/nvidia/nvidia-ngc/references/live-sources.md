# NGC Catalog — Live Sources

Curated entry points for the NVIDIA NGC Catalog. NGC splits across two domains:

- `https://catalog.ngc.nvidia.com/` — the browse UI (Next.js CSR; cite-only)
- `https://nvcr.io/` — the Container Registry (Docker Registry v2; anonymous-queryable)

Apply `retrieval-rule.md` to translate user intent into one of three flows: **Docker Registry v2** (for tags/manifests), **sitemap-grep** (for discovery), or **forum-fallback** (for gated content).

Verified 2026-05-13.

---

## Discovery-first workflow

Most NGC questions are best served by hitting the sitemap first — it's the single canonical source of which catalog pages exist. Then route by what was found:

| Question shape | Where to look first |
|---|---|
| "Is there a container for X?" | sitemap → `/containers/` lines |
| "Are there hosted models for X?" | sitemap → `/models/` lines |
| "What's the latest tag of `<repo>`?" | `nvcr.io/v2/<repo>/tags/list` |
| "What labels / arch / env vars does tag Y carry?" | `nvcr.io/v2/<repo>/manifests/<tag>` (v1+prettyjws) |
| "What's in this collection?" | sitemap → `/collections/` lines (URL only) + nvidia-forums fallback |

## The single sitemap entry point

| Topic | URL | Extraction Prompt |
|---|---|---|
| Full catalog sitemap | `https://catalog.ngc.nvidia.com/sitemap.xml` | "Returns 200 text/xml, ~459 KB. Each `<loc>` is one public catalog page. Filter to the path types you care about (`containers/`, `models/`, `resources/`, `helm-charts/`, `collections/`). Strip the noisy `orgs/0615409268808334/` (automated test org) entries. URLs are stable; new entries appear within a day of publication." |

## Catalog top-level entry pages (citation-only — HTML is CSR)

These exist for citing in user-facing replies. Don't try to scrape content from them.

| Section | URL |
|---|---|
| Containers | `https://catalog.ngc.nvidia.com/containers` |
| Models | `https://catalog.ngc.nvidia.com/models` |
| Resources | `https://catalog.ngc.nvidia.com/resources` |
| Helm Charts | `https://catalog.ngc.nvidia.com/helm-charts` |
| Collections | `https://catalog.ngc.nvidia.com/collections` |

## Container Registry v2 — the workhorse

Anonymous flow per `retrieval-rule.md` Pattern E. These are the canonical NGC container paths across the robotics + Physical-AI stack.

### Isaac

| Container | Catalog URL (cite) | Registry path (pull) | Notes |
|---|---|---|---|
| Isaac Sim | `https://catalog.ngc.nvidia.com/orgs/nvidia/teams/isaac/containers/isaac-sim` | `nvcr.io/nvidia/isaac-sim` (verified) | 79 total tags as of 2026-05-13. **Tag families don't sort naively**: legacy year-style (`2020.x_ea`, `2021.x.x`, `2022.x.x`) coexists with the modern Omniverse-aligned family (`4.x.x`). Sort by family first, then by numeric tail. Manifest `v1+prettyjws` labels include `com.nvidia.omniverse.build.{branch,build,build_tool_version,compliant,family,release,service}` and `org.opencontainers.image.ref.name=ubuntu`. |
| Isaac Lab | `https://catalog.ngc.nvidia.com/orgs/nvidia/teams/isaac/containers/isaac-lab` | `nvcr.io/nvidia/isaac/isaac-lab` (sitemap-probe before claiming) | RL/IL training container. Tags follow Lab release cadence. |
| Isaac ROS Dev | `https://catalog.ngc.nvidia.com/orgs/nvidia/teams/isaac/containers/ros` | `nvcr.io/nvidia/isaac/ros` (sitemap-probe before claiming) | ROS 2 Humble + Isaac ROS packages. Tags include `<jetson-arch>-<ros-distro>-<release>` patterns. |
| Isaac ROS resources (model weights, sample datasets) | `https://catalog.ngc.nvidia.com/orgs/nvidia/teams/isaac/resources/...` | n/a (not Docker images) | Rich catalog: `isaac_ros_visual_slam_assets`, `isaac_ros_foundationpose_assets`, `isaac_manipulator_ur_dnn_policy_assets`, `dnn_stereo_disparity` model, etc. Discoverable via sitemap; deep file metadata requires NGC API key. |

### Foundation models

| Family | What exists on NGC (verified 2026-05-13) | Notes |
|---|---|---|
| **Cosmos** | Team `nvidia/teams/cosmos/` is populated. Collection: `cosmos`. Models include `cosmos-1.0-autoregressive-12b` and friends under `…/teams/cosmos/models/…`. Containers may exist under `…/teams/cosmos/containers/…` — sitemap-grep before claiming a specific path. | Cite the catalog URL; deep file metadata is API-key gated. Cross-ref the `nvidia-cosmos` sub-skill for usage. |
| **Cosmos Embed (via TAO)** | `nvidia/teams/tao/models/cosmos-embed1` | Embedding variant published under TAO team. |
| **GR00T** | **Not on NGC under that name** as of 2026-05-13. The HuggingFace mirror (`nvidia/GR00T-N1.5-3B` etc.) is the canonical published surface. | Don't fabricate an `nvcr.io/nvidia/gr00t/...` path. If a user asks where to get GR00T, point them at HuggingFace + the `isaac-groot` sub-skill. |
| **NeMo / NeMoTron** | Heavy presence under `nvidia/teams/nemo/models/...` (Llama / Nemotron-H / Phi / classifiers) and `nvidia/collections/nemo_*`. | Out of robotics scope but commonly co-installed; cite if asked. |

(Sitemap-grep when probing for anything not listed — these teams add new resources regularly.)

### Omniverse

| Container | Catalog URL | Registry path |
|---|---|---|
| Omniverse Kit base | `https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/containers/kit` | `nvcr.io/nvidia/omniverse/kit` |
| Replicator | `https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/containers/replicator` | `nvcr.io/nvidia/omniverse/replicator` |

### Adjacent NVIDIA stacks (out of robotics but commonly co-installed)

| Container | Registry path |
|---|---|
| PyTorch on NGC | `nvcr.io/nvidia/pytorch` |
| TensorRT | `nvcr.io/nvidia/tensorrt` |
| Triton Inference Server | `nvcr.io/nvidia/tritonserver` |
| Riva | `nvcr.io/nvidia/riva/riva-speech` |
| DeepStream | `nvcr.io/nvidia/deepstream` |
| CUDA base | `nvcr.io/nvidia/cuda` |

## Sitemap-grep recipes (anonymous, no token)

```sh
# Cache the sitemap once per session
curl -s https://catalog.ngc.nvidia.com/sitemap.xml > /tmp/ngc.sitemap.xml

# Extract every public URL, drop the CI-test org noise
grep -oE '<loc>[^<]+</loc>' /tmp/ngc.sitemap.xml \
  | sed -E 's|<loc>||; s|</loc>||' \
  | grep -v '/orgs/0615409268808334/' \
  > /tmp/ngc.urls.txt
wc -l /tmp/ngc.urls.txt   # ~3020 lines as of 2026-05-13

# Find every container related to "isaac" or "groot"
grep -E '/containers/' /tmp/ngc.urls.txt | grep -iE 'isaac|gr00t'

# Find every model related to "cosmos"
grep -E '/models/' /tmp/ngc.urls.txt | grep -i cosmos

# Find every collection
grep -E '/collections/' /tmp/ngc.urls.txt | grep -v '/orgs/0615409268808334/'
```

## Discovery pattern

When a user mentions a product that isn't listed above:

1. **Sitemap-grep** for the product name across the four resource type paths.
2. If you get container hits, **probe `nvcr.io/v2/<repo>/tags/list`** for the freshest tag info.
3. If you get model/resource/collection hits and the user wants the *contents*, cite the catalog URL and tell the user the deep metadata is API-key gated — offer to fall back to `nvidia-forums` for community context.
4. If you get nothing, **don't guess**. NGC doesn't have everything. Common gaps: experimental product previews (announced on GitHub but not yet promoted to NGC), HuggingFace-only model releases, NVAIE-gated content.

## High-signal canonical examples

These are real, verified queries that demonstrate the full Pattern E flow.

| Query | Path | Notes |
|---|---|---|
| Latest Isaac Sim 4.x tag | `nvcr.io/v2/nvidia/isaac-sim/tags/list` → filter `^4\.` | Returned 79 total tags as of 2026-05-13; `4.5.0` is the newest GA. |
| Inspect Isaac Sim `4.5.0` build metadata | `nvcr.io/v2/nvidia/isaac-sim/manifests/4.5.0` (v1+prettyjws) | Labels include `com.nvidia.omniverse.build.branch=release-4.5`, `com.nvidia.omniverse.build.build=f59b3005`. |
| Find all Cosmos containers | Sitemap grep `/containers/.*cosmos` | Returns 4-6 containers; cross-ref `nvidia-cosmos` sub-skill for what each does. |
| GR00T model checkpoint listing | Sitemap grep `/models/.*gr00t` | Returns URLs only. For files / sha / size → `nvidia-forums` or NGC API with key. |

---

## Notes on extraction

- **Always extract `name` + `tags[]` first** when querying the registry. Then if the user needs metadata, fetch the manifest for a specific tag.
- **Cite the catalog URL** (`catalog.ngc.nvidia.com/orgs/...`) for the human, AND the `nvcr.io/...` registry path for the `docker pull` command.
- **For container labels**, request `application/vnd.docker.distribution.manifest.v1+prettyjws` — labels live inside `history[0].v1Compatibility.config.Labels`, JSON-stringified. The newer v2 format only carries layer digests.
- **Include the date** when reporting tag lists, since they change weekly: "As of 2026-05-13, the latest tag is X."
- **Strip the CI-test org** (`orgs/0615409268808334/`) from any sitemap results before showing the user.

## Exceptions

- **NVAIE-entitled repos** (NVIDIA AI Enterprise SKU) return 401 even with a fresh anonymous token — the `proxy_auth` endpoint rejects the scope request. Tell the user the repo needs NVAIE entitlement.
- **Pre-release / staged repos** sometimes 404 on `tags/list` even though they appear in the sitemap. NVIDIA stages catalog UI entries before opening the registry path.
- **Manifest v1+prettyjws is deprecated upstream by OCI** but `nvcr.io` still serves it. If NVIDIA shuts this off, fall back to fetching the manifest v2 `config` blob and reading labels from the OCI image config JSON.
- **Rate limits** on `nvcr.io` exist but are generous for anonymous tag-list / manifest reads. For bulk enumeration, throttle to ~30 req/min.

## Version drift

NGC's catalog UI version is irrelevant; what matters is:

- **Docker Registry v2 protocol** — stable since 2015, additive only.
- **NVIDIA's container-label conventions** (`com.nvidia.*`) — additive; new labels appear with new product releases. See `references/schema.md`.
- **Sitemap location** (`/sitemap.xml`) — stable since the Next.js rewrite; if it moves, `robots.txt` will point to the new location.
- **Container path conventions** — `nvcr.io/<org>/<team>/<image>` for team-scoped or `nvcr.io/<org>/<image>` for top-level org images. Verified stable.
