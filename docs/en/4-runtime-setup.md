# 4. Runtime Setup

## Install

```bash
cd ~/projects/AILamp
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[hardware,simulation,voice,test]"
```

Jetson Nano 4GB API-hybrid install:

```bash
cd ~/projects/AILamp
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[nano,test]"
export OPENAI_API_KEY=...
```

Do not install the local YOLO pose stack, MuJoCo, or local large models on the Jetson Nano profile.

## Configure

Edit the active profile config only if Linux assigns different device paths: `config/hardware.toml` for Orin Nano Super, or `config/hardware.jetson-nano.toml` for Jetson Nano 4GB.

```bash
ailamp runtime-check
ailamp hardware-check
ailamp hardware-check --include-devices
ailamp --config config/hardware.jetson-nano.toml runtime-check
ailamp --config config/hardware.jetson-nano.toml runtime-check --include-devices --include-voice
ailamp --config config/hardware.jetson-nano.toml hardware-check
ailamp --config config/hardware.jetson-nano.toml hardware-check --include-devices
```

`runtime-check` validates the Python entrypoint, recordings, Pico firmware file, writable `outputs/`, and `OPENAI_API_KEY` for the Jetson Nano API-hybrid profile. Add `--include-motor-runtime` after installing the upstream LeLamp runtime.

## Pico WH Firmware

Copy `firmware/pico_led_controller/code.py` to the CircuitPython drive on the Pico WH.

Pico WH requirements:

```text
CircuitPython 9.x for Raspberry Pi Pico WH
adafruit-circuitpython-neopixel library in /lib
NeoMatrix data line on GP0
TXS0108E level shifter between Pico GP0 and NeoMatrix DIN
```

Serial protocol:

```text
PING
CLEAR
SOLID r g b
BRIGHTNESS value
PIXELS r,g,b;r,g,b
```

## Jetson Nano Acceptance Flow

Use this order on the Jetson Nano:

```bash
ailamp --config config/hardware.jetson-nano.toml runtime-check
ailamp --config config/hardware.jetson-nano.toml hardware-check --include-devices
ailamp --config config/hardware.jetson-nano.toml camera-test
ailamp --config config/hardware.jetson-nano.toml audio-test
ailamp --config config/hardware.jetson-nano.toml led-test
ailamp --config config/hardware.jetson-nano.toml motor-test
ailamp --config config/hardware.jetson-nano.toml agent-tools-test --event person_right --offset 0.6 --request "follow me"
ailamp --config config/hardware.jetson-nano.toml vision-loop --frames 30
```

Only after those pass:

```bash
ailamp --config config/hardware.jetson-nano.toml vision-loop --with-outputs
ailamp --config config/hardware.jetson-nano.toml agent --with-outputs
```
