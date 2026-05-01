# Omniverse Replicator Docs

Reliable live access to Omniverse Replicator documentation at `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html` and the `ext_replicator/` sub-tree.

## When to use this sub-skill

Trigger on: NVIDIA Omniverse Replicator, synthetic data generation (SDG) for training ML / CV / robotics models, domain randomization, `rep.randomizer`, `rep.Writer` / custom writers, Replicator annotators (2d/3d bounding box, semantic segmentation, instance segmentation, normal map, depth, pose, occlusion, etc.), the Replicator YAML config workflow, Replicator-on-container / Replicator-on-AWS headless runs, Replicator subframes, `omni.replicator`, physics-aware scattering, or training data for defect detection / autonomous vehicles / robot perception. Also triggers on adjacent uses — Replicator inside Isaac Sim (via `isaacsim.replicator` wrappers — but route to isaac-sim for those), NVIDIA DRIVE Sim, Siemens / manufacturing inspection pipelines using Replicator, and any "generate training images / labels from a USD scene" question for non-robotics domains.

## Why this skill exists

Replicator is NVIDIA's framework for **programmatic synthetic data generation** — spawn objects, randomize appearance / pose / lighting, attach annotators, write labeled data to disk. It's used in robotics (via Isaac Sim's wrappers), autonomous vehicles (DRIVE Sim), and manufacturing defect detection (Siemens). The domain-randomization primitives, writer authoring contract, and annotator catalog are specific enough that memory drift produces wrong code. Live docs keep answers grounded.

## The retrieval rule

Pattern A — **append `.md` to any `.html` URL** under `docs.omniverse.nvidia.com`. Verified 200 `text/markdown` on `ext_replicator.html.md` and sub-pages under `ext_replicator/`.

| HTML URL | Markdown URL |
|---|---|
| `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html` | `…ext_replicator.html.md` |
| `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html` | `…ext_replicator/getting_started.html.md` |
| `https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html` | `…ext_replicator/custom_writer.html.md` |

## HTML exceptions

- **Python API pages (`/py/replicator/`)** return 403 on `.md`. Fall back to HTML (`WebFetch` directly).
- **Isaac Sim's `isaacsim.replicator`** is a different, robot-specific wrapper — covered by the `isaac-sim` skill, not this one.

## Workflow

1. Classify the question — conceptual (what is Replicator, how does randomization work), practical (write a randomizer / custom writer), annotator-specific (which annotator for which label type), or integration (run headless / containerized / AWS).
2. Look up the starting URL in `shared/live-sources.md`.
3. `WebFetch` the `.html.md` URL; fall back to `.html` if 403.
4. If the user is inside Isaac Sim, route them to the `isaac-sim` skill for `isaacsim.replicator.*` — that's the robot-aware wrapper, not raw Replicator.
5. Cite the HTML URL back to the user.

## Reference files

- `shared/live-sources.md` — curated entry points: Getting Started · Randomizers · Annotators · Writers · YAML workflow · Advanced (headless, physics, container, AWS) · Examples.
- `shared/retrieval-rule.md` — rewrite rule, 403 fallback, verification date.

## Common pitfalls

- **Python API (`omni.replicator.core`) is at `/py/replicator/`** — those pages return 403 on `.md`. Use HTML fallback or the `omni.replicator.core` section of the main ext page.
- **`rep.randomizer` vs `with rep.trigger.on_frame():`** — Replicator mixes decorator-style randomizers with `with`-block trigger contexts. Pull `basic_functionalities.html` before answering authoring-pattern questions.
- **Writers are the output contract.** The user wanting "why isn't my data saving" almost always has a writer problem — route to `writer_examples.html` or `custom_writer.html`.
- **Semantics authoring is load-bearing.** Objects must have correct semantic labels for instance / semantic segmentation to work. Check `semantics_schema_editor.html`.
- **Isaac Sim wraps this.** If the user is using Isaac Sim, don't answer with raw `omni.replicator.core` — point them at `isaacsim.replicator` in the Isaac Sim skill.
- **AWS / container setups drift.** Environment pages (`aws_setup.html`, `container_setup.html`) often lag the actual images — verify container tags on NGC before recommending.
