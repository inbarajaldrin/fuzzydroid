# Export multi-component design as MULTI-LINK URDF with fixed joints.
# Each component gets its own link + STL. All connected via fixed joints.
# The grounded component (or first occurrence) becomes base_link.
#
# Run via: fusion_exec_python(code="exec(open('/tmp/export_multi_link_urdf.py', encoding='utf-8').read())")
import adsk.core, adsk.fusion, os, json, traceback

# =============================================
# CONFIGURATION -- set these before running
# =============================================
OUTPUT_DIR = ''        # REQUIRED: e.g. 'outputs/hw3_scara_multi_link'
OBJECT_NAME = None     # None = auto-detect from document name
# =============================================

CM_TO_M = 0.01
KGCM2_TO_KGM2 = 1e-6

result = {}

try:
    if not OUTPUT_DIR:
        raise ValueError("OUTPUT_DIR must be set before running this script")

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    if OBJECT_NAME is None:
        OBJECT_NAME = app.activeDocument.name.replace(' ', '_').lower()

    for d in ['', 'urdf', 'meshes']:
        os.makedirs(os.path.join(OUTPUT_DIR, d), exist_ok=True)

    export_mgr = design.exportManager
    pkg = OBJECT_NAME + '_pkg'

    def fv(v): return f'{v:f}'
    def fo(v): return '0' if abs(v) < 1e-10 else f'{v:g}'

    # Collect all occurrences
    occurrences = []
    base_occ = None

    for i in range(root.occurrences.count):
        occ = root.occurrences.item(i)
        clean_name = occ.name.split(':')[0].strip()
        occurrences.append((occ, clean_name))
        if occ.isGrounded:
            base_occ = (occ, clean_name)

    # If no grounded component, use first one as base
    if base_occ is None:
        base_occ = occurrences[0]

    base_occ_obj, base_name = base_occ
    other_occs = [(o, n) for o, n in occurrences if n != base_name]

    # Get base_link world position (reference for joint origins)
    base_transform = base_occ_obj.transform
    base_origin = (
        base_transform.translation.x * CM_TO_M,
        base_transform.translation.y * CM_TO_M,
        base_transform.translation.z * CM_TO_M,
    )

    links_xml = []
    joints_xml = []
    exported = []

    def export_link(occ, link_name):
        comp = occ.component

        stl_name = f'{link_name}.stl'
        stl_path = os.path.join(OUTPUT_DIR, 'meshes', stl_name)

        stl_opts = export_mgr.createSTLExportOptions(occ, stl_path)
        stl_opts.sendToPrintUtility = False
        stl_opts.isBinaryFormat = True
        stl_opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
        export_mgr.execute(stl_opts)

        phys = comp.getPhysicalProperties(
            adsk.fusion.CalculationAccuracy.HighCalculationAccuracy
        )
        mass = phys.mass
        com = phys.centerOfMass
        com_m = (com.x * CM_TO_M, com.y * CM_TO_M, com.z * CM_TO_M)

        ret_val, xx, yy, zz, xy, yz, xz = phys.getXYZMomentsOfInertia()
        inertia = {
            'ixx': xx * KGCM2_TO_KGM2, 'ixy': xy * KGCM2_TO_KGM2,
            'ixz': xz * KGCM2_TO_KGM2, 'iyy': yy * KGCM2_TO_KGM2,
            'iyz': yz * KGCM2_TO_KGM2, 'izz': zz * KGCM2_TO_KGM2,
        }

        # Visual origin: negative of the occurrence's world position
        # shifts STL (in global coords) into the link's local frame
        t = occ.transform.translation
        vis_origin = (-(t.x * CM_TO_M), -(t.y * CM_TO_M), -(t.z * CM_TO_M))

        stl_size = os.path.getsize(stl_path) if os.path.isfile(stl_path) else 0

        link = f'''  <link name="{link_name}">
    <visual>
      <origin xyz="{fo(vis_origin[0])} {fo(vis_origin[1])} {fo(vis_origin[2])}" rpy="0 0 0"/>
      <geometry>
        <mesh filename="package://{pkg}/meshes/{stl_name}" scale="0.001 0.001 0.001"/>
      </geometry>
    </visual>
    <collision>
      <origin xyz="{fo(vis_origin[0])} {fo(vis_origin[1])} {fo(vis_origin[2])}" rpy="0 0 0"/>
      <geometry>
        <mesh filename="package://{pkg}/meshes/{stl_name}" scale="0.001 0.001 0.001"/>
      </geometry>
    </collision>
    <inertial>
      <origin xyz="{fo(com_m[0])} {fo(com_m[1])} {fo(com_m[2])}" rpy="0 0 0"/>
      <mass value="{fv(mass)}"/>
      <inertia ixx="{fv(inertia['ixx'])}" ixy="{fv(inertia['ixy'])}" ixz="{fv(inertia['ixz'])}"
              iyy="{fv(inertia['iyy'])}" iyz="{fv(inertia['iyz'])}" izz="{fv(inertia['izz'])}"/>
    </inertial>
  </link>'''

        return link, {'name': link_name, 'mass': round(mass, 6), 'stl_size': stl_size}

    # Export base_link
    link_xml, link_info = export_link(base_occ_obj, base_name)
    links_xml.append(link_xml)
    exported.append(link_info)

    # Export other components + create fixed joints to base
    for occ, name in other_occs:
        link_xml, link_info = export_link(occ, name)
        links_xml.append(link_xml)
        exported.append(link_info)

        t = occ.transform.translation
        jx = (t.x * CM_TO_M) - base_origin[0]
        jy = (t.y * CM_TO_M) - base_origin[1]
        jz = (t.z * CM_TO_M) - base_origin[2]

        joint_name = f'{base_name}_to_{name}_fixed'
        joint_xml = f'''  <joint name="{joint_name}" type="fixed">
    <parent link="{base_name}"/>
    <child link="{name}"/>
    <origin xyz="{fo(jx)} {fo(jy)} {fo(jz)}" rpy="0 0 0"/>
  </joint>'''
        joints_xml.append(joint_xml)

    # Assemble URDF
    urdf = f'<?xml version="1.0"?>\n<robot name="{OBJECT_NAME}">\n\n'
    urdf += '\n\n'.join(links_xml)
    urdf += '\n\n'
    urdf += '\n\n'.join(joints_xml)
    urdf += '\n\n</robot>\n'

    urdf_path = os.path.join(OUTPUT_DIR, 'urdf', f'{OBJECT_NAME}.urdf')
    with open(urdf_path, 'w', encoding='utf-8') as f:
        f.write(urdf)

    result = {
        'status': 'success',
        'object_name': OBJECT_NAME,
        'links': exported,
        'joints': len(joints_xml),
        'output_dir': OUTPUT_DIR,
    }

except Exception as e:
    result = {'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}

_result = json.dumps(result, indent=2)
with open(os.path.join(OUTPUT_DIR, 'result.json'), 'w', encoding='utf-8') as f:
    f.write(_result)
