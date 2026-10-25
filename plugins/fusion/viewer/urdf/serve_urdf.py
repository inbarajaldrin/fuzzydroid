#!/usr/bin/env python3
"""
Serve a URDF package in the gkjohnson 3D interactive viewer.

Usage:
    python3 serve_urdf.py <urdf_dir> [--port 8090] [--no-open]

    urdf_dir: Path to a directory containing urdf/ and meshes/ subdirectories.
              e.g. outputs/scara_urdf/

The viewer auto-detects all .urdf files in the directory and lists them.
Meshes are resolved via relative paths in the URDF (../meshes/*.stl).
"""

import argparse
import atexit
import http.server
import json
import os
import re
import shutil
import signal
import sys
import tempfile
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path

VIEWER_DIR = Path(__file__).parent / "viewer"

INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <meta charset="utf-8"/>
        <title>URDF Viewer — {title}</title>
        <!-- Import map: lets the prune overlay import the locally-vendored three +
             three-mesh-bvh by bare name (offline-safe; no CDN). Must precede any
             module script. The viewer bundle uses no bare imports, so it is unaffected. -->
        <script type="importmap">
        {{
            "imports": {{
                "three": "./assets/vendor/three.module.js",
                "three-mesh-bvh": "./assets/vendor/three-mesh-bvh.module.js"
            }}
        }}
        </script>
        <script src="https://unpkg.com/@webcomponents/webcomponentsjs@2.4.3/webcomponents-bundle.js"></script>
        <link href="https://fonts.googleapis.com/css?family=Roboto:100,300" rel="stylesheet"/>
        <script type="module" crossorigin src="./assets/{js_main}"></script>
        <link rel="modulepreload" crossorigin href="./assets/{js_loader}">
        <link rel="modulepreload" crossorigin href="./assets/{js_drag}">
        <link rel="modulepreload" crossorigin href="./assets/{js_orbit}">
        <link rel="stylesheet" crossorigin href="./assets/{css_main}">
        <!-- Prune / collision / export overlay (drives the <urdf-viewer> public API). -->
        <script type="module" src="./assets/prune_overlay.js?v={overlay_ver}"></script>
    </head>
    <body tabindex="0">
        <div id="menu">
            <ul id="urdf-options">
{urdf_items}
            </ul>
            <div id="controls">
                <div id="toggle-controls"></div>
                <div>Drag and drop URDF files or folders! <br/> (Chrome Only)</div>
                <div id="ignore-joint-limits" class="toggle">Ignore Joint Limits</div>
                <div id="hide-fixed" class="toggle">Hide Fixed Joints</div>
                <div id="radians-toggle" class="toggle">Use Radians</div>
                <div id="autocenter-toggle" class="toggle checked">Autocenter</div>
                <div id="collision-toggle" class="toggle">Show Collision</div>
                <div id="do-animate" class="toggle">Animate Joints</div>
                <label>
                    Up Axis
                    <select id="up-select">
                        <option value="+X">+X</option>
                        <option value="-X">-X</option>
                        <option value="+Y">+Y</option>
                        <option value="-Y">-Y</option>
                        <option value="+Z">+Z</option>
                        <option value="-Z" selected>-Z</option>
                    </select>
                </label>
                <ul></ul>
            </div>
        </div>
        <urdf-viewer up="-Z" display-shadow tabindex="0" {package_attr}></urdf-viewer>
        <script>
        // Auto-zoom camera to fit the URDF bounding box after model loads.
        // Avoids THREE imports by reading world matrices and geometry bounds directly.
        document.addEventListener('WebComponentsReady', () => {{
            const viewer = document.querySelector('urdf-viewer');
            viewer.addEventListener('urdf-processed', () => {{
                requestAnimationFrame(() => {{
                    const robot = viewer.robot;
                    if (!robot) return;
                    const target = viewer.controls.target;
                    let maxExtent = 0;
                    robot.traverse(child => {{
                        if (child.isMesh && child.geometry) {{
                            child.geometry.computeBoundingSphere();
                            const r = child.geometry.boundingSphere
                                    ? child.geometry.boundingSphere.radius : 0;
                            child.updateWorldMatrix(true, false);
                            const m = child.matrixWorld.elements;
                            // Extract world scale to convert local radius to world units
                            const sx = Math.sqrt(m[0]*m[0] + m[1]*m[1] + m[2]*m[2]);
                            const worldR = r * sx;
                            const dx = m[12] - target.x;
                            const dy = m[13] - target.y;
                            const dz = m[14] - target.z;
                            const d = Math.sqrt(dx*dx + dy*dy + dz*dz) + worldR;
                            if (d > maxExtent) maxExtent = d;
                        }}
                    }});
                    const dist = Math.max(maxExtent * 2.5, 0.15);
                    viewer.camera.position.set(-dist, dist * 0.6, dist);
                    viewer.controls.update();
                }});
            }});
        }});
        </script>
    </body>
