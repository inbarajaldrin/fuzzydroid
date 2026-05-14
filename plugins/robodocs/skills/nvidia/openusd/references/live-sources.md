# OpenUSD Docs — Live Sources

Curated entry points into Pixar / Linux Foundation OpenUSD documentation at `https://openusd.org/release/`. Every URL below is plain HTML — `WebFetch` it directly per `retrieval-rule.md`.

When the user asks about a slug not listed here, scrape the sidebar (see `retrieval-rule.md`) to find the page, or try `https://openusd.org/release/<slug>.html` directly.

Verified against the `/release/` branch on 2026-04-23.

---

## Get Started

| Topic | URL | Extraction Prompt |
|---|---|---|
| Landing / TOC | `https://openusd.org/release/index.html` | "Extract the top-level section listing (Intro, Tutorials, User Guides, Toolset, Specs, API) and any release banner." |
| Introduction | `https://openusd.org/release/intro.html` | "Extract what USD is, its core design goals, and how stages / layers / prims relate at a high level." |
| OpenExec intro | `https://openusd.org/release/intro_to_openexec.html` | "Extract what OpenExec is, its relationship to USD composition, and basic usage." |
| USD products (consumers) | `https://openusd.org/release/usd_products.html` | "List the DCC apps / engines / pipelines that read/write USD." |
| Downloads | `https://openusd.org/release/dl_downloads.html` | "Extract build / binary download links and reference assets (ALab, Kitchen Set, Moore Lane, Shader Ball)." |
| Contributing | `https://openusd.org/release/contributing_to_usd.html` | "Extract the CLA, git workflow, coding conventions, and PR checklist." |
| Contributors | `https://openusd.org/release/contributors.html` | "List the organizations and individuals contributing to OpenUSD." |
| Release schedule | `https://openusd.org/release/release_schedule.html` | "Extract the release cadence, LTS status, and upcoming milestones." |
| Press — open source announce | `https://openusd.org/release/press_opensource_announce.html` | "Extract Pixar's open-source announcement for context on USD's history." |
| Press — open source release | `https://openusd.org/release/press_opensource_release.html` | "Extract the open-source release announcement." |

## Core Concepts & Terminology

| Topic | URL | Extraction Prompt |
|---|---|---|
| Glossary (authoritative) | `https://openusd.org/release/glossary.html` | "Extract definitions for the terms the user asked about (stage, prim, attribute, reference, payload, sublayer, variant, composition arc, LIVRPS, etc.)." |
| FAQ | `https://openusd.org/release/usdfaq.html` | "Extract the FAQ answers relevant to the user's question. This page is anchored — use the anchor matching the question (e.g. `#sublayers-or-references`, `#what-data-types-are-supported`)." |
| Spec overview | `https://openusd.org/release/spec.html` | "Extract the top-level USD specification outline — what's normative vs reference material." |

## Tutorials

| Topic | URL | Extraction Prompt |
|---|---|---|
| Tutorials index | `https://openusd.org/release/tut_usd_tutorials.html` | "List all tutorial pages with their one-line descriptions." |
| Hello World | `https://openusd.org/release/tut_helloworld.html` | "Extract the minimal Python snippet that creates a stage, adds a sphere, and saves — with imports." |
| Hello World (redux) | `https://openusd.org/release/tut_helloworld_redux.html` | "Extract the expanded Hello World walkthrough explaining each API call." |
| Inspect and author properties | `https://openusd.org/release/tut_inspect_and_author_props.html` | "Extract how to query / set / block an attribute or relationship from Python." |
| Traversing a stage | `https://openusd.org/release/tut_traversing_stage.html` | "Extract iteration patterns over prims — `Traverse()`, `TraverseAll()`, predicates, prim flags." |
| Authoring variants | `https://openusd.org/release/tut_authoring_variants.html` | "Extract how to create a variant set, add variants, and author opinions inside each." |
| Referencing layers | `https://openusd.org/release/tut_referencing_layers.html` | "Extract how to add references and payloads between layers from Python." |
| Xforms | `https://openusd.org/release/tut_xforms.html` | "Extract the xformOp stack, ordering, time-sampling, and Python Write patterns." |
| Simple shading | `https://openusd.org/release/tut_simple_shading.html` | "Extract the UsdShade minimal example — Material, Shader, connection, binding." |
| Converting between layer formats | `https://openusd.org/release/tut_converting_between_layer_formats.html` | "Extract the commands / API to convert .usda ↔ .usdc ↔ .usd and when each is preferred." |
| End-to-end pipeline example | `https://openusd.org/release/tut_end_to_end.html` | "Extract the multi-stage / multi-artist pipeline walkthrough." |
| Generating new schemas | `https://openusd.org/release/tut_generating_new_schema.html` | "Extract the `usdGenSchema` workflow and the `.usda` schema input format." |
| Houdini example | `https://openusd.org/release/tut_houdini_example.html` | "Extract Houdini Solaris / LOPs authoring example steps." |
| Katana variants example | `https://openusd.org/release/tut_variants_example_in_katana.html` | "Extract the Katana variants workflow example." |
| usdview plugin tutorial | `https://openusd.org/release/tut_usdview_plugin.html` | "Extract how to write a usdview plugin — registration, callbacks, UI integration." |

