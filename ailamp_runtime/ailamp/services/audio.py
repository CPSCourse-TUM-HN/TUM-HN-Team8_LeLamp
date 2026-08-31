from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioDeviceReport:
    input_model: str
    speaker_model: str
    devices: list[str]


class AudioService:
    def __init__(self, input_model: str, speaker_model: str):
        self.input_model = input_model
        self.speaker_model = speaker_model

    def probe(self) -> AudioDeviceReport:
        import sounddevice as sd  # type: ignore

        devices = [str(device) for device in sd.query_devices()]
        return AudioDeviceReport(self.input_model, self.speaker_model, devices)

