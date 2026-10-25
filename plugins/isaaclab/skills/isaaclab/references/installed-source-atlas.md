# Installed-source atlas (Isaac Lab)

Isaac Lab's installed tree is the version-true API reference for *this box* —
read it directly for API-exact questions. It sits on top of Isaac Sim's own
atlas (see the `isaacsim` plugin's `references/installed-source-atlas.md` for
the Kit/Isaac platform underneath).

## Where the tree is (derive, never hardcode)

Read `variant` and `lab_root` from the state file
(`~/.config/fuzzydroid/isaaclab.toml`):

| variant | what `lab_root` is | where the Lab code lives |
|---|---|---|
| `pip` | the venv | `<lab_root>/lib/pythonX.Y/site-packages/isaaclab*/` |
| `source` | the IsaacLab checkout | `<lab_root>/source/isaaclab*/` |

**Shadowing gotcha**: a source checkout on the import path silently wins over
a pip dist in the same interpreter. Always confirm with the interpreter
primitive below rather than trusting dist metadata — the two can disagree.

## The map

| Path | What | Go here for |
|---|---|---|
| `isaaclab/` | The core framework | `envs`, `sim` (SimulationContext, spawners), `assets`, `managers`, `sensors`, `actuators`, `scene`, `controllers`, `app` (AppLauncher) |
| `isaaclab_tasks/` | Every registered task/environment | Task ids (`Isaac-Cartpole-v0`, …), their cfg classes — the answer to "what envs exist and how are they configured" |
| `isaaclab_assets/` | Robot/articulation asset configs | Ready-made robot cfgs to copy from |
| `isaaclab_rl/` | RL library integrations | rsl_rl / rl_games / skrl / sb3 wrapper code |
| `isaaclab_mimic/` | Imitation-learning stack | Mimic/teleop data-gen internals |
| checkout `scripts/tutorials/` | Runnable canonical examples, numbered by topic | The working form of every docs tutorial |
| checkout `scripts/reinforcement_learning/<lib>/` | `train.py` / `play.py` per RL library | The canonical training entry points |
| checkout `apps/*.kit` | Lab's own Kit experiences (`isaaclab.python.headless.kit`, …) | What AppLauncher actually loads per flag combination |

(`scripts/` and `apps/` exist only in a checkout; a pip-only install has the
packages but not the tutorials — clone the IsaacLab repo when you need them.)

## Two navigation primitives (state these before any enumeration)

1. **Ask the recorded interpreter** (`lab_python` from the state file) — the
   authoritative answer to "which code actually runs", including shadowing:

   ```bash
   <lab_python> -c "import isaaclab; print(isaaclab.__version__, isaaclab.__file__)"
   ```

2. **Grep the tree as an API search engine**:

   ```bash
   grep -rn "class AppLauncher" <lab_code_root> --include='*.py' | head
   ```

## Routing doctrine — installed source vs live docs

| Question shape | Route |
|---|---|
| Exact signature / cfg field / task id / manager term | **Installed source** (this atlas) |
| Concept, workflow choice, tutorial, deprecation | **Live docs** (`/robodocs:robodocs (nvidia workflow)` → isaac-lab) |
| The two disagree | **Installed source wins** for code that runs on this box — the runtime is the arbiter |
