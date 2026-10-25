> Internal workflow loaded by the main skill. The plugin root comes from
> that skill. Resolve this workflow's `references/`, `scripts/`, and
> `evals/` paths relative to this directory.

# Assemble — clean-room, feature-derived CAD assembly

For an assembly whose transform history cannot be trusted, **derive frames from
features and datasheets; compute placement matrices; prove the result with
signed point checks and exact overlap analysis.**

## The pipeline

1. **Pristine sources only.** Work from the vendor CAD import and the datasheet.
   Any document that has been reframed/moved in past sessions is suspect — its
   transform lineage is exactly what you are trying to escape. Never modify or
   save the sources.
2. **Define each part's frame from B-Rep features** (via the bridge, occurrence
   *proxy* bodies — never component-local): mating plane (largest plane, normal
   on the axis; verify with a datasheet depth like a dowel-hole depth), bore/disc
   axis (Circle3D centers), clocking features (dowel hole, connector/pin block —
   these give you SIGN). Prefer the frame the vendor documents (torque/coordinate
   figure) — it makes the result auditable forever.
3. **Derive the placement matrices on paper** (datasheet distances + feature
   azimuths). Each matrix is a documented equation, e.g.
   `T = Trans(0,0,seat) · Ry(−π/2)` with the clock fixed by "pin block must meet
   pad block".
4. **Build FRESH**: new doc, `occurrences.addByInsert(dataFile, identity, True)`
   (live links), all inserts FIRST, then `transform2 = matrix`. Never insert into
   an already-built assembly (it re-solves and flings occupants).
5. **Prove it — two layers**:
   - **Boolean-overlap categorization** (`TemporaryBRepManager` intersection per
     body pair, grouped by part number): designed engagements (telescoping,
     spring connectors) vs real collisions. `measureMinimumDistance` is BLIND to
     interpenetration — never use it as a seat test.
   - **Signed point checks**: a uniform per-pin engagement signature (e.g. 12
     pogo pins × identical 0.29 mm³) is the only test that catches 90°/180°
     clock errors. Unsigned checks (bboxes, axis-parallelism) provably cannot.
6. **Guard-save the NEW doc only** (verify seat/values before save; never save
   sources).
7. **Bake meshes in the documented frame** when the assembly feeds a URDF:
   `tbm.copy(proxy)` → temp component → STL → delete temp (CopyPasteBodies fails
   in direct-modeling docs; parametric docs need a baseFeature). Mesh frame ≡ link
   frame, identity origins — the Robotiq discipline. Scale mm→m for URDF. For the
   VISUAL set, bake per-color body groups (appearances resolved body→occurrence→
   component) and assemble colored `.dae` per link — collision stays plain STL;
   method: `../cad-to-urdf/workflow.md` `references/colored-visuals.md`.
8. **Datum-audit the URDF against CAD**: per-link, URDF FK × mesh bbox vs the
   CAD station bbox in the same frame, at the same pose — and **assert every
   axis**. The −10 mm RG2 datum bug lived for weeks because widths (y) and
   depths (x) were asserted and z never was.

## Failure catalog (each cost real time)

| Trap | Reality |
|---|---|
| "Rotate the part until it looks right" | Rotation has 3 meanings: move (transform2), reframe (bake), declare (URDF origin). Applying one twice, or in two places, is the root of every clock bug. |
| Neutral-mesh + decomposed rotations (misapplied Robotiq pattern) | Robotiq's actual discipline is mesh-in-link-frame + pure translations. Decomposing across mesh/joint/arg invites double-counting. |
| Unsigned verification | Axis-parallel ≠ correctly clocked. Only point features (dowel, pins) pin the sign. |
| Two export sessions, two datums | Every mesh-emit session must state its datum; mixed generations produce self-consistent-but-shifted sets. Discriminate mesh-internal vs joint-origin shifts by reading the JOINT origins (if joints are CAD-true, fix the mesh origins; never fix at a shared root joint — it breaks frames). |
| 4-fold flange ambiguity | ISO-9409 bolt circles repeat every 90°. Without a dowel pin, the physical clock is a lab fact — confirm against hardware, carry it as a config arg (steps of π/2), not a package change. |

## Verification record

For each assembly, record the source geometry, feature-derived frames, placement
matrices, signed landmark checks, and boolean-overlap results. Compare exported
mesh datums to the same CAD features before packaging. Keep the resulting scripts
and evidence in the user's project; derive document names and output paths from
that project rather than a previous assembly session.
