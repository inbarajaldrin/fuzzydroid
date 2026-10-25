# NVIDIA NGC Catalog Docs

Reliable live access to NVIDIA's distribution catalog at `https://catalog.ngc.nvidia.com/` — containers, models, resources (datasets), Helm charts, and collections. NGC is **not** a docs site; it's the place where Omniverse / Isaac / Cosmos / GR00T / CUDA / TensorRT / Triton / Riva / DeepStream binaries actually live.

## When to use this sub-skill

Trigger on: NGC, NGC Catalog (`catalog.ngc.nvidia.com`), the NGC Container Registry (`nvcr.io/...`), `docker pull nvcr.io/...`, container tag lookups ("what tags exist for `nvcr.io/nvidia/isaac-sim`", "what's the latest container for X"), image labels / arch / size, NGC hosted models (foundation-model checkpoints — GR00T N1 / Cosmos predict / etc. on NGC, **not** the HuggingFace mirror), NGC resources (datasets, code samples, playbooks), Helm charts (NGC-hosted K8s deployments — Triton, Riva, etc.), NGC collections (curated bundles like the Isaac Sim collection), or anyone wanting to know "what's available on NGC for X". Also triggers on the phrases "NGC CLI", `ngc registry`, `ngc collection`, container build labels (`com.nvidia.*` OCI labels), and "is X published on NGC".

Cross-ref out:
- For docs of the **product itself** (how to use Isaac Sim, what Cosmos can do) → the matching product sub-skill.
- For **community Q&A about NGC** (deprecation announcements, "container X broken in tag Y", staff workarounds) → `nvidia-forums`.
- For **HuggingFace-hosted versions of NVIDIA models** (LeRobot datasets, GR00T HF mirror) → the `lerobot` sibling skill or the product skill's HF section.

## Why this skill exists

NGC's metadata drifts faster than every product's docs. Container tags get added/yanked weekly; new model checkpoints land between docs releases; collections get re-bundled. Querying NGC directly is the only way to answer "what's actually published right now" reliably.

The other ten sub-skills mention NGC in passing (e.g., "verify the container tag on NGC") but have no fetch path for it — they end up citing tags that the product docs reference, which drift behind reality. This sub-skill closes that gap.

## The retrieval rule

NGC's surface is not uniform — it splits across three mechanisms:

| Surface | Mechanism | Anonymous? |
|---|---|---|
| **Container tags + manifests + labels** | Docker Registry v2 (`nvcr.io/v2/...`) with anonymous proxy_auth token | ✅ Yes — verified |
| **URL discovery (everything in the catalog)** | Sitemap (`catalog.ngc.nvidia.com/sitemap.xml`) | ✅ Yes — verified |
| **Catalog metadata pages** (HTML at `/orgs/.../containers/...`) | Next.js client-side rendered — WebFetch returns the shell only | ⚠️ Citation-only — content hydrates in browser |
| **Model / Helm / Resource / Collection deep metadata** (`api.ngc.nvidia.com/v2/...`) | REST API requiring NGC API key Bearer token | ❌ Auth-gated |

This makes NGC a **Pattern E** sub-skill — Docker Registry v2 + sitemap, with documented gaps for the auth-gated surfaces.

See `references/retrieval-rule.md` for the full anonymous Docker token flow and the sitemap-grep recipe.

## What's reachable vs gated (be honest with the user)

| Question shape | Path | Coverage |
|---|---|---|
| "What tags exist for container X?" | `nvcr.io/v2/<repo>/tags/list` (anon) | ✅ Full |
| "What's the latest tag of `nvidia/isaac-sim`?" | tags list → pick newest semver | ✅ Full |
| "What labels / arch / env / layer count does tag Y have?" | `nvcr.io/v2/<repo>/manifests/<tag>` v1+prettyjws (anon) | ✅ Full |
| "Does NGC have a container for X?" | sitemap grep + (anon) tag probe | ✅ Full |
| "What models are published on NGC for GR00T?" | sitemap grep `/models/` paths | ⚠️ URLs only — descriptions/files need API key |
| "What's in the Isaac Sim collection?" | sitemap (collection URLs exist) + nvidia-forums | ⚠️ Composition gated — cite collection URL + cross-ref |
| "Has this container been deprecated?" | sitemap absence + `nvidia-forums` search | ⚠️ Cross-ref forums |
| "Pricing / entitlement / NVAIE-gated content" | NGC user guide + forums | ❌ Tell user it requires an NGC account |

