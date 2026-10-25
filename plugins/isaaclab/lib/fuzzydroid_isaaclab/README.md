# fuzzydroid-isaaclab

Bundled Python for the fuzzydroid `isaaclab` plugin. Stdlib only.

| module | role |
|---|---|
| `fuzzydroid_isaaclab.detect` | find pip venvs containing the `isaaclab` dist and IsaacLab source checkouts — never assumes a venv name |
| `fuzzydroid_isaaclab.setup` | non-interactive recorder: validates the confirmed install, warns on the static-TLS blanket-guard hazard, writes `~/.config/fuzzydroid/isaaclab.toml` |
| `fuzzydroid_isaaclab.doctor` | state-file-driven health table; absent components read N/A, never FAIL; FAILs the static-TLS guard-rule violation |

Run via `uv run --with-editable . python -m fuzzydroid_isaaclab.<module>`;
the `/isaaclab:*` commands do this for you.
