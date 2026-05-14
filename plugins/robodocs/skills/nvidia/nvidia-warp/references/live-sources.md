# NVIDIA Warp Docs — Live Sources

Curated entry points into NVIDIA Warp's documentation at `https://nvidia.github.io/warp/`. Every URL below is plain HTML — `WebFetch` directly per `retrieval-rule.md`.

When the user asks about a slug not listed here, scrape the sidebar (see `retrieval-rule.md`) or construct `https://nvidia.github.io/warp/<section>/<slug>.html` directly.

Verified 2026-04-23 against the `main`-branch docs (Warp 1.12-era).

---

## User Guide — Core Concepts

| Topic | URL | Extraction Prompt |
|---|---|---|
| Installation | `https://nvidia.github.io/warp/user_guide/installation.html` | "Extract the pip / source install commands, supported OS / CUDA versions, and any GPU driver requirements." |
| Basics (kernels, arrays, launch) | `https://nvidia.github.io/warp/user_guide/basics.html` | "Extract the minimal kernel + launch example, `@wp.kernel` / `wp.launch` semantics, array creation, user functions, user structs, compilation model, and the Python-scope vs kernel-scope distinction. Use the anchor matching the user's question." |
| Runtime | `https://nvidia.github.io/warp/user_guide/runtime.html` | "Extract runtime initialization, module compilation, and launch dispatch internals." |
| Configuration | `https://nvidia.github.io/warp/user_guide/configuration.html` | "Extract global / module / kernel settings and the `wp.config` surface + env vars." |
| Devices | `https://nvidia.github.io/warp/user_guide/devices.html` | "Extract device selection, default device, current CUDA device, custom CUDA contexts, peer access, and device synchronization." |
| Differentiability (autograd tape) | `https://nvidia.github.io/warp/user_guide/differentiability.html` | "Extract `wp.Tape()` usage, forward/backward patterns, supported ops, and gradient interop with PyTorch / JAX." |
| Generics | `https://nvidia.github.io/warp/user_guide/generics.html` | "Extract generic-kernel authoring, type parameters, and constraints." |
| Interoperability | `https://nvidia.github.io/warp/user_guide/interoperability.html` | "Extract PyTorch / JAX / NumPy / DLPack interop — zero-copy tensor sharing and conversion patterns." |
| Tiles | `https://nvidia.github.io/warp/user_guide/tiles.html` | "Extract the tile-primitive programming model — `wp.tile_zeros`, `wp.tile_matmul`, shared-memory semantics." |
| Debugging | `https://nvidia.github.io/warp/user_guide/debugging.html` | "Extract printing values, debug-mode compilation, assertions, non-finite detection, CUDA error verification, step-through debugging, and environment diagnostics." |
| FAQ | `https://nvidia.github.io/warp/user_guide/faq.html` | "Extract answers to the specific question the user asked." |
| Limitations | `https://nvidia.github.io/warp/user_guide/limitations.html` | "Extract known limitations — unsupported Python features inside kernels, platform gaps, feature gaps vs CUDA." |
| Compatibility | `https://nvidia.github.io/warp/user_guide/compatibility.html` | "Extract platform compatibility (Linux / Windows / macOS) and Warp's support policy." |
| Changelog | `https://nvidia.github.io/warp/user_guide/changelog.html` | "Extract the release notes for the version the user asked about (or the most recent if unspecified)." |
| Contribution guide | `https://nvidia.github.io/warp/user_guide/contribution_guide.html` | "Extract contribution workflow, code style, testing, and benchmark guidance." |
| Publications | `https://nvidia.github.io/warp/user_guide/publications.html` | "List the papers / talks that use or cite Warp." |

## Language Reference — Built-in Functions

The `builtins.html` page enumerates every `wp.*` built-in by category. Use anchors.

| Topic | URL | Extraction Prompt |
|---|---|---|
| Built-ins landing | `https://nvidia.github.io/warp/language_reference/builtins.html` | "List every function family (Scalar Math, Vector Math, Quaternion Math, Matrix Math, Transformations, Spatial Math, Geometry, Volumes, Random, Textures, Tile Primitives, Utility, Operators, Code Generation, Other). Do not dump individual signatures; list families with a one-line description each." |
| Scalar math | `https://nvidia.github.io/warp/language_reference/builtins.html#scalar-math` | "Extract scalar-math built-ins (abs, sin, cos, tan, sqrt, pow, log, exp, etc.) with signatures." |
| Vector math | `https://nvidia.github.io/warp/language_reference/builtins.html#vector-math` | "Extract vector built-ins (vec2 / vec3 / vec4 constructors, dot, cross, length, normalize, lerp) with signatures." |
| Quaternion math | `https://nvidia.github.io/warp/language_reference/builtins.html#quaternion-math` | "Extract quaternion built-ins (quat, quat_from_axis_angle, quat_rotate, quat_slerp, quat_to_matrix)." |
| Transformations | `https://nvidia.github.io/warp/language_reference/builtins.html#transformations` | "Extract transform built-ins (transform, transform_point, transform_vector, transform_multiply, transform_inverse)." |
| Spatial math | `https://nvidia.github.io/warp/language_reference/builtins.html#spatial-math` | "Extract spatial_vector / spatial_matrix built-ins." |
| Geometry | `https://nvidia.github.io/warp/language_reference/builtins.html#geometry` | "Extract geometry primitives — closest-point-on-triangle, ray-triangle, BVH queries, mesh queries." |
| Volumes | `https://nvidia.github.io/warp/language_reference/builtins.html#volumes` | "Extract volume / VDB built-ins — sampling, trilinear, world-to-index transforms." |
| Textures | `https://nvidia.github.io/warp/language_reference/builtins.html#textures` | "Extract texture sampling built-ins." |
| Random | `https://nvidia.github.io/warp/language_reference/builtins.html#random` | "Extract RNG built-ins (rand_init, randf, randn, randi) and seeding patterns." |
| Tile primitives | `https://nvidia.github.io/warp/language_reference/builtins.html#tile-primitives` | "Extract tile_zeros / tile_load / tile_store / tile_matmul / tile_atomic built-ins and shared-memory rules." |
| Utility | `https://nvidia.github.io/warp/language_reference/builtins.html#utility` | "Extract misc utility built-ins (select, min, max, clamp, step, smoothstep, etc.)." |
| Operators | `https://nvidia.github.io/warp/language_reference/builtins.html#operators` | "Extract supported operator overloads in kernel scope." |
| Code generation | `https://nvidia.github.io/warp/language_reference/builtins.html#code-generation` | "Extract the code-generation helpers available at kernel authoring time." |

