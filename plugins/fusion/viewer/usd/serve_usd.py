#!/usr/bin/env python3
"""
Serve USD files in an interactive Three.js web viewer.

Usage:
    python3 serve_usd.py <usd_dir> [--port 8091] [--no-open]

    usd_dir: Path to a directory containing .usda/.usdc/.usd files.
             e.g. outputs/cup_usd/

The viewer auto-detects all USD files in the directory.
Meshes are parsed server-side via the pxr (OpenUSD) library and
served as JSON for the Three.js frontend.

Press Ctrl+C to stop.
"""

import argparse
import http.server
import json
import os
import signal
import string
import sys
import webbrowser
from pathlib import Path
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# USD parsing (requires pxr / OpenUSD)
# ---------------------------------------------------------------------------

def parse_usd_file(filepath: str) -> dict:
    """Parse a USD file and return mesh data as a dict suitable for JSON."""
    from pxr import Usd, UsdGeom, UsdShade, Gf

    stage = Usd.Stage.Open(filepath)
    up_axis = UsdGeom.GetStageUpAxis(stage)
    meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)

    mesh_data = {
        "name": Path(filepath).stem,
        "upAxis": up_axis,
        "metersPerUnit": meters_per_unit,
        "meshes": [],
    }

    for prim in stage.Traverse():
        if prim.GetTypeName() != "Mesh":
            continue

        mesh = UsdGeom.Mesh(prim)
        points_attr = mesh.GetPointsAttr().Get()
        fvc_attr = mesh.GetFaceVertexCountsAttr().Get()
        fvi_attr = mesh.GetFaceVertexIndicesAttr().Get()
        normals_attr = mesh.GetNormalsAttr().Get()

        if not points_attr or not fvi_attr:
            continue

        # Flatten points to [x,y,z, x,y,z, ...]
        points = []
        for p in points_attr:
            points.extend([float(p[0]), float(p[1]), float(p[2])])

        # Flatten normals
        normals = []
        if normals_attr:
            for n in normals_attr:
                normals.extend([float(n[0]), float(n[1]), float(n[2])])

        # Triangulate faces
        indices = []
        normal_indices = []  # for faceVarying normals
        idx_offset = 0
        for count in fvc_attr:
            count = int(count)
            if count == 3:
                indices.extend([
                    int(fvi_attr[idx_offset]),
                    int(fvi_attr[idx_offset + 1]),
                    int(fvi_attr[idx_offset + 2]),
                ])
                if normals:
                    normal_indices.extend([idx_offset, idx_offset + 1, idx_offset + 2])
            elif count == 4:
                # Split quad into two triangles
                i0 = int(fvi_attr[idx_offset])
                i1 = int(fvi_attr[idx_offset + 1])
                i2 = int(fvi_attr[idx_offset + 2])
                i3 = int(fvi_attr[idx_offset + 3])
                indices.extend([i0, i1, i2, i0, i2, i3])
                if normals:
                    normal_indices.extend([
                        idx_offset, idx_offset + 1, idx_offset + 2,
                        idx_offset, idx_offset + 2, idx_offset + 3,
                    ])
            else:
                # Fan triangulation for n-gons
                for j in range(1, count - 1):
                    indices.extend([
                        int(fvi_attr[idx_offset]),
                        int(fvi_attr[idx_offset + j]),
                        int(fvi_attr[idx_offset + j + 1]),
                    ])
                    if normals:
                        normal_indices.extend([
                            idx_offset,
                            idx_offset + j,
                            idx_offset + j + 1,
                        ])
            idx_offset += count

        # If normals are faceVarying, expand them to per-vertex-per-face
        expanded_normals = []
        if normals and normal_indices:
            for ni in normal_indices:
                expanded_normals.extend([
                    normals[ni * 3],
                    normals[ni * 3 + 1],
                    normals[ni * 3 + 2],
                ])

        # Find bound material color
        color = [0.7, 0.7, 0.7]  # default grey
        metallic = 0.0
        roughness = 0.5

        # Walk up to find material binding
        material_prim = None
        check_prim = prim
        while check_prim:
            binding_api = UsdShade.MaterialBindingAPI(check_prim)
            mat_binding = binding_api.ComputeBoundMaterial()
            if mat_binding and mat_binding[0]:
                material_prim = mat_binding[0]
                break
            check_prim = check_prim.GetParent() if check_prim.GetParent() else None
            if check_prim and not check_prim.GetPath().IsAbsoluteRootPath():
                continue
            break

        # If no binding found, search sibling/parent for Material prims
        if not material_prim:
            parent = prim.GetParent()
            if parent:
                for child in parent.GetChildren():
                    if child.GetTypeName() == "Material":
                        material_prim = UsdShade.Material(child)
                        break

        if material_prim:
            # Find the surface shader
            surface_output = material_prim.GetSurfaceOutput()
            if surface_output:
                connected_sources = surface_output.GetConnectedSources()
                if connected_sources and connected_sources[0]:
                    for src_info in connected_sources[0]:
                        shader_prim = UsdShade.Shader(src_info.source.GetPrim())
                        dc_input = shader_prim.GetInput("diffuseColor")
                        if dc_input and dc_input.Get():
                            dc = dc_input.Get()
                            color = [float(dc[0]), float(dc[1]), float(dc[2])]
                        met_input = shader_prim.GetInput("metallic")
                        if met_input and met_input.Get() is not None:
                            metallic = float(met_input.Get())
                        rough_input = shader_prim.GetInput("roughness")
                        if rough_input and rough_input.Get() is not None:
                            roughness = float(rough_input.Get())

        mesh_entry = {
            "path": str(prim.GetPath()),
            "vertices": len(points_attr),
            "faces": len(indices) // 3,
            "points": points,
            "indices": indices,
            "color": color,
            "metallic": metallic,
            "roughness": roughness,
        }

        if expanded_normals:
            mesh_entry["normals"] = expanded_normals

        mesh_data["meshes"].append(mesh_entry)

    return mesh_data


