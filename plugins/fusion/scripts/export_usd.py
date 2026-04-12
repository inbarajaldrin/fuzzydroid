#!/usr/bin/env python3
"""
Reusable STL → USD converter with color material.

Usage:
    python3 export_usd.py <stl_path> <output.usda> [--color R G B] [--scale S] [--name NAME]

    --color R G B   : RGB floats 0-1 (default: 0.5 0.5 0.5)
    --scale S       : uniform scale factor (default: 0.001 for mm→m)
    --name NAME     : object name in USD stage (default: from filename)

Examples:
    python3 export_usd.py cup.stl cup_blue.usda --color 0.0 0.4 0.87 --name cup_blue
    python3 export_usd.py cup.stl cup_orange.usda --color 0.93 0.27 0.07
"""

import argparse
import os
import sys
import struct
import numpy as np

from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf


def read_stl_binary(path):
    """Read binary STL, return (vertices Nx3, faces Mx3, normals Mx3)."""
    with open(path, 'rb') as f:
        header = f.read(80)
        num_tri = struct.unpack('<I', f.read(4))[0]

        normals = np.zeros((num_tri, 3), dtype=np.float32)
        vertices = np.zeros((num_tri * 3, 3), dtype=np.float32)

        for i in range(num_tri):
            data = struct.unpack('<12fH', f.read(50))
            normals[i] = data[0:3]
            vertices[i*3]   = data[3:6]
            vertices[i*3+1] = data[6:9]
            vertices[i*3+2] = data[9:12]

    faces = np.arange(num_tri * 3).reshape(-1, 3)
    return vertices, faces, normals


def deduplicate_vertices(vertices, faces, tol=1e-6):
    """Merge duplicate vertices to reduce USD file size."""
    unique, inverse = np.unique(
        np.round(vertices / tol) * tol, axis=0, return_inverse=True
    )
    new_faces = inverse[faces]
    return unique, new_faces


def stl_to_usd(stl_path, usd_path, color=(0.5, 0.5, 0.5), scale=0.001, name=None):
    """Convert STL file to USDA with a colored material.

    Args:
        stl_path: Path to input .stl file
        usd_path: Path for output .usda or .usdc file
        color: (R, G, B) tuple, floats 0-1
        scale: Uniform scale (0.001 converts mm to meters)
        name: Object name (default: derived from filename)

    Returns:
        dict with status and file info
    """
    if name is None:
        name = os.path.splitext(os.path.basename(stl_path))[0]
    name = name.replace(' ', '_').replace('-', '_')

    # Read and process STL
    verts, faces, normals = read_stl_binary(stl_path)
    verts = verts * scale  # apply scale
    verts, faces = deduplicate_vertices(verts, faces)

    # Create USD stage
    stage = Usd.Stage.CreateNew(usd_path)
    stage.SetMetadata('metersPerUnit', 1.0)
    stage.SetMetadata('upAxis', 'Z')

    # Root xform
    root_path = f'/{name}'
    xform = UsdGeom.Xform.Define(stage, root_path)
    stage.SetDefaultPrim(xform.GetPrim())

    # Mesh
    mesh_path = f'{root_path}/mesh'
    mesh = UsdGeom.Mesh.Define(stage, mesh_path)
    mesh.GetPointsAttr().Set([Gf.Vec3f(float(v[0]), float(v[1]), float(v[2])) for v in verts])
    mesh.GetFaceVertexCountsAttr().Set([3] * len(faces))
    mesh.GetFaceVertexIndicesAttr().Set([int(x) for x in faces.flatten()])
    mesh.GetSubdivisionSchemeAttr().Set('none')

    # Per-face normals
    face_normals = []
    for f in faces:
        v0, v1, v2 = verts[f[0]], verts[f[1]], verts[f[2]]
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n)
        if norm > 0:
            n = n / norm
        face_normals.extend([Gf.Vec3f(float(n[0]), float(n[1]), float(n[2]))] * 3)
    mesh.GetNormalsAttr().Set(face_normals)
    mesh.SetNormalsInterpolation('faceVarying')

    # Material
    mat_path = f'{root_path}/material'
    material = UsdShade.Material.Define(stage, mat_path)

    # PBR shader
    shader_path = f'{mat_path}/PBRShader'
    shader = UsdShade.Shader.Define(stage, shader_path)
    shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.4)
    shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.0)

    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')

    # Bind material to mesh
    UsdShade.MaterialBindingAPI(mesh).Bind(material)

    stage.Save()

    return {
        'status': 'ok',
        'output': usd_path,
        'name': name,
        'vertices': len(verts),
        'faces': len(faces),
        'color_rgb': list(color),
        'scale': scale,
        'file_size': os.path.getsize(usd_path),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert STL to USD with color')
    parser.add_argument('stl', help='Input STL file')
    parser.add_argument('output', help='Output USD file (.usda or .usdc)')
    parser.add_argument('--color', nargs=3, type=float, default=[0.5, 0.5, 0.5],
                        metavar=('R', 'G', 'B'), help='RGB color (0-1)')
    parser.add_argument('--scale', type=float, default=0.001, help='Scale factor (default: 0.001 mm→m)')
    parser.add_argument('--name', type=str, default=None, help='Object name in USD')
    args = parser.parse_args()

    result = stl_to_usd(args.stl, args.output, tuple(args.color), args.scale, args.name)
    import json
    print(json.dumps(result, indent=2))
