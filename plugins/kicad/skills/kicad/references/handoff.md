# PCB fabrication and Fusion handoff

Run a repeatable handoff for a saved two-layer PCB and its sibling schematic:

```text
fzd-kicad --json handoff --board /absolute/board.kicad_pcb --output /new/handoff-directory --fusion
```

An alternate schematic path can be passed with `--schematic`. Omit `--fusion`
for fabrication/STEP exports without a Fusion import. Use a fresh output folder;
existing files aren't overwritten. Both KiCad backends must be available. Fusion
import additionally requires `/fusion:setup` and a running Fusion bridge.

The pipeline saves the expected live PCB and reads its closed outline, layer
count, thickness, component references and model declarations. It runs ERC and
DRC with schematic parity against the saved original project, preserving custom
rules. Any violation stops fabrication export. Checks respect the project's
configured severities and ignored rules, which remain visible in JSON reports.

After the gates pass, it generates front/back copper, masks, silkscreens, board
outline and Excellon drill files. The ZIP uses one consistent absolute origin
for Gerbers and drills. This preset intentionally rejects boards with more than
two copper layers rather than silently omitting inner layers.

The mechanical STEP includes component models, PCB core, pads, copper and solder
mask. Exporting only the core can yield a thinner solid than the nominal finished
board. Fusion validation measures the union of PCB stack geometry and checks
outline/thickness within 0.05 mm. It records nominal, measured and error values;
for the qualified LED demo the finished stack is 1.61 mm versus nominal 1.6 mm.
It also checks that each populated, modeled footprint has imported body geometry.

The Fusion import creates a new document, tags it by STEP SHA-256, and exports a
local F3D archive and API viewport image. Re-executing the same import script can
reuse its tagged document; the pipeline does not automatically retry uncertain
bridge writes. It never saves into an Autodesk cloud project or orders boards.

Outputs include:

- `fabrication/<board>-fabrication.zip`: Gerbers, job file and drill data, published
  only after all requested gates pass.
- `mechanical/<board>-assembled.step`: mechanical interchange model.
- `fusion/<board>-assembled.f3d` and `fusion/validation.json`: local native archive
  and measured geometry report when Fusion import is requested.
- `preview/bottom-copper-1to1.pdf`: unmirrored review/print plot; print at actual
  size with page fitting disabled. Mirroring depends on the user's etching process.
- `preview/kicad-3d.png`, `preview/fusion-3d.png`: application-generated previews.
- `validation/`: ERC, DRC/parity and drill report; drill maps are in `fabrication/drill/`.
- `handoff.json`: source hashes, artifact hashes, commands and gate outcomes.

This is a one-way mechanical handoff. Electrical nets and PCB authoring remain
in KiCad; Gerbers/drills are the fabrication input, and STEP/F3D support mechanical
design in Fusion. The current check is CAD exchange validation, not enclosure
interference analysis or a board-fabricator-specific DFM sign-off.

Official references:

- https://docs.kicad.org/10.0/en/cli/cli.html
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ImportManager_Sample.htm