# ---------------------------------------------------------------------------
# HTML / JS viewer (self-contained, using string.Template for safe substitution)
# ---------------------------------------------------------------------------

VIEWER_TEMPLATE = string.Template("""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>USD Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #ffffff; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        #canvas-container { width: 100vw; height: 100vh; }
        canvas { display: block; }
        #info-panel {
            position: fixed;
            top: 16px;
            left: 16px;
            background: rgba(245, 245, 247, 0.94);
            border: 1px solid #d1d1d6;
            border-radius: 12px;
            padding: 16px 20px;
            color: #1d1d1f;
            font-size: 0.85rem;
            line-height: 1.6;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            min-width: 220px;
            max-width: 260px;
            z-index: 10;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        #info-panel h2 {
            font-size: 1.1rem;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 4px;
        }
        #info-panel .label { color: #86868b; }
        #info-panel .divider {
            border: none;
            border-top: 1px solid #d1d1d6;
            margin: 10px 0;
        }
        #file-select {
            width: 100%;
            padding: 6px 8px;
            background: #ffffff;
            border: 1px solid #d1d1d6;
            border-radius: 6px;
            color: #1d1d1f;
            font-size: 0.85rem;
            outline: none;
            margin-bottom: 10px;
            cursor: pointer;
        }
        #file-select:focus { border-color: #0071e3; }
        #color-picker-wrap {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        #color-picker {
            width: 48px;
            height: 32px;
            border: 1px solid #d1d1d6;
            border-radius: 6px;
            background: #fff;
            cursor: pointer;
            padding: 2px;
        }
        #color-hex {
            font-family: "SF Mono", Menlo, monospace;
            font-size: 0.85rem;
            color: #1d1d1f;
        }
        #export-name {
            width: 100%;
            padding: 6px 8px;
            background: #ffffff;
            border: 1px solid #d1d1d6;
            border-radius: 6px;
            color: #1d1d1f;
            font-size: 0.85rem;
            outline: none;
        }
        #export-name:focus { border-color: #0071e3; }
        #export-name-wrap {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;
        }
        #export-name-wrap .suffix {
            color: #86868b;
            font-size: 0.8rem;
            white-space: nowrap;
        }
        #export-btn {
            width: 100%;
            padding: 8px;
            background: #0071e3;
            border: none;
            border-radius: 6px;
            color: #ffffff;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        }
        #export-btn:hover { background: #0077ed; }
        #export-btn:active { background: #005bb5; }
        #export-status {
            font-size: 0.75rem;
            color: #86868b;
            margin-top: 6px;
            min-height: 1.2em;
        }
        #loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #86868b;
            font-size: 1.2rem;
            z-index: 20;
        }
        #controls-help {
            position: fixed;
            bottom: 16px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(245, 245, 247, 0.85);
            border: 1px solid #d1d1d6;
            border-radius: 8px;
            padding: 8px 16px;
            color: #86868b;
            font-size: 0.75rem;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            z-index: 10;
        }
    </style>
</head>
<body>
    <div id="loading">Loading mesh...</div>
    <div id="canvas-container"></div>
    <div id="info-panel" style="display:none">
        <select id="file-select"></select>
        <h2 id="model-name"></h2>
        <div><span class="label">Vertices:</span> <span id="vert-count"></span></div>
        <div><span class="label">Faces:</span> <span id="face-count"></span></div>
        <div><span class="label">Up Axis:</span> <span id="up-axis"></span></div>
        <hr class="divider">
        <div style="margin-bottom:6px"><span class="label">Color</span></div>
        <div id="color-picker-wrap">
            <input type="color" id="color-picker" value="#888888">
            <span id="color-hex">#888888</span>
        </div>
        <hr class="divider">
        <div style="margin-bottom:6px"><span class="label">Export as</span></div>
        <div id="export-name-wrap">
            <input type="text" id="export-name" placeholder="cup_red">
            <span class="suffix">.usd</span>
        </div>
        <button id="export-btn">Export USD</button>
        <div id="export-status"></div>
    </div>
    <div id="controls-help">Left-drag: orbit &middot; Right-drag: pan &middot; Scroll: zoom</div>

    <script type="importmap">
    {
        "imports": {
            "three": "https://unpkg.com/three@0.163.0/build/three.module.js",
            "three/addons/": "https://unpkg.com/three@0.163.0/examples/jsm/"
        }
    }
    </script>
    <script type="module">
        import * as THREE from 'three';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

        // Scene setup
        const container = document.getElementById('canvas-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xffffff);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.0001, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.4;
        container.appendChild(renderer.domElement);

        // Controls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.rotateSpeed = 0.8;
        controls.zoomSpeed = 1.2;

        // Lights (tuned for white background)
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);

        const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
        dirLight1.position.set(5, 10, 7);
        dirLight1.castShadow = true;
        dirLight1.shadow.mapSize.set(2048, 2048);
        scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
        dirLight2.position.set(-5, 5, -5);
        scene.add(dirLight2);

        const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe0e0e0, 0.4);
        scene.add(hemiLight);

        // Grid (subtle light gray on white)
        const gridHelper = new THREE.GridHelper(1, 20, 0xcccccc, 0xe0e0e0);
        scene.add(gridHelper);

        // State
        let activeMeshes = [];
        let modelGroup = null;
        let currentFilename = '$default_file';

        // Populate file selector
        const fileSelect = document.getElementById('file-select');
        const availableFiles = $files_json;
        availableFiles.forEach(f => {
            const opt = document.createElement('option');
            opt.value = f.name;
            opt.textContent = f.name;
            if (f.name === currentFilename) opt.selected = true;
            fileSelect.appendChild(opt);
        });

        fileSelect.addEventListener('change', (e) => {
            currentFilename = e.target.value;
            // Auto-fill export name from selected file (without extension)
            document.getElementById('export-name').value = currentFilename.replace(/\.[^.]+$$/, '');
            document.getElementById('export-status').textContent = '';
            loadMesh(currentFilename);
        });

        function clearScene() {
            if (modelGroup) {
                scene.remove(modelGroup);
                modelGroup.traverse(child => {
                    if (child.geometry) child.geometry.dispose();
                    if (child.material) child.material.dispose();
                });
                modelGroup = null;
            }
            activeMeshes = [];
        }

        async function loadMesh(filename) {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('info-panel').style.display = 'none';
            clearScene();

            try {
                const resp = await fetch('/api/mesh/' + encodeURIComponent(filename));
                if (!resp.ok) throw new Error('Failed to load mesh: ' + resp.status);
                const data = await resp.json();

                const upAxis = data.upAxis || 'Y';
                const group = new THREE.Group();
                modelGroup = group;

                let totalVerts = 0;
                let totalFaces = 0;
                let mainColor = [0.7, 0.7, 0.7];

                for (const meshData of data.meshes) {
                    const geometry = new THREE.BufferGeometry();

                    // Points
                    const positions = new Float32Array(meshData.points);
                    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

                    // Indices
                    const indices = new Uint32Array(meshData.indices);
                    geometry.setIndex(new THREE.BufferAttribute(indices, 1));

                    // Normals -- faceVarying normals need to be applied per-face-vertex
                    if (meshData.normals && meshData.normals.length > 0) {
                        const faceNormals = new Float32Array(meshData.normals);
                        const newPositions = new Float32Array(indices.length * 3);
                        const newNormals = new Float32Array(indices.length * 3);

                        for (let i = 0; i < indices.length; i++) {
                            const vi = indices[i];
                            newPositions[i * 3] = positions[vi * 3];
                            newPositions[i * 3 + 1] = positions[vi * 3 + 1];
                            newPositions[i * 3 + 2] = positions[vi * 3 + 2];
                            newNormals[i * 3] = faceNormals[i * 3];
                            newNormals[i * 3 + 1] = faceNormals[i * 3 + 1];
                            newNormals[i * 3 + 2] = faceNormals[i * 3 + 2];
                        }

                        geometry.deleteAttribute('position');
                        geometry.setIndex(null);
                        geometry.setAttribute('position', new THREE.BufferAttribute(newPositions, 3));
                        geometry.setAttribute('normal', new THREE.BufferAttribute(newNormals, 3));
                    } else {
                        geometry.computeVertexNormals();
                    }

                    // Material
                    const color = new THREE.Color(meshData.color[0], meshData.color[1], meshData.color[2]);
                    const material = new THREE.MeshStandardMaterial({
                        color: color,
                        metalness: meshData.metallic || 0,
                        roughness: meshData.roughness || 0.5,
                        side: THREE.DoubleSide,
                    });

                    const mesh = new THREE.Mesh(geometry, material);
                    mesh.castShadow = true;
                    mesh.receiveShadow = true;
                    group.add(mesh);
                    activeMeshes.push(mesh);

                    totalVerts += meshData.vertices;
                    totalFaces += meshData.faces;
                    mainColor = meshData.color;
                }

                // Handle up axis
                if (upAxis === 'Z') {
                    group.rotation.x = -Math.PI / 2;
                }

                scene.add(group);

                // Auto-zoom to fit
                const box = new THREE.Box3().setFromObject(group);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const fov = camera.fov * (Math.PI / 180);
                let cameraDistance = maxDim / (2 * Math.tan(fov / 2));
                cameraDistance *= 1.8;

                controls.target.copy(center);
                camera.position.set(
                    center.x + cameraDistance * 0.6,
                    center.y + cameraDistance * 0.4,
                    center.z + cameraDistance * 0.7
                );
                camera.near = maxDim * 0.001;
                camera.far = maxDim * 100;
                camera.updateProjectionMatrix();
                controls.update();

                // Update grid to match model scale
                gridHelper.scale.set(maxDim * 3, maxDim * 3, maxDim * 3);
                gridHelper.position.y = box.min.y;

                // Update info panel
                document.getElementById('loading').style.display = 'none';
                document.getElementById('info-panel').style.display = 'block';
                document.getElementById('model-name').textContent = data.name.replace(/_/g, ' ');
                document.getElementById('vert-count').textContent = totalVerts.toLocaleString();
                document.getElementById('face-count').textContent = totalFaces.toLocaleString();
                document.getElementById('up-axis').textContent = upAxis;

                // Set color picker to model's color
                const hexColor = '#' + new THREE.Color(mainColor[0], mainColor[1], mainColor[2]).getHexString();
                document.getElementById('color-picker').value = hexColor;
                document.getElementById('color-hex').textContent = hexColor;

                // Clear export status on file change
                document.getElementById('export-status').textContent = '';

            } catch (err) {
                document.getElementById('loading').textContent = 'Error: ' + err.message;
                console.error(err);
            }
        }

        // Live color picker
        document.getElementById('color-picker').addEventListener('input', (e) => {
            const hex = e.target.value;
            document.getElementById('color-hex').textContent = hex;
            const c = new THREE.Color(hex);
            activeMeshes.forEach(m => { m.material.color.copy(c); });
        });

        // Export button
        document.getElementById('export-btn').addEventListener('click', async () => {
            const status = document.getElementById('export-status');
            const exportName = document.getElementById('export-name').value.trim();
            if (!exportName) {
                status.textContent = 'Enter a name first';
                status.style.color = '#ff3b30';
                return;
            }
            const hex = document.getElementById('color-picker').value;
            const c = new THREE.Color(hex);
            status.textContent = 'Exporting...';
            status.style.color = '#86868b';
            try {
                const resp = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source: currentFilename,
                        name: exportName,
                        color: [c.r, c.g, c.b],
                    }),
                });
                const result = await resp.json();
                if (result.status === 'ok') {
                    status.textContent = 'Saved: ' + result.path;
                    status.style.color = '#34c759';
                    // Refresh file list
                    const filesResp = await fetch('/api/files');
                    const newFiles = await filesResp.json();
                    fileSelect.innerHTML = '';
                    newFiles.forEach(f => {
                        const opt = document.createElement('option');
                        opt.value = f.name;
                        opt.textContent = f.name;
                        if (f.name === currentFilename) opt.selected = true;
                        fileSelect.appendChild(opt);
                    });
                } else {
                    status.textContent = 'Error: ' + result.error;
                    status.style.color = '#ff3b30';
                }
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.style.color = '#ff3b30';
            }
        });

        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        animate();

        // Handle resize
        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        // Initial load
        loadMesh(currentFilename);
    </script>
</body>
</html>
""")


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class USDViewerHandler(http.server.BaseHTTPRequestHandler):
    """Custom handler that serves the viewer HTML and mesh/file/export JSON API."""

    usd_dir = None
    usd_files = []
    mesh_cache = {}

    def log_message(self, format, *args):
        # Quieter logging
        msg = str(args[0]) if args else ''
        if '/api/' in msg:
            sys.stderr.write(f"  [API] {msg}\n")

    def do_GET(self):
        path = unquote(self.path)

        # API: mesh data for a file
        if path.startswith('/api/mesh/'):
            filename = path[len('/api/mesh/'):]
            self.serve_mesh_json(filename)
            return

        # API: list all available files with colors
        if path == '/api/files':
            self.serve_files_json()
            return

        # Root or any other path -> serve the viewer
        if path == '/' or path == '/index.html':
            self.serve_viewer()
            return

        # Legacy /view/<file> paths redirect to / (file chosen via dropdown)
        if path.startswith('/view/'):
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        path = unquote(self.path)

        if path == '/api/export':
            self.handle_export()
            return

        self.send_error(404, "Not Found")

    def serve_viewer(self):
        """Serve the Three.js viewer, loading the first file by default."""
        files = self.__class__.usd_files
        if not files:
            self.send_error(500, "No USD files available")
            return

        default_file = files[0].name

        # Build files JSON for the dropdown
        files_list = []
        for f in files:
            color = [0.7, 0.7, 0.7]
            try:
                mesh_data = self._get_mesh_data(f.name)
                if mesh_data['meshes']:
                    color = mesh_data['meshes'][0]['color']
            except Exception:
                pass
            files_list.append({"name": f.name, "color": color})

        html = VIEWER_TEMPLATE.substitute(
            default_file=default_file,
            files_json=json.dumps(files_list),
        )

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def serve_files_json(self):
        """Return JSON list of all available files with their colors."""
        files_list = []
        for f in self.__class__.usd_files:
            color = [0.7, 0.7, 0.7]
            try:
                mesh_data = self._get_mesh_data(f.name)
                if mesh_data['meshes']:
                    color = mesh_data['meshes'][0]['color']
            except Exception:
                pass
            files_list.append({"name": f.name, "color": color})

        json_bytes = json.dumps(files_list).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(json_bytes)))
        self.end_headers()
        self.wfile.write(json_bytes)

    def _get_mesh_data(self, filename):
        """Get mesh data, using cache."""
        cache = self.__class__.mesh_cache
        if filename not in cache:
            filepath = self.__class__.usd_dir / filename
            cache[filename] = parse_usd_file(str(filepath))
        return cache[filename]

    def serve_mesh_json(self, filename):
        """Parse the USD file and return mesh data as JSON."""
        valid_names = {f.name for f in self.__class__.usd_files}
        if filename not in valid_names:
            self.send_error(404, f"USD file not found: {filename}")
            return

        try:
            mesh_data = self._get_mesh_data(filename)
            json_bytes = json.dumps(mesh_data).encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(json_bytes)))
            self.end_headers()
            self.wfile.write(json_bytes)

        except Exception as e:
            error = json.dumps({"error": str(e)}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error)

    def handle_export(self):
        """Handle POST /api/export — clone a USDA file with a new diffuseColor."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body)

            source = payload.get('source', '')
            name = payload.get('name', '')
            color = payload.get('color', [0.7, 0.7, 0.7])

            if not source or not name:
                raise ValueError("Missing 'source' or 'name' field")

            valid_names = {f.name for f in self.__class__.usd_files}
            if source not in valid_names:
                raise ValueError(f"Source file not found: {source}")

            from pxr import Usd, UsdShade, Gf

            src_path = self.__class__.usd_dir / source
            dst_path = self.__class__.usd_dir / f"{name}.usda"

            # Open source stage and update color
            stage = Usd.Stage.Open(str(src_path))
            for prim in stage.Traverse():
                if prim.GetTypeName() == "Shader":
                    shader = UsdShade.Shader(prim)
                    dc_input = shader.GetInput("diffuseColor")
                    if dc_input:
                        dc_input.Set(Gf.Vec3f(float(color[0]), float(color[1]), float(color[2])))

            # Export all 3 formats
            exported = []
            for ext in ['.usd', '.usda', '.usdc']:
                out_path = self.__class__.usd_dir / f"{name}{ext}"
                stage.Export(str(out_path))
                exported.append(f"{name}{ext}")

            # Refresh file list and invalidate caches
            self.__class__.usd_files = find_usd_files(self.__class__.usd_dir)
            for ext in ['.usd', '.usda', '.usdc']:
                cache_key = f"{name}{ext}"
                if cache_key in self.__class__.mesh_cache:
                    del self.__class__.mesh_cache[cache_key]

            result = json.dumps({
                "status": "ok",
                "path": f"{name}.usd",
                "exported": exported,
            }).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(result)))
            self.end_headers()
            self.wfile.write(result)

        except Exception as e:
            error = json.dumps({"status": "error", "error": str(e)}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(error)))
            self.end_headers()
            self.wfile.write(error)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_usd_files(directory: Path) -> list[Path]:
    """Find all USD files in the given directory."""
    extensions = {'.usda', '.usdc', '.usd'}
    files = []
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f)
    return files


def main():
    parser = argparse.ArgumentParser(
        description="View USD files in an interactive 3D browser viewer"
    )
    parser.add_argument(
        "usd_dir",
        help="Path to directory containing .usda/.usdc/.usd files",
    )
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    usd_dir = Path(args.usd_dir).resolve()
    if not usd_dir.is_dir():
        print(f"Error: {usd_dir} is not a directory")
        sys.exit(1)

    usd_files = find_usd_files(usd_dir)
    if not usd_files:
        print(f"Error: No .usda/.usdc/.usd files found in {usd_dir}/")
        sys.exit(1)

    print(f"Found {len(usd_files)} USD file(s):")
    for f in usd_files:
        print(f"  - {f.name}")

    # Pre-parse all files to warm cache and report stats
    print("\nParsing USD files...")
    for f in usd_files:
        try:
            data = parse_usd_file(str(f))
            USDViewerHandler.mesh_cache[f.name] = data
            for m in data['meshes']:
                c = m['color']
                print(f"  {f.name}: {m['vertices']} vertices, {m['faces']} faces, "
                      f"color=({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f})")
        except Exception as e:
            print(f"  {f.name}: ERROR - {e}")

    # Configure handler
    USDViewerHandler.usd_dir = usd_dir
    USDViewerHandler.usd_files = usd_files

    # Start server
    server = http.server.HTTPServer(("127.0.0.1", args.port), USDViewerHandler)

    url = f"http://localhost:{args.port}/"
    print(f"\nServing USD viewer at {url}")
    print("Press Ctrl+C to stop.\n")

    if not args.no_open:
        webbrowser.open(url)

    def shutdown_handler(*_):
        print("\nStopping...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopped.")


if __name__ == "__main__":
    main()
