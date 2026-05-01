# NVIDIA Forums — Live Sources

Curated entry points for `forums.developer.nvidia.com`. The forum runs Discourse; every HTML URL has a `.json` counterpart per `retrieval-rule.md`.

Verified 2026-04-23.

---

## Search-first workflow

Most forum questions are best served by starting at **search**, not browsing categories. The search index covers topic title + post body across every public category.

| Topic | URL | Extraction Prompt |
|---|---|---|
| Global search | `https://forums.developer.nvidia.com/search.json?q=<QUERY>` | "Find all topics matching the query. Return `topics[]` (id, title, slug, posts_count, last_posted_at) and `posts[]` (with topic_id so we can follow to the thread). Rank by recency + reply_count." |
| Search within category | `https://forums.developer.nvidia.com/search.json?q=<QUERY>%20%23<cat-slug>` | "Discourse syntax: `#<category-slug>` in the query scopes to that category. Example: `CreateXR #isaac-sim` limits to the Isaac Sim sub." |
| Get a topic's full content | `https://forums.developer.nvidia.com/t/<slug>/<id>.json` | "Extract `title`, `last_posted_at`, `post_stream.posts[]`. Read the first post for the question; filter remaining posts by `admin`/`moderator`/`accepted_answer` to surface staff / solution replies." |

## Category catalog (top-level + relevant subs)

Use these when the user wants to browse "recent X threads" rather than search a specific query.

### Omniverse (parent id: **300**)

| Subcategory | ID | URL | Extraction Prompt |
|---|---|---|---|
| Isaac Sim | **69** | `https://forums.developer.nvidia.com/c/omniverse/simulation/69.json` | "List recent Isaac Sim threads. Each topic has id, title, posts_count, reply_count, last_posted_at. **Canonical slug is `simulation`** — the old `isaac-sim` slug 301-redirects but returns `content-type: text/html` even though the body is valid JSON." |
| XR & Spatial Computing | **707** | `https://forums.developer.nvidia.com/c/omniverse/xr-spatial-computing/707.json` | "List recent XR / VR / AR threads in the Omniverse category — CloudXR, Vision Pro, OpenXR, Quest, SteamVR." |
| Synthetic Data Generation (SDG) | **595** | `https://forums.developer.nvidia.com/c/omniverse/synthetic-data-generation-sdg/595.json` | "List recent Replicator / SDG threads." |
| Core Platform | **397** | `https://forums.developer.nvidia.com/c/omniverse/platform/397.json` | "List threads about Omniverse Kit, Carbonite, extensions, app framework." |
| Learning and Resources | **681** | `https://forums.developer.nvidia.com/c/omniverse/resources/681.json` | "Educational / tutorial threads." |
| Announcements | **302** | `https://forums.developer.nvidia.com/c/omniverse/announcements/302.json` | "Official release / news announcements." |
| Feedback | **682** | `https://forums.developer.nvidia.com/c/omniverse/feedback/682.json` | "Product feedback / feature requests." |
| Archive | **725** | `https://forums.developer.nvidia.com/c/omniverse/omniverse-archive/725.json` | "Archived legacy threads — useful for historical context; flag staleness." |
| Deprecated Apps and Extensions | **728** | `https://forums.developer.nvidia.com/c/omniverse/deprecated-apps-and-extensions/728.json` | "Threads about apps that have been deprecated (Create XR, old Kit apps). Useful for the 'is X still a thing' question." |

### Robotics & Edge Computing (parent id: **55**)

Isaac ROS, Jetson, and related robotics platforms. Use search with `#robotics-edge-computing` or enumerate subcategories via `/categories.json`.

| Category | URL pattern | Extraction Prompt |
|---|---|---|
| Robotics top-level | `https://forums.developer.nvidia.com/c/robotics-edge-computing/55.json` | "List recent robotics / edge compute threads — Isaac ROS, Jetson, robot controllers, motion planning." |

### AI & Data Science (parent id: **86**)

TensorRT, Triton, cuDNN, ML frameworks. 16 subs.

| Category | URL pattern |
|---|---|
| AI & Data Science top-level | `https://forums.developer.nvidia.com/c/ai-data-science/86.json` |

### Autonomous Vehicles (parent id: **517**)

