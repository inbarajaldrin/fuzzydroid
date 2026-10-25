# Thread trimming and consolidation

Produce one watertight solid per physical part. Treat connector dimensions,
phase, clearance, and target transforms as inputs measured from the current
host; previous project's coordinates are not a fit contract.

## Construction sequence

Author each completed part at the root of an isolated parametric document. This
keeps helical paths unambiguous and avoids repeated-component context failures.

For a male connector:

1. Build the host and minor-radius core from named dimensions.
2. Give the core enough overlap with the host for a robust boolean union. A
   deeply buried periodic stem can fail even when a shallow overlap succeeds;
   derive and validate the overlap for the current geometry.
3. Sweep the calibrated ridge at the intended phase with smooth terminations.
4. Join the ridge and its tapers to the core, then join the completed stem to
   the host. Verify a single solid after each stage.

For a female connector:

1. Build the host with a bore derived from the clearance contract.
2. Construct a male-shaped helical cutter at the assembled thread phase.
3. Extend the cutter beyond the socket boundary and let the host trim it.
   Account for the profile's axial half-span when deriving start/end phases;
   shifting the first profile center can introduce first-turn interference.
4. Subtract the cutter from the host. Avoid additive female ridge bodies that
   protrude outside the host or depend on a slicer to merge them.

Only transfer the completed solid after the isolated document reports one solid.
Use `TemporaryBRepManager.copy`, retire the old destination body with a remove
feature, and restore repeated occurrences with their recorded transforms.

## Kernel failure handling

A nested repeated-component helix can fail with `Utils::getObjectPath`.
Periodic boolean operations can fail with `ASM_INCONS_REL`, including a ridge
joined directly to a previously combined host. Move construction to an isolated
root document, stage ridge-to-core and core-to-host unions separately, and
recheck the necessary overlap. Retain failed experiments under explicit names;
never label an unresolved multi-solid result as production output.

## Acceptance gates

- Exactly one solid per physical part, with no unintended surfaces or fragments.
- Every repeated occurrence retains its intended target transform.
- Zero positive-volume target interference across every mating body pair.
- STEP round-trip preserves solid counts, definitions, and placement.
- Consumer-side exact boolean checks confirm target clearance after export.
- STL exports are watertight and consistently wound, with the intended connected
  components after ordinary duplicate-vertex welding.
- Changes outside the declared connector region remain within the project's
  source-resolution and manufacturing tolerances.

Keep source hashes, generator parameters, exports, and the resulting acceptance
receipts in the user's project. Recalculate all axial bounds and thread phases
when the host envelope, socket depth, handedness, or moving part changes.
