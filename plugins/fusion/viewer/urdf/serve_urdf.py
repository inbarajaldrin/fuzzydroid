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
import http.server
import os
import re
import signal
import sys
import webbrowser
from pathlib import Path

VIEWER_DIR = Path(__file__).parent / "viewer"

INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
        <meta charset="utf-8"/>
        <title>URDF Viewer — {title}</title>
        <script src="https://unpkg.com/@webcomponents/webcomponentsjs@2.4.3/webcomponents-bundle.js"></script>
        <link href="https://fonts.googleapis.com/css?family=Roboto:100,300" rel="stylesheet"/>
        <script type="module" crossorigin src="./assets/{js_main}"></script>
        <link rel="modulepreload" crossorigin href="./assets/{js_loader}">
        <link rel="modulepreload" crossorigin href="./assets/{js_drag}">
        <link rel="modulepreload" crossorigin href="./assets/{js_orbit}">
        <link rel="stylesheet" crossorigin href="./assets/{css_main}">
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
    return INDEX_TEMPLATE.format(
        title=title,
        urdf_items="\n".join(items),
        package_attr=package_attr,
        **assets,
    )


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

    # Create/update symlink: viewer/robot → urdf_dir
    link_path = VIEWER_DIR / "robot"
    if link_path.is_symlink() or link_path.exists():
        link_path.unlink() if link_path.is_symlink() else None
    link_path.symlink_to(urdf_dir)

    # Generate index.html
    index_html = generate_index(VIEWER_DIR, urdf_dir, urdfs)
    (VIEWER_DIR / "index.html").write_text(index_html)

    # Serve
    os.chdir(VIEWER_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(("127.0.0.1", args.port), handler)

    url = f"http://localhost:{args.port}/"
    print(f"\nServing URDF viewer at {url}")
    print("Press Ctrl+C to stop.\n")

    if not args.no_open:
        webbrowser.open(url)

    signal.signal(signal.SIGINT, lambda *_: (server.shutdown(), sys.exit(0)))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up symlink
        if link_path.is_symlink():
            link_path.unlink()
        # Clean up generated index.html
        generated = VIEWER_DIR / "index.html"
        if generated.exists():
            generated.unlink()
        print("Stopped.")


if __name__ == "__main__":
    main()
