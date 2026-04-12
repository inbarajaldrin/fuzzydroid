"""
Headless URDF exporter for Fusion 360 robot assemblies.
Run via fusion_exec_python: exec(open('<path>/export_urdf.py').read())

Exports a complete ROS2 URDF package from the currently open Fusion 360 design:
  - meshes/*.stl         STL mesh per link (except ee_link → sphere geometry)
  - urdf/<name>.urdf     Base URDF with package:// mesh paths
  - urdf/<name>_rviz.urdf    + world link + joint0_fixed
  - urdf/<name>_gazebo.urdf  + world + damping + ros2_control + gazebo plugin
  - CMakeLists.txt       ament_cmake build file
  - package.xml          ROS2 package manifest
  - config/              scara_gazebo.yaml (controller config), scara_config.rviz
  - launch/              scara_rviz.launch.py, scara_gazebo.launch.py

CONFIGURATION — set these before running:
  OUTPUT_DIR   Where to write the package (will create subdirs)
  PKG_NAME     ROS2 package name (used in package://, CMakeLists, etc.)
  ROBOT_NAME   Robot name (used in URDF <robot name="...">, filenames)

REQUIREMENTS:
  - Active Fusion design with as-built or regular joints
  - A component named 'base_link'
  - Components named with clean identifiers (e.g. motor_1, link_1)
  - For ee_link: can be a joint-connected link or an orphan occurrence

KEY FORMULAS:
  Visual origin  = -(joint_global_position_where_link_is_child) × 0.01
  Joint origin   = (this_joint_global - parent_link_frame_global) × 0.01
  Inertia        = getXYZMomentsOfInertia() × 1e-6  (kgcm² → kgm²)

JOINT TYPE DISCRIMINATION:
  Fusion may model fixed connections as revolute joints with rotation limits.
  This script treats: rigid OR revolute-with-limits → fixed,
                      revolute-without-limits → continuous.

STL EXPORT:
  Uses rename-before-copy pattern: creates a temp component at root, copies
  bodies into it, exports as STL. This avoids Fusion's "(1)" suffix issue.
  Close the design WITHOUT saving after export to discard temp components.

WARNING:
  This script creates temporary components for STL export. The design will be
  modified. Close without saving after export, or undo.
"""
import adsk.core, adsk.fusion, os, json, traceback

# ═══════════════════════════════════════════════
# CONFIGURATION — CHANGE THESE
# ═══════════════════════════════════════════════
OUTPUT_DIR = '/tmp/urdf_export'    # Output directory (created if needed)
PKG_NAME = 'my_robot_pkg'         # ROS2 package name
ROBOT_NAME = 'my_robot'           # Robot name in URDF
# ═══════════════════════════════════════════════

CM_TO_M = 0.01
KGCM2_TO_KGM2 = 1e-6
EE_SPHERE_RADIUS = 0.04

result = {}

