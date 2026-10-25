"""fuzzydroid isaacsim plugin — detect / setup / doctor for NVIDIA Isaac Sim.

Linux: records the chosen Isaac Sim install (pip / binary / source) and its
omni.kit.mcp bridge registration, with an optional persistent ROS 2 bridge
enable. macOS: records the Isaac Viewer app install. All install knowledge
lives in the upstream repos' live docs — this package only detects, records,
and verifies.
"""

PLUGIN_NAME = "isaacsim"
PLUGIN_VERSION = "0.2.0"
PYTHON_VERSION = "3.11"
