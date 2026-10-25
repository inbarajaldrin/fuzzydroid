# Docker Registry v2 + NGC Schema

The schemas this sub-skill consumes. Three Docker-Registry-v2 response shapes (token, tags/list, manifest), the NVIDIA-specific OCI label conventions, and the sitemap XML shape.

This is the **second Pattern B-ish skill** in the suite (alongside `nvidia-forums`), and the only one consuming the Docker Registry v2 protocol — so it gets its own schema file like the forums one.

## Anonymous token — `GET https://nvcr.io/proxy_auth?scope=...&service=nvcr.io`

Returned when probing the registry without credentials.

### Response shape

| Key | Purpose |
|---|---|
| `token` | The Bearer token. ~1100-1200 chars, signed JWT, opaque from the caller's POV. |
| `expires_in` | Seconds until expiry. Typically `300`. |
| `issued_at` | ISO 8601 timestamp of issuance. |
| `access_token` | Alias for `token` (some Docker clients use this name; prefer `token`). |

### Scope grammar

The `scope` query parameter MUST be `repository:<repo>:<action>`:

| Form | Example | Granted? |
|---|---|---|
| `repository:<repo>:pull` | `repository:nvidia/isaac-sim:pull` | ✅ for public repos |
| `repository:<repo>:pull,push` | — | ❌ requires auth |
| `registry:catalog:*` | — | ❌ never granted anonymously |
| Missing `repository:` prefix | `nvidia/isaac-sim:pull` | ❌ `proxy_auth` returns errors |

Only one scope at a time. To probe N repos, get N tokens (or pool by reuse within TTL).

## Tags list — `GET https://nvcr.io/v2/<repo>/tags/list`

Headers required: `Authorization: Bearer <token>`.

### Response shape

| Key | Purpose |
|---|---|
| `name` | The repo path, echoed back. |
| `tags` | Array of tag strings. **Not sorted by recency** — NVIDIA returns them in registry-insertion order which mostly tracks chronology but not reliably. For a "newest version" answer, parse-sort by semver or fetch each tag's manifest and sort by `Last-Modified` HTTP header on the manifest response. |

### Typical sizes

- Isaac Sim: 79 tags as of 2026-05-13
- Mature CUDA-X containers (PyTorch, TensorRT, Triton): 200-500 tags
- New product lines (GR00T, Cosmos): 5-30 tags

### Empty / 404 cases

- `404 {"errors":[{"code":"NAME_UNKNOWN", ...}]}` — repo doesn't exist or hasn't published a tag yet.
- `{"name":"<repo>","tags":null}` — repo exists, no tags published. Rare but valid.

## Manifest v2 — `GET https://nvcr.io/v2/<repo>/manifests/<tag>`

Headers: `Authorization: Bearer <token>` + `Accept: application/vnd.docker.distribution.manifest.v2+json`.

The default modern Docker manifest format. **Does NOT carry labels directly** — you'd need to fetch the `config` blob to get image labels. Use v1+prettyjws below for label inspection.

### Response shape

| Key | Purpose |
|---|---|
| `schemaVersion` | Always `2`. |
| `mediaType` | `application/vnd.docker.distribution.manifest.v2+json`. |
| `config` | `{ mediaType, size, digest }` — points to the OCI image config blob. |
| `layers` | Array of `{ mediaType, size, digest }` — one per filesystem layer (compressed). Sum gives total image size. |

### When you get a manifest list instead

If you fetch without `Accept` specifying v2-or-list, or the image is multi-arch, you may receive:

| Key | Purpose |
|---|---|
| `mediaType` | `application/vnd.docker.distribution.manifest.list.v2+json` or `application/vnd.oci.image.index.v1+json` |
| `manifests` | Array of per-platform descriptors: `{ digest, mediaType, platform: { architecture, os, [variant] } }` |

To inspect a specific platform, follow the digest: `GET /v2/<repo>/manifests/<digest>`.

## Manifest v1+prettyjws — `GET https://nvcr.io/v2/<repo>/manifests/<tag>`

Headers: `Authorization: Bearer <token>` + `Accept: application/vnd.docker.distribution.manifest.v1+prettyjws`.

**Upstream-deprecated but `nvcr.io` still serves it as of 2026-05-13.** This is the format that carries labels + env + arch inline (no extra blob fetch needed). Use this for label inspection.

