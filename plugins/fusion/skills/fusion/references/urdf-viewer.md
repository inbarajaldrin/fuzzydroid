# URDF Viewer

Bundled interactive browser viewer for any ROS-style URDF package — joint sliders,
drag controls, collision toggle, animate-joints, ignore-limits, autocenter, up-axis
selector. Built on the [gkjohnson/urdf-loaders](https://github.com/gkjohnson/urdf-loaders)
JavaScript library (Apache-2.0), bundled in `plugins/fusion/viewer/urdf/`.

## When to use

User says any of:
- "show me the URDF"
- "view this robot"
- "open the URDF / robot model in a browser"
- "let me see the joints / spin the wheels"

## Quick usage

```bash
python3 plugins/fusion/viewer/urdf/serve_urdf.py <pkg_dir> --port 8090
```

`<pkg_dir>` is any directory containing `urdf/*.urdf` and `meshes/*.STL`. The script:

1. Auto-detects all `.urdf` files in the package.
2. Auto-detects every `package://NAME/...` reference and maps each name to the same
   web root via a symlink (so cross-package mesh references resolve correctly).
3. Generates `viewer/index.html` with the URDF list rendered as a clickable menu.
4. Serves on `127.0.0.1:<port>` by default.
5. Opens the browser unless `--no-open` is passed.

Ctrl+C cleans up the symlink and generated index.

## Flags

| Flag | Default | Purpose |
|---|---|---|
| `--port N` | `8090` | TCP port to bind |
| `--host HOST` | `127.0.0.1` | Bind address. **Use `0.0.0.0` to expose on Tailscale / LAN.** |
| `--no-open` | off | Skip auto-opening the browser (use when the agent is launching it) |

## Expose on Tailscale

```bash
python3 serve_urdf.py /tmp/mybot --port 8091 --host 0.0.0.0 --no-open
# Then share http://<mac-tailscale-hostname>:8091/ with colleagues on the tailnet
```

Tailscale encrypts the transport between devices, so plain HTTP on the tailnet is
fine. **Anyone on your tailnet** can reach the server while it's running — stop it
when done sharing: `lsof -ti tcp:<port> | xargs kill`.

## Two URDFs side-by-side

The script is **single-tenant by design**: it writes one `viewer/index.html` and one
`viewer/robot` symlink per run. Two simultaneous viewers need **two copies** of the
script directory:

```bash
cp -R plugins/fusion/viewer/urdf /tmp/urdf-view-a
cp -R plugins/fusion/viewer/urdf /tmp/urdf-view-b
python3 /tmp/urdf-view-a/serve_urdf.py /path/to/pkg_a --port 8090 &
python3 /tmp/urdf-view-b/serve_urdf.py /path/to/pkg_b --port 8091 &
```

## How `package://` resolution works

The viewer's web component takes a `package="name1:./robot,name2:./robot"` attribute.
At render time, every `package://name1/...` URI gets rewritten to `./robot/...`.

That's why the script's `<pkg_dir>` argument needs to be the directory that contains
the meshes — not the directory containing other ROS packages. If the URDF references
`package://bunker_description/meshes/wheel1.STL`, the viewer looks for
`<pkg_dir>/meshes/wheel1.STL` (the package name is stripped). Cross-package URDFs
require either consolidating meshes into one dir or pointing each `package://NAME` at
a separate symlinked subtree.

## Bundled assets

In `plugins/fusion/viewer/urdf/viewer/assets/`:
- `URDFLoader-*.js` — compiled gkjohnson loader (Apache-2.0)
- `URDFDragControls-*.js` — mouse-drag joint manipulation
- `OrbitControls-*.js` — three.js camera
- `index-*.js`, `index-*.css` — the viewer page itself
- `vr-*.js`, `simple-*.js` — minimal example pages (unused at runtime)

The asset filenames have content hashes — `serve_urdf.py` discovers them dynamically
in `find_assets()`. If the bundle is updated, the script keeps working as long as the
filename **prefixes** stay the same (`URDFLoader-`, `OrbitControls-`, etc.).

## Stopping the viewer

```bash
lsof -ti tcp:<port> | xargs kill
```

Or Ctrl+C in the terminal that started it. The script's signal handler removes the
`viewer/robot` symlink and the generated `index.html` on exit.

## Future migration

Per the original design spec, the URDF viewer is currently **inside the `fusion`
plugin only because no dedicated `urdf` plugin exists yet**. When a `urdf` plugin
ships, `viewer/urdf/` migrates there and this reference moves with it. The current
fusion plugin's `viewer/README.md` documents this.
