"""
Export the currently open Fusion 360 design as a single-object URDF (no joints).
Works for any design — single body, multi-body, or assembly without joints.
Exports the entire root component as one STL mesh + one URDF link.

Run via: fusion_exec_python(code="exec(open('/tmp/export_single_urdf.py').read())")
"""
import adsk.core, adsk.fusion, os, json, traceback

# ═══════════════════════════════════════════════
# CONFIGURATION — set these before running
# ═══════════════════════════════════════════════
OUTPUT_DIR = ''        # REQUIRED: e.g. '/path/to/outputs/base3_urdf'
OBJECT_NAME = None     # None = auto-detect from document name
# ═══════════════════════════════════════════════

CM_TO_M = 0.01
KGCM2_TO_KGM2 = 1e-6

result = {}

try:
    if not OUTPUT_DIR:
        raise ValueError("OUTPUT_DIR must be set before running this script")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    # Auto-detect name from document
    if OBJECT_NAME is None:
        OBJECT_NAME = app.activeDocument.name.replace(' ', '_').lower()

    # Create output dirs
    for d in ['', 'urdf', 'meshes']:
        os.makedirs(os.path.join(OUTPUT_DIR, d), exist_ok=True)

    # ── Collect info ──
    body_count = root.bRepBodies.count
    occ_count = root.occurrences.count
    joint_count = root.joints.count + root.asBuiltJoints.count

    # ── Get physical properties ──
    # For root component with multiple bodies/occurrences, we use the root's properties
    phys = root.getPhysicalProperties(
        adsk.fusion.CalculationAccuracy.HighCalculationAccuracy
    )
    mass = phys.mass  # kg
    com = phys.centerOfMass  # Point3D in cm
    com_m = (com.x * CM_TO_M, com.y * CM_TO_M, com.z * CM_TO_M)

    ret_val, xx, yy, zz, xy, yz, xz = phys.getXYZMomentsOfInertia()
    inertia = {
        'ixx': xx * KGCM2_TO_KGM2, 'ixy': xy * KGCM2_TO_KGM2,
        'ixz': xz * KGCM2_TO_KGM2, 'iyy': yy * KGCM2_TO_KGM2,
        'iyz': yz * KGCM2_TO_KGM2, 'izz': zz * KGCM2_TO_KGM2,
    }

    # ── Export STL ──
    export_mgr = design.exportManager
    stl_path = os.path.join(OUTPUT_DIR, 'meshes', f'{OBJECT_NAME}.stl')
    stl_opts = export_mgr.createSTLExportOptions(root, stl_path)
    stl_opts.sendToPrintUtility = False
    stl_opts.isBinaryFormat = True
    stl_opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
    export_mgr.execute(stl_opts)

    stl_exists = os.path.isfile(stl_path)
    stl_size = os.path.getsize(stl_path) if stl_exists else 0

    # ── Generate URDF ──
    def fv(v):
        return f'{v:f}'

    def fo(v):
        if abs(v) < 1e-10:
            return '0'
        return f'{v:g}'

    pkg = OBJECT_NAME + '_pkg'

    urdf = f'''<?xml version="1.0"?>
<robot name="{OBJECT_NAME}">

  <link name="base_link">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <mesh filename="package://{pkg}/meshes/{OBJECT_NAME}.stl" scale="0.001 0.001 0.001"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry>
        <mesh filename="package://{pkg}/meshes/{OBJECT_NAME}.stl" scale="0.001 0.001 0.001"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="{fo(com_m[0])} {fo(com_m[1])} {fo(com_m[2])}" rpy="0 0 0"/>
      <mass value="{fv(mass)}"/>
      <inertia ixx="{fv(inertia['ixx'])}" ixy="{fv(inertia['ixy'])}" ixz="{fv(inertia['ixz'])}"
              iyy="{fv(inertia['iyy'])}" iyz="{fv(inertia['iyz'])}" izz="{fv(inertia['izz'])}"/>
    </inertial>
  </link>

</robot>
'''

    urdf_path = os.path.join(OUTPUT_DIR, 'urdf', f'{OBJECT_NAME}.urdf')
    with open(urdf_path, 'w') as f:
        f.write(urdf)

    # ── Result ──
    result = {
        'status': 'success',
        'object_name': OBJECT_NAME,
        'design_info': {
            'bodies': body_count,
            'occurrences': occ_count,
            'joints': joint_count,
        },
        'physics': {
            'mass_kg': round(mass, 6),
            'center_of_mass_m': [round(v, 6) for v in com_m],
            'inertia_kgm2': {k: round(v, 9) for k, v in inertia.items()},
        },
        'files': {
            'stl': stl_path,
            'stl_exists': stl_exists,
            'stl_size_bytes': stl_size,
            'urdf': urdf_path,
        },
        'output_dir': OUTPUT_DIR,
    }

except Exception as e:
    result = {'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}

_result = json.dumps(result, indent=2)