## API Reference — Module by module

| Topic | URL | Extraction Prompt |
|---|---|---|
| `warp` core API | `https://nvidia.github.io/warp/api_reference/warp.html` | "Extract the top-level `warp` module surface — Kernel / Function / Struct decorators, array types, launch, sync, context, module init/capture/release." |
| `warp.types` | `https://nvidia.github.io/warp/api_reference/warp_types.html` | "Extract type primitives — vec2 / vec3 / vec4 / mat22 / mat33 / mat44 / quat / transform / spatial_vector / array / uint8 / int32 / float32." |
| `warp.utils` | `https://nvidia.github.io/warp/api_reference/warp_utils.html` | "Extract utility helpers — ScopedTimer, timing utilities, print utilities." |
| `warp.config` | `https://nvidia.github.io/warp/api_reference/warp_config.html` | "Extract the `wp.config.*` settings surface." |
| `warp.autograd` | `https://nvidia.github.io/warp/api_reference/warp_autograd.html` | "Extract the autograd API — Tape, gradient computation, function adjoints." |
| `warp.optim` | `https://nvidia.github.io/warp/api_reference/warp_optim.html` | "Extract Warp optimizers (Adam, SGD variants) for differentiable sim / learning loops." |
| `warp.render` | `https://nvidia.github.io/warp/api_reference/warp_render.html` | "Extract rendering utilities (OpenGL / USD render interface, CUDA graphics interop)." |
| `warp.sparse` | `https://nvidia.github.io/warp/api_reference/warp_sparse.html` | "Extract sparse-matrix types (BSR, CSR), iterative solvers (CG, BiCGSTAB), and preconditioners." |
| `warp.fem` | `https://nvidia.github.io/warp/api_reference/warp_fem.html` | "Extract the FEM module surface — spaces, integrands, operators, domains." |
| `warp.jax_experimental` | `https://nvidia.github.io/warp/api_reference/warp_jax_experimental.html` | "Extract the experimental JAX interop surface and known limitations." |

## Domain Modules (high-level usage)

| Topic | URL | Extraction Prompt |
|---|---|---|
| FEM module | `https://nvidia.github.io/warp/domain_modules/fem.html` | "Extract basic FEM workflow, fields, operators, integrands, and introductory examples. Scope to the sub-topic the user asked about (advanced usages / basic workflow / etc.)." |
| Sparse module | `https://nvidia.github.io/warp/domain_modules/sparse.html` | "Extract sparse-matrix construction and iterative linear solver usage." |
| Render module | `https://nvidia.github.io/warp/domain_modules/render.html` | "Extract the standalone renderers (OpenGL / USD) and CUDA graphics interface." |

## Deep Dive — Internals & Performance

| Topic | URL | Extraction Prompt |
|---|---|---|
| Codegen internals | `https://nvidia.github.io/warp/deep_dive/codegen.html` | "Extract AOT compilation workflow, dynamic kernel creation, late binding, static expressions, external references and constants." |
| Allocators | `https://nvidia.github.io/warp/deep_dive/allocators.html` | "Extract stream-ordered memory pool allocator semantics and when to use each allocator." |
| Concurrency (streams, graphs) | `https://nvidia.github.io/warp/deep_dive/concurrency.html` | "Extract CUDA stream usage, graph capture, async ops, and synchronization guidance." |
| Profiling | `https://nvidia.github.io/warp/deep_dive/profiling.html` | "Extract ScopedTimer usage, CUDA activity profiling, CUDA event timing, Nsight Compute, and module-compilation profiling." |

## Index

| Topic | URL | Extraction Prompt |
|---|---|---|
| Global index | `https://nvidia.github.io/warp/genindex.html` | "Look up a specific symbol name — the page indexes every public function / class alphabetically. Use when the user mentions a symbol not covered elsewhere." |

---

## Notes on extraction

- All URLs are plain HTML. No rewrite.
- `builtins.html` and `api_reference/warp.html` are long — **always use an anchor** on `builtins.html`; scope the extraction prompt on `warp.html` to just the submodule the user asked about.
- Python-scope vs kernel-scope is a real distinction — when answering "why does my `wp.vec3(...)` not work inside a kernel?", extract the `user_guide/basics.html#python-scope-vs-kernel-scope-api` section.

## Exceptions

- **`_sources/*.rst.txt`** — only works for a small subset of pages. Don't depend on it.
- **`warp.sim`** — still shipping but migrating to Newton. Flag this when a user asks.
- **Newton physics engine** — built on Warp but a separate project at `https://github.com/newton-physics/newton`. This skill does not catalog Newton; mention it when relevant.

## Version drift

This catalog tracks the `main`-branch docs (Warp ~v1.12 as of 2026-04-23). The URL structure has been stable across recent releases. If a page 404s after a release, re-run the sidebar enumeration to find the renamed slug.
