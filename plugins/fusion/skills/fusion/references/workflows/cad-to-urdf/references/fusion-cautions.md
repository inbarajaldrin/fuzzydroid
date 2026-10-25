# Fusion cautions — the traps that waste hours

Everything that runs inside the Fusion process. These are non-obvious failure modes; each
one cost real time.

## Phantom save (the worst one)

`doc.save()` returns `True` but **persists NOTHING** when another currently-open document
references the target doc (a linked reference holds the lineage). You think you saved v5;
you didn't.

**Always verify a save by close+reopen**, not by the return value:

1. Save.
2. Close the doc (and any docs referencing it).
3. Reopen from `dataFile.versions` / by name.
4. Confirm `dataFile.versionNumber` advanced AND the change is actually present.

`saveDataVersion()` may not apply; `DataFile.promote()` created a new lineage version but did
NOT publish a modified historical tab in one case. When in doubt, the durable artifact was a
NEW named data item, and the check is `doc.isModified` + `dataFile.versionNumber` +
`dataFile.versions` read AFTER a reopen.

## Never save a reference / source doc

Reference and source docs (the authoritative CAD, linked sub-assemblies) are read-only. If a
script dirties one (a temp component, a measurement that touched geometry), **close WITHOUT
saving and reopen clean**. A QC export once left the station `isModified=true`; the fix was
close-without-save + reopen the clean version. Verify `isModified=false` before you consider
the doc untouched.

## Live-link & breakLink export traps (the f3d / breakLink / STEP family)

Three related traps that bite when producing the required-output artifacts (native doc +
STEP + meshes) from a live-linked rigged doc. They read together.

### (1) Live-linked `.f3d` is a hollow ~33 KB stub — breakLink to make a native doc

