# 1. 3D Print

AILamp uses the original LeLamp print files in `3D/`.

## CAD Source

Keep the upstream LeLamp mechanical workflow:

- Primary CAD software: OnShape.
- Upstream CAD reference: `https://cad.onshape.com/documents/16c9706360b5ad34f9c8db49/w/2edfa54c83253c120fbc9e58/e/a7196194821d9cfe2842a44a`
- Upstream assembly reference: `https://cad.onshape.com/documents/16c9706360b5ad34f9c8db49/w/2edfa54c83253c120fbc9e58/e/a35eec618cd78ea5d74bf01b`
- Export print files as `.3mf`.
- Export simulation meshes as `.stl` when MuJoCo assets need updating.

Do not switch the primary mechanical workflow to Blender, SolidWorks, Fusion 360, or FreeCAD for AILamp v1.

## Print Counts

| File | Qty |
| --- | ---: |
| `LampBase.3mf` | 1 |
| `LampBase - Cover.3mf` | 1 |
| `LampArm (Base-Elbow).3mf` | 1 |
| `LampArm (Elbow-Wrist).3mf` | 1 |
| `LampArm (Pitch).3mf` | 2 |
| `LampHead.3mf` | 1 |
| `LampHead - Diffuser.3mf` | 1 |

## AILamp Replacement Base Kit

AILamp v1 keeps the original seven LeLamp `.3mf` files unchanged for reference. For the Jetson Nano hidden-electronics build, do not print the original `LampBase.3mf` and `LampBase - Cover.3mf` as final parts. Print the AILamp replacement base shell and cover instead.

Fit check: the selected Jetson Nano 4GB developer kit is treated as a 100 x 80 x 29 mm board assembly, Raspberry Pi Pico WH as 51 x 21 mm, and the Waveshare Servo Driver with ESP32 as 65 x 30 mm. The original LeLamp `LampBase.3mf` outer envelope is about 160 x 190 x 40 mm, so the AILamp base replacement grows the base to 190 x 230 x 48 mm and moves electronics into the base body.

Native rounded geometry: the replacement shell, cover, and arm-link boot are no longer built by scaling the original LampBase mesh or by subtracting strip-shaped boxes from a rectangular block. They are constructed directly from CCW rounded-rectangle polygons that are then extruded with proper outer/inner walls and annular caps (24 segments per corner). All outer and inner corners are true triangulated arcs rather than staircase approximations, the recessed perimeter lip and the raised arm-mount collar share that smoothness, and the resulting STL files are about half the size of the previous voxel-subtraction output (shell drops from ~2.5 MB to ~0.9 MB; cover from ~8.5 MB to ~0.6 MB).

| Adapter file | Qty | Purpose |
| --- | ---: | --- |
| `AILamp_LampBase_Electronics_Shell.3mf` | 1 | Replacement LampBase shell for Jetson Nano, Pico WH, ST3215 driver, wiring, and airflow |
| `AILamp_LampBase_Electronics_Cover.3mf` | 1 | Replacement LampBase cover with raised arm-mount collar, screw holes, and service vents |
| `AILamp_Base_Arm_Link_Boot.3mf` | 1 | Moving link boot between the fixed cover collar and the arm root |
| `AILamp_Cable_Clip_6mm.3mf` | 2-4 | USB and signal cable routing |
| `AILamp_Cable_Clip_10mm.3mf` | 2-4 | Power and servo cable routing |
| `AILamp_Jetson_Nano_Base_Tray.3mf` | optional | Bench-fit tray for testing the Jetson outside the lamp |
| `AILamp_Electronics_Side_Deck.3mf` | optional | Bench-fit side deck for testing the Pico WH and ST3215 driver outside the lamp |

Each listed adapter `.3mf` has a matching `.stl` export with the same base name for slicer compatibility and visual checks.

Replacement base geometry:

- Replacement shell: 190 x 230 x 48 mm.
- Replacement cover plate: 190 x 230 x 8 mm, with a 22 mm total height including the raised base-arm mount collar.
- Lower service pass-through: 72 x 86 mm.
- Raised arm-mount collar: 92 x 98 x 18 mm, with a 58 x 64 mm loose center clearance around the base servo/arm root.
- Arm-mount collar screw positions: x +/-36 mm, y +/-40 mm.
- Moving base-arm link boot: 74 x 74 x 42 mm, with a 42 x 48 mm loose center clearance. In MuJoCo this boot is attached at the original LeLamp base-cover transform so it follows the arm root instead of the fixed electronics shell.
- Original base reference footprint: 160 x 190 mm, used to scale the replacement shell proportions and preserve the forward-biased base layout.
- Cover-to-shell screw positions: four corner holes at x +/-82 mm, y -88 mm and y +118 mm. The asymmetric Y positions follow the original LeLamp base relationship to the arm origin.
- Internal Jetson standoffs: 84 x 64 mm pattern, with 3.4 mm loose screw clearance.
- Internal Waveshare driver standoffs: 58 x 23 mm pattern, matching the board mounting-hole spacing.

Do not print or install lamp-head adapter parts for the current replacement-base revision. Camera, LED, and audio hardware should be routed as wiring/devices first; mechanical mounts for those parts need a separate fit pass after the Jetson Nano base layout is confirmed.

Fit rule: print the first adapter pass slightly loose. PCB pockets include 1.5 mm clearance per side, cable exits include at least 2.5 mm extra width, and retention should use screws, zip ties, or removable straps rather than hard snap-fit pressure.

For the hidden-electronics route, print `AILamp_LampBase_Electronics_Shell.3mf`, `AILamp_LampBase_Electronics_Cover.3mf`, and `AILamp_Base_Arm_Link_Boot.3mf` first at low infill for fit testing. These replace the original LeLamp base and cover in the AILamp build.
