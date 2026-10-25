# Fusion authoring and validation workflow

## Authoring pattern

1. Build or open the non-threaded physical part in a new document lineage.
2. Create the thread profile and helical path from named parameters.
3. Model the complete male and female geometry in an isolated component or root
   document where the helix has one unambiguous assembly path.
4. Transfer the completed B-Rep into the destination component if necessary.
5. For repeated parts, create the threaded component definition once and restore
   or add the remaining occurrences at the preserved target transforms.
6. Hide construction sketches and surfaces before review and export.

The Fusion API uses centimetres internally. Convert millimetres to centimetres
at API boundaries and keep the thread contract itself in millimetres.

## Known Fusion failure signatures

- A persisted helix `Path.create` inside a nested repeated component can fail
  with `InternalValidationError: Utils::getObjectPath`. Author it with only one
  occurrence path or in an isolated root document.
- Direct feature Combine and `TemporaryBRepManager.booleanOperation` on some
  transferred periodic B-Reps can fail with `ASM_INCONS_REL`.
- A failed combine may also report `ALL_TOOL_BODY_REFERENCE_LOST`.

Do not catch these errors and silently claim a merged result. Retain the model as
a named clearance experiment and preserve the exact error. For the proven
fallback—isolated root-document authoring, ridge-to-core union, shallow host
overlap, bounded subtractive female cutters, and one-solid transfer—follow
`trimming-and-consolidation.md`.

## Exact assembly validation

Occurrence-level analysis is unreliable for an occurrence that contains several
overlapping bodies. Validate body proxies instead:

```python
for native_a in component_a.bRepBodies:
    proxy_a = native_a.createForAssemblyContext(occurrence_a)
    for native_b in component_b.bRepBodies:
        proxy_b = native_b.createForAssemblyContext(occurrence_b)
        entities = adsk.core.ObjectCollection.create()
        entities.add(proxy_a)
        entities.add(proxy_b)
        check = design.createInterferenceInput(entities)
        check.areCoincidentFacesIncluded = False
        results = design.analyzeInterference(check)
```

Sum the positive interference-body volumes after converting Fusion's cm^3 to
mm^3 (`volume_mm3 = volume_cm3 * 1000`). Test every host-versus-mating-part body
pair at every target occurrence. A minimum-distance result cannot replace this
because penetrating solids can still report zero distance.

Store at least:

```json
{
  "constraint": "dz_mm = pitch_mm * dangle_deg / 360",
  "checked_body_pairs": 104,
  "intersection_count": 0,
  "total_interference_mm3": 0.0,
  "representation": "clearance-experiment or production"
}
```

## Export gates

### Clearance experiment

- Geometry and phase are derived and recorded.
- Source-to-CAD mesh diff passes.
- Every cross-component body pair has zero positive-volume interference.
- The document and metadata say that same-component overlapping solids remain.
- STEP/STL outputs are not promoted to a production asset pipeline.

### Production

- Each physical part reports exactly one solid body and no construction bodies.
- Thread tails are bounded by the physical host and create no exterior slivers.
- Every assembled target passes exact body-pair interference analysis.
- STEP round-trip still reports one solid per part.
- High-refinement STL is watertight, consistently wound, and one connected
  component per physical part.
- Target transforms and part identity match the unthreaded source assembly.

## Reproducibility bundle

Save the new generator script, F3D, part STEP files, high-refinement part STLs,
assembled target metadata, thread contract JSON, exact interference report, and
source-to-CAD comparison report. Never overwrite the source generator or the
known-good unthreaded assets.
