# Omniverse Kit Docs — Live Sources

Curated entry points into the Omniverse Kit SDK documentation. Every URL below is an **HTML URL** — apply the `.md` suffix rewrite from `retrieval-rule.md` before `WebFetch`, with HTML fallback on 403.

When the user asks about a `carb.*` / `omni.kit.*` / `omni.*` symbol not listed, consult `API.html` (the auto-generated index) or scrape via the sitemap.

Verified 2026-04-23.

---

## Kit Manual — Core

| Topic | URL | Extraction Prompt |
|---|---|---|
| Kit Manual landing | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/index.html` | "Extract the Kit overview — what Kit is, its relationship to Omniverse, and the top-level sidebar sections (Getting Started, Extension Creation, Carbonite, API Reference, etc.)." |
| API reference index | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/API.html` | "Extract the top-level API index — list every `carb.*`, `omni.kit.*`, `omni.*` module group with a one-line purpose." |

## Carbonite (`carb.*` runtime)

| Topic | URL | Extraction Prompt |
|---|---|---|
| Carbonite landing | `https://docs.omniverse.nvidia.com/kit/docs/carbonite/latest/index.html` | "Extract what Carbonite is — the C++ runtime foundation under Kit, threading model, plugin/interface system, and how Python bindings relate." |
| `carb.audio` overview | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/carb.audio.html` | "Extract audio playback / capture interfaces — IAudioPlayback, Voice, Context, SoundData." |
| `carb.dictionary` | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/carb.dictionary.html` | "Extract dictionary serialization (JSON / TOML / YAML) and IDictionary interface." |
| `carb.settings` | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/carb.settings.html` | "Extract the settings interface — get/set, subscriptions, persistence." |
| `carb.tokens` | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/carb.tokens.html` | "Extract token resolution semantics (`${env:...}`, `${app:...}`) and the ITokens interface." |
| `carb.windowing` | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/carb.windowing.html` | "Extract window / monitor enumeration and IWindowing surface." |
| `carb.input` | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/carb.input.html` | "Extract input event handling — keyboard, mouse, gamepad abstractions." |

## Extension Authoring

| Topic | URL | Extraction Prompt |
|---|---|---|
| Extensions landing | `https://docs.omniverse.nvidia.com/extensions/latest/index.html` | "Extract the extensions index — list top-level extension families with a one-line purpose each." |
| Extensions — common technical requirements | `https://docs.omniverse.nvidia.com/extensions/latest/common/technical-requirements.html` | "Extract hardware / driver requirements for running Omniverse Kit applications." |
| Formats (asset / file formats reference) | `https://docs.omniverse.nvidia.com/extensions/latest/common/formats.html` | "Extract the list of supported file formats across Omniverse (USD, FBX, OBJ, glTF, Alembic, etc.) and converter mappings." |
| Glossary | `https://docs.omniverse.nvidia.com/extensions/latest/common/glossary-of-terms.html` | "Extract definitions for the specific term the user asked about." |

## Omniverse Top-Level Reference

| Topic | URL | Extraction Prompt |
|---|---|---|
| Sitemap | `https://docs.omniverse.nvidia.com/sitemap.xml` | "Enumerate all Omniverse doc URLs. Use as discovery source when a user's topic doesn't match the curated catalog." |
| Release-notes / news page (check for latest) | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/released.html` | "Extract the most recent release notes and changelog entries." |

## XR / VR / Spatial Streaming

The supported VR paths in Omniverse (2026) are Apple Vision Pro + iPad via CloudXR (fully documented under `/avp/`) and developer-level XR via `omni.kit.xr.*` extensions (HTML-only — `.md` 403s). The legacy "Create XR" app at `/app_omniverse-xr/` is gated (403) and should not be recommended.

### Spatial Streaming (Apple Vision Pro / iPad via CloudXR)

| Topic | URL | Extraction Prompt |
|---|---|---|
| AVP landing | `https://docs.omniverse.nvidia.com/avp/latest/index.html` | "Extract what Omniverse Spatial Streaming is, the supported clients (Vision Pro / iPad), and the doc set structure." |
| Requirements | `https://docs.omniverse.nvidia.com/avp/latest/requirements.html` | "Extract OS / driver / Kit SDK / GPU / CPU / RAM / network requirements, firewall ports, and supported client devices." |
| Setup SDK (server side) | `https://docs.omniverse.nvidia.com/avp/latest/setup-sdk.html` | "Extract the server-side steps — kit-app-template clone, repo.bat template new / build / launch, adding `omni.kit.xr.bundle.apple_vision_pro` to `.kit` dependencies, and the AR Panel sequence (stop AR → Output Plugin = OpenXR → OpenXR Runtime = CloudXR → Start AR)." |
| Setup Client (Vision Pro) | `https://docs.omniverse.nvidia.com/avp/latest/setup-client.html` | "Extract Apple developer account setup, Xcode + visionOS configuration, Configurator.xcodeproject signing, deploy to Vision Pro, trust-cert flow, and Manual IP-Address connection." |
| Setup Network | `https://docs.omniverse.nvidia.com/avp/latest/setup-network.html` | "Extract the network topology — NIC requirements, router specs (5GHz, avoid dual-5GHz), firewall ports, and remote-access compatibility (RDP NOT supported; Amazon DCV / Parsec alternatives)." |
| Client-Server overview | `https://docs.omniverse.nvidia.com/avp/latest/client-server-overview.html` | "Extract the end-to-end architecture — how rendering happens on the server, what's streamed, what the client does." |
| Client features | `https://docs.omniverse.nvidia.com/avp/latest/client-features.html` | "Extract the in-headset UI features — hand tracking, portals, gestures, supported interactions." |
| Performance | `https://docs.omniverse.nvidia.com/avp/latest/performance.html` | "Extract performance tuning — resolution / framerate targets, bandwidth, latency budget, profiling." |
| New functionality | `https://docs.omniverse.nvidia.com/avp/latest/new-functionality.html` | "Extract what's new in the latest AVP spatial-streaming release." |
| Migration guide 6.0 (HTML only) | `https://docs.omniverse.nvidia.com/avp/latest/migration-guide-6.0.html` | "Extract CloudXR 5.x → 6.0 migration steps. **HTML fetch** — `.md` returns 403." |
| Troubleshooting | `https://docs.omniverse.nvidia.com/avp/latest/troubleshooting.html` | "Look up the specific symptom the user is hitting — connection failures, framerate drops, tracking issues, cert problems." |

