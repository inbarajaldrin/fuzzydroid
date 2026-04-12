# fuzzydroid Plugin Conventions

Every plugin published under the fuzzydroid marketplace follows this template. The conventions exist so that users who install one fuzzydroid plugin already know how to install the next one, and so that Claude (or a future human contributor) can bootstrap a new plugin without re-brainstorming shape.

## 1. Two convention commands (required)

Every plugin MUST ship exactly two convention commands:

- `/<name>:setup` — idempotent one-time install. Verifies prerequisites, creates the shared venv if missing, installs the plugin's Python code editable, performs plugin-specific setup (symlinks, config files, etc.), writes a state file, prints manual-action instructions if any, and offers to run doctor.
- `/<name>:doctor` — health check. Reads the state file, verifies every install artifact is still healthy, detects version drift (e.g. `pyproject.toml` hash changed), and prints a markdown table with ✅/❌ per component.

Any additional commands are optional and plugin-specific.

## 2. State file (required)

Every plugin MUST write a per-plugin state file at:

- **macOS:** `~/.config/fuzzydroid/<name>.toml`
- **Windows:** `%APPDATA%\fuzzydroid\<name>.toml`

Minimum required fields:

| Field | Type | Purpose |
|---|---|---|
| `venv_path` | string | Absolute path to the shared fuzzydroid venv |
| `plugin_version` | string | Plugin version at time of last setup |
| `pyproject_hash` | string | SHA-256 of `shared/fuzzydroid/pyproject.toml` at last setup |
| `install_timestamp` | string (ISO-8601) | When setup last ran |
| `python_version` | string | Python version used to create the venv |

Plugin-specific fields are allowed (e.g., the `fusion` plugin adds `addin_symlink_path`).

## 3. Shared venv (required)

All fuzzydroid plugins install their Python code into a single user-level venv:

- **macOS:** `~/.local/share/fuzzydroid/venv`
- **Windows:** `%LOCALAPPDATA%\fuzzydroid\venv`

The first plugin whose `/setup` command runs creates the venv with `uv venv <path> --python 3.11`. Subsequent plugins reuse it. Python version is pinned to 3.11 for the fleet until an explicit reason to change arises.

## 4. Python code layout (required)

A plugin's Python code lives at `shared/fuzzydroid/fuzzydroid/<name>/` in the monorepo. Inside the `fuzzydroid` namespace package, each plugin is a subpackage imported as `fuzzydroid.<name>`.

Plugin-specific scripts that must be run as files rather than imports (e.g., Fusion scripts executed via `fusion_exec_python`) live in `plugins/<name>/scripts/`.

## 5. Cross-platform minimum (required)

Every plugin MUST support macOS and Windows 10+ unless the underlying tool is Linux-only (e.g., a hypothetical future `roslaunch` plugin). Plugins that can't support a platform MUST fail with a friendly message explaining why, not with a cryptic error.

Platform detection belongs in `fuzzydroid.common.platform`. Do not scatter `platform.system()` calls across plugin code.

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

---

## Bootstrap checklist for a new plugin

When adding a new plugin to fuzzydroid:

1. Create `plugins/<name>/` with `plugin.json`, `skills/<name>/SKILL.md`, and `commands/setup.md` + `doctor.md`.
2. Create `shared/fuzzydroid/fuzzydroid/<name>/` with `__init__.py`, `setup.py`, `doctor.py`.
3. Add `shared/fuzzydroid/tests/<name>/` with `test_setup.py` and `test_doctor.py`.
4. Add a row to `plugins/fusion/` section in `README.md`.
5. Add the plugin to `marketplace.json`.
6. If using upstream code, update `NOTICES.md`.
7. Test on macOS AND Windows before shipping.