</html>
"""

COLORS = ["#2196F3", "#E91E63", "#009688", "#FFB300"]


def find_assets(viewer_dir: Path) -> dict:
    """Auto-detect bundled asset filenames (they have hashes in names)."""
    assets = list((viewer_dir / "assets").glob("*"))
    result = {}
    for a in assets:
        name = a.name
        if name.endswith(".map"):
            continue
        if name.startswith("index-") and name.endswith(".js"):
            result["js_main"] = name
        elif name.startswith("URDFLoader-") and name.endswith(".js"):
            result["js_loader"] = name
        elif name.startswith("URDFDragControls-") and name.endswith(".js"):
            result["js_drag"] = name
        elif name.startswith("OrbitControls-") and name.endswith(".js"):
            result["js_orbit"] = name
        elif name.startswith("index-") and name.endswith(".css"):
            result["css_main"] = name
    return result


def find_urdfs(urdf_dir: Path) -> list[Path]:
    """Find all .urdf files in the directory (checks urdf/ subdir first, then root)."""
    urdfs = sorted(urdf_dir.glob("urdf/*.urdf"))
    if not urdfs:
        urdfs = sorted(urdf_dir.glob("*.urdf"))
    return urdfs


def detect_packages(urdfs: list[Path]) -> set[str]:
    """Scan URDF files for package:// references and return unique package names."""
    pkg_pattern = re.compile(r'package://([^/]+)/')
    packages = set()
    for urdf_path in urdfs:
        text = urdf_path.read_text()
        packages.update(pkg_pattern.findall(text))
    return packages


def generate_index(viewer_dir: Path, urdf_dir: Path, urdfs: list[Path]) -> str:
    """Generate index.html with URDF list items pointing to robot/ symlink."""
    assets = find_assets(viewer_dir)
    items = []
    for i, urdf_path in enumerate(urdfs):
        # Path relative to urdf_dir, prefixed with robot/
        rel = urdf_path.relative_to(urdf_dir)
        color = COLORS[i % len(COLORS)]
        label = urdf_path.stem.replace("_", " ").title()
        items.append(
            f'                <li urdf="./robot/{rel}" color="{color}" up="+Z">{label}</li>'
        )

    # Detect package:// references and map them all to ./robot
    packages = detect_packages(urdfs)
    if packages:
        # Format: "pkg1:./robot,pkg2:./robot" — maps package:// to the symlinked dir
        mapping = ",".join(f"{pkg}:./robot" for pkg in sorted(packages))
        package_attr = f'package="{mapping}"'
    else:
        package_attr = ""

    title = urdf_dir.name.replace("_", " ").title()
    # cache-bust the un-bundled overlay by its mtime so browsers refetch on edit
    try:
        overlay_ver = str(int((viewer_dir / "assets" / "prune_overlay.js").stat().st_mtime))
    except OSError:
        overlay_ver = "0"
    return INDEX_TEMPLATE.format(
        title=title,
        urdf_items="\n".join(items),
        package_attr=package_attr,
        overlay_ver=overlay_ver,
        **assets,
    )


def _mesh_rel(filename: str, pkg_dir: Path, urdf_path: Path) -> Path:
    """Resolve package URIs from the package root and other paths from the URDF."""
    match = re.match(r"package://[^/]+/(.*)", filename)
    source = pkg_dir / match.group(1) if match else urdf_path.parent / filename
    source = source.resolve()
    try:
        relative = source.relative_to(pkg_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"Mesh is outside the package: {filename}") from exc
    if not source.is_file():
        raise FileNotFoundError(f"Mesh not found: {filename}")
    return relative


def export_pruned(pkg_dir: Path, urdf_path: Path, prune: list) -> dict:
    """Write a pruned copy of the package to a sibling '<name>_pruned' dir.

    Kept <visual> elements retain their exact mesh refs + origins; the <visual>
    elements named in `prune` (by owning link + document-order index) are removed.
    Mesh files still referenced by any kept <visual>/<collision> are copied across.
    The source package is never modified or overwritten.
    """
    tree = ET.parse(urdf_path)
    root = tree.getroot()

    prune_map = {}
    for p in prune:
        prune_map.setdefault(p["link"], set()).add(int(p["visualIndex"]))

    pruned_count = 0
    for link_el in root.findall("link"):
        name = link_el.get("name")
        if name not in prune_map:
            continue
        visuals = link_el.findall("visual")
        for idx in sorted(prune_map[name], reverse=True):
            if 0 <= idx < len(visuals):
                link_el.remove(visuals[idx])
                pruned_count += 1

    # Mesh files still referenced after pruning (visual + collision).
    mesh_refs = {m.get("filename") for m in root.iter("mesh") if m.get("filename")}

    # Validate every source before creating an output. A unique directory preserves
    # prior exports and any unrelated sibling named '<package>_pruned'.
    mesh_paths = {_mesh_rel(filename, pkg_dir, urdf_path) for filename in mesh_refs}
    out = Path(tempfile.mkdtemp(prefix=f"{pkg_dir.name}_pruned_", dir=pkg_dir.parent))
    try:
        out_urdf = out / urdf_path.relative_to(pkg_dir)
        out_urdf.parent.mkdir(parents=True, exist_ok=True)
        tree.write(out_urdf, xml_declaration=True, encoding="utf-8")

        for rel in mesh_paths:
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pkg_dir / rel, dst)

        for extra in ("package.xml", "CMakeLists.txt"):
            source = pkg_dir / extra
            if source.exists():
                shutil.copy2(source, out / extra)
    except Exception:
        shutil.rmtree(out)
        raise

    return {
        "ok": True,
        "output_dir": str(out),
        "pruned_count": pruned_count,
        "kept_visuals": len(list(root.iter("visual"))),
        "meshes_copied": len(mesh_paths),
    }