### Response shape

| Key | Purpose |
|---|---|
| `schemaVersion` | Always `1`. |
| `name` | The repo. |
| `tag` | The tag. |
| `architecture` | e.g., `amd64`, `arm64`. |
| `fsLayers` | Array of `{ blobSum: <digest> }`, one per layer (reverse order — newest first). |
| `history` | Array of `{ v1Compatibility: "<JSON-stringified config>" }`, one per layer. |
| `signatures` | JWS signatures (ignore — historical). |

### `history[i].v1Compatibility` — JSON-stringified per-layer config

Parse each entry with `json.loads(...)`. **The first entry (`history[0]`) is the topmost / final image** and carries the merged config you usually care about.

| Key inside `v1Compatibility` JSON | Purpose |
|---|---|
| `id` | Layer ID (legacy). |
| `parent` | Parent layer ID. |
| `created` | ISO 8601 build timestamp of this layer. |
| `container_config` | The `docker build` step that created this layer (`Cmd` shows the actual `RUN`/`COPY`/`LABEL` step). |
| `config` | The image's runtime config — **labels, env, entrypoint, cmd, workingdir, exposedports live here**. |
| `architecture` | Same as top-level. |
| `os` | `linux`. |
| `throwaway` | If `true`, this layer is a metadata-only step (LABEL/ENV/etc.) — no filesystem change. |

### `config.Labels` — the NVIDIA metadata

| Pattern | Example | Where it's set |
|---|---|---|
| `com.nvidia.omniverse.build.*` | `com.nvidia.omniverse.build.branch=release-4.5`<br>`com.nvidia.omniverse.build.build=f59b3005`<br>`com.nvidia.omniverse.build.family=gl`<br>`com.nvidia.omniverse.build.build_tool_version=1.3.0`<br>`com.nvidia.omniverse.build.compliant=0` | Omniverse / Isaac Sim containers — internal build metadata. |
| `com.nvidia.isaac.*` | `com.nvidia.isaac.release` | Isaac product line. |
| `com.nvidia.cuda.version` | `com.nvidia.cuda.version=12.4` | Base CUDA version baked into the container. |
| `com.nvidia.cudnn.version` | `com.nvidia.cudnn.version=9.x.x.x` | cuDNN version. |
| `com.nvidia.volumes.needed` | `com.nvidia.volumes.needed=nvidia_driver` | Hint for legacy nvidia-docker v1; ignore in modern Docker. |
| `com.nvidia.deepstream.version` | `com.nvidia.deepstream.version=7.1` | DeepStream containers. |
| `maintainer` | `NVIDIA CORPORATION <sw-mobile-cuda@nvidia.com>` | Standard OCI label. |

There's no published catalog of NVIDIA labels — they're product-team conventions, additive. Treat unknown `com.nvidia.*` keys as informational.

### `config.Env`

Array of `"KEY=VALUE"` strings. Common NVIDIA-set env:

- `NVIDIA_VISIBLE_DEVICES=all`
- `NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics`
- `NVIDIA_REQUIRE_CUDA="cuda>=12.4 brand=tesla,driver>=535"` — drives the nvidia-container-runtime to reject incompatible hosts at run time.
- `CUDA_VERSION=12.4.1`

## Sitemap XML — `GET https://catalog.ngc.nvidia.com/sitemap.xml`

Standard sitemaps.org schema.

### Response shape

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://catalog.ngc.nvidia.com/containers</loc>
    <lastmod>...</lastmod>
    <changefreq>...</changefreq>
  </url>
  ...
</urlset>
```

In practice, NVIDIA's NGC sitemap returns mostly `<loc>` tags (no `<lastmod>` / `<changefreq>` on detail pages). For agent parsing, grep `<loc>` directly — that's the only line worth extracting.

### Path conventions in `<loc>`

| Pattern | Meaning |
|---|---|
| `/containers`, `/models`, `/resources`, `/helm-charts`, `/collections` | Top-level category indexes. |
| `/orgs/<org>/containers/<image>` | Org-scoped container detail page. |
| `/orgs/<org>/teams/<team>/containers/<image>` | Team-scoped container detail page. |
| Same shape for `/models/`, `/resources/`, `/helm-charts/`, `/collections/` | One detail page per resource. |
| `/orgs/0615409268808334/...` | **Automated test org** — filter out. |

## Common extraction patterns

### "What's the latest version of container X?"

```python
import requests, json, re