### Developer-level XR (omni.kit.xr.* — HTML only, `.md` 403)

All URLs below return 403 on `.md` — use HTML fallback.

| Topic | URL | Extraction Prompt |
|---|---|---|
| `omni.kit.xr.core` index | `https://docs.omniverse.nvidia.com/kit/docs/omni.kit.xr.core/latest/index.html` | "Extract the XR Core extension surface and what lifecycle management it provides. HTML fetch." |
| `omni.kit.xr.core` Overview | `https://docs.omniverse.nvidia.com/kit/docs/omni.kit.xr.core/latest/OVERVIEW.html` | "Extract what XRCore manages — lifecycle, frame scheduling, stereoscopic / foveated rendering, input devices, plugin system for OpenXR / OpenVR / CloudXR runtimes, compositor. HTML fetch." |
| `omni.kit.xr.core` Changelog | `https://docs.omniverse.nvidia.com/kit/docs/omni.kit.xr.core/latest/CHANGELOG.html` | "Extract XR Core release history. HTML fetch." |
| `omni.kit.xr.system.openxr` | `https://docs.omniverse.nvidia.com/kit/docs/omni.kit.xr.system.openxr/latest/index.html` | "Extract the OpenXR system extension — how it provides OpenXR runtime binding to XRCore. HTML fetch." |

**Extension discovery pattern:** NVIDIA publishes many `omni.kit.xr.*` extensions (OpenXR binding, Meta passthrough, hand tracking samples, etc.). Construct URLs as `https://docs.omniverse.nvidia.com/kit/docs/omni.kit.xr.<subname>/latest/index.html` and fetch as HTML. Examples: `omni.kit.xr.openxr.meta.passthrough`, `omni.kit.xr.openxr.ext.hand_tracking`, `omni.kit.xr.samples.openxr.hand_tracking`.

### Legacy path (avoid)

- `https://docs.omniverse.nvidia.com/app_omniverse-xr/latest/*` — the "Create XR" app. Returns 403 on both HTML and `.md` as of 2026-04-23. Deprecated / access-gated. Do NOT recommend this URL to users.

## Unbundled Omniverse Libraries (2025+)

The modular libraries (`ovrtx`, `ovphysx`, `ovstorage`) let you embed Omniverse rendering / physics / storage into non-Kit apps. Docs URLs may evolve — verify via the sitemap before authoritative answers.

| Topic | URL | Extraction Prompt |
|---|---|---|
| Omniverse libraries landing (developer portal) | `https://developer.nvidia.com/omniverse` | "Extract the list of modular / unbundled Omniverse libraries (ovrtx, ovphysx, ovstorage, any newer), their purpose, and links to per-library docs." |
| Kit apps catalog / launcher docs | `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/guide/kit_overview.html` | "Extract the 'how Kit composes into apps' overview and the app-template story." |

---

## Notes on extraction

- Always prefer the **`.md` URL** first. Fall back to HTML (`WebFetch` the `.html` URL directly) on 403.
- Cite the **HTML URL** back to the user.
- For `carb.*` / `omni.kit.*` classes not listed above, look them up from `API.html` and construct the URL by convention (`kit-manual/latest/<module>.<Class>.html`).

## Exceptions

- **403 on `.md` for some `/kit/docs/<ext>/` and `/py/<pkg>/` paths** — fall back to HTML. Specifically observed on `omni.graph`, `omni.replicator` (Python package), and `py/replicator/`.
- **Trailing-slash URLs return 403 on `.md`.** Always use explicit `.html` paths.

## Version drift

This catalog targets `/latest/` paths which redirect/serve current stable. Pinned version paths (`/106.x/`, etc.) also work when available. If `/latest/` ever fails, find the current version under `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/` and pin explicitly.