def make_handler(pkg_dir: Path, urdf_path: Path):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_POST(self):
            origin = self.headers.get("Origin")
            if origin is not None and origin != f"http://{self.headers.get('Host')}":
                self.send_error(403, "Cross-origin export requests are not allowed")
                return
            if self.path.rstrip("/") != "/export":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 <= length <= 1024 * 1024:
                    raise ValueError("Export request exceeds 1 MiB")
                payload = json.loads(self.rfile.read(length) or b"{}")
                result = export_pruned(pkg_dir, urdf_path, payload.get("prune", []))
            except Exception as exc:  # surface the error to the browser, don't 500 silently
                result = {"ok": False, "error": str(exc)}
            body = json.dumps(result).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main():
    parser = argparse.ArgumentParser(
        description="View URDF in interactive 3D browser viewer"
    )
    parser.add_argument(
        "urdf_dir",
        help="Path to URDF package directory (contains urdf/ and meshes/ subdirs)",
    )
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    urdf_dir = Path(args.urdf_dir).resolve()
    if not urdf_dir.is_dir():
        print(f"Error: {urdf_dir} is not a directory")
        sys.exit(1)

    urdfs = find_urdfs(urdf_dir)
    if not urdfs:
        print(f"Error: No .urdf files found in {urdf_dir}/urdf/ or {urdf_dir}/")
        sys.exit(1)

    print(f"Found {len(urdfs)} URDF file(s):")
    for u in urdfs:
        print(f"  - {u.name}")

    # Build an ephemeral serve-root OUTSIDE the source tree. The plugin's
    # viewer/ dir is read-only: it ships only the static assets/ bundle. Runtime
    # artifacts (the generated index.html and the robot symlink to the user's
    # URDF dir) are assembled in a temp dir and served from there, so running the
    # viewer can never write into — or dirty — the plugin source.
    #
    # index.html references ./assets/ and ./robot/ relatively, so we symlink the
    # real assets bundle and the user's URDF dir into the temp root beside it.
    runtime_dir = Path(tempfile.mkdtemp(prefix="urdf-viewer-"))
    (runtime_dir / "assets").symlink_to(VIEWER_DIR / "assets")
    (runtime_dir / "robot").symlink_to(urdf_dir)
    index_html = generate_index(VIEWER_DIR, urdf_dir, urdfs)
    (runtime_dir / "index.html").write_text(index_html)

    # Serve from the temp root
    os.chdir(runtime_dir)

    def cleanup(*_):
        """Delete the ephemeral serve-root. Idempotent (atexit + finally)."""
        shutil.rmtree(runtime_dir, ignore_errors=True)

    # Clean up however the process ends: normal exit, Ctrl+C (SIGINT), or a
    # kill/terminate (SIGTERM — e.g. an agent stopping a background server).
    # SIGKILL can't be caught, but since the serve-root lives in the OS temp dir
    # (never the repo), even a leaked dir cannot dirty the plugin source.
    atexit.register(cleanup)

    # Serve from the temp root, but POST /export writes a pruned copy of the real
    # package (urdf_dir) to a sibling dir — the browser posts the prune list.
    handler = make_handler(urdf_dir, urdfs[0])
    server = http.server.HTTPServer(("127.0.0.1", args.port), handler)

    url = f"http://localhost:{args.port}/"
    print(f"\nServing URDF viewer at {url}")
    print("Press Ctrl+C to stop.\n")

    if not args.no_open:
        webbrowser.open(url)

    # Raise SystemExit from the handler rather than calling server.shutdown():
    # shutdown() blocks until serve_forever() returns, but the handler runs on
    # the same thread that's inside serve_forever(), so calling it here would
    # deadlock. sys.exit() unwinds serve_forever() cleanly, then finally/atexit
    # run cleanup().
    def _stop(*_):
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
        print("Stopped.")


if __name__ == "__main__":
    main()
