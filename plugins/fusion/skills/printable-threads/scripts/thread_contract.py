#!/usr/bin/env python3
"""Calculate BOSL2-compatible printable-thread radii and seated phase."""

from __future__ import annotations

import argparse
import json
import math


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--major-diameter", type=float, default=24.0)
    result.add_argument("--pitch", type=float, default=8.0)
    result.add_argument("--depth", type=float, default=3.0)
    result.add_argument("--slop", type=float, default=0.10)
    result.add_argument("--segments", type=int, default=96)
    result.add_argument("--male-center-z-at-zero", type=float)
    result.add_argument("--female-local-center-z-at-zero", type=float)
    result.add_argument("--seat-z", type=float)
    result.add_argument("--seat-angle", type=float)
    result.add_argument("--angle", type=float)
    result.add_argument("--pretty", action="store_true")
    return result


def require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise SystemExit(f"{name} must be positive")


def main() -> None:
    args = parser().parse_args()
    require_positive("major diameter", args.major_diameter)
    require_positive("pitch", args.pitch)
    require_positive("depth", args.depth)
    if args.slop < 0:
        raise SystemExit("slop cannot be negative")
    if args.segments < 3:
        raise SystemExit("segments must be at least 3")

    external_major = args.major_diameter / 2.0
    external_minor = external_major - args.depth
    if external_minor <= 0:
        raise SystemExit("depth must be smaller than the nominal major radius")
    internal_major = (
        external_major / math.cos(math.pi / args.segments) + 2.0 * args.slop
    )
    internal_minor = internal_major - args.depth

    output: dict[str, object] = {
        "geometry": {
            "major_diameter_mm": args.major_diameter,
            "pitch_mm": args.pitch,
            "depth_mm": args.depth,
            "slop_mm": args.slop,
            "segments": args.segments,
            "external_major_radius_mm": external_major,
            "external_minor_radius_mm": external_minor,
            "internal_major_radius_mm": internal_major,
            "internal_minor_radius_mm": internal_minor,
            "radial_clearance_mm": internal_major - external_major,
        },
        "motion": {
            "convention": "right-handed, single-start; verify sign after axis changes",
            "relation": "z = seat_z + pitch * (angle - seat_angle) / 360",
            "delta_relation": "dz = pitch * dangle / 360",
        },
    }

    phase_inputs = (
        args.male_center_z_at_zero,
        args.female_local_center_z_at_zero,
        args.seat_z,
    )
    if any(value is not None for value in phase_inputs):
        if not all(value is not None for value in phase_inputs):
            raise SystemExit(
                "phase derivation requires --male-center-z-at-zero, "
                "--female-local-center-z-at-zero, and --seat-z together"
            )
        axial_phase = (
            args.seat_z
            + args.female_local_center_z_at_zero
            - args.male_center_z_at_zero
            - args.pitch / 2.0
        )
        derived_seat_angle = (360.0 * axial_phase / args.pitch) % 360.0
        output["phase"] = {
            "axial_phase_mm": axial_phase,
            "seat_angle_deg": derived_seat_angle,
            "ridge_center_separation_mm_mod_pitch": args.pitch / 2.0,
        }
    else:
        derived_seat_angle = None

    seat_angle = args.seat_angle
    if seat_angle is None:
        seat_angle = derived_seat_angle
    if args.angle is not None:
        if args.seat_z is None or seat_angle is None:
            raise SystemExit(
                "--angle requires --seat-z and either --seat-angle or all phase inputs"
            )
        output["pose"] = {
            "angle_deg": args.angle,
            "z_mm": args.seat_z
            + args.pitch * (args.angle - seat_angle) / 360.0,
        }

    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