## User Guides

| Topic | URL | Extraction Prompt |
|---|---|---|
| Collections and patterns | `https://openusd.org/release/user_guides/collections_and_patterns.html` | "Extract how to define pattern-based vs relationship-mode collections and path-expression syntax." |
| Color user guide | `https://openusd.org/release/user_guides/color_user_guide.html` | "Extract supported color spaces, inheritance / resolution rules, and how to author color-space opinions." |
| Namespace editing | `https://openusd.org/release/user_guides/namespace_editing.html` | "Extract `UsdNamespaceEditor` usage — move/rename/reparent, dependent-stage edits, relocates considerations." |
| Primvars | `https://openusd.org/release/user_guides/primvars.html` | "Extract primvar interpolation modes (constant / uniform / varying / vertex / faceVarying), indexed primvars, and element size." |
| Render user guide | `https://openusd.org/release/user_guides/render_user_guide.html` | "Extract RenderSettings / RenderProduct / RenderVar / RenderPass authoring and how to bind materials to collections." |
| Variable expressions | `https://openusd.org/release/user_guides/variable_expressions.html` | "Extract the variable-expression syntax, supported operators, and where expressions can be used." |

## Schemas — per domain

| Topic | URL | Extraction Prompt |
|---|---|---|
| Schemas index | `https://openusd.org/release/user_guides/schemas/index.html` | "List every schema domain (UsdLux, UsdMedia, UsdRender, UsdUI, UsdVol, ...) with a one-line purpose each." |
| **UsdLux** overview | `https://openusd.org/release/user_guides/schemas/usdLux/overview.html` | "Extract the UsdLux light-type taxonomy and the IsA / API split." |
| UsdLux TOC | `https://openusd.org/release/user_guides/schemas/usdLux/usdLux_toc.html` | "List every UsdLux schema (SphereLight, DistantLight, DiskLight, CylinderLight, RectLight, DomeLight, GeometryLight, PortalLight, LightAPI, ShadowAPI, ShapingAPI, MeshLightAPI, VolumeLightAPI, etc.)." |
| UsdLux SphereLight | `https://openusd.org/release/user_guides/schemas/usdLux/SphereLight.html` | "Extract SphereLight attributes (radius, treatAsPoint, color, intensity, exposure, ...)." |
| UsdLux DistantLight | `https://openusd.org/release/user_guides/schemas/usdLux/DistantLight.html` | "Extract DistantLight attributes and typical authoring." |
| UsdLux DomeLight | `https://openusd.org/release/user_guides/schemas/usdLux/DomeLight.html` | "Extract DomeLight attributes (texture:file, portals, poleAxis, format)." |
| UsdLux LightAPI | `https://openusd.org/release/user_guides/schemas/usdLux/LightAPI.html` | "Extract LightAPI attributes common to all lights — color, intensity, exposure, diffuse, specular, enableColorTemperature, colorTemperature." |
| UsdLux ShadowAPI | `https://openusd.org/release/user_guides/schemas/usdLux/ShadowAPI.html` | "Extract ShadowAPI attributes (enable, color, distance, falloff, falloffGamma)." |
| UsdLux ShapingAPI | `https://openusd.org/release/user_guides/schemas/usdLux/ShapingAPI.html` | "Extract ShapingAPI attributes (focus, focusTint, cone:angle / softness, IES file)." |
| **UsdMedia** overview | `https://openusd.org/release/user_guides/schemas/usdMedia/overview.html` | "Extract UsdMedia's purpose — asset previews, spatial audio." |
| UsdMedia SpatialAudio | `https://openusd.org/release/user_guides/schemas/usdMedia/SpatialAudio.html` | "Extract SpatialAudio attributes (filePath, auralMode, playbackMode, gain, startTime, endTime, mediaOffset)." |
| UsdMedia AssetPreviewsAPI | `https://openusd.org/release/user_guides/schemas/usdMedia/AssetPreviewsAPI.html` | "Extract how to author preview thumbnails on an asset." |
| **UsdRender** overview | `https://openusd.org/release/user_guides/schemas/usdRender/overview.html` | "Extract how RenderSettings / RenderProduct / RenderVar / RenderPass compose into a render graph." |
| UsdRender RenderSettings | `https://openusd.org/release/user_guides/schemas/usdRender/RenderSettings.html` | "Extract RenderSettings attributes — resolution, camera, aspectRatio, products, includedPurposes, materialBindingPurposes." |
| UsdRender RenderProduct | `https://openusd.org/release/user_guides/schemas/usdRender/RenderProduct.html` | "Extract RenderProduct attributes — productType, productName, orderedVars, camera." |
| UsdRender RenderVar | `https://openusd.org/release/user_guides/schemas/usdRender/RenderVar.html` | "Extract RenderVar attributes (dataType, sourceName, sourceType)." |
| UsdRender RenderPass | `https://openusd.org/release/user_guides/schemas/usdRender/RenderPass.html` | "Extract RenderPass attributes and how passes chain." |
| **UsdUI** overview | `https://openusd.org/release/user_guides/schemas/usdUI/overview.html` | "Extract UsdUI's purpose — editor hints, backdrops, accessibility, node-graph layout." |
| UsdUI Backdrop | `https://openusd.org/release/user_guides/schemas/usdUI/Backdrop.html` | "Extract Backdrop attributes." |
| UsdUI AccessibilityAPI | `https://openusd.org/release/user_guides/schemas/usdUI/AccessibilityAPI.html` | "Extract AccessibilityAPI attributes for hinting alt text / labels in USD." |
| **UsdVol** overview | `https://openusd.org/release/user_guides/schemas/usdVol/overview.html` | "Extract UsdVol's purpose — volumes, fields, asset types." |
| UsdVol Volume | `https://openusd.org/release/user_guides/schemas/usdVol/Volume.html` | "Extract Volume prim structure and field binding." |
| UsdVol OpenVDBAsset | `https://openusd.org/release/user_guides/schemas/usdVol/OpenVDBAsset.html` | "Extract OpenVDBAsset attributes and VDB file binding." |
| UsdVol Field3DAsset | `https://openusd.org/release/user_guides/schemas/usdVol/Field3DAsset.html` | "Extract Field3DAsset attributes." |