DRIVE Sim, DRIVE OS, perception.

| Category | URL pattern |
|---|---|
| AV top-level | `https://forums.developer.nvidia.com/c/autonomous-vehicles/517.json` |

### Accelerated Computing (parent id: **5**)

CUDA, compilers, NCCL, libraries.

| Category | URL pattern |
|---|---|
| Accelerated Computing | `https://forums.developer.nvidia.com/c/accelerated-computing/5.json` |

### Gaming & Visualization (parent id: **192**)

RTX, DLSS, G-SYNC, CloudXR for gaming.

| Category | URL pattern |
|---|---|
| Gaming & Vis | `https://forums.developer.nvidia.com/c/gaming-and-visualization-technologies/192.json` |

## Discovery pattern

When a user mentions a product that isn't in the catalog (e.g., `Cosmos`, `GR00T`, `Riva`, `DeepStream`, `Metropolis`), don't guess a category ID. Instead:

1. Search for the product name: `/search.json?q=<product>`
2. Look at the top results' `category_id` — that tells you which existing category hosts it.
3. Optionally fetch `/categories.json` and grep for the slug.

For anything under Omniverse / Isaac, use the subcategory IDs above directly. For anything else, search first.

## High-signal canonical threads (examples)

These are real, verified threads that answer common cross-product questions. Great for demonstrating the extraction flow or for users who land here from a search.

| Topic | URL | Extraction Prompt |
|---|---|---|
| "Integration between IsaacSim and Create XR" (2022 NVIDIA staff answer about enabling XR extensions in Isaac Sim) | `https://forums.developer.nvidia.com/t/integration-between-isaacsim-and-create-xr/229108.json` | "Extract the NVIDIA staff reply (`Hammad_M`) explaining that Isaac Sim ships the same XR extensions as Create XR — enable via Extension Manager. Note the Windows-only limitation and the Linux workaround (semu.xr.openxr)." |
| "Can I use CreateXR with IsaacSim?" | `https://forums.developer.nvidia.com/t/can-i-use-createxr-with-isaacsim/232462.json` | "Follow-up thread — read the resolution." |
| "VR headsets on Isaac Sim" | `https://forums.developer.nvidia.com/t/can-isaac-sim-display-simulation-content-correctly-on-different-vr-headsets/350774.json` | "Extract the current supported-headset matrix and staff-recommended upgrade path." |
| "OpenXR on Isaac Sim with VR Experience extensions" | `https://forums.developer.nvidia.com/t/how-to-use-openxr-on-isaac-sim-with-vr-experience-extenstions/296597.json` | "Known OpenXR init error on Quest Pro, workarounds and staff guidance." |
| "Request for CloudXR Runtime access for Isaac Sim + Vision Pro teleoperation" | `https://forums.developer.nvidia.com/t/request-for-cloudxr-runtime-access-for-isaac-sim-apple-vision-pro-teleoperation/365778.json` | "CloudXR early-access context for Vision Pro teleop users." |
| "Help Us Improve Isaac Sim Documentation — Share Your Developer Workflows" (2026) | `https://forums.developer.nvidia.com/t/2026-help-us-improve-isaac-sim-documentation-share-your-developer-workflows/359712.json` | "NVIDIA's own docs-feedback thread — useful context for 'what's being worked on'." |

---

## Notes on extraction

- **Always extract `title`, `last_posted_at`, and post 1 first.** That's the question. Everything else is optional.
- **Filter by `staff`/`admin`/`moderator`** to surface authoritative replies in long threads.
- **`cooked` is HTML** — strip `<[^>]+>` for plain text; retain `<a>` when the user wants links.
- **Cite the HTML URL** (without `.json`) back to the user so they can open it in a browser.
- **Include the date** when citing old posts: "In a 2022 thread, NVIDIA staffer X said..."

## Exceptions

- **Admin-only endpoints** return 401/403 — skip.
- **Deleted / flagged posts** may appear with `visible: false` — skip.
- **Private messages** (`/u/<user>/messages`) need auth — skip.

## Version drift

Discourse schema is stable — additive changes only. If a field goes missing, check Discourse's public API docs (this is upstream open-source software). Category IDs are stable; slugs occasionally change — always use IDs for routing.