try:
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    rootComp = design.rootComponent
    export_mgr = design.exportManager

    # Create output directories
    for d in ['', 'urdf', 'meshes', 'config', 'launch']:
        os.makedirs(os.path.join(OUTPUT_DIR, d), exist_ok=True)

    # ═══════════════════════════════════════════════
    # PHASE 1: DATA COLLECTION
    # ═══════════════════════════════════════════════

    occ_by_name = {}
    for occ in rootComp.occurrences:
        occ_by_name[occ.component.name] = occ

    raw_joints = []

    # Collect as-built joints
    for joint in rootComp.asBuiltJoints:
        child_name = joint.occurrenceOne.component.name
        parent_name = joint.occurrenceTwo.component.name
        geo = joint.geometry
        gx, gy, gz = geo.origin.x, geo.origin.y, geo.origin.z  # cm

        jtype = joint.jointMotion.jointType
        if jtype == 0:  # rigid
            urdf_type = 'fixed'
            axis = None
        elif jtype == 1:  # revolute
            has_lim = (joint.jointMotion.rotationLimits.isMinimumValueEnabled or
                       joint.jointMotion.rotationLimits.isMaximumValueEnabled)
            if has_lim:
                urdf_type = 'fixed'
                axis = None
            else:
                urdf_type = 'continuous'
                av = joint.jointMotion.rotationAxisVector
                axis = (av.x, av.y, av.z)
        else:
            urdf_type = 'fixed'
            axis = None

        raw_joints.append({
            'child': child_name, 'parent': parent_name,
            'global_cm': (gx, gy, gz), 'urdf_type': urdf_type, 'axis': axis
        })

    # Collect regular joints
    for joint in rootComp.joints:
        child_name = joint.occurrenceOne.component.name
        parent_name = joint.occurrenceTwo.component.name
        geo = joint.geometryOrOriginOne
        gx, gy, gz = geo.origin.x, geo.origin.y, geo.origin.z

        jtype = joint.jointMotion.jointType
        if jtype == 0:
            urdf_type = 'fixed'
            axis = None
        elif jtype == 1:
            has_lim = (joint.jointMotion.rotationLimits.isMinimumValueEnabled or
                       joint.jointMotion.rotationLimits.isMaximumValueEnabled)
            if has_lim:
                urdf_type = 'fixed'
                axis = None
            else:
                urdf_type = 'continuous'
                av = joint.jointMotion.rotationAxisVector
                axis = (av.x, av.y, av.z)
        else:
            urdf_type = 'fixed'
            axis = None

        raw_joints.append({
            'child': child_name, 'parent': parent_name,
            'global_cm': (gx, gy, gz), 'urdf_type': urdf_type, 'axis': axis
        })

    # ═══════════════════════════════════════════════
    # PHASE 2: BUILD KINEMATIC CHAIN
    # ═══════════════════════════════════════════════

    parent_to_joints = {}
    for j in raw_joints:
        parent_to_joints.setdefault(j['parent'], []).append(j)

    ordered = []
    visited = {'base_link'}

    def walk(link):
        for j in parent_to_joints.get(link, []):
            if j['child'] not in visited:
                visited.add(j['child'])
                ordered.append(j)
                walk(j['child'])

    walk('base_link')

    # Detect orphaned occurrences (e.g. ee_link not connected by joints)
    connected = {'base_link'} | {j['child'] for j in ordered}
    orphans = set(occ_by_name.keys()) - connected

    for name in sorted(orphans):
        occ = occ_by_name[name]
        phys = occ.getPhysicalProperties()
        com = phys.centerOfMass
        gx, gy, gz = com.x, com.y, com.z  # cm
        last_link = ordered[-1]['child'] if ordered else 'base_link'
        ordered.append({
            'child': name, 'parent': last_link,
            'global_cm': (gx, gy, gz), 'urdf_type': 'fixed', 'axis': None,
            'is_orphan': True
        })

    # ═══════════════════════════════════════════════
    # PHASE 3: COMPUTE URDF VALUES
    # ═══════════════════════════════════════════════

    link_frame = {'base_link': (0.0, 0.0, 0.0)}
    for j in ordered:
        link_frame[j['child']] = j['global_cm']

    for j in ordered:
        pg = link_frame[j['parent']]
        tg = j['global_cm']
        j['origin_m'] = (
            (tg[0] - pg[0]) * CM_TO_M,
            (tg[1] - pg[1]) * CM_TO_M,
            (tg[2] - pg[2]) * CM_TO_M,
        )

    for i, j in enumerate(ordered, 1):
        suffix = 'revolute' if j['urdf_type'] in ('continuous', 'revolute') else 'fixed'
        j['name'] = f'joint{i}_{suffix}'

    link_visual = {}
    for name, gpos in link_frame.items():
        link_visual[name] = (-gpos[0] * CM_TO_M, -gpos[1] * CM_TO_M, -gpos[2] * CM_TO_M)

    # ═══════════════════════════════════════════════
    # PHASE 4: EXTRACT PHYSICS + EXPORT STLs
    # ═══════════════════════════════════════════════

    link_order = ['base_link'] + [j['child'] for j in ordered]
    link_props = {}

    for lname in link_order:
        is_ee = 'ee' in lname.lower() or any(
            j.get('is_orphan') and j['child'] == lname for j in ordered
        )

        if is_ee:
            link_props[lname] = {'is_ee': True, 'visual_origin': (0, 0, 0)}
            continue

        occ = occ_by_name.get(lname)
        if not occ:
            continue

        transform = adsk.core.Matrix3D.create()
        temp_occ = rootComp.occurrences.addNewComponent(transform)
        temp_occ.component.name = lname

        for bi in range(occ.bRepBodies.count):
            body = occ.bRepBodies.item(bi)
            body.copyToComponent(temp_occ)

        phys = temp_occ.getPhysicalProperties()
        mass = phys.mass
        _, xx, yy, zz, xy, yz, xz = phys.getXYZMomentsOfInertia()

        link_props[lname] = {
            'is_ee': False,
            'visual_origin': link_visual[lname],
            'mass': mass,
            'inertia': {
                'ixx': xx * KGCM2_TO_KGM2, 'ixy': xy * KGCM2_TO_KGM2,
                'ixz': xz * KGCM2_TO_KGM2, 'iyy': yy * KGCM2_TO_KGM2,
                'iyz': yz * KGCM2_TO_KGM2, 'izz': zz * KGCM2_TO_KGM2,
            }
        }

        stl_path = os.path.join(OUTPUT_DIR, 'meshes', f'{lname}.stl')
        stl_opts = export_mgr.createSTLExportOptions(temp_occ, stl_path)
        stl_opts.sendToPrintUtility = False
        stl_opts.isBinaryFormat = True
        stl_opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
        export_mgr.execute(stl_opts)

    # ═══════════════════════════════════════════════
    # PHASE 5: GENERATE URDF XML
    # ═══════════════════════════════════════════════

    def fv(v):
        return f'{v:f}'

    def fo(v):
        if abs(v) < 1e-10:
            return '0'
        return f'{v:g}'

    def fxyz(x, y, z):
        return f'{fo(x)} {fo(y)} {fo(z)}'

    def gen_link(name, props, pkg):
        vo = props['visual_origin']
        ostr = fxyz(*vo)
        if props['is_ee']:
            return (
                f'  <link name="{name}">\n'
                f'    <visual>\n'
                f'      <origin xyz="0 0 0" rpy="0 0 0"/>\n'
                f'      <geometry>\n'
                f'        <sphere radius="{EE_SPHERE_RADIUS}"/>\n'
                f'      </geometry>\n'
                f'    </visual>\n'
                f'    <collision>\n'
                f'      <origin xyz="0 0 0" rpy="0 0 0"/>\n'
                f'      <geometry>\n'
                f'        <sphere radius="{EE_SPHERE_RADIUS}"/>\n'
                f'      </geometry>\n'
                f'    </collision>\n'
                f'  </link>'
            )
        mesh = f'package://{pkg}/meshes/{name}.stl'
        I = props['inertia']
        return (
            f'  <link name="{name}">\n'
            f'    <visual>\n'
            f'      <origin xyz="{ostr}" rpy="0 0 0"/>\n'
            f'      <geometry>\n'
            f'        <mesh filename="{mesh}" scale="0.001 0.001 0.001"/>\n'
            f'      </geometry>\n'
            f'    </visual>\n'
            f'    <collision>\n'
            f'      <origin xyz="{ostr}" rpy="0 0 0"/>\n'
            f'      <geometry>\n'
            f'        <mesh filename="{mesh}" scale="0.001 0.001 0.001"/>\n'
            f'      </geometry>\n'
            f'    </collision>\n'
            f'    <inertial>\n'
            f'      <origin xyz="{ostr}" rpy="0 0 0"/>\n'
            f'      <mass value="{fv(props["mass"])}"/>\n'
            f'      <inertia ixx="{fv(I["ixx"])}" ixy="{fv(I["ixy"])}" ixz="{fv(I["ixz"])}"\n'
            f'              iyy="{fv(I["iyy"])}" iyz="{fv(I["iyz"])}" izz="{fv(I["izz"])}"/>\n'
            f'    </inertial>\n'
            f'  </link>'
        )

    def gen_joint(j, damping=None):
        ostr = fxyz(*j['origin_m'])
        lines = [
            f'  <joint name="{j["name"]}" type="{j["urdf_type"]}">',
            f'    <origin xyz="{ostr}" rpy="0 0 0"/>',
            f'    <parent link="{j["parent"]}"/>',
            f'    <child link="{j["child"]}"/>',
        ]
        if j['axis']:
            a = j['axis']
            lines.append(f'    <axis xyz="{int(a[0])} {int(a[1])} {int(a[2])}"/>')
        if damping is not None and j['urdf_type'] == 'continuous':
            lines.append(f'    <dynamics damping="{damping}"/>')
        lines.append('  </joint>')
        return '\n'.join(lines)

    # ── Base URDF ──
    parts = ['<?xml version="1.0"?>', f'<robot name="{ROBOT_NAME}">', '']
    for name in link_order:
        if name in link_props:
            parts.append(gen_link(name, link_props[name], PKG_NAME))
            parts.append('')
    for j in ordered:
        parts.append(gen_joint(j))
        parts.append('')
    parts.append('</robot>')
    parts.append('')
    with open(os.path.join(OUTPUT_DIR, 'urdf', f'{ROBOT_NAME}.urdf'), 'w') as f:
        f.write('\n'.join(parts))

    # ── RViz URDF ──
    parts = ['<?xml version="1.0"?>', f'<robot name="{ROBOT_NAME}">', '']
    parts.append('  <link name="world"/>')
    parts.append('')
    for name in link_order:
        if name in link_props:
            parts.append(gen_link(name, link_props[name], PKG_NAME))
            parts.append('')
    parts.append('  <joint name="joint0_fixed" type="fixed">')
    parts.append('    <origin xyz="0 0 0" rpy="0 0 0"/>')
    parts.append('    <parent link="world"/>')
    parts.append('    <child link="base_link"/>')
    parts.append('  </joint>')
    parts.append('')
    for j in ordered:
        parts.append(gen_joint(j))
        parts.append('')
    parts.append('</robot>')
    parts.append('')
    with open(os.path.join(OUTPUT_DIR, 'urdf', f'{ROBOT_NAME}_rviz.urdf'), 'w') as f:
        f.write('\n'.join(parts))

    # ── Gazebo URDF ──
    continuous_joints = [j for j in ordered if j['urdf_type'] == 'continuous']
    parts = ['<?xml version="1.0"?>',
             f'<robot name="{ROBOT_NAME}" xmlns:xacro="http://www.ros.org/wiki/xacro">', '']
    parts.append('  <link name="world"/>')
    parts.append('')
    for name in link_order:
        if name in link_props:
            parts.append(gen_link(name, link_props[name], PKG_NAME))
            parts.append('')
    parts.append('  <joint name="joint0_fixed" type="fixed">')
    parts.append('    <origin xyz="0 0 0" rpy="0 0 0"/>')
    parts.append('    <parent link="world"/>')
    parts.append('    <child link="base_link"/>')
    parts.append('  </joint>')
    parts.append('')
    for j in ordered:
        parts.append(gen_joint(j, damping=5))
        parts.append('')
    parts.append('  <ros2_control name="IgnitionSystem" type="system">')
    parts.append('    <hardware>')
    parts.append('      <plugin>ign_ros2_control/IgnitionSystem</plugin>')
    parts.append('    </hardware>')
    parts.append('')
    for ci, cj in enumerate(continuous_joints):
        if ci == 0:
            parts.append('    <!-- Define joints and their command/state interfaces -->')
        parts.append(f'    <joint name="{cj["name"]}">')
        parts.append('      <command_interface name="position">')
        parts.append('        <param name="min">-1</param>')
        parts.append('        <param name="max">1</param>')
        parts.append('      </command_interface>')
        parts.append('      <state_interface name="position">')
        parts.append('        <param name="initial_value">0.0</param>')
        parts.append('      </state_interface>')
        parts.append('      <state_interface name="velocity"/>')
        parts.append('      <state_interface name="effort"/>')
        parts.append('    </joint>')
        parts.append('')
    parts.append('  </ros2_control>')
    parts.append('')
    parts.append('  <gazebo>')
    parts.append('    <plugin filename="ign_ros2_control-system" name="ign_ros2_control::IgnitionROS2ControlPlugin">')
    parts.append(f'      <parameters>$(find {PKG_NAME})/config/scara_gazebo.yaml</parameters>')
    parts.append('    </plugin>')
    parts.append('  </gazebo>')
    parts.append('')
    parts.append('</robot>')
    parts.append('')
    with open(os.path.join(OUTPUT_DIR, 'urdf', f'{ROBOT_NAME}_gazebo.urdf'), 'w') as f:
        f.write('\n'.join(parts))

    # ═══════════════════════════════════════════════
    # PHASE 6: GENERATE ROS2 PACKAGE FILES
    # ═══════════════════════════════════════════════

    # CMakeLists.txt
    cmake = f"""cmake_minimum_required(VERSION 3.8)
project({PKG_NAME})

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(robot_state_publisher REQUIRED)
find_package(xacro REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

install(DIRECTORY
  launch
  config
  urdf
  meshes
  DESTINATION share/${{PROJECT_NAME}}/
)

ament_package()
"""
    with open(os.path.join(OUTPUT_DIR, 'CMakeLists.txt'), 'w') as f:
        f.write(cmake)

    # package.xml
    pkg_xml = f"""<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>{PKG_NAME}</name>
  <version>0.0.1</version>
  <description>{ROBOT_NAME} robot — ROS 2 URDF package exported from Fusion 360</description>

  <maintainer email="todo@todo.com">TODO</maintainer>
  <license>Apache License 2.0</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>rclpy</depend>
  <depend>rclcpp</depend>
  <depend>robot_state_publisher</depend>
  <depend>xacro</depend>
  <depend>joint_state_publisher</depend>

  <depend>control_msgs</depend>
  <depend>geometry_msgs</depend>
  <depend>hardware_interface</depend>
  <depend>effort_controllers</depend>
  <depend>joint_state_broadcaster</depend>
  <depend>joint_trajectory_controller</depend>
  <depend>velocity_controllers</depend>

  <depend>ign_ros2_control</depend>
  <depend>ros_ign_gazebo</depend>
  <depend>ros_gz_bridge</depend>

  <depend>launch</depend>
  <depend>launch_ros</depend>
  <depend>ros2launch</depend>

  <depend>std_msgs</depend>

  <test_depend>ament_lint_auto</test_depend>
  <test_depend>ament_lint_common</test_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
"""
    with open(os.path.join(OUTPUT_DIR, 'package.xml'), 'w') as f:
        f.write(pkg_xml)

    # config/scara_gazebo.yaml — controller config
    cj_names = '\n'.join(f'      - {cj["name"]}' for cj in continuous_joints)
    gazebo_yaml = f"""controller_manager:
  ros__parameters:
    update_rate: 100  # Hz

    joint_trajectory_controller:
      type: joint_trajectory_controller/JointTrajectoryController

    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster

joint_trajectory_controller:
  ros__parameters:
    joints:
{cj_names}
    command_interfaces:
      - position
    state_interfaces:
      - position
      - velocity
"""
    with open(os.path.join(OUTPUT_DIR, 'config', 'scara_gazebo.yaml'), 'w') as f:
        f.write(gazebo_yaml)

    # launch/scara_rviz.launch.py
    rviz_launch = f'''import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    package_name = "{PKG_NAME}"
    robot_name = "{ROBOT_NAME}"

    ros2_ws_path = os.path.expanduser("~/ros2_ws/src")

    urdf_file = os.path.join(ros2_ws_path, package_name, "urdf", f"{{robot_name}}_rviz.urdf")
    rviz_config_file = os.path.join(ros2_ws_path, package_name, "config", "scara_config.rviz")

    with open(urdf_file, "r") as infp:
        robot_description = infp.read()

    return LaunchDescription([
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[{{"robot_description": robot_description}}]
        ),
        Node(
            package="joint_state_publisher_gui",
            executable="joint_state_publisher_gui",
            output="screen",
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            output="screen",
            arguments=["-d", rviz_config_file, "--fixed-frame", "world"]
        ),
    ])
'''
    with open(os.path.join(OUTPUT_DIR, 'launch', 'scara_rviz.launch.py'), 'w') as f:
        f.write(rviz_launch)

    # launch/scara_gazebo.launch.py
    gazebo_launch = f'''import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.event_handlers import OnProcessExit

import xacro

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    package_name = "{PKG_NAME}"
    robot_name = "{ROBOT_NAME}"

    pkg_path = get_package_share_directory(package_name)

    xacro_file = os.path.join(pkg_path, 'urdf', f'{{robot_name}}_gazebo.urdf')

    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)
    params = {{'robot_description': doc.toxml()}}

    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[params]
    )

    ignition_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-string', doc.toxml(),
                   '-name', robot_name,
                   '-allow_renaming', 'true'],
    )

    load_joint_state_broadcaster = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'joint_state_broadcaster'],
        output='screen'
    )

    load_joint_trajectory_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'joint_trajectory_controller'],
        output='screen'
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='True',
            description='Use sim time if true'
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [os.path.join(get_package_share_directory('ros_ign_gazebo'),
                              'launch', 'ign_gazebo.launch.py')]),
            launch_arguments=[('gz_args', [' -r -v 4 empty.sdf'])]),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=ignition_spawn_entity,
                on_exit=[load_joint_state_broadcaster],
            )
        ),
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=load_joint_state_broadcaster,
                on_exit=[load_joint_trajectory_controller],
            )
        ),
        node_robot_state_publisher,
        ignition_spawn_entity,
        bridge,
    ])
'''
    with open(os.path.join(OUTPUT_DIR, 'launch', 'scara_gazebo.launch.py'), 'w') as f:
        f.write(gazebo_launch)

    # ═══════════════════════════════════════════════
    # RESULT
    # ═══════════════════════════════════════════════
    all_files = []
    for root_dir, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            rel = os.path.relpath(os.path.join(root_dir, fname), OUTPUT_DIR)
            all_files.append(rel)

    result = {
        'status': 'success',
        'links': link_order,
        'joints': [{
            'name': j['name'], 'type': j['urdf_type'],
            'parent': j['parent'], 'child': j['child'],
            'origin_m': [round(v, 6) for v in j['origin_m']]
        } for j in ordered],
        'files': sorted(all_files),
        'output_dir': OUTPUT_DIR,
    }

except Exception as e:
    result = {'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}

_result = json.dumps(result, indent=2)
