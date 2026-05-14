# NVIDIA Warp Docs

Reliable live access to NVIDIA Warp's documentation at `https://nvidia.github.io/warp/`.

## When to use this sub-skill

Trigger on: NVIDIA Warp (the GPU Python framework), `@wp.kernel`, `@wp.func`, `@wp.struct`, `wp.launch`, `wp.array`, `wp.Tape()`, differentiable physics / autodiff, `warp.sim`, `warp.fem` (finite element), `warp.sparse` (sparse linear solvers), `warp.render`, `warp.optim`, tile primitives, Warp interop with PyTorch / JAX / NumPy, CUDA stream / graph capture in Warp, Warp kernel debugging, `WARP_ENABLE_*` env vars, or Python-side GPU kernel authoring via Warp. Also triggers on adjacent use: Isaac Lab reward / observation Warp kernels, NVIDIA Newton (physics engine built on Warp), MuJoCo-Warp, Warp as an Omniverse Kit extension, and general "how do I write a fast GPU kernel in pure Python" questions.

## Why this skill exists

Warp is the "Python-native GPU kernels" framework used across NVIDIA robotics (Isaac Lab rewards/obs), physics (Newton engine built on Warp), VFX, and ML. Kernel semantics (`@wp.kernel`, `wp.launch`, kernel-scope vs Python-scope), the built-in function library (`wp.vec3`, `wp.mat33`, `wp.quat`, geometry / volume / tile primitives), the autograd tape, and PyTorch / JAX / DLPack interop are all easy to get subtly wrong from memory. This skill keeps answers grounded in the current Sphinx docs rather than a training snapshot.

## The retrieval rule

Pattern D — **plain HTML, WebFetch the URL directly**. nvidia.github.io/warp is a PyData-Sphinx site; every page returns substantial server-rendered body content.

No URL rewrite needed.

| HTML URL | Fetch URL |
|---|---|
| `https://nvidia.github.io/warp/` | same |
| `https://nvidia.github.io/warp/user_guide/basics.html` | same |
| `https://nvidia.github.io/warp/api_reference/warp.html` | same |
| `https://nvidia.github.io/warp/language_reference/builtins.html` | same |

## HTML exceptions

- **Top-level Sphinx `_sources/*.rst.txt`** — works for the landing page (`/_sources/index.rst.txt` returns 200) but **not** for deep pages (most return 404). Treat as a curiosity; prefer the rendered HTML.
- **API pages are long** — `warp.html` and `builtins.html` enumerate hundreds of functions. Use anchors to narrow.
- **Versioning** — the GitHub Pages site tracks the `main` branch. Pinned-version docs live at `https://nvidia.github.io/warp/vX.Y/...` but are not always published; default to unversioned unless the user asks for a specific release.

## Workflow

1. Identify the topic — kernel basics, a specific built-in family (math / geometry / volume / tile), autograd, interop, a domain module (sim / fem / sparse / render), or a debug/profiling concern.
2. Look up the starting URL in `references/live-sources.md`. Page structure is `user_guide/` (concepts), `language_reference/builtins.html` (function catalog), `api_reference/` (module APIs), `domain_modules/` (sim/fem/sparse/render), `deep_dive/` (allocators, codegen, concurrency, profiling).
3. `WebFetch` the URL with an extraction prompt that names the concept or anchor.
4. For built-in functions, use the anchored form: `language_reference/builtins.html#vector-math`, `#quaternion-math`, `#geometry`, `#volumes`, `#tile-primitives`, etc.
5. Cite the HTML URL back to the user.

## Reference files

- `references/live-sources.md` — curated entry points grouped by User Guide · Language Reference · API Reference · Domain Modules · Deep Dive.
- `references/retrieval-rule.md` — Pattern D rule, probe commands, verification date.

## Common pitfalls

- **Kernel-scope vs Python-scope is a real distinction.** `wp.vec3()` means different things inside `@wp.kernel` vs outside. When answering API questions, check `user_guide/basics.html#python-scope-vs-kernel-scope-api`.
- **Built-ins are anchored.** Don't WebFetch `builtins.html` without an anchor — the page enumerates many families (scalar / vector / matrix / quaternion / spatial / geometry / random / volumes / tiles / textures / utility / operators / codegen). Narrow to the one the user asked about.
- **Autograd tape semantics.** `wp.Tape()` records on launch; backward requires matching forward kernel + captured tensors. See `user_guide/differentiability.html` before answering autodiff questions.
- **Device / stream / graph capture.** Warp supports CUDA streams and graph capture but has specific rules. Pull `user_guide/devices.html` and `deep_dive/concurrency.html` for stream/graph semantics, not memory.
- **Newton and MuJoCo-Warp are *uses* of Warp, not Warp modules.** If the user asks about Newton physics or MuJoCo-Warp specifically, note that they're external projects built on Warp — link them but don't invent Warp APIs for them.
- **`warp.sim` is deprecated in favor of Newton.** The `warp.sim` module still ships but new work should be in Newton. Confirm from `user_guide/changelog.html` before recommending `warp.sim`.
- **Tile primitives are newer.** `language_reference/builtins.html#tile-primitives` is the authoritative reference — don't answer tile questions from the main API reference.
