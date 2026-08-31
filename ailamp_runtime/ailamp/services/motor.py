from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JointDeltaCommand:
    joint: str
    delta_deg: float


DEFAULT_JOINT_LIMITS_DEG: dict[str, tuple[float, float]] = {
    "base_yaw": (-60.0, 60.0),
    "base_pitch": (-55.0, 20.0),
    "elbow_pitch": (20.0, 105.0),
    "wrist_roll": (-45.0, 45.0),
    "wrist_pitch": (-25.0, 35.0),
}


class JointSafetyLimiter:
    def __init__(self, limits: dict[str, tuple[float, float]] | None = None):
        self.limits = limits or DEFAULT_JOINT_LIMITS_DEG

    def apply(self, current_state: dict[str, float], deltas: list[JointDeltaCommand] | tuple[JointDeltaCommand, ...]) -> dict[str, float]:
        target = dict(current_state)
        for command in deltas:
            low, high = self.limits[command.joint]
            key = f"{command.joint}.pos"
            current = target.get(key, 0.0)
            target[key] = max(low, min(high, current + command.delta_deg))
        return target


class RecordingStore:
    def __init__(self, recordings_dir: str | Path):
        self.recordings_dir = Path(recordings_dir)

    def list_names(self) -> list[str]:
        if not self.recordings_dir.exists():
            return []
        return sorted(path.stem for path in self.recordings_dir.glob("*.csv"))

    def load(self, name: str) -> list[dict[str, float]]:
        path = self.recordings_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(path)

        rows: list[dict[str, float]] = []
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append({key: float(value) for key, value in row.items() if key != "timestamp"})
        return rows


class MotorService:
    def __init__(self, port: str, lamp_id: str, recordings_dir: str | Path):
        self.port = port
        self.lamp_id = lamp_id
        self.recordings = RecordingStore(recordings_dir)
        self.limiter = JointSafetyLimiter()
        self._animation_service: Optional[object] = None

    def connect(self) -> None:
        try:
            from lelamp.service.motors.animation_service import AnimationService  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Physical ST3215 playback needs the upstream LeLamp runtime. "
                "Clone https://github.com/humancomputerlab/lelamp_runtime next to AILamp "
                "and install it with `python3 -m pip install -e ../lelamp_runtime` on the Jetson."
            ) from exc

        self._animation_service = AnimationService(port=self.port, lamp_id=self.lamp_id)
        self._animation_service.start()
        logger.info("MotorService connected: port=%s lamp_id=%s", self.port, self.lamp_id)

    def close(self) -> None:
        if self._animation_service is not None:
            self._animation_service.stop()
            self._animation_service = None
            logger.info("MotorService closed")

    def play(self, recording_name: str) -> None:
        if self._animation_service is None:
            raise RuntimeError("MotorService is not connected")
        self._animation_service.dispatch("play", recording_name)

    def apply_joint_deltas(self, deltas: list[JointDeltaCommand] | tuple[JointDeltaCommand, ...]) -> dict[str, float]:
        if self._animation_service is None:
            raise RuntimeError("MotorService is not connected")
        if not deltas:
            return {}

        current_state = getattr(self._animation_service, "_current_state", None)
        if current_state is None:
            current_state = self._initial_idle_state()
        target = self.limiter.apply(current_state, deltas)

        robot = getattr(self._animation_service, "robot", None)
        if robot is None:
            raise RuntimeError("MotorService robot is not connected")

        # Stop any current recording so this single-frame tracking command is not immediately overwritten.
        setattr(self._animation_service, "_current_recording", None)
        setattr(self._animation_service, "_current_actions", [])
        setattr(self._animation_service, "_interpolation_frames", 0)
        robot.send_action(target)
        setattr(self._animation_service, "_current_state", target.copy())
        return target

    def _initial_idle_state(self) -> dict[str, float]:
        rows = self.recordings.load("idle")
        if not rows:
            return {}
        return rows[0]
