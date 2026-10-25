# Sliders, multi-part links, and serial chains

Extend the parent skill's joint-authoring rules with the methods below for
prismatic axes and repeated links. For the full drag-chain method, read
`drag-chain/rig-drag-chain.md`.

## Slider (prismatic) joints

1. **As-built slider is right for an already-assembled rail** — no rotational pivot to
   permute (Law 4's as-built danger is revolute-specific), and it never snaps/teleports.
2. **Non-rigid as-built joints require non-null geometry.** Pass
   `JointGeometry.createByPoint(comp.originConstructionPoint.createForAssemblyContext(occ))`.
   Only rigid welds accept `None`.
3. **Direction enums resolve in the joint-geometry COMPONENT's frame, not world.**
   A STEP sub-assembly authored tilted (ours: 32° about Y) poisons every enum. Never
   guess: sweep X/Y/Z empirically (create → drive +5 → measure world delta → delete).
   The winning enum changes when you change the child part.
4. **The rail-edge frame trick:** if no enum is world-aligned, build the joint geometry
   from a **world-aligned linear edge on the OTHER side**:
   `createByCurve(rail_edge, MiddleKeyPoint)` → `ZAxisJointDirection` slides along that
   edge. (Custom-direction *entities* for as-built sliders are unreliable — they
   silently resolve to wrong axes; the geometry-frame route is deterministic.)
5. Translational limits are sane (no ±2π traps): plain min/max in cm, enforced.

## Multi-part moving links (Law 3, sharpened)

- **Never rigid-JOINT a sub-assembly container** expecting its children to follow.
  A container with zero direct bodies binds only its frame — drive it and one welded
  part follows while the other 16 stay behind. Rigid-GROUP the geometry-bearing
  leaves (+ riders) instead, then joint a *member* of the group.
- **Validate on ≥2 distinct parts of the link** (a fastener + a plate). One landmark
  moving proves nothing about the rest.

## Deletion, phantoms, and direct mode

- In direct-modeling designs, `timelineItem.deleteMe()` **silently no-ops** while
  `entity.deleteMe()` works. A joint "deleted" from the collection can persist as a
  functional phantom that over-constrains every retry ("A joint in system exists").
  The timeline entities are the truth.
- **`transform2` edits DO work in direct mode even on jointed occurrences** — the
  "silently discarded" gotcha is the direct→parametric switch, and the "no-ops when
  jointed" gotcha is parametric-only. Rigid-moving a jointed-but-dangling segment is
  a legitimate repair (conjugate the world correction through the parent occurrence:
  `local' = P⁻¹ · C_world · P · local`).

## Serial chains (the big ones)

- **Building blocks are machine-readable connectors.** Identical modular parts mate
  via coincident same-radius circle pairs — build the adjacency graph from circle
  coincidence (<0.6 mm) and walk it for the chain order.
- **Each pivot has MULTIPLE coincident pairs** (two rims + a collar, radii within
  0.1 mm of each other). The wrong pick throws the child laterally — an error angle
  compensation can NEVER fix. Gate = brute-force (pair × flip), keep minimum
  displacement, then angle-iterate.
- **Segment-bridging joints:** when both sides of a new joint already belong to
  jointed segments, forward angle compensation *diverges* (error doubles per
  iteration). Creating the joint with geometry sides **swapped** resolves through the
  other side and can land at 0.0000.
- **THE cardinal rule: create→measure→delete gating is only safe on a virgin pose.**
  After joints have been driven, every joint creation snap redistributes drive values
  across *neighboring* joints, and deletion does not roll that back — retry loops
  compound corruption. Escape pattern: **create the troublesome joint ONCE (tolerate
  the snap explosion), then heal everything by driving** — walk proximal→distal,
  rotating each joint so its child's landmark reaches its recorded as-modeled target
  (test ± sign; 2–4 rounds converge).
- **Drive-heal is the universal recovery.** With a pose table recorded at import
  (first-planar-face origin per part), any corruption — even 30 cm — is reversible by
  target-converging drives. No version rollback needed. Used 3× in production.
- **Audit the FULL watch list including the far end before every save.** A save
  captured a corrupted chain because only the near landmark was checked.

## Closed kinematic loops: don't (chain edition)

Law 7 says loops freeze. A 26-revolute chain loop is worse: ~20 *redundant* DOF, so
the solver doesn't freeze — it **wanders** (any solution satisfies the constraints;
nothing pulls it back), and at geometric jams it **breaks constraints silently**
(a rigid weld failed at a 3.5 cm drive with no error, corrupting poses). Verified
across rigid weld, pin-slot, and free-slider closures. Leave chains OPEN and compute
coupled poses by script (URDF-mimic-style, but nonlinear-capable):

```
jointₖ(q) = r₀ₖ + sₖ · wrap(δₖ(q) − δₖ(0))     # sₖ = empirically calibrated sign
```

with δₖ(q) from a path model (straight runs + circular bend, chord-walked at the
measured pitch, bend center solved by shooting). Fit achieved: 0.09 mm. Scripted
poses are deterministic, exactly restorable, and cannot corrupt anything.
Full math and script skeletons: `drag-chain/`.

## Law 10 corollary: mesh export vs healed joints

`addNewComponent`/`copyToComponent` (the Law-10 world-baking recipe) triggers a full
solver re-evaluation. A joint that was created at a bad pose and later healed BY
DRIVING gets re-derived from its STORED creation frame during that recompute — its
subchain snaps back to the old bad pose *before* the copy captures geometry.
Deterministic; survives save/reopen; the live face-geometry reads stay correct right
up until the copy, so only a post-copy audit or the STL's world bounds reveal it.

- Audit landmarks in the same exec immediately before each copy AND verify each
  exported STL's world bounds after.
- For affected bodies, skip temp components: export the body directly (native
  component space), read ≥3 circle-edge centers from the component body and the
  world proxy at the SAME edge indices (exact correspondence), Kabsch-fit the
  native→world transform (residual must be ~0), bake it with trimesh.
  Do NOT chain `occurrence.transform2` matrices by hand for nested occurrences —
  measured correspondence is the only reliable route.
- After any temp-comp export, re-audit; recover via drive-heal or
  close-without-save + reopen.
