# Compatibility and evidence

Qualified live target: **KiCad 10.0.7 on macOS, ARM64**. The embedded Python is
3.9; the external plugin runtime is Python 3.11. Keep embedded imports compatible
with 3.9. Windows/Linux path and loopback behavior have automated tests; live
Windows qualification is still required before a cross-platform release.

KiCad 10's published kicad-python 0.8.0 wheel does not decode ReferencePoint items
returned by the qualified app. Setup builds the official stable bindings at
`8cdeb8964597968b11b2176ee288ccf1811d1633`, with proto submodule
`17d01cb65d379cd14a16c8ca141ab1d857c562a5`. Archives are revision-pinned and
checksum-verified. The proto archive is downloaded as a subtree, avoiding KiCad's
full Git history. This code is an installed dependency, not bundled KiCad source.

Setup installs `fuzzydroid_kicad` in the shared venv and writes the usual
`~/.config/fuzzydroid/kicad.toml` (Windows: `%APPDATA%/fuzzydroid/kicad.toml`).
KiCad executable paths, plugin loader path and source root are recorded facts,
not constants in the published skill. A tiny generated user-level loader points
to the installed plugin package. Application files and unrelated plugins are
preserved. Loader changes take effect after restarting PCB Editor.

Doctor checks setup state, package version, dependency hash, editable-install root,
loader hash, IPC decoding and native source provenance. A source mismatch requires
an editor restart; dependency or checkout drift requires rerunning setup.

The official IPC and native bindings expose selected functionality. No claim is
made of complete schematic, camera-internal or arbitrary C++ control. Native
menu discovery/invocation gives access to real menus without keyboard simulation.
Menu labels depend on application language. Discover the current labels.

Legacy SWIG bindings are deprecated and planned for removal in KiCad 11. The
native backend explicitly refuses other major versions. `--no-native` sets up
the IPC-only path for another supported installation, whose operations still
require version-specific validation.

Sources:

- https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/
- https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/
- https://gitlab.com/kicad/code/kicad-python/-/tree/stable
