# Omniverse Kit Docs

Reliable live access to the Omniverse Kit SDK documentation at `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/` and related Kit product pages at `https://docs.omniverse.nvidia.com/`.

## When to use this sub-skill

Trigger on: NVIDIA Omniverse Kit SDK, Kit apps, `extension.toml`, Kit extensions, Carbonite (`carb.*` / `carb.audio` / `carb.dictionary` / `carb.settings` / `carb.tokens` / `carb.windowing` / `carb.input`), Omniverse Python bindings, building custom Omniverse applications, the `.kit` file format for app configurations, Kit Extension Manager, Kit Commands, USD Composer / USD Presenter (as Kit apps), or the newer unbundled Omniverse libraries (`ovrtx`, `ovphysx`, `ovstorage` introduced in 2025). Also triggers on Omniverse VR / XR / Spatial Streaming — setting up VR in an Omniverse Kit app, Apple Vision Pro spatial streaming, CloudXR integration, OpenXR in Kit, `omni.kit.xr.core` / `omni.kit.xr.system.openxr`, `omni.kit.xr.bundle.apple_vision_pro`, AR Panel configuration, Vision Pro / Quest / iPad as Omniverse clients — this is THE sub-skill for "how do I get VR/AR working with Omniverse". Also triggers when the user is embedding Omniverse rendering / physics / asset storage into their own non-Kit apps, authoring a new extension, debugging `omni.kit.*` extensions, or working at the Omniverse platform level below a specific vertical product like Isaac Sim or Replicator.

## Why this skill exists

Omniverse Kit is the application framework under every Omniverse app — including Isaac Sim, USD Composer, USD Presenter, and any custom extension-based app. Its surface (Carbonite runtime, the `omni.kit.*` extension family, the `.kit` app manifest, extension.toml metadata, Python↔C++ bindings) is large and NVIDIA has recently begun unbundling pieces (`ovrtx` / `ovphysx` / `ovstorage`) for embedding outside Kit. Accurate answers require live docs rather than recall.

## The retrieval rule

Pattern A — **append `.md` to any `.html` page** under `docs.omniverse.nvidia.com`. Verified 200 `text/markdown` on Kit manual, Carbonite, Extension pages.

| HTML URL | Markdown URL |
|---|---|
| `https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/index.html` | `…index.html.md` |
| `https://docs.omniverse.nvidia.com/kit/docs/carbonite/latest/index.html` | `…index.html.md` |
| `https://docs.omniverse.nvidia.com/extensions/latest/ext_XXX.html` | `…ext_XXX.html.md` |

Rule: **strip nothing; append `.md` to the `.html` URL**. Trailing `/` paths don't work — always target a `.html` page.

## HTML exceptions

- **Some nested Kit paths return 403 for `.md`** — e.g., `/kit/docs/omni.graph/latest/index.html.md` is 403 despite the HTML being 200. When `.md` returns 403, fall back to fetching the HTML directly (Pattern D).
- **The unbundled libraries (`ovrtx` / `ovphysx` / `ovstorage`)** have their own pages under the main Omniverse site; check `docs.omniverse.nvidia.com` sitemap for their current paths.
- **Kit API reference (`carb.*`)** is Python-binding auto-generated — pages are per-class/function. Enumerate via the `API.html` index rather than listing every class.

## Workflow

1. Identify whether the question is about: Kit runtime / app shell, a specific Kit extension (`omni.kit.*`), Carbonite (`carb.*`), extension authoring, the `.kit` app manifest, or the unbundled libraries.
2. Look up the starting URL in `references/live-sources.md`. For individual `carb.*` / `omni.*` classes not listed, apply the rewrite to any valid `.html` path from the Kit manual sidebar.
3. `WebFetch` the `.html.md` URL; fall back to `.html` if `.md` returns 403.
4. Cite the HTML URL back to the user (not the `.md` URL).

## Reference files

- `references/live-sources.md` — curated entry points grouped by Kit Manual · Carbonite · Extension Authoring · Unbundled Libraries · Kit Apps.
- `references/retrieval-rule.md` — full rewrite rule, 403 fallback, probe commands, verification date.

## Common pitfalls

- **Kit != Omniverse.** Kit is the framework; Omniverse is the platform above. Don't conflate when routing.
- **`.md` suffix doesn't cover all nested paths.** Some `/kit/docs/<ext>/latest/index.html` routes return 403 for `.md`. Check before committing and fall back to HTML.
- **The sitemap at root technically exists** (`https://docs.omniverse.nvidia.com/sitemap.xml` returns 200) but **contains only ~2 entries** — it's not useful for discovery. Use WebSearch or direct navigation from a known-working page instead.
- **Carbonite (`carb.*`) is the C++ runtime layer.** Python exposes bindings; for deep behavior you may need the C++ reference. Don't assume Python docs cover everything.
- **`.kit` files are TOML-like app manifests.** The `.kit` format docs live under the Kit manual; don't confuse with `extension.toml`.
- **Unbundled libs are new (2025+).** When the user asks about embedding Omniverse pieces into non-Kit apps, check `ovrtx` / `ovphysx` / `ovstorage` pages — don't assume everything goes through Kit anymore.
- **VR / XR in Omniverse: `/avp/` is the live path, `/app_omniverse-xr/` is gated.** The legacy "Create XR" app returns 403 on every URL tested — don't cite it. The current canonical VR docs are under `/avp/` (Apple Vision Pro spatial streaming, via CloudXR) and `omni.kit.xr.*` extensions (HTML only — `.md` 403s).
- **AR Panel sequence for enabling VR is fiddly.** The in-app path is: Stop AR → Output Plugin = OpenXR → OpenXR Runtime = CloudXR → Start AR. Missing any of those leaves the session in the wrong state. The skill's `setup-sdk` entry has the full sequence.
