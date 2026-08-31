# AILamp Current 3D Print Files

This package contains the current AILamp print set after the Jetson Nano replacement-base revision.

## Required_3MF

Print these for the current AILamp build:

| File | Qty | Role |
|---|---:|---|
| `AILamp_LampBase_Electronics_Shell.3mf` | 1 | Replacement base shell with cleaner internal Jetson / driver / Pico layout |
| `AILamp_LampBase_Electronics_Cover.3mf` | 1 | Replacement base cover with finer rounded edges and raised arm root collar |
| `AILamp_Base_Arm_Link_Boot.3mf` | 1 | Moving transition boot between the fixed cover collar and the arm root |
| `AILamp_Cable_Clip_6mm.3mf` | 2-4 | Small signal / USB cable clips |
| `AILamp_Cable_Clip_10mm.3mf` | 2-4 | Power / servo cable clips |
| `LampArm (Base-Elbow).3mf` | 1 | Original LeLamp lower arm |
| `LampArm (Elbow-Wrist).3mf` | 1 | Original LeLamp upper arm |
| `LampArm (Pitch).3mf` | 1 | Original LeLamp pitch link |
| `LampHead.3mf` | 1 | Original LeLamp lamp head |
| `LampHead - Diffuser.3mf` | 1 | Original LeLamp diffuser |

Do not print `LampBase.3mf` or `LampBase - Cover.3mf` for the current hidden-electronics build. The AILamp shell and cover replace them.

## Optional_3MF

These are optional fit-test or fallback parts. They are not required when the internal replacement base is used:

| File | Role |
|---|---|
| `AILamp_Jetson_Nano_Base_Tray.3mf` | External Jetson tray for early bench testing |
| `AILamp_Electronics_Side_Deck.3mf` | External Pico / servo-driver deck for early bench testing |

## STL_Exports

The STL exports mirror the AILamp-generated parts and can be used by slicers that do not import 3MF cleanly.

## Print Notes

- Print the replacement shell and cover as a low-infill fit test before a final print.
- Keep the arm-root area loose; do not shrink holes until a physical fit check is done.
- Route USB and power cables before tightening the cover screws.
- The shell, cover, and arm-link boot are now generated from native triangulated rounded geometry (24 corner segments) instead of scaled LampBase voxel approximations. STL/3MF sizes are about half of the previous revision and printed surfaces are visibly smoother along all outer/inner rounded corners.
