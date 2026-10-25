# Visual-mesh color routes — the full menu, the default, and the hard rule

Every way a URDF package can carry (or not carry) color, compared; then the default
route in depth. Choose the route from the source appearance data and the target
renderer; verify color and normal topology independently.

## All routes

| route | what ships | per-part color | cost | when it's right |
|---|---|---|---|---|
| (a) **No color** — plain STL visuals, no materials | 1 STL/link | none (RViz default grey) | zero | collision-only work, throwaway geometry audits |
| (b) **STL + base-color `<material>` tag** — one flat URDF color per link | 1 STL/link + a `<material>` per visual | one color per LINK | trivial | sources that genuinely have no appearance data; quick placeholders (this was the RG2's pre-2026-07-10 state) |
| (c) **Per-material STL split + `<material>` tags** — bodies grouped by color, one `<visual>` per group | N STLs/link + N tags | yes (per body group) | no new deps; more files/visual entries | when a DAE toolchain is unavailable but per-part color is required (viable; the RG2 finger plate/tip/pad triple is a natural example) |
| (d) **DAE with embedded materials** — the reference-package convention | 1 `.dae`/link (+ STL collision) | yes (per body group, in-mesh) | pycollada assembly step; see the render-quality WHAT-NOT-TO-DO below | **THE DEFAULT** — what ur_description/husarion/Robotiq all ship |
| (e) OBJ+MTL | unexplored here | yes | Fusion's API has no direct OBJ+MTL export; assimp would load it | not currently a route we can produce from Fusion |

**DEFAULT: route (d)** — colored `.dae` visuals, plain STL collision, no `<material>`
tags on mesh visuals.

> **HARD RULE: STL-with-base-color (route b) must NEVER be the default when the source
> Fusion file already carries color.** Per-body appearances are sitting in the CAD; a
> single flat tag throws them away. Route (b) is only acceptable when the source truly
> has no appearance data — and say so in the package README when you use it.

## THE EXPORT FLOW (locked doctrine, 2026-07-11)

Every CAD→URDF mesh export follows this flow — visual and collision alike:

1. **Rig with rich features.** Keep every vendor part through rigging — pins, bores and
   fasteners are the measurement features the rig is built from. Never pre-delete.
2. **Prune pass before export (DEFAULT — full-detail export is the opt-out).** A human
   hides visually-unnecessary internals (lightbulb off, never delete), OR the agent
   proposes a hide list and asks the human to review. Either way the prune is
   SYMMETRY-CHECKED before use: pair bodies across the mechanism's symmetry plane
   (mirrored centroids) and across _l/_r links; flag anything hidden on one side only;
   flag hidden bodies that are large or define the link's outer hull. (Worked example:
   the RG2 prune — 152/181 bodies hidden, hand.dae 62 MB → ~4 MB.)
3. **Per-link B-Rep boolean UNION, always — at BOTH levels.** Tessellating parts
   separately and concatenating triangles leaves internal faces, non-watertight shells
   and doubled walls. Union in B-Rep (`TemporaryBRepManager.booleanOperation`, Union),
   THEN tessellate once.
4. **Color rule: never merge across appearances.** Group VISIBLE bodies by resolved
   appearance color (body → occurrence → component override chain); union WITHIN each
   group; emit ONE single-color mesh per color group (a multi-color link ships N visual
   meshes, each single-color, all in the link frame with identity origins — the RG2
   finger plate/tip/pad split, generalized).
5. **Collision is colorblind but prune-AWARE:** union the VISIBLE bodies per link
   (colorblind — ignore appearance, but honor the prune) → ONE watertight STL per link.
   Hidden bodies are PRUNED (removed from the config) or internal structure the exposed
   shell already encloses; unioning them inflates the collision past the visual envelope
   and makes flush-mounted neighbors interpenetrate (a hidden RG2 hand body in the
   coupler-mate region overlapped the quick-changer by ~0.2 cm³ — invisible to the
   per-link extent gate, caught only by an inter-link overlap check). Visible-only keeps
   collision == the exposed CAD == the visuals, and still collapses megabody links for
   free. (Corrected 2026-07-11; was "union ALL bodies".)
6. **`is_volume` gate:** every emitted mesh — visual and collision — must load in
   trimesh with `is_volume == True` (watertight, consistent winding, positive volume).
   Ship it as a pytest gate in the package.

### THE OPEN-SURFACE TRUNCATION TRAP (root-caused 2026-07-11, moment_arm)