## Toolset

| Topic | URL | Extraction Prompt |
|---|---|---|
| Toolset overview (all CLI tools) | `https://openusd.org/release/toolset.html` | "List every CLI tool with a one-line purpose. Use anchors (`#usdview`, `#usdcat`, `#usdedit`, `#usdchecker`, `#usdrecord`, `#usdzip`, etc.) to narrow to the tool the user asked about." |
| usdview (anchor) | `https://openusd.org/release/toolset.html#usdview` | "Extract usdview usage, keyboard shortcuts, and plugin capabilities." |
| usdcat (anchor) | `https://openusd.org/release/toolset.html#usdcat` | "Extract usdcat flags — format conversion, flattening, output options." |
| usdedit (anchor) | `https://openusd.org/release/toolset.html#usdedit` | "Extract usdedit invocation and editor env var." |
| usdchecker (anchor) | `https://openusd.org/release/toolset.html#usdchecker` | "Extract usdchecker rules, --arkit flag, and common failures." |
| usdrecord (anchor) | `https://openusd.org/release/toolset.html#usdrecord` | "Extract usdrecord flags for rendering stages to image sequences." |
| usdzip (anchor) | `https://openusd.org/release/toolset.html#usdzip` | "Extract usdzip usage — packaging, --arkitAsset, validation." |
| usdtree (anchor) | `https://openusd.org/release/toolset.html#usdtree` | "Extract usdtree's prim-tree inspection flags." |
| usdstitch / usdstitchclips (anchors) | `https://openusd.org/release/toolset.html#usdstitch` | "Extract usdstitch (layer merging) and usdstitchclips (value clips authoring) usage." |
| usdGenSchema (anchor) | `https://openusd.org/release/toolset.html#usdgenschema` | "Extract usdGenSchema's .usda input format and generated C++/Python surface." |
| usdGenSchemaFromSdr (anchor) | `https://openusd.org/release/toolset.html#usdgenschemafromsdr` | "Extract usdGenSchemaFromSdr's workflow for shader schemas." |
| usdMeasurePerformance (anchor) | `https://openusd.org/release/toolset.html#usdmeasureperformance` | "Extract usdMeasurePerformance for running the reference performance benchmarks." |
| sdfdump / sdffilter (anchors) | `https://openusd.org/release/toolset.html#sdfdump` | "Extract sdfdump and sdffilter usage for low-level Sdf inspection." |

