# Geometry and mate contract

## Canonical printable profile

Use this baseline when reproducing the validated BOSL2 pair or adapting it to a
coarse furniture connector:

| Property | Value |
|---|---:|
| Starts | 1 |
| Handedness | right |
| Profile | symmetric trapezoid |
| Major diameter | 24.0 mm |
| Pitch and lead | 8.0 mm |
| Radial depth | 3.0 mm |
| Included angle | 90 degrees |
| Tessellation | 96 segments |
| Female `$slop` | 0.10 mm |

The 45-degree flanks are printable without support when the thread axis is
vertical. Slop is a fit parameter, not a substitute for recording the printer,
material, nozzle, layer height, temperatures, speed, cooling, and slicer.

## BOSL2-compatible radii

For nominal major diameter `D`, depth `h`, segment count `n`, and female slop
`s`:

```text
external_major_radius = D / 2
external_minor_radius = external_major_radius - h
internal_major_radius = external_major_radius / cos(pi / n) + 2s
internal_minor_radius = internal_major_radius - h
radial_clearance = internal_major_radius - external_major_radius
```

For `D=24`, `h=3`, `n=96`, and `s=0.10`:

```text
external major/minor = 12.0 / 9.0 mm
internal major/minor = 12.206428392125261 / 9.206428392125261 mm
radial clearance     = 0.206428392125261 mm
```

The slop term contributes 0.20 mm nominal radial clearance. The additional
0.006428 mm is the 96-segment radius correction, so do not round it away when
matching the reference.

## Phase and screw motion

For the validated right-handed, single-start convention:

```text
z(angle) = seat_z + pitch * (angle - seat_angle) / 360
dz       = pitch * dangle / 360
```

At the assembled target, separate the male and female **material ridge centers**
by half a pitch modulo one pitch. Do not align ridge center to ridge center.

If the male world ridge center at polar angle zero is `M`, the female local ridge
center is `F`, and the female part is translated to `seat_z`, this specific
right-handed convention derives:

```text
axial_phase = seat_z + F - M - pitch/2
seat_angle  = normalize_0_360(360 * axial_phase / pitch)
```

Calibration values `M=14.8`, `F=7.995`, `seat_z=7`, and `pitch=8` give
`seat_angle=188.775 degrees`.

Changing the handedness, moving the male instead of the female, reversing the
axis, or changing transform multiplication order can reverse the angular sign.
Derive it from the generated helix rather than copying the sign blindly.

## Mesh-diff evidence to preserve

For a new generator, compare each source mesh and Fusion export in both
directions with area-weighted samples and exact closest-point queries. Record:

- axis-aligned envelope and volume delta;
- connected-component count, watertightness, and winding consistency;
- median, p95, and maximum sampled surface distance in both directions;
- thread profile, pitch, diameters, handedness, and start/end envelopes.

The validated 24x8 Fusion copy reproduced the source envelope. Its bolt p95 was
0.0295 mm with sampled maxima below 0.129 mm; its nut p95 was approximately
0.0165 mm with sampled maxima below 0.086 mm. Treat these as precedent, not
universal tolerances: set the acceptance threshold from source resolution and
manufacturing intent.
