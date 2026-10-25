# Coupling / transform measurement — the biggest lesson

**Read a coupling from the PHYSICAL MATING GEOMETRY via a BOOLEAN-INTERSECTION overlap test,
and place parts by their OWN FEATURES.** Not from occurrence transforms (circular). Not from
eyeballed face areas. And NOT from `measureMinimumDistance` — that is the trap that cost the
most time: it returns 0 for touching AND for interpenetrating solids, so it cannot tell a
clean seat from a collision.

## DO NOT confirm a seat with min-distance (the expensive bug)

`app.measureManager.measureMinimumDistance(a, b)` returns **0.0 for both touching and
overlapping** solids. A coupling once "confirmed clean, minDist 0.0" was actually a 176 mm³
collision the whole time — the whole "17.8 mm is datasheet-accurate" conclusion was wrong and
had to be redone. Min-distance is fine for measuring a GAP between separated parts; it is
useless for confirming a seat.

## The correct test: boolean-intersection overlap volume

Use a temporary boolean intersection (read-only — no change to the design):

```python
tbm = adsk.fusion.TemporaryBRepManager.get()
ca = tbm.copy(bodyA); cb = tbm.copy(bodyB)
if tbm.booleanOperation(ca, cb, adsk.fusion.BooleanTypes.IntersectionBooleanType):
    overlap_mm3 = ca.volume * 1000.0   # cm³ → mm³
```

Notes learned the hard way:
- `design.analyzeInterference(...)` returns **None** on linked/assembly occurrences — do not
  rely on it. The `TemporaryBRepManager` boolean is the reliable path.
- Pre-filter pairs by bounding-box overlap so you only boolean the bodies that can touch.
- An assembly occurrence's `.bRepBodies` is EMPTY — the real solids live in its child
  occurrences. Gather solids **recursively**, not just `occ.bRepBodies`.
- To find the flush seat, **axial-sweep**: translate temp-body copies of one part along the
  approach axis in small steps and find where the overlap drops to 0 (`tbm.transform(copy,
  translation_matrix)`). That displacement IS the seat correction.

Use `scripts/overlap_probe.py` (recursive solids + bbox pre-filter + boolean overlap +
optional axial sweep).

## Place parts by their OWN features (feature-mate, not numerical transform)

Reading a coupling off an assembly is only as good as the placement. If the parts are
mis-placed, you measure the mis-placement. Prove it and fix it by feature-mating:

1. **Concentric** — align the parts on their Ø bolt-circle / disc-rim axis. Find the axis
   from the Ø71 (or whatever) rim circle center + normal, or the Ø50 bolt-circle center.
2. **Clock** — align the Ø6 dowel-pin axes (the dowel is the odd hole; see below).
3. **Flush** — make the mount FACES coincident. Verify with face NORMALS (a tilt shows as a
   normal a few tenths of a degree off the approach axis) and boolean interference = 0.

Diagnostic that saves hours: **measure each part in its OWN frame** to decide whether a
"defect" is placement or intrinsic. If a whole sub-unit reads tilted in the assembly but its
parts are each perpendicular-to-their-own-axis (and mutually parallel), the tilt is 100%
placement and DISSOLVES in a proper feature-mate — no CAD fix needed. (This session: a 0.068°
"tilt" and a "0.6 mm datasheet-vs-collision conflict" both turned out to be placement.)

## Designed overlaps are NOT collision

At a datasheet-correct quick-changer seat the solids STILL overlap, by design — do not chase
these to zero:
- a **cam / coupler telescopes** into an un-hollowed receptacle body (the receptacle isn't
  modeled hollow), and
- a **spring pogo-pin electrical connector compresses** on mate.

Enumerate the overlapping body pairs **by part number** and categorize:
- **Expected** (ignore for the seat): cam-in-pocket, coupler-into-receptacle, connector
  compression.
- **Real** (a genuine seat problem): mount-face-vs-mount-face interpenetration, or a bolt
  shank vs solid. Only these move the seat.
The expected ones are collision-mesh cleanup for later (hollow the receptacle, model the
connector compliant), NOT a seat error.

## No-drift principle: CAD = URDF = USD

- **Read it from the CAD; never bake a measured delta into the URDF.** The URDF standoff IS
  the CAD face-to-face distance.
- **If the CAD deviates from the datasheet, decide at the CAD** — accept it (it's the built
  part) or fix the CAD and re-export. No "split the difference in the URDF" fudge.

## Two occurrence-transform / face-ID traps (why not those)

- **Occurrence transforms are circular:** a placement transform can encode a prior
  reconstruction — reading it back "confirms" the number you put in. The geometry is
  independent truth; the placement is not.
- **Eyeballed faces bit us twice** (both diagnosed only because a later boolean/feature check
  disagreed with min-distance): an 18.4 mm read off a flange bore edge 0.6 mm proud of the
  mating face; a "12.8 mm" read off a recess face 0.125 mm off the seat.

## The worked coupling (RG2 on Quick Changer)

Re-derived by an ideal feature-mate (concentric bolt-circle + dowel-clock + flush faces;
verified tilt = 0, flange↔QC interference = 0):

| Segment | Value | Basis |
|---|---|---|
| flange → rg2_base (the URDF standoff) | **18.10 mm** | datasheet-exact: 13.60 + 4.50 |
| flange → QC tool coupler | 13.60 mm | OnRobot QC datasheet §1.3 |
| QC coupler → rg2_base | 4.50 mm | RG2 into-body, measured in the RG2 part's OWN frame |
| clocking | fingers ⊥ UR dowel | dowel dot 0.0006 (89.97°); `rotation = π/2` |

The two 0.041 mm mount-face gaps (flange↔QC and QC↔RG2) are equal-and-opposite and NULLIFY —
the seat stays exactly 18.10 mm. (The earlier "17.80 mm" was a min-distance reading against a
mis-mated, interpenetrating assembly — wrong; the transient 18.4–18.64 mm were collision-
inflated. The feature-mate resolves all of it to 18.10 mm.)

## Identifying a dowel / index feature

Find the dowel by what makes it DIFFERENT from the bolt pattern (size, no counterbore,
azimuth off-pattern): the UR flange dowel was the odd non-counterbored Ø6 hole at azimuth
85.9° among bolts at 40.9/130.9/220.9/310.9°. Then verify the mating part's motion axis is
perpendicular (or per spec) to it via a **dot product**, not by eye.