`is_volume` alone is a LIAR: a truncated stub is still watertight, so it passes. This
bit the RG2 moment_arm — the shipped lever was a 30 mm stub of the true 65.6 mm part,
and it sailed through both the `is_volume` gate and a growth-only bounds check.

Root cause: a vendor body can be an **OPEN SURFACE** (`BRepBody.isSolid == False`) —
the moment_arm lever (part 102658) was one, a closed-looking shell with only two sub-mm
fastener-recess holes. When such a shell is fed to the watertight-repair ladder
(`trimesh.repair.fill_holes` → `pymeshfix` per-component/soup), the ladder can only make
it a volume by **discarding most of it** — the per-component path drops the big open
component, the soup path erodes it — leaving a small closed stub that is watertight and
passes `is_volume`. The `is_volume` gate + a shrink-allowed bounds check saw nothing.

Doctrine:
- **DETECT before the bake.** Count `isSolid==false` bodies in each link's VISIBLE set
  (a one-line probe). Any open-surface body is at truncation risk. (RG2 blast radius:
  exactly the moment_arm lever L+R; every other link was all-solid.)
- **Close open shells by FAN-TRIANGULATING their boundary loops directly**, NOT via the
  repair ladder. Merge vertices → find boundary edges (appear once) → group into loops
  (networkx connected components / `cycle_basis`) → fan-triangulate each loop →
  `fix_normals`. This preserves the EXACT extent (the moment_arm fix reproduced
  65.59×41.77×20.0 to 0.01 mm, watertight) instead of eroding it. Only if a component is
  already `is_volume` do you leave it; concatenate the closed pin/bolt shells untouched.
- **OUTER-SHELL-UNION technique (for non-manifold many-body links).** A related SOLID
  failure mode: a many-body boolean union goes NON-MANIFOLD at abutting faces (internal
  walls where bolts meet the shell), and `pymeshfix` then erodes the thinnest feature (the
  RG2 hand base lost 1.7 mm at its tip this way — a 123-body union). Do NOT fight the
  non-manifold full union. Instead build the collision from the VISIBLE OUTER shells only:
  the hidden internal bolts sit INSIDE the outer envelope, so the outer-shell union is a
  clean manifold that fan-fills at the exact extent. MANDATORY verification: confirm the
  outer-shell union is ENVELOPE-IDENTICAL to the full all-bodies union (measure both bbox
  extents; they must match — for the hand both gave 142.95×75.0×75.33), proving no
  outer-defining body was dropped. Only then is dropping the interior bodies safe.