An API `Fusion Archive (.f3d)` export of a doc whose parts are LIVE-LINKED external
references is a **hollow ~33 KB stub**: the archive holds the assembly structure + the
xref pointers, but the B-Rep lives only in the cloud source, so the file has empty
`Breps.BlobParts`. It "opens" only where the cloud xref resolves — useless as a portable
or reliable prune source. A genuinely-embedded `.f3d` of the same part is multi-MB (the
QC's was 33 KB linked vs 3.85 MB after embedding).

### (2) Make the doc NATIVE with breakLink (safe — does not touch the source)

`occurrence.breakLink()` on the linked occurrence copies the geometry INTO the doc (it
does NOT modify the pristine source — safe). Verify `occurrence.isReferencedComponent ==
False` on the top occurrence AND all children, and that bodies are `isSolid` editable
B-Rep. Then the `.f3d` embeds real geometry. Guard-verify extents BEFORE saving the native
doc (breakLink embeds geometry as-is → pre/post extents must match).

### (3) breakLink breaks direct STEP export — flatten to fix

After breakLink, the part is
restructured into nested child occurrences, and a direct assembly STEP export
(`createSTEPExportOptions(step, root)`) SILENTLY DROPS bodies (the QC lost 3 of 8; the
STEP file had 5 `MANIFOLD_SOLID_BREP`, extents came out short). Close+reopen did NOT fix
it. **Fix: flatten** — `TemporaryBRepManager.copy` every world-placed body into one temp
base-feature component and `createSTEPExportOptions(step, temp.component)` that. Verify
the STEP by re-import: solid count AND extents. Guard-verify extents BEFORE saving the
native doc (breakLink embeds geometry as-is → pre/post extents must match).

## Open-surface bodies defeat the `is_volume` gate (silent mesh truncation)

A vendor `BRepBody` can be an OPEN SURFACE (`isSolid == False`) even when it looks closed.
Feeding one to the watertight-repair ladder (`trimesh.repair.fill_holes` → `pymeshfix`
per-component/soup) closes it only by DISCARDING most of it → a truncated stub that is
STILL watertight, so `is_volume` passes and the truncation ships silently (the RG2
moment_arm: a 30 mm stub of a 65.6 mm lever). Detect `isSolid==false` bodies before the
bake; close them by fan-triangulating their boundary loops directly (preserves exact
extent); and add a two-sided (shrink AND growth) extent gate. Full doctrine:
`references/colored-visuals.md` "THE OPEN-SURFACE TRUNCATION TRAP".

## Single-agent resource

Fusion is a single-agent resource: one owner at a time, one heavy call at a time. Before
starting, verify the doc state fresh (nothing user-touched, `isModified=false`). On ANY
wedge, **stop and report — do not retry-hammer** the bridge (repeated heavy calls compound a
wedge). A wedged bridge recovered after a ~15 s poll once; hammering it would not have helped.

Activate the target doc by iterating `app.documents` and calling `.activate()` by name. But:
**the `Documents` collection index invalidates when you close docs mid-iteration** — snapshot
the list first if you're going to close things while looping ("Bad index parameter" / "Bad
index parameter" deletions that did nothing came from iterating `app.documents` while closing).

## Flexible-occurrence limitation (linked sub-assembly poses don't hold)

A linked sub-assembly's internal joint pose will NOT hold at the parent-assembly level in
this Fusion API build. You cannot pose a linked arm's joints from the station and expect it
to stick.

**Work around it, don't fight it:** use the linked part at its REST/default pose, and move
the OTHER assembly to match — e.g. don't re-pose a linked UR5e's joints; bring it in at its
source rest pose and move the wrist-mounted QC+gripper unit onto the rest-pose flange. Bake a
desired rest pose into the SOURCE doc (saved at joints-zero) so the linked instance lands
there. This sidesteps the flex-occurrence trap entirely.

## Measure faces/edges only — never bboxes/vertex proxies

`boundingBox` and vertex-proxy reads go stale after edits and mislead. Read live geometry
from faces and circle edges. `measureManager` is on `app` (the `Application`), NOT on the
`Design` (`des.measureManager` → AttributeError; use `app.measureManager`). Lengths come back
in **cm**; report mechanical gaps in **mm**.

## Duplicate DataFile disambiguation — by structure, not name

Two DataFiles can share a name (a duplicated adapter: `quick_changer_cable_holder` existed as
a 1:04 original and a 1:24 copy, both same name). Disambiguate by STRUCTURE, not the label:

- The 1:24 copy was the 1:04 rotated exactly +90° about Z; the rotated one was physically
  correct (fingers ⊥ dowel), the original wasn't.
- Identify which one an assembly actually references (follow the occurrence's `dataFile` id),
  and verify a candidate is unreferenced (zero references anywhere) BEFORE deleting it.
- Deletion guards that were required before removing the stale one: (a) confirm it's the
  correct stale id, (b) verify ZERO references to it, (c) do not touch the correct one or any
  other doc. `dataFile.deleteMe()` returning `True` + only the correct one remaining = done.

## Passing parameters into Fusion scripts

Environment variables do NOT cross into the Fusion process. Pass parameters via a JSON file
the script reads (`/tmp/export_params.json`), not env vars. Also: never `printf` a script
that contains `%` — write the file and `cat` it into the bridge.

## Recursive cloud walks time out

Walking a cloud project folder recursively can time out and wedge the bridge. Do shallow,
per-folder listings instead of a deep recursive walk.

## `addByInsert` — the third arg is `isReferencedComponent` (link vs copy)

`root.occurrences.addByInsert(dataFile, transform, isReferencedComponent)` — the 3rd arg is
**isReferencedComponent**, NOT `isGroundToParent` (a persistent misread that cost this session
hours concluding "live links are UI-only"):

- `True` → LIVE external link (appears in `document.documentReferences`; `isReferencedComponent`
  == True). `False` → embedded local COPY.
- FAILS / returns null if the dataFile is not in the SAME PROJECT as the target doc while True.
- Resolve the DataFile by lineage urn: `app.data.findFileById(lineage_urn)`.

## Linked insert into a BUILT assembly flings existing parts to the origin

`addByInsert` into an assembly that already has transform2-placed occurrences triggers a
re-solve that RESETS those occurrences to the origin (their `transform2` reads `(0,0,0)` —
`measureManager` world distance confirms they physically moved ~72 cm off). Fixes:

- **Build fresh** (preferred): `app.documents.add(FusionDesignDocumentType)` →
  `doc.saveAs(name, folder, desc, "")` into the project → insert ALL parts at **identity** →
  position each via `transform2` AFTER all inserts. Nothing positioned during inserts = nothing
  to corrupt. (See `scripts/linked_insert.py`.)
- **Record + restore**: capture every existing occurrence's `transform2` BEFORE the insert, then
  re-set them AFTER. Setting `transform2` on an already-present occurrence is safe — only the
  INSERT corrupts.
- Verify final geometry with `measureManager` WORLD distance, not `transform2` (which reads
  stale/`(0,0,0)` right after an insert).

## Phantom save #2 — saving from a NON-latest version does nothing

Opening an OLD version (e.g. v10 when v11 is the latest) and calling `save()` returns `True` and
flips nothing, but creates NO new version — the latest on disk stays v11. You must be on the
LATEST version to save forward. Verify by close+reopen reading `dataFile.versionNumber`. (This is
distinct from the other phantom save — save() lying while a referencing doc is open.)

## Memory-pressure bridge wedge + the close-iteration trap

- Long Fusion sessions accumulate memory pressure that WEDGES the fzd-fusion bridge ("not
  reachable" / stale `(0,0,0)` transform2 reads). It self-recovers in ~15–30 s for a transient
  wedge; a full Fusion RESTART clears it entirely. Do NOT hammer a wedged bridge.
- Closing docs while iterating the live `app.documents` collection raises
  `RuntimeError: 3 : Bad index parameter`. Snapshot the list first:
  `docs = [app.documents.item(i) for i in range(app.documents.count) if …]` then close from the
  snapshot.

## Bridge alive but every exec times out (dead CustomEvent, 2026-07-10)

After a Fusion crash-relaunch (`open -a`), the bridge add-in can come up in a state
where PING answers (socket-thread fast path) but every `exec` times out: the
`registerCustomEvent` performed during add-in auto-start returned a DEAD event — the
main-thread handler never fires, and even the add-in's backup timer re-poke can't wake
it. `../../doctor.md` shows all green (its bridge check is a ping). Reproduced on two
consecutive boots.

RECOVERY (no restart needed): re-register the event ON the main thread via the Text
Commands palette (Py mode) — activate Fusion, focus the palette input, run:

    import sys; m=[v for k,v in sys.modules.items() if k.endswith('tcpServer.entry')][0]; a=m.adsk.core.Application.get(); a.unregisterCustomEvent(m.CUSTOM_EVENT_ID); ev=a.registerCustomEvent(m.CUSTOM_EVENT_ID); h=m.BridgeEventHandler(); ev.add(h); m._handlers.append(h); m._custom_event=ev; m.futil.log('bridge event re-registered', force_console=True)

exec returns immediately afterwards (and any queued work drains). The palette runs on
the main thread, which is exactly why it can fix what the socket thread cannot.
