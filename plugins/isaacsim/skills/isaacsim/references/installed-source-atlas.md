# Installed-source atlas

The installed Isaac tree is a **self-describing platform**: every extension
ships its own docs, the app definitions are readable TOML, and reference
implementations are installed as example extensions. For API-exact questions,
read it directly — it is version-true for *this box*, which no website is.

## Where the tree is (derive, never hardcode)

Read `variant` and `isaac_root` from the state file
(`~/.config/fuzzydroid/isaacsim.toml`):

| variant | atlas root |
|---|---|
| `pip-lab` / `pip-standalone` | `<isaac_root>/lib/pythonX.Y/site-packages/isaacsim/` |
| `binary` | `<isaac_root>/` (same subdirs, no site-packages) |
| `source` | the checkout's build output (`_build/…`), same shape |

## The map

| Path (under the atlas root) | What | Go here for |
|---|---|---|
| `exts/` | **Isaac-owned extensions** — every one ships `docs/` with `api.rst`, `README.md`, `CHANGELOG.md`, and `ogn/` (OmniGraph node reference) | API ground truth: `isaacsim.core.*`, `robot.*`, `sensors.*`, `gui.components`, `ros2.bridge`, `replicator.*` |
| `extscache/` | **The Kit/Omniverse platform** (versioned dirnames): `omni.kit.*` (the full UI/framework), `omni.physx.*`, `omni.graph.*`, `omni.usd.*`, `omni.services.*`, `omni.anim.*`, `omni.hydra.*` | Kit/Omniverse platform internals — widgets, physics, OmniGraph, USD utilities, microservices |
| `apps/` | The `.kit` experience files | **What an app *is*** — readable TOML recipes listing every extension each app loads |
| `extsDeprecated/` | Old `omni.isaac.*` names | Migration breadcrumbs when an old tutorial references a dead module |
| `extsUser/` | User drop-in extensions | Local additions |
| sibling `warp/` (site-packages) | Full NVIDIA Warp source | GPU kernel API truth |

### Example extensions — working reference code, not prose

- `isaacsim.examples.ui` — UI widget patterns
- `isaacsim.examples.extension` — how to write an extension
- `isaacsim.examples.interactive`, `isaacsim.examples.browser`
- `isaacsim.replicator.examples`, `isaacsim.robot.manipulators.examples`
- `isaacsim.gui.components` — the builder library (`ui_utils.py`:
  `btn_builder`, `str_builder`, `dropdown_builder`, …) and `style.py`
  (`get_style()` — the native Isaac look)

### Isaac Lab

Isaac Lab has its own atlas — see the `isaaclab` plugin's
`references/installed-source-atlas.md`.

## Two navigation primitives (state these before any enumeration)

1. **Ask the recorded interpreter where anything lives** — also catches
   shadowing (a source checkout silently winning over a pip dist):

   ```bash
   <isaac_python> -c "import isaacsim.core.api as m; print(m.__version__ if hasattr(m,'__version__') else '', m.__file__)"
   ```

2. **Grep the tree as an API search engine** — hundreds of extensions of source:

   ```bash
   grep -rn "def set_world_pose" <atlas_root>/exts <atlas_root>/extscache --include='*.py' | head
   ```

## Routing doctrine — installed source vs live docs

| Question shape | Route |
|---|---|
| Exact signature / widget / kwarg / setting key / OGN node name | **Installed source** (this atlas) |
| Concept, tutorial, "how should I", "is this deprecated" | **Live docs** (`/robodocs:nvidia` → isaac-sim) |
| The two disagree | **Installed source wins** for code that runs on this box — the runtime is the arbiter |
