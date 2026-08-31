# 0. Prerequisites

## Hardware BOM

Default Orin Nano Super profile:

| Subsystem | Exact part | Qty |
| --- | --- | ---: |
| Main controller | NVIDIA Jetson Orin Nano Super Developer Kit, MPN `945-13766-0000-000` | 1 |
| Storage | Samsung 980 NVMe M.2 2280 500GB, `MZ-V8V500B` | 1 |
| System card | SanDisk Ultra microSDXC 64GB UHS-I | 1 |
| Servo | Waveshare ST3215 Servo, 30kg.cm @ 12V, SKU `22414` | 5 |
| Servo driver | Waveshare Servo Driver with ESP32, SKU `21593` | 1 |
| Servo power | MEAN WELL `GST120A12-P1J`, 12V 10A 120W | 1 |
| LED controller | Raspberry Pi Pico WH | 1 |
| LED panel | Adafruit NeoPixel NeoMatrix 8x8, 64 RGB LED, Product ID `1487` | 1 |
| LED power | MEAN WELL `GST60A05-P1J`, 5V 6A 30W | 1 |
| Logic level shifter | TXS0108E 8-Channel Logic Level Converter Module | 1 |
| LED resistor | 330 ohm 1/4W resistor | 5 |
| LED capacitor | 1000 uF 6.3V or 10V electrolytic capacitor | 2 |
| Camera | Arducam `UB0234`, 2MP OV2710 USB2.0 UVC Camera, 1080p, M12 lens | 1 |
| Audio input | Seeed Studio ReSpeaker XVF3800 USB 4-Mic Array with Case, Product `6490` | 1 |
| Speaker | Seeed Studio Mono Enclosed Speaker, 4 ohm 5W | 1 |
| Emergency switch | 12V 10A DC inline switch / emergency stop switch | 1 |
| USB cable | USB-A to USB-C data cable, 0.5m | 1 |
| USB cable | USB-A to Micro-USB data cable, 0.5m | 1 |
| USB extension | USB-A extension cable, 0.3m or 0.5m | 1 |
| Servo extension | ST / SC serial bus servo extension cable | 5 |
| Power terminal | 5.5mm x 2.1mm DC barrel screw terminal adapter | 4 |
| Power connector | WAGO 221-413 lever connector | 10 |
| Power wire | 22AWG red silicone wire | 2m |
| Power wire | 22AWG black silicone wire | 2m |
| Signal wire | 24AWG silicone wire | 2m |

Jetson Nano 4GB API-hybrid profile changes:

| Subsystem | Exact part | Qty |
| --- | --- | ---: |
| Main controller | NVIDIA Jetson Nano Developer Kit 4GB, MPN `945-13450-0000-100` | 1 |
| Storage | Not used on the basic Jetson Nano Developer Kit; boot from microSD | 0 |
| System card | SanDisk Ultra microSDXC 64GB UHS-I | 1 |

All servo, LED, camera, audio, power, cable, connector, and wire items stay the same as the default BOM.

## Power Domains

```text
Jetson power -> Jetson only
GST120A12-P1J -> Waveshare Servo Driver with ESP32 -> 5x ST3215
GST60A05-P1J -> Adafruit NeoPixel NeoMatrix 8x8
Jetson USB -> Pico WH control only
```

## Default Ports

```text
/dev/ttyACM0 -> Waveshare Servo Driver with ESP32
/dev/ttyACM1 -> Raspberry Pi Pico WH
/dev/video0  -> Arducam UB0234
USB audio    -> ReSpeaker XVF3800
```
