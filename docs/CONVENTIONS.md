# fuzzydroid Plugin Conventions

Every plugin published under the fuzzydroid marketplace follows this template. The conventions exist so that users who install one fuzzydroid plugin already know how to install the next one, and so that Claude (or a future human contributor) can bootstrap a new plugin without re-brainstorming shape.

## 1. Two convention commands (required)

Every plugin with a local runtime MUST ship exactly two convention commands
(documentation-only plugins such as RoboDocs do not need setup or doctor):

- `/<name>:setup` — idempotent one-time install. Verifies prerequisites, creates the plugin venv if missing, installs the plugin's Python code editable, performs plugin-specific setup (symlinks, config files, etc.), writes a state file, prints manual-action instructions if any, and offers to run doctor.
- `/<name>:doctor` — health check. Reads the state file, verifies every install artifact is still healthy, detects version drift (e.g. `pyproject.toml` hash changed), and prints a markdown table with ✅/❌ per component.

Any additional commands are optional and plugin-specific.

## 2. State file (required)

Every plugin MUST write a per-plugin state file at:

- **macOS:** `~/.config/fuzzydroid/<name>.toml`
- **Windows:** `%APPDATA%\fuzzydroid\<name>.toml`

Minimum required fields:

| Field | Type | Purpose |
|---|---|---|
| `venv_path` | string | Absolute path to the plugin's venv |
| `plugin_version` | string | Plugin version at time of last setup |
| `pyproject_hash` | string | SHA-256 of the plugin's bundled `lib/<pkg>/pyproject.toml` at last setup |
| `install_timestamp` | string (ISO-8601) | When setup last ran |
| `python_version` | string | Python version used to create the venv |

Plugin-specific fields are allowed (e.g., the `fusion` plugin adds `addin_symlink_path`).

## 3. Per-plugin venv (required)

Every fuzzydroid plugin installs its Python code into its **own** user-level venv:

- **macOS/Linux:** `~/.local/share/fuzzydroid/<name>/venv`
- **Windows:** `%LOCALAPPDATA%\fuzzydroid\<name>\venv`

The plugin's `/setup` command creates it with `uv venv <path> --python 3.11`. Python version is pinned to 3.11 for the fleet until an explicit reason to change arises.