7. **TWO-SIDED extent gate (the guard `is_volume` can't be):** pin every collision mesh's
   full bbox extents to a known-good baseline and assert within tolerance on BOTH sides —
   SHRINK (truncation) as well as growth. A growth-only gate is what let the moment_arm
   stub ship (the prune legitimately shrinks pruned links, so the finalize allowed shrink
   blanket-wide). Distinguish the two by baselining the PRUNED links post-prune and the
   NON-pruned links at their full known-good extent. Reference implementation:
   `onrobot_rg2_description/test/test_fk_against_settlement.py::test_collision_extents_no_truncation`
   (per-axis, ±0.5 mm). Note a Z-window-only datum check (as `test_mesh_datum_z` was) does
   NOT catch in-plane X/Y truncation — the gate must check all three extents.

## The default route in depth: COLLADA `.dae` with embedded CAD appearances

## The convention (verified against three references)

| package | visual | collision | URDF `<material>` on mesh visuals |
|---|---|---|---|
| `ur_description` (ROS-official UR) | `.dae`, materials in `library_effects` | plain `.stl` | none |
| husarion `onrobot_rg2_description` | `.dae` per link | `.stl` per link | none |
| Robotiq official 2F-85 | `.dae` per part | `.stl` per part | none |

**Rule: visual = COLLADA `.dae` with lambert materials embedded in the mesh; collision =
plain STL; no `<material>` tags on mesh visuals** (RViz reads the mesh's own materials;
a URDF material would fight them). Keep any URDF `<material>` *definitions* only for
primitive geometry and external references — namespaced (`pkg/name`), defined exactly
once across the workcell (duplicate names crash composition).

## The pipeline (three steps, all reusable)

1. **Harvest per-BODY appearances** (Fusion-side, read-only). For every body of every
   visual mesh, resolve the appearance in override order **body → occurrence →
   component**, and read the diffuse RGBA from the appearance's `ColorProperty`.
   Real CAD is rich: the RG2 hand has 16 distinct vendor colors (screw brass, a blue
   O-ring, housing white...). Keep an explicit override map for known CAD-vs-physical
   mismatches (RG2: vendor paints the rubber bumper mid-grey; we borrow the vendor's own
   rubber-pad color) — overrides must be *declared in the script*, never silent.
2. **Bake per-COLOR groups** (Fusion-side). Identical to the plain link-frame bake
   (TemporaryBRepManager copy → transform to link frame → temp component + baseFeature →
   STL, mm), except bodies are grouped by resolved color and each group exports its own
   STL. Frames/datums must be byte-identical to the collision bake.
3. **Assemble one `.dae` per link** (host-side, pycollada + trimesh — the FIXED
   generator `15c_build_dae_fixed.py`). Load each group STL, scale mm→m, one lambert
   effect/material per group (diffuse = RGBA/255), one geometry per group, all bound in
   a single scene node. `up_axis Z_UP`, `unit meter=1`. **Normals: one per FACE,
   indexed independently of positions** (`(vertex_index, face_normal_index)` per
   corner) — see THE MISSED THING below; averaged shared-index normals are the defect
   that ruined the first generation.

## Size discipline

Tessellated CAD → XML is big (the undecimated 123-body hand is ~62 MiB vs the
references' 1–5 MiB authored meshes). Live with it until it's a real problem: the
first generation's decimation experiments (quadric, even aggression 0) traded shading
quality for size and masked the real defect. If size ever must come down, reduce the
Fusion export refinement per offending link and re-run the A/B — never decimate as an
afterthought.

## Gates (appearance-only means PROVE geometry unchanged)

- Per-mesh bounds: new `.dae` vs the collision STL (same bake) — RG2 worst 0.0087 mm.
- The FK/z-datum pytest keeps running against the visuals: trimesh parses `.dae` via
  `pycollada` (`pytest.importorskip("collada")` when filenames end `.dae`).
- Final render check in RViz — embedded materials are only proven when you see them.

## THE MISSED THING — normal topology (root-caused 2026-07-10, GPT forensics + online research)

The first DAE generation rendered as "a mess" (user verdict) while the colors were
correct. The route (DAE) was never the problem — **the generator's normal topology
was**. Forensic XML diff against the known-good DAEs (the old `onrobot_rg2_sim_control`
set and `ur_description`'s — ALL Blender-authored per their `<authoring_tool>` tags):

- **Broken:** pycollada triangle indices repeated the same index for `VERTEX` and
  `NORMAL` (`<p>0 0 1 1 2 2…</p>` — v==n for 100% of corners), with one *averaged*
  normal per merged vertex. Averaging across hard CAD edges melts every chamfer,
  fillet and machined edge into blobs. That, not colors or effects, is what looked bad.
- **Good (every reference):** positions shared between triangles, **normals indexed
  INDEPENDENTLY** — face/loop normals, so adjacent faces share a position but not a
  normal, and hard edges stay hard. `v==n` ≈ 0.1% in the references.

The fix: write one normal per FACE (`trimesh.face_normals`) and build the
index stream as `(vertex_index, face_normal_index)` per corner; drop decimation
entirely (it frayed thin features and is unnecessary once shading is correct); strip
pycollada's `double_sided` extra and zeroed material defaults; keep diffuse-only
lambert (the OnRobot reference's shading; ur_description uses phong but its quality
comes from the normals, not the shader). Verified: bounds vs collision STLs worst
0.0087 mm, pytest 10/10, RViz A/B on a4500 holds the ur_description quality bar.

What NOT to do (the actual anti-patterns, method-level):
1. **Never author COLLADA normals by blanket vertex averaging** (trimesh
   `vertex_normals` with shared v/n indices). STL has no normals; you must SPLIT them —
   face normals (simplest, what the fix uses) or crease-angle splitting.
2. **Don't decimate visuals to chase file size before fixing shading** — the first
   pass blamed size/tessellation when the real defect was normals. (Size note: the
   undecimated hand.dae is ~62 MiB — over GitHub's 50 MiB warning, under the hard
   limit; revisit only if it becomes a real problem, and never at the cost of shading.)
3. **Don't ship a colored set without an RViz A/B against ur_description** in the same
   frame — the only test that catches shading-quality regressions.

## THE SECOND MISSED THING — colors DO survive DAE→GLB (root-caused 2026-08-31, RG2 finger-tree render send-back; recorded 2026-09-01)

Downstream mirror of the lesson above. A renderer-side pass (these `.dae` visuals →
trimesh-baked per-link GLB → a three.js web viewer) produced white/grey stills, and the
first diagnosis was "the CAD appearance colors do not survive the trimesh DAE→GLB pass."
That diagnosis was **wrong**, and the wrong call pattern is general enough to recur:

**FACT (measured):** embedded per-group COLLADA appearances **SURVIVE DAE → baked GLB →
emitted viewer GLB byte-exactly**. Verified on all 11 RG2 links, blue O-ring group
(0.286, 0.616, 0.855) included: per link, the set of embedded DAE diffuse RGBAs equals
the GLB `baseColorFactor` set in count and value to 1e-6, in both the baked GLB and the
viewer-emitted copy. A white/grey render almost never means lost materials — assume
presentation until the artifact bytes say otherwise.

**TRAP 1 — the false probe (what was actually misread).** The misdiagnosis came from
probing trimesh's IN-MEMORY material wrapper: after `trimesh.load()` on a DAE, each
geometry's `.visual` is a `TextureVisuals` wrapper whose defaulted color fields read
white, and the probe took that default as evidence the appearance had been dropped —
and was never re-verified against the emitted asset bytes. The correct programmatic
check reads the ARTIFACTS, never the wrapper — pycollada for the DAE side, the GLB
file's own JSON chunk for the GLB side:

```python
import collada, json, struct

def dae_rgba_set(dae_path):                      # the DAE side, via pycollada
    c = collada.Collada(str(dae_path))
    return sorted(tuple(float(v) for v in m.effect.diffuse) for m in c.materials)

def glb_rgba_set(glb_path):                      # the GLB side, from the bytes
    data = open(glb_path, "rb").read()
    assert data[:4] == b"glTF"
    ln = struct.unpack("<I", data[12:16])[0]     # length of the JSON chunk
    js = json.loads(data[20:20 + ln])
    return sorted(tuple(float(v) for v in m["pbrMetallicRoughness"]["baseColorFactor"])
                  for m in js.get("materials", []))

# per link: dae_rgba_set(dae) == glb_rgba_set(baked) == glb_rgba_set(emitted), to 1e-6.
# Set equality in COUNT and VALUE — a dropped, averaged, or substituted group fails.
```

**TRAP 2 — presentation masquerading as color loss.** Two compounding renderer-side
effects, neither of which touches the data:
1. **Camera:** the default camera looked from +X while the O-ring ring face points −X —
   the only strongly-colored group was an occluded sliver. Fixed with a hero camera
   (position (−0.13, 0.15, 0.27) → target (0.10, 0, 0), fov 38) that faces the colored
   groups.
2. **Tone pipeline:** an ACES-filmic + hemisphere/key/fill viewer compresses albedo
   contrast, so 0.38–0.75 mid-grey groups lift toward white at distance. In the shared
   robo-render viewer that is `assets/robo-render-viewer.js:223-253` (tone mapping +
   light rig); its material normalization (:144-168) keeps GLB baseColor untouched —
   the tonal flattening is a display trait, **not data loss**.

**THE VERIFICATION METHOD — run BOTH layers before ever claiming color loss:**
1. **Asset layer:** per-link embedded-material RGBA **set equality** across
   DAE == baked GLB == emitted/deployed GLB (the snippet above).
2. **Pixel layer:** render a LABEL-FREE still — no axis rods, labels, or UI chrome that
   could masquerade as vendor color — from a camera that actually faces the colored
   groups, and assert per color group: a cluster-count floor, a median-RGB check, and
   hue ordering matching the authored color. RG2 worked numbers: O-ring mask
   `(b > g+10) & (g > r+15) & lum > 90` → 2411 px, median RGB (90, 146, 185), ordered
   b > g > r like the authored (0.286, 0.616, 0.855); neutral pixels split by luminance
   into grey body groups (12 631 px) rendering distinctly below the white housing mass
   (52 031 px).

Canonical implementation (both layers, one JSON receipt beside the media):
`robot-integration/bracket/rg2_finger_tree/verify_colors.py` in the prompt2assembly
workspace (dual-a4500); receipt
`plan-anything/setup/rg2-finger-tree-slice0-media/color-verification.json`.

## Traps

- Fusion cannot export DAE/OBJ-with-materials directly — STL-per-color-group + host-side
  assembly is the route.
- `body.appearance` is often `None` — you must walk the override chain up to the
  component, else everything comes back default-grey.
- Don't decimate with default aggression (silhouette drift, see above).
- The bake dirties the Fusion doc (temp components) — close without saving.
