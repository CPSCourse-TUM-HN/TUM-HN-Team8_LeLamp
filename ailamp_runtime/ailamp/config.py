from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib

from ailamp.paths import project_root


@dataclass(frozen=True)
class SystemConfig:
    project_name: str
    platform: str


@dataclass(frozen=True)
class ControllerConfig:
    model: str
    mpn: str
    storage: str
    system_card: str


@dataclass(frozen=True)
class MotorConfig:
    port: str
    driver_model: str
    servo_model: str
    servo_quantity: int
    fps: int
    ids: dict[str, int]


@dataclass(frozen=True)
class LEDConfig:
    port: str
    controller: str
    panel: str
    count: int
    baudrate: int
    brightness: int
    power_supply: str
    logic_level_shifter: str


@dataclass(frozen=True)
class PowerConfig:
    servo_supply: str
    led_supply: str
    emergency_switch: str
    barrel_adapter: str
    power_connector: str
    power_wire_red: str
    power_wire_black: str
    signal_wire: str


@dataclass(frozen=True)
class BOMItem:
    part: str
    quantity: str


@dataclass(frozen=True)
class CameraConfig:
    model: str
    device: int
    device_path: str
    width: int
    height: int
    fps: int
    pixel_format: str


@dataclass(frozen=True)
class VisionConfig:
    backend: str
    model: str
    pose_model: str
    pose_enabled: bool
    api_enabled: bool
    api_model: str
    api_interval_s: float
    api_image_max_px: int
    api_timeout_s: float
    api_event_ttl_s: float
    confidence: float
    left_threshold: float
    right_threshold: float
    close_area_ratio: float
    far_area_ratio: float
    far_depth_m: float


@dataclass(frozen=True)
class AudioConfig:
    input_model: str
    speaker_model: str
    input_device: str
    output_device: str


@dataclass(frozen=True)
class VoiceConfig:
    provider: str
    transport: str
    enabled: bool


@dataclass(frozen=True)
class RuntimeConfig:
    vision_state_file: str
    vision_interval_s: float
    action_cooldown_s: float


@dataclass(frozen=True)
class BirthdayConfig:
    enabled: bool
    month: int
    day: int
    message: str
    motion: str
    rgb: tuple[int, int, int]
    state_file: str
    speech_command: str


@dataclass(frozen=True)
class SimulationConfig:
    model_path: str
    recordings_dir: str
    lock_freejoint: bool


@dataclass(frozen=True)
class BehaviorEntry:
    """One row of the [behavior_map] config: motion CSV name + LED RGB."""
    motion: str
    rgb: tuple[int, int, int]


@dataclass(frozen=True)
class HardwareConfig:
    system: SystemConfig
    controller: ControllerConfig
    power: PowerConfig
    motors: MotorConfig
    led: LEDConfig
    camera: CameraConfig
    vision: VisionConfig
    audio: AudioConfig
    voice: VoiceConfig
    runtime: RuntimeConfig
    birthday: BirthdayConfig
    simulation: SimulationConfig
    hardware_bom: dict[str, BOMItem]
    behavior_map: dict[str, BehaviorEntry] | None = None


def _resolve_config_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return project_root() / candidate


def load_hardware_config(path: str | Path) -> HardwareConfig:
    config_path = _resolve_config_path(path)
    with config_path.open("rb") as handle:
        raw: dict[str, Any] = tomllib.load(handle)

    birthday_raw = raw["birthday"]
    vision_raw = {
        "backend": "local_yolo",
        "api_enabled": False,
        "api_model": "gpt-4.1-mini",
        "api_interval_s": 1.0,
        "api_image_max_px": 512,
        "api_timeout_s": 10.0,
        "api_event_ttl_s": 2.0,
    }
    vision_raw.update(raw["vision"])

    behavior_map_raw = raw.get("behavior_map") or {}
    behavior_map = {
        event_key: BehaviorEntry(motion=str(entry["motion"]), rgb=tuple(int(c) for c in entry["rgb"]))
        for event_key, entry in behavior_map_raw.items()
    } or None

    return HardwareConfig(
        system=SystemConfig(**raw["system"]),
        controller=ControllerConfig(**raw["controller"]),
        power=PowerConfig(**raw["power"]),
        motors=MotorConfig(**raw["motors"]),
        led=LEDConfig(**raw["led"]),
        camera=CameraConfig(**raw["camera"]),
        vision=VisionConfig(**vision_raw),
        audio=AudioConfig(**raw["audio"]),
        voice=VoiceConfig(**raw["voice"]),
        runtime=RuntimeConfig(**raw["runtime"]),
        birthday=BirthdayConfig(
            enabled=birthday_raw["enabled"],
            month=birthday_raw["month"],
            day=birthday_raw["day"],
            message=birthday_raw["message"],
            motion=birthday_raw["motion"],
            rgb=tuple(birthday_raw["rgb"]),
            state_file=birthday_raw["state_file"],
            speech_command=birthday_raw["speech_command"],
        ),
        simulation=SimulationConfig(**raw["simulation"]),
        hardware_bom={key: BOMItem(**value) for key, value in raw["hardware_bom"].items()},
        behavior_map=behavior_map,
    )
