"""fuzzydroid isaaclab plugin — detect / setup / doctor for Isaac Lab.

Records which Isaac Lab install (pip venv or source checkout) a box uses —
never assuming a venv name — plus the omni-kit-mcp checkout used for
bridge+livestream launches. All install knowledge lives in the official live
docs at https://isaac-sim.github.io/IsaacLab; this package only detects,
records, and verifies. Includes the per-profile guard check: the static-TLS
GLIBC tunable must never leak into Lab standalone runs.
"""

PLUGIN_NAME = "isaaclab"
PLUGIN_VERSION = "0.1.0"
PYTHON_VERSION = "3.11"

# IsaacLabExtensionTemplate has no release tags (only `main`), so new-project
# pins a commit SHA. Bump deliberately after verifying the template still
# works with the fleet's Isaac Lab version.
TEMPLATE_REPO = "https://github.com/isaac-sim/IsaacLabExtensionTemplate"
TEMPLATE_PINNED_COMMIT = "c326b3bdca9480d1cb3c3f59844cb2d36e446fa9"  # main, 2025-09-26
