# OpenUSD Docs

Reliable live access to Pixar / Linux Foundation OpenUSD documentation at `https://openusd.org/release/`.

## When to use this sub-skill

Trigger on: OpenUSD / Pixar USD, USD files (`.usd`, `.usda`, `.usdc`, `.usdz`), USD Python APIs (`pxr.Usd`, `pxr.UsdGeom`, `pxr.UsdShade`, `pxr.Sdf`, `pxr.UsdLux`, `pxr.UsdSkel`, `pxr.UsdPhysics`, `pxr.UsdMedia`, `pxr.UsdRender`, `pxr.UsdUI`, `pxr.UsdVol`, `pxr.Kind`), Hydra / `HdStorm` / `HdPrman`, USD composition (sublayers, references, payloads, variants, inherits, specializes / LIVRPS), stages and prims, USD schemas (codeful vs codeless, IsA vs API), CLI tools (`usdview` / `usdcat` / `usdedit` / `usdchecker` / `usdrecord` / `usdzip`), UsdPreviewSurface, USDZ AR packaging, or any Pixar / OpenUSD / AOUSD topic. Also triggers on cross-ecosystem USD use: Omniverse (built on USD), Apple RealityKit / Reality Composer Pro (USDZ), Houdini Solaris, Maya USD plugin, Katana, Blender USD I/O, Unreal Engine USD importer.

## Why this skill exists

OpenUSD is the scene description standard underneath NVIDIA Omniverse, Apple RealityKit, and most modern 3D pipelines. Its composition semantics (LIVRPS: Local ▸ Inherits ▸ VariantSets ▸ References ▸ Payloads ▸ Specializes) are easy to misremember — as are the schema families (UsdGeom / UsdShade / UsdLux / UsdSkel / UsdPhysics / UsdMedia / UsdRender / UsdUI / UsdVol). OpenUSD also versions rapidly, and schemas move between codeful and codeless forms. This skill keeps answers grounded in openusd.org rather than a training snapshot.

## The retrieval rule

Pattern D — **plain HTML, WebFetch the URL directly**. openusd.org is a static site (Doxygen + custom HTML) and every documented page returns substantial body content inline.

No URL rewrite needed. If a user references a specific openusd.org page, fetch it as-is.

| HTML URL | Fetch URL |
|---|---|
| `https://openusd.org/release/index.html` | same |
| `https://openusd.org/release/tut_helloworld.html` | same |
| `https://openusd.org/release/user_guides/schemas/usdLux/SphereLight.html` | same |

## HTML exceptions

- **API reference (Doxygen)** — `/release/api/` is Doxygen-generated and heavy. Paragraphs are inside C++-heavy structure. For Python API questions, prefer the matching page under `/release/user_guides/` or the tutorial pages where possible, and fall back to the Doxygen page only when you need a specific signature.
- **Versioned paths** — `/release/` is current-stable; `/dev/` is development; `/v25.05/` (etc.) pins a release. Default to `/release/` unless the user explicitly wants dev or a pinned version.

## Workflow

1. Identify the topic — composition, schemas, a specific tutorial, file format, toolset, performance, etc.
2. Look up the starting URL in `references/live-sources.md`. If it's not listed, scrape the sidebar of any rendered page (`curl | grep href`) to find the slug.
3. `WebFetch` the URL directly with a specific extraction prompt (name the section, anchor, or concept).
4. If you land on a Doxygen API page and the user's question is conceptual, swap to the sibling user-guide or tutorial page — don't try to summarize thousands of auto-generated symbols.
5. Cite the HTML URL back to the user so they can open it in a browser.

## Reference files

- `references/live-sources.md` — curated entry points grouped by topic (Get Started · Core Concepts · Tutorials · User Guides · Schemas · Toolset · File Formats · Composition · Performance · API).
- `references/retrieval-rule.md` — full Pattern D rule, probe commands, and verification date.

## Common pitfalls

- **Don't confuse `/release/` vs `/dev/` vs pinned versions.** openusd.org's default landing is `/release/`. APIs may differ between them. Default to `/release/` and tell the user which branch you checked.
- **Composition order (LIVRPS) is easy to get wrong.** When answering composition questions, pull the actual `glossary.html` / `intro.html` pages — don't recite from memory.
- **Schemas split into IsA / API / codeless.** UsdLux recently gained codeless schemas. User guide pages at `/user_guides/schemas/usd{Lux,Media,Render,UI,Vol}/` are the authoritative overviews; don't over-index on the Doxygen class pages.
- **USDZ constraints differ from plain USD.** Packaging, layer flattening, ASCII vs binary, asset type restrictions — always check `spec_usdz.html` before recommending a USDZ workflow.
- **Python vs C++ naming.** Python uses `Usd.Stage.CreateNew(...)`; C++ uses `UsdStage::CreateNew(...)`. Tutorials include both; be explicit about which the user needs.
- **Performance guidance lives in two places.** `maxperf.html` is the advice page; `ref_performance_metrics.html` is the measurement methodology. Cite the right one for the user's question (tuning vs benchmarking).
- **The `tut_` prefix is load-bearing.** Tutorials are always under slugs starting with `tut_` (e.g., `tut_helloworld.html`, `tut_xforms.html`). If the user asks for "the USD xforms tutorial", the URL is `tut_xforms.html`, not `xforms.html`.