def get_token(repo):
    r = requests.get(f"https://nvcr.io/proxy_auth?scope=repository:{repo}:pull&service=nvcr.io")
    return r.json()["token"]

def list_tags(repo):
    tok = get_token(repo)
    r = requests.get(f"https://nvcr.io/v2/{repo}/tags/list",
                     headers={"Authorization": f"Bearer {tok}"})
    return r.json()["tags"] or []

# Semver-ish filter: keep tags matching N.N.N (drop _ea, -arm64, etc.)
tags = list_tags("nvidia/isaac-sim")
semver = [t for t in tags if re.fullmatch(r"\d+\.\d+\.\d+", t)]
semver.sort(key=lambda t: tuple(map(int, t.split("."))))
print(semver[-1])  # newest GA
```

### "What labels does tag Y have?"

```python
tok = get_token("nvidia/isaac-sim")
r = requests.get(
    "https://nvcr.io/v2/nvidia/isaac-sim/manifests/4.5.0",
    headers={"Authorization": f"Bearer {tok}",
             "Accept": "application/vnd.docker.distribution.manifest.v1+prettyjws"})
m = r.json()
top = json.loads(m["history"][0]["v1Compatibility"])
labels = top.get("config", {}).get("Labels", {}) or {}
print(labels)
```

### "Is product Z on NGC?"

```sh
curl -s https://catalog.ngc.nvidia.com/sitemap.xml \
  | grep -oE '<loc>[^<]+</loc>' \
  | sed -E 's|<loc>||; s|</loc>||' \
  | grep -v '/orgs/0615409268808334/' \
  | grep -iE "containers|models|resources|helm-charts|collections" \
  | grep -i "<product>"
```

### "Does container X support arm64?"

```python
# Fetch with Accept allowing manifest list
tok = get_token("nvidia/isaac/isaac-sim")
r = requests.get(
    "https://nvcr.io/v2/nvidia/isaac/isaac-sim/manifests/4.5.0",
    headers={"Authorization": f"Bearer {tok}",
             "Accept": ",".join([
                 "application/vnd.docker.distribution.manifest.list.v2+json",
                 "application/vnd.oci.image.index.v1+json",
                 "application/vnd.docker.distribution.manifest.v2+json"])})
m = r.json()
if m.get("mediaType", "").endswith("list.v2+json") or m.get("manifests"):
    archs = sorted({p["platform"]["architecture"] for p in m["manifests"]})
    print("Multi-arch:", archs)
else:
    print("Single-arch:", m.get("config", {}))  # arch via config blob
```

## Tips

- **Cache the token by repo for the session** (300s TTL). Don't re-request on every manifest read.
- **Always sort tags yourself.** `tags[]` is not chronologically sorted.
- **Multi-arch detection** — check the response `mediaType` first; dispatch on whether it's a list or a manifest.
- **Stringified JSON inside JSON.** `history[i].v1Compatibility` is a JSON-encoded string, not a nested object. `json.loads()` is required before reading config / labels.
- **Treat `com.nvidia.omniverse.build.compliant=0` as "developer build, not certified for NVAIE"** — `1` means it passed NVIDIA's enterprise compliance gate.
- **OCI label keys are dotted reverse-domain.** When matching, anchor at `com.nvidia.` and split on `.` to discover the product family.
- **Manifest v1+prettyjws may disappear.** If it does, fetch the v2 manifest, then `GET /v2/<repo>/blobs/<config.digest>` (also requires the same Bearer token) — that blob is the OCI image config JSON with `config.Labels` at the same path.

## Why this skill consumes v1+prettyjws despite OCI deprecating it

The OCI spec removed v1+prettyjws from official support, but `nvcr.io` continues to serve it because:

1. **Backward compatibility** — older Docker clients (pre-1.10) only spoke v1.
2. **Convenience** — v1's history blob carries the config inline, saving one round-trip per image inspection.

If NVIDIA ever shuts this off, fall back to the manifest-v2 → config-blob flow shown in the "Common extraction patterns" section. The data is identical; it's just two requests instead of one.
