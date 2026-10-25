# The θᵢ(q) pose engine — math

Everything in Fusion-internal cm and radians. The chain plane is XZ (pivot axes
along Y); adapt axis names to your assembly.

## Path model

The chain occupies a piecewise path parameterized by arc length s:

```
P(s) = (x_a + s, z_top)                                    0 ≤ s ≤ s₁      top run
     = (x_b + R·sin θ, z_c + R·cos θ),  θ=(s−s₁)/R         s₁ < s ≤ s₁+πR   U-bend
     = (x_b − (s − s₁ − πR), z_bot)                        s > s₁+πR        bottom run
```

with `s₁ = x_b − x_a`, `z_c = (z_top+z_bot)/2`, `R = (z_top−z_bot)/2`.
- `x_a(q) = x_a0 + q` — the anchor pin rides the carriage.
- `x_b` — bend center, the one unknown.

Parameters come from MEASURED pins at park: `z_top`/`z_bot` = mean z of the first/
last few pins (straight runs only — bend pins contaminate naive z-filters; this bug
produced R=42 cm instead of 9 cm once), pitch = mean consecutive pin distance on a
straight run.

## Chord walk (exact link lengths)

Links are rigid: consecutive pins must be exactly one pitch apart as a CHORD, not
arc length (in the bend, arc per chord = 2R·asin(p/2R)·(R/p)·p > p). Place pin k+1
by bisecting on Δs until `|P(s+Δs) − pinₖ| = pitch` (48 bisection steps ≈ 1e-14).

## Shooting for the bend center

`x_b` is fixed by the tail boundary condition: bisect x_b until the chord walk's
last pin lands at the tail x (60 steps). Monotonicity: larger x_b → longer runs →
last pin lands further along.

## Tail physics (drape-first, pull-only)

```
x_t = x_t0                                   # planted at park by default
solve x_b;  if x_b − x_t < L_min:            # bottom run exhausted →
    x_t = max(rail_min, x_b − L_min)         # tail DRAGGED backward only
    re-solve x_b (iterate ×~5, converges)
```

The tail is never pushed forward past park (chains transmit compression into drape,
not tail motion). Consequences to verify against your model — they are the
signatures of correctness:
- bend center moves at **exactly q/2** while the tail is planted;
- with the tail free-riding instead (wrong model), the bend moves at q (rigid
  translation) and no link rotates.

## Angles

```
φ₀   = orientation of the anchored bracket (constant; it rides the carriage)
φₖ   = atan2(zₖ − zₖ₋₁, xₖ − xₖ₋₁)      k = 1..N−1   (link k between pins k−1,k)
φ_N  = tail bracket orientation (constant, flat on its rail)
δₖ   = wrap(φₖ₊₁ − φₖ)                  relative angle at joint k
jointₖ(q) = r₀ₖ + sₖ · wrap(δₖ(q) − δₖ(0))
```

- `r₀ₖ` = the joint's Fusion value at park (its zero is its creation pose, NOT your
  convention — never assume 0).
- `sₖ` = empirically calibrated sign: drive +0.06, measure the child's actual
  rotation direction about the pivot (project onto the chain plane, atan2 of the
  landmark-minus-pivot vector before/after). Expect a few inverted joints —
  swapped-geometry joints in particular.
- Using the DIFFERENCE δₖ(q) − δₖ(0) cancels systematic model-vs-CAD bias; only the
  model's *changes* need to be right.
- Always `wrap()` to (−π, π] when differencing angles near ±π (bottom-run links
  point −X).

## Acceptance numbers (from the reference implementation)

| Check | Achieved |
|---|---|
| Model pins vs measured pins at park | 0.009 cm max |
| Tail drift across full ±62.5 cm sweep | ≤ 0.11 cm |
| Bend-center speed while tail planted | q/2 exactly |
| Park restore after any sweep | 0.0000 cm |

If your numbers are 10×/100× off, check: cm-vs-mm at a boundary, bend pins polluting
z_top/z_bot, a missing wrap(), or an uncalibrated sign.

## Design-review bonus

The model doubles as a design checker: solve the bend center at travel extremes and
compare to the tray/rail ends. (The reference hardware put the bend at 93.7 cm vs a
94.5 cm tray end at full extension — the chain length was sized exactly for the
travel, which the model surfaced without a tape measure.)
