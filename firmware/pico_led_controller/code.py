import sys
import board
import neopixel


LED_PIN = board.GP0
LED_COUNT = 64
BRIGHTNESS = 0.5

pixels = neopixel.NeoPixel(LED_PIN, LED_COUNT, brightness=BRIGHTNESS, auto_write=False)


def ok(message="OK"):
    print(message)


def parse_channel(value):
    channel = int(value)
    if channel < 0 or channel > 255:
        raise ValueError("channel out of range")
    return channel


def solid(parts):
    if len(parts) != 4:
        raise ValueError("SOLID requires r g b")
    color = (parse_channel(parts[1]), parse_channel(parts[2]), parse_channel(parts[3]))
    pixels.fill(color)
    pixels.show()
    ok()


def brightness(parts):
    global BRIGHTNESS
    if len(parts) != 2:
        raise ValueError("BRIGHTNESS requires value")
    value = parse_channel(parts[1])
    BRIGHTNESS = value / 255.0
    pixels.brightness = BRIGHTNESS
    pixels.show()
    ok()


def clear():
    pixels.fill((0, 0, 0))
    pixels.show()
    ok()


def paint_pixels(line):
    payload = line[len("PIXELS ") :].strip()
    colors = []
    if payload:
        for item in payload.split(";"):
            channels = item.split(",")
            if len(channels) != 3:
                raise ValueError("pixel must be r,g,b")
            colors.append(tuple(parse_channel(channel) for channel in channels))
    if len(colors) > LED_COUNT:
        raise ValueError("too many pixels")
    for index in range(LED_COUNT):
        pixels[index] = colors[index] if index < len(colors) else (0, 0, 0)
    pixels.show()
    ok()


while True:
    line = sys.stdin.readline()
    if not line:
        continue
    line = line.strip()
    if not line:
        continue
    try:
        parts = line.split()
        command = parts[0].upper()
        if command == "PING":
            ok("PONG")
        elif command == "CLEAR":
            clear()
        elif command == "SOLID":
            solid(parts)
        elif command == "BRIGHTNESS":
            brightness(parts)
        elif command == "PIXELS":
            paint_pixels(line)
        else:
            raise ValueError("unknown command")
    except Exception as exc:
        print("ERR " + str(exc))