When a question falls into the gated rows, **say so explicitly**, give the URL the user can browse, and offer the forum-search fallback — don't hallucinate metadata from training memory.

## Workflow

1. Classify the question — is it a container query, a discovery query, or a deep-metadata query for a non-container resource?
2. **Container query** → use Pattern E (Docker Registry v2 anonymous). Get token, list tags, optionally fetch v1 manifest for labels.
3. **Discovery query** ("does NGC have X") → grep `sitemap.xml` for the term across `/containers/`, `/models/`, `/resources/`, `/helm-charts/`, `/collections/` paths.
4. **Gated query** (model contents / collection composition / dataset files) → return the public catalog URL as a citation, then route to `nvidia-forums` for community context, and tell the user the deep metadata needs an NGC API key.
5. **Tag lookup with version constraint** ("latest 4.x for Isaac Sim") → list tags, filter, return the newest matching the user's pattern; cite the catalog HTML URL so the user can verify in browser.
6. Cite **two URLs** when possible: the human-facing `catalog.ngc.nvidia.com/orgs/.../<resource>` (for the user to open), AND the `nvcr.io/...` registry path (the actual `docker pull` target).

## Reference files

- `references/live-sources.md` — entry-point catalog (top categories + canonical container/model paths across the NVIDIA Physical-AI stack) and the sitemap-grep recipe.
- `references/retrieval-rule.md` — full Pattern E rule with the anonymous Docker Registry v2 token flow + sitemap probe.
- `references/schema.md` — Docker Registry v2 response schemas (token, tags/list, manifest v2, manifest v1+prettyjws history) and NVIDIA-specific OCI label conventions (`com.nvidia.*`).

## Common pitfalls

- **`catalog.ngc.nvidia.com` HTML pages are Next.js CSR.** `curl` / `WebFetch` returns the bare shell ("GPU-optimized AI, ML, & HPC Software" title + an image tag — that's it). The actual container description hydrates in JavaScript. Don't try to extract metadata from the HTML — use the registry or sitemap.
- **`api.ngc.nvidia.com/v2/...` returns 401 unauthenticated.** It needs an NGC API key (Bearer token). This is different from `nvcr.io/proxy_auth`, which is anonymous. Don't confuse the two — they're separate services.
- **`nvcr.io` is the Container Registry, `catalog.ngc.nvidia.com` is the Catalog UI.** The catalog UI may show a container as "available" while the registry returns 404 for a specific tag — products move tags, yank old ones, or gate them behind NVAIE entitlement. The `nvcr.io/v2/<repo>/tags/list` response is authoritative for what's *actually pullable*.
- **NGC tags are not semver-clean.** Isaac Sim has tags like `4.5.0`, `4.5.0-stable`, `latest`, `2020.1_ea`, `2023.1.0-arm64`, `latest-arm64`. Don't assume monotonic ordering — list and sort by `Last-Modified` from the manifest if recency matters.
- **The sitemap has CI-test noise.** Lines starting with `orgs/0615409268808334/` are an automated test org (`test_container_*`, `test_collection_*`). Filter these out before showing the user results.
- **Container labels are in manifest v1 `history[0].v1Compatibility.config.Labels`, NOT manifest v2.** Manifest v2 only has layer digests + config blob digest; you'd need a second blob fetch to read labels there. For label inspection, request `application/vnd.docker.distribution.manifest.v1+prettyjws` — it's deprecated but still served by `nvcr.io` and contains a JSON-stringified v1 config per history entry. See `references/schema.md`.
- **`scope=repository:<repo>:pull` is the only scope that anonymous tokens are granted.** You cannot anonymous-list orgs, search the catalog, or read manifests for repos that haven't been made public (NVAIE-only). For those, `nvcr.io` returns 401 even with a fresh token request.
- **Don't route ROS/CUDA-toolkit container questions away from this skill.** All NVIDIA-published containers (PyTorch on NGC, TensorRT, Triton, Riva, DeepStream, CUDA-X) live in `nvcr.io` and are queryable the same way. This skill is the right home regardless of product.
- **Models / datasets on NGC are NOT Docker images.** They use NGC's own resource API which is auth-gated. `nvcr.io` won't help for `models/<...>` paths.
