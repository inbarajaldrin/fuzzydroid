# Omniverse OmniGraph Docs

Reliable live access to Omniverse OmniGraph documentation at `https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html` plus the `ext_omnigraph/` sub-tree and the Kit-manual `omni.graph` reference.

## When to use this sub-skill

Trigger on: Omniverse OmniGraph (the visual compute / action graph framework), Action Graph, Push Graph, OG nodes, `omni.graph.core`, `omni.graph.nodes`, `omni.graph.action`, compute graph in Kit, node authoring (`OgnNode`, `compute()`, node attributes, bundle types), visual scripting in USD Composer / USD Presenter, AnimGraph (built on OmniGraph Action Graph), or the broader "data-flow graphs in Omniverse" pattern. Also triggers on adjacent use — Isaac Sim's robot-specific OG nodes (differential controllers, ROS 2 bridge publishers, sensor nodes) are wrapped in the isaac-sim sub-skill, but the framework itself lives here; IoT / digital-twin graphs in Omniverse use OmniGraph; DriveSim DataStudio graphs use it.

## Why this skill exists

OmniGraph is the graph-computation framework under every Omniverse app — Action Graph (event-driven), Push Graph (continuous evaluation), AnimGraph (character animation on top of Action Graph), and thousands of pre-built nodes across vision / physics / simulation. Isaac Sim exposes robot-specific nodes built on OmniGraph, VFX pipelines use AnimGraph, DriveSim / IoT twins use data-flow graphs. The core framework (node authoring `compute()`, bundle types, graph types, evaluators) is subtle and easy to recall wrong.

## The retrieval rule

Pattern A — **append `.md` to any `.html` URL**, with HTML fallback for the `/kit/docs/omni.graph/` path tree which returns 403 on `.md`.

| HTML URL | `.md` works? | Notes |
|---|---|---|
| `/extensions/latest/ext_omnigraph.html` | YES | Main conceptual docs |
| `/extensions/latest/ext_omnigraph/<slug>.html` | YES | All sub-pages (core concepts, interface, node library) |
| `/kit/docs/omni.graph/latest/index.html` | **NO (403)** | Python API — HTML fallback |
| `/kit/docs/omni.graph.docs/latest/index.html` | **NO (403)** | Architecture guide — HTML fallback |

## HTML exceptions

- **`/kit/docs/omni.graph/` and `/kit/docs/omni.graph.docs/`** → 403 on `.md`. Fetch HTML directly.
- **Individual node-library pages** (thousands of them under `/ext_omnigraph/node-library/nodes/`) — don't enumerate; teach the agent to construct the URL from the node name when the user asks about a specific node.

## Workflow

1. Classify — is it conceptual (what's OmniGraph), authoring (write a node), Action vs Push distinction, AnimGraph (character anim layer), node-library lookup (specific node semantics), or the Python API (`omni.graph.core`)?
2. Look up in `shared/live-sources.md`. For a specific node, construct the URL: `https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph/node-library/nodes/<group>/<node-name>-<version>.html`. When the group / version isn't known, fall back to the `node-library/node-library.html` index.
3. `WebFetch` `.html.md` first; HTML fallback on 403.
4. If the user is in Isaac Sim asking about robot-specific OG nodes (differential controllers, ROS bridge) — route to the `isaac-sim` skill.
5. Cite the HTML URL back.

## Reference files

- `shared/live-sources.md` — curated entry points: Concepts · Graph Types (Action / Push) · Node Authoring · Python API · AnimGraph · Node Library Index.
- `shared/retrieval-rule.md` — rewrite rule, 403 fallback list, probe commands.

## Common pitfalls

- **Action Graph ≠ Push Graph.** Action = event-driven (keyboard, timeline, trigger). Push = continuous evaluation (data-flow, animation blend). Always disambiguate before answering.
- **AnimGraph is built on OmniGraph.** User says "AnimGraph" → look under `ext_animation-graph.html` AND the OmniGraph Action Graph concept.
- **Don't enumerate every node.** The node library has thousands of entries. Teach the URL pattern; look up specific nodes on demand.
- **Python API is at `/kit/docs/omni.graph/` which 403s on `.md`.** Always use HTML fallback for those pages.
- **Isaac Sim robot nodes are NOT here.** Differential / holonomic controllers, ROS bridge publishers, IMU sensors — those live in `isaac-sim`, not OmniGraph core.
- **Bundle types are subtle.** Inputs / outputs on OG nodes can be bundled dynamic types. Check `core_concepts.html` before recommending bundle usage.
