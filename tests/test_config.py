from pathlib import Path
import tomllib

from ailamp.config import load_hardware_config


def test_loads_exact_hardware_bom_and_ports():
    config = load_hardware_config(Path("config/hardware.toml"))

    assert config.system.project_name == "AILamp"
    assert config.controller.model == "NVIDIA Jetson Orin Nano Super Developer Kit"
    assert config.controller.mpn == "945-13766-0000-000"
    assert config.motors.port == "/dev/ttyACM0"
    assert config.led.port == "/dev/ttyACM1"
    assert config.camera.device_path == "/dev/video0"
    assert config.motors.ids == {
        "base_yaw": 1,
        "base_pitch": 2,
        "elbow_pitch": 3,
        "wrist_roll": 4,
        "wrist_pitch": 5,
    }
    assert config.led.count == 64
    assert config.power.servo_supply == "MEAN WELL GST120A12-P1J, 12V 10A 120W"
    assert config.led.logic_level_shifter == "TXS0108E 8-Channel Logic Level Converter Module"
    assert config.hardware_bom["power_connector"].quantity == "10"
    assert config.hardware_bom["camera"].part.startswith("Arducam UB0234")
    assert config.birthday.month == 5
    assert config.birthday.day == 8
    assert config.birthday.message == "Happy birthday, Yugu!"
    assert config.birthday.motion == "happy_wiggle"
    assert config.birthday.rgb == (255, 180, 80)
    assert config.runtime.vision_state_file == "outputs/vision_state.json"
    assert config.runtime.vision_interval_s == 0.2
    assert config.runtime.action_cooldown_s == 1.5
    assert config.vision.pose_enabled is True
    assert config.vision.pose_model == "yolov8n-pose.pt"
    assert config.vision.far_area_ratio == 0.02


def test_loads_camera_path_and_pixel_format():
    config = load_hardware_config(Path("config/hardware.toml"))

    assert config.camera.device_path == "/dev/video0"
    assert config.camera.pixel_format == "MJPG"


def test_loads_jetson_nano_api_hybrid_profile():
    config = load_hardware_config(Path("config/hardware.jetson-nano.toml"))

    assert config.controller.model == "NVIDIA Jetson Nano Developer Kit 4GB"
    assert config.controller.mpn == "945-13450-0000-100"
    assert config.camera.width == 640
    assert config.camera.height == 480
    assert config.camera.fps == 15
    assert config.vision.backend == "api_hybrid"
    assert config.vision.pose_enabled is False
    assert config.vision.api_enabled is True
    assert config.vision.api_model == "gpt-4.1-mini"
    assert config.vision.api_interval_s == 1.0
    assert config.vision.api_image_max_px == 512
    assert config.runtime.vision_interval_s == 0.2


def test_hardware_bom_quantities_are_complete():
    from ailamp.hardware_check import EXPECTED_BOM_QUANTITIES

    config = load_hardware_config(Path("config/hardware.toml"))

    assert set(config.hardware_bom) == set(EXPECTED_BOM_QUANTITIES)
    assert {key: item.quantity for key, item in config.hardware_bom.items()} == EXPECTED_BOM_QUANTITIES


def test_nano_extra_includes_voice_and_responses_api_dependencies():
    raw = tomllib.loads(Path("pyproject.toml").read_text())
    nano_deps = raw["project"]["optional-dependencies"]["nano"]

    assert "livekit-plugins-noise-cancellation>=0.2" in nano_deps
    assert "openai>=2.35.0" in nano_deps