## File Format Specs

| Topic | URL | Extraction Prompt |
|---|---|---|
| USDZ spec | `https://openusd.org/release/spec_usdz.html` | "Extract the USDZ package constraints — zip layout, file types, streaming considerations, ARKit requirements, version history (current HEAD: 1.3)." |
| UsdPreviewSurface spec | `https://openusd.org/release/spec_usdpreviewsurface.html` | "Extract UsdPreviewSurface node definitions (PreviewSurface, PrimvarReader, TextureReader, Transform2d) and the current version semantics." |

## Composition & Performance

| Topic | URL | Extraction Prompt |
|---|---|---|
| Max performance guide | `https://openusd.org/release/maxperf.html` | "Extract performance recommendations — binary USD for heavy geometry, payloads for deferred loading, multithreading allocators, scene-weight guidance." |
| Performance metrics methodology | `https://openusd.org/release/ref_performance_metrics.html` | "Extract how Pixar measures USD performance — build, platform matrix (Linux/macOS/Windows), reference scenes (ALab, Kitchen Set, Moore Lane, Shader Ball), and how to add custom metrics." |

## Plugins

| Topic | URL | Extraction Prompt |
|---|---|---|
| Plugins overview | `https://openusd.org/release/plugins.html` | "List the built-in USD plugin ecosystem and extension points." |
| Alembic | `https://openusd.org/release/plugins_alembic.html` | "Extract the usdAbc plugin behavior and known limitations." |
| RenderMan (HdPrman) | `https://openusd.org/release/plugins_renderman.html` | "Extract HdPrman build / configuration / run usage and supported render-pass AOVs." |

## API Reference

| Topic | URL | Extraction Prompt |
|---|---|---|
| Doxygen landing | `https://openusd.org/release/api/index.html` | "Extract the top-level C++ namespace / module listing. For Python API questions, prefer the `user_guides/` or tutorial pages." |
| API overview | `https://openusd.org/release/apiDocs.html` | "Extract how the API reference is organized (modules, namespaces, Python bindings)." |
| Doxygen _usd__overview_and_purpose | `https://openusd.org/release/api/_usd__overview_and_purpose.html` | "Extract the Usd module's design rationale and main class entry points (UsdStage, UsdPrim, UsdAttribute, UsdRelationship, UsdReferences, UsdPayloads, UsdVariantSets, UsdInherits, UsdSpecializes)." |

---

## Notes on extraction

- All URLs above return **plain HTML**. Apply no rewrite before WebFetch.
- Many pages (especially `usdfaq.html`, `toolset.html`, `maxperf.html`, schemas) are long single pages with numerous anchors. Include the anchor in the URL *and* mention the section name in the extraction prompt when the user's question is specific.
- When citing back to the user, drop the anchor if it's noise, keep it if it targets a specific sub-topic.
- For Python vs C++ choice, inspect `glossary.html` / tutorials for Python syntax; `api/*.html` for C++ signatures.

## Exceptions

- **Doxygen API pages** — heavy auto-generated C++ pages under `/release/api/`. Prefer user-guide / tutorial pages for conceptual explanations; drop to Doxygen only for specific signatures.
- **Anchor-only pages** — `toolset.html` and `usdfaq.html` are long single pages. Use anchors to scope the fetch.

## Version drift

This catalog tracks `/release/` (current stable). If OpenUSD publishes a new release and you need the old behavior, substitute `/v<ver>/` for `/release/` in every URL. The rewrite rule itself is branch-agnostic.
