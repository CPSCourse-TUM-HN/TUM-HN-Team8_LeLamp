# 2. Servo Setup

## Fixed Servo IDs

| Joint | ST3215 ID |
| --- | ---: |
| base_yaw | 1 |
| base_pitch | 2 |
| elbow_pitch | 3 |
| wrist_roll | 4 |
| wrist_pitch | 5 |

## Commands

```bash
cd ~/projects/AILamp
ailamp motor-test
```

Use the upstream LeLamp calibration flow for physical ID writing and calibration:

```bash
cd ~/projects
git clone https://github.com/humancomputerlab/lelamp_runtime.git
cd ~/projects/AILamp
python3 -m pip install -e ../lelamp_runtime
python3 -m lelamp.setup_motors --id ailamp --port /dev/ttyACM0
sudo python3 -m lelamp.calibrate --id ailamp --port /dev/ttyACM0
```

Power the ST3215 chain from the MEAN WELL `GST120A12-P1J`; do not power servos from Jetson USB.
