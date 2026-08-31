import pytest

from ailamp.services.led_serial import LEDSerialProtocol


def test_led_protocol_encodes_required_commands():
    protocol = LEDSerialProtocol(led_count=64)

    assert protocol.ping() == b"PING\n"
    assert protocol.clear() == b"CLEAR\n"
    assert protocol.solid(255, 180, 80) == b"SOLID 255 180 80\n"
    assert protocol.brightness(128) == b"BRIGHTNESS 128\n"
    assert protocol.pixels([(255, 0, 0), (0, 255, 0)]) == b"PIXELS 255,0,0;0,255,0\n"


def test_led_protocol_rejects_invalid_values():
    protocol = LEDSerialProtocol(led_count=64)

    with pytest.raises(ValueError):
        protocol.solid(256, 0, 0)
    with pytest.raises(ValueError):
        protocol.brightness(-1)
    with pytest.raises(ValueError):
        protocol.pixels([(0, 0, 0)] * 65)

