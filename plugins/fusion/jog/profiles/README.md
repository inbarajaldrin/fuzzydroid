# Jog profiles — registering a robot

A profile teaches the jog palette how to present one device (an arm, a gripper).
Bundled profiles live here; drop overrides into `~/.config/fuzzydroid/jog_profiles/`
(same `name` wins). Matching is by joint-name fragments, so one profile serves the
standalone robot doc AND any assembly containing it.

## Common fields

```jsonc
{
  "name": "ur5e",            // unique id (user profile with same name overrides)
  "title": "UR5e",           // section heading in the UI
  "kind": "arm",             // "arm" | "gripper"
  "match": {
    "any_of_joints": ["shoulder_pan", "wrist_1"],  // case-insensitive substrings
    "min_matches": 4          // how many must be present in the active doc
  }
}
```

## kind: "arm"

```jsonc
{
  "joints": [                 // ORDER MATTERS — base to flange (used by IK)
    {
      "id": "shoulder_pan_joint",   // model-side (URDF) name
      "fusion_match": "shoulder_pan", // substring locating the Fusion joint
      "label": "Shoulder pan",
      "sign": 1,                    // fusion_rad = sign * model_rad + offset
      "offset_deg": 0.0,
      "min_deg": -360, "max_deg": 360,
      "home_deg": 0
    }
  ],
  "ik": {"type": "ur_analytic", "variant": "ur5e"},  // omit if no solver
  "poses": {"home": [0,0,0,0,0,0]}   // named poses, model-side degrees
}
```

`sign`/`offset_deg` absorb any mismatch between the Fusion rig's joint zero and
the URDF/DH zero — calibrate once per rigging, keep CAD = URDF = palette.

Supported IK: `ur_analytic` with `variant` in ur3e / ur5e / ur10e / ur16e
(closed form, all branches FK-verified, nearest applied). Other arms still get
sliders and poses — just omit `ik`.

## kind: "gripper"

```jsonc
{
  "drive": {
    "fusion_match": "rg2_gripper_joint", // the ONE drive joint (motion links move the rest)
    "sign": -1,                     // fusion_rad = sign * model_rad + offset — the CAD
    "offset_deg": 17.95,            // rig's drive direction/datum may differ from the
                                    // URDF/firmware theta; CALIBRATE by sweeping the drive
                                    // and measuring the finger gap (fit sin curve)
    "open_model_rad": 0.77308,      // extremes in MODEL (URDF/firmware) angles
    "closed_model_rad": -0.452
  },
  "width": {                        // optional width readout/slider
    "model": "rg2_arc",             // raw_mm (Modbus reg 267) = amp*sin(alpha0+theta_model)+raw_offset
    "alpha0_deg": 27.95, "amp_mm": 110.0, "raw_offset_mm": 5.24,
    "tip_offset_mm": 4.6            // width-with-offset (reg 275 / pad gap) = raw - 2*tip_offset
  },
  "passive_matches": ["rg2_l_finger"] // motion-linked joints to hide from the generic list
}
```

Calibration lesson (RG2): never assume the rig drive equals the model theta.
Sweep the drive, measure the physical gap (boolean-safe min distance between
finger bodies), fit `gap = A*sin(a0 - theta)+C` — A recovers the arm length,
and the (sign, offset) drop out. The RG2 rig turned out inverted + re-datumed
(sign -1, +17.95°); after mapping, CAD width matches live firmware readbacks
to 0.1 mm.

## Assemblies

Nothing extra to register: a station doc containing UR5e + RG2 matches both
profiles and the palette shows both sections. Joints inside externally
referenced components are found and driven via assembly-context proxies.
