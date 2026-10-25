# MuJoCo community forums (GitHub Discussions)

## Why this matters

When a user asks "why is my contact unstable", "how do I tune solref", "MJX won't compile on H100", "how do I import URDF X" — these are **community questions**. Someone has almost certainly asked them before. The answer is in a GitHub Discussion, not in the formal docs.

**Do not direct users to `http://www.mujoco.org/forum`** — that forum was deleted when DeepMind acquired MuJoCo in 2021–2022 (see `https://github.com/google-deepmind/mujoco/issues/21`). All historical posts are lost. The replacement is GitHub Discussions across the six MuJoCo-ecosystem repos.

## The six forums

| Repo | Discussions URL | Best for |
|---|---|---|
| `mujoco` | `github.com/google-deepmind/mujoco/discussions` | Core sim, XML modeling, C API, Python bindings, contact / solver tuning, rendering |
| `mujoco_menagerie` | `github.com/google-deepmind/mujoco_menagerie/discussions` | Asset issues, robot-specific quirks, requests for new robots |
| `mujoco_warp` | `github.com/google-deepmind/mujoco_warp/discussions` | NVIDIA Warp backend issues, GPU perf, kernel bugs |
| `mujoco_playground` | `github.com/google-deepmind/mujoco_playground/discussions` | RL training, sim-to-real, Madrona rendering, environment design |
| `mujoco_mpc` | `github.com/google-deepmind/mujoco_mpc/discussions` | MJPC tuning, custom tasks, planner choice |
| `dm_control` | `github.com/google-deepmind/dm_control/discussions` | Composer, Suite environments, PyMJCF |

## How to search (with `gh`)

```bash
# Search across one repo
gh search discussions --repo google-deepmind/mujoco "contact instability"

# Search across multiple
for r in mujoco mujoco_warp mujoco_playground; do
  echo "=== $r ==="
  gh search discussions --repo google-deepmind/$r "<keywords>"
done
```

`gh search discussions` ranks by relevance and prints title + URL + first-line snippet.

## How to read a thread

```bash
# By number (from the URL: .../discussions/3094)
gh api repos/google-deepmind/mujoco/discussions/3094 --jq '.title, .body'

# Plus all replies
gh api graphql -f query='
  query {
    repository(owner: "google-deepmind", name: "mujoco") {
      discussion(number: 3094) {
        title
        body
        comments(first: 50) {
          nodes { author { login } body }
        }
      }
    }
  }
'
```

If `gh` is unavailable, plain `WebFetch` on the discussion URL also works — GitHub Discussions are server-rendered.

## How to list recent activity

```bash
# Recent across the whole MuJoCo discussion forum
gh api graphql -f query='
  query {
    repository(owner: "google-deepmind", name: "mujoco") {
      discussions(first: 20, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes { number title category { name } updatedAt url }
      }
    }
  }
'
```

## Categories on the main `mujoco` repo (verified live)

The main MuJoCo forum has six categories. The naming differs from a typical Stack Overflow tag — note in particular that there is no "Q&A" category; the equivalent is **Asking for Help**.

| Category | Slug | Best for |
|---|---|---|
| 📣 Announcements | `announcements` | DeepMind release notes, version drops, deprecations |
| 🙏 Asking for Help | `asking-for-help` | User questions — the Stack Overflow analog |
| 💬 General | `general` | Open-ended discussion |
| 💡 Ideas | `ideas` | Feature requests, design open questions |
| 🗳️ Polls | `polls` | Community polls (lower volume) |
| 🙌 Show and tell | `show-and-tell` | Community projects, integrations, demos |

## Search heuristics

- **Asking for Help** is the highest-signal-for-help-questions filter. URL: `.../discussions/categories/asking-for-help`
- **Announcements** is where DeepMind posts releases, deprecations, breaking changes. Worth checking when a user reports a version-related bug.
- Threads can be **years old** — confirm the latest reply date before quoting an answer as authoritative. The MuJoCo API changed significantly across the 2.x → 3.x boundary (Feb 2024).
- Maintainer responses (typically `@yuvaltassa`, `@btaba`, `@kevinzakka`, `@erikfrey` and other DeepMind staff) carry more weight than community speculation. Their GitHub badges show "Member" or "Collaborator".

## Sub-forum specialization notes

- **Playground** discussions skew toward RL (PPO, BRAX, JAX gotchas, sim-to-real on Unitree Go2 / Franka).
- **Warp** discussions skew toward CUDA driver, multi-GPU, kernel fusion limits.
- **Menagerie** discussions are mostly "my robot X behaves wrong" or "add robot Y" — short, asset-focused.
- **dm_control** discussions are now lower-volume because new work has migrated to Playground; treat as historical reference for Composer.