Plugins deliberately do NOT share a venv. Marketplace installs ship each plugin's subtree independently, so there is no shared install unit — and a shared venv couples every plugin's dependency set and install lifecycle (one plugin's reinstall, dependency conflict, or `claude plugin prune` could break the others). Isolation costs a few MB of disk and buys zero cross-plugin blast radius.

## 4. Python code layout (required)

A plugin's Python code lives at `plugins/<name>/lib/<pkg>/` — **bundled inside the plugin directory** so the marketplace install (which only ships the `plugins/<name>/` subtree) includes it. `<pkg>` is a flat, standalone package named `fuzzydroid_<name>` (distribution `fuzzydroid-<name>`):

```
plugins/<name>/lib/fuzzydroid_<name>/
├── pyproject.toml
├── fuzzydroid_<name>/
│   ├── _common.py        # vendored fleet plumbing (see §4a)
│   ├── setup.py          # /​<name>:setup orchestrator
│   ├── doctor.py         # /​<name>:doctor checks
│   └── ...               # plugin-specific modules
└── tests/
```

The canonical install path at runtime is `${CLAUDE_PLUGIN_ROOT}/lib/fuzzydroid_<name>`, identical for dev and marketplace installs. Each plugin's package is fully standalone — no imports across plugins, no namespace packages.

If the plugin ships a console script, name it `fzd-<name>` (e.g. `fzd-fusion`).

Plugin-specific scripts that must be run as files rather than imports (e.g., Fusion scripts executed via `exec`) live in `plugins/<name>/scripts/`.

### 4a. Vendored common plumbing

The setup/doctor plumbing every plugin needs (platform detection, per-plugin venv paths, uv venv management, TOML state I/O, file hashing) lives in ONE canonical master at `tools/common/_common.py`. Each plugin vendors a **byte-identical copy** at `plugins/<name>/lib/<pkg>/<pkg>/_common.py`.

- Edit the master first, then re-copy it into every plugin.
- `python3 tools/check_common_sync.py` verifies all copies match (also runnable via pytest).
- Anything plugin-specific (e.g. fusion's add-in symlink helper) stays out of `_common.py` and lives in the plugin's own modules.

If the fleet outgrows vendoring, the escape hatch is publishing `fuzzydroid-common` and replacing the copies with a real dependency.

## 5. Cross-platform minimum (required)

Every plugin MUST support macOS and Windows 10+ unless the underlying tool is Linux-only (e.g., a hypothetical future `roslaunch` plugin). Plugins that can't support a platform MUST fail with a friendly message explaining why, not with a cryptic error.

Platform detection belongs in the vendored `_common.py`. Do not scatter `platform.system()` calls across plugin code.

## 6. Attribution (required)

See `NOTICES.md` at the repo root. Every plugin that imports, copies, or adapts code from an upstream project MUST:

a. Preserve the upstream copyright header in the derived file.
b. Add an entry to `NOTICES.md`.
c. Verify the upstream's license is compatible with Apache-2.0 (MIT, BSD, Apache-2.0, and Autodesk Sample License are compatible; GPL/AGPL are not).

## 7. Updates via native `/plugin update` only (required)

No plugin ships a custom `<name>:update` command. Native Claude Code `/plugin update` pulls new files from the marketplace repo, and the combination of editable-install venv + symlinked on-disk artifacts means most updates are automatic.

The one exception is `pyproject.toml` dependency changes, which require re-running `/<name>:setup` to install new deps. `/<name>:doctor` MUST detect this by hash-comparing `pyproject.toml` and print a clear message.

## 8. No stubs in the marketplace manifest (required)

A plugin only appears in `.claude-plugin/marketplace.json` when it works end-to-end. No placeholder plugins, no "coming soon" entries. The fleet vision is documented in `README.md` and this file, not in the manifest.

## 9. Claude Code and Codex packaging (required)

Keep `.claude-plugin/marketplace.json`, each plugin's
`.claude-plugin/plugin.json`, and `commands/*.md` as the metadata and command
sources. Run `python3 tools/sync_plugins.py` to generate
`.agents/plugins/marketplace.json`, each plugin's `.codex-plugin/plugin.json`,
and small command skills that load the same command workflows. Run it with
`--check` before committing. Do not edit generated files directly.

Both hosts load `skills/<name>/SKILL.md`. Every skill needs valid `name` and
`description` frontmatter; descriptions must fit Codex's 1024-character limit.
Use Claude's `/plugin:skill` or Codex's `$plugin:skill` to invoke it. Resolve
plugin-relative paths from the real skill location, not the caller's working
directory. Pass the resolved root as `CLAUDE_PLUGIN_ROOT` for existing command
examples. Python entry points also accept Codex's `PLUGIN_ROOT` variable.

Host-specific tool names in workflows mean the equivalent shell, file, web, or
user-input capability of the current host. Runtime assets and dependencies must
stay inside each plugin subtree or be installed by its setup workflow.

Keep personal tutorials, session transcripts, robot-specific experiments, and
their full artifacts in the user's project or reference archive. Skills should
contain general procedures, parameterized tools, and reusable references, and
must work without that personal archive. Before generalizing session notes,
preserve their full originals with the user's reference material.

A multi-skill plugin's main skill should route natural-language goals to its
specialist instructions internally. Resolve and read sibling skill files in the
current task, combine workflows when needed, and continue through verification.
Specialist names are optional direct entry points; do not require users to
invoke them individually to complete a request through the main router.

---

## Bootstrap checklist for a new plugin

When adding a new plugin to fuzzydroid:

1. Create `plugins/<name>/` with `plugin.json`, `skills/<name>/SKILL.md`, and `commands/setup.md` + `doctor.md`.
2. Create `plugins/<name>/lib/fuzzydroid_<name>/fuzzydroid_<name>/` with `__init__.py`, `setup.py`, `doctor.py`, plus a `pyproject.toml` at `plugins/<name>/lib/fuzzydroid_<name>/pyproject.toml`. Vendor `tools/common/_common.py` into the package and confirm `tools/check_common_sync.py` passes.
3. Add `plugins/<name>/lib/fuzzydroid_<name>/tests/` with `test_setup.py` and `test_doctor.py`.
4. Add a row to `plugins/<name>/` section in `README.md`.
5. Add the plugin to `marketplace.json`.
6. If using upstream code, update `NOTICES.md`.
7. Test on macOS AND Windows before shipping.
