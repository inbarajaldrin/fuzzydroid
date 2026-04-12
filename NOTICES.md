# Upstream Notices

fuzzydroid incorporates code from the following open-source projects. Each is listed with its source, license, and scope of use in this repository.

## Autodesk Fusion 360 Add-In Sample

**Source:** Autodesk Fusion 360 SDK sample add-ins (distributed with Fusion)
**Copyright:** Copyright 2022 Autodesk, Inc.
**License:** Autodesk Sample License (permissive; requires copyright preservation)
**Used in:**
- `plugins/fusion/addin/fusion_bridge/lib/fusionAddInUtils/` — error handling, event cleanup, logging utilities (unmodified)
- `plugins/fusion/addin/fusion_bridge/commands/` scaffolding pattern (`commands = [...]`, `start()` / `stop()`)
- `plugins/fusion/addin/fusion_bridge/fusion_bridge.py` add-in entry structure

All copyright headers from Autodesk are preserved in the derived files.

## fusion2urdf (conceptual prior art)

**Source:** https://github.com/syuntoku14/fusion2urdf
**License:** MIT
**Scope:** No code is directly copied or forked from fusion2urdf. The URDF export
scripts in `plugins/fusion/scripts/export_urdf*.py` are original implementations
that cover the same problem space (walking Fusion component trees, emitting ROS2
URDF XML, computing joint/visual origins from Fusion joint geometry). fusion2urdf
is listed here as acknowledged prior art for the domain because anyone working in
this space will have read it; the listing is conservative and does not imply a
derivative-work relationship.

## urdf-loaders

**Source:** https://github.com/gkjohnson/urdf-loaders
**License:** Apache-2.0
**Used in:**
- `plugins/fusion/viewer/urdf/viewer/assets/URDFLoader-*.js` — Three.js URDF loader (bundled, minified)
- `plugins/fusion/viewer/urdf/viewer/assets/URDFDragControls-*.js` — drag controls for URDF joints (bundled, minified)

## Three.js

**Source:** https://github.com/mrdoob/three.js
**Copyright:** Copyright 2010-2024 Three.js Authors
**License:** MIT (SPDX-License-Identifier: MIT)
**Used in:**
- Bundled into `plugins/fusion/viewer/urdf/viewer/assets/URDFLoader-*.js` and
  `OrbitControls-*.js` — urdf-loaders is a Three.js plugin and ships Three.js
  classes in the minified output. The `@license`/copyright block is preserved
  in the bundled file.
- Referenced at runtime (loaded from unpkg, not bundled) by
  `plugins/fusion/viewer/usd/serve_usd.py` — this usage does not redistribute
  Three.js, but it is listed here for completeness.

## Autodesk Fusion 360 Python API Stubs

**Source:** Autodesk Fusion 360 Python API documentation
**License:** Autodesk (internal development use)
**Used in:**
- Not shipped to end users. Used as IDE autocomplete aid during development only. Will NOT be included in the installable plugin.

---

## How to add a new upstream

When a plugin imports, copies, or adapts code from an upstream project:

1. Preserve the upstream copyright header in the derived file.
2. Add an entry to this file with source, license, and scope.
3. Verify the upstream's license is compatible with Apache-2.0. MIT, BSD, Apache-2.0, and the Autodesk Sample License are compatible. GPL/AGPL are NOT compatible and must be either refused or flagged in a separate "Copyleft dependencies" section.
