"""Pluggable motor backends — LeLamp (physical ST3215 bus) and MuJoCo (simulation)."""
from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

from ailamp.paths import resolve_project_path
from ailamp.services.motor import JointDeltaCommand, JointSafetyLimiter, RecordingStore


logger = logging.getLogger(__name__)


@runtime_checkable
class MotorBackend(Protocol):
    """Common contract for any device that can play recordings and accept joint deltas.

    Implementations must be idempotent on close() so callers don't worry about double-shutdown.
    """

    def connect(self) -> None: ...
    def close(self) -> None: ...
    def play(self, recording_name: str) -> None: ...
    def apply_joint_deltas(
        self, deltas: Iterable[JointDeltaCommand]
    ) -> dict[str, float]: ...


# ---------- LeLamp (physical) backend ----------------------------------------


class LeLampMotorBackend:
    """Drives the real ST3215 bus through the lelamp_runtime AnimationService.

    Kept compatible with the original behavior of `MotorService`: lazy import of the
    upstream lib, reaches into private `_animation_service` state to interrupt a playing
    recording when single-frame tracking arrives. That hack is documented as fragile in
    docs/ and is the main reason for keeping this implementation isolated.
    """

    def __init__(self, port: str, lamp_id: str, recordings_dir: str | Path):
        self.port = port
        self.lamp_id = lamp_id
        self.recordings = RecordingStore(recordings_dir)
        self.limiter = JointSafetyLimiter()
        self._animation_service: object | None = None

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
        logger.info("LeLampMotorBackend connected: port=%s lamp_id=%s", self.port, self.lamp_id)

    def close(self) -> None:
        if self._animation_service is not None:
            self._animation_service.stop()
            self._animation_service = None
            logger.info("LeLampMotorBackend closed")

    def play(self, recording_name: str) -> None:
        if self._animation_service is None:
            raise RuntimeError("LeLampMotorBackend is not connected")
        self._animation_service.dispatch("play", recording_name)

    def apply_joint_deltas(
        self, deltas: Iterable[JointDeltaCommand]
    ) -> dict[str, float]:
        if self._animation_service is None:
            raise RuntimeError("LeLampMotorBackend is not connected")
        deltas_t = tuple(deltas)
        if not deltas_t:
            return {}

        current_state = getattr(self._animation_service, "_current_state", None)
        if current_state is None:
            current_state = self._initial_idle_state()
        target = self.limiter.apply(current_state, deltas_t)

        robot = getattr(self._animation_service, "robot", None)
        if robot is None:
            raise RuntimeError("LeLampMotorBackend robot is not connected")

        # Interrupt any ongoing recording so this single-frame tracking command lands.
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


# ---------- MuJoCo backend ---------------------------------------------------


_CSV_TO_ACTUATOR: dict[str, str] = {
    "base_pitch.pos": "2",
    "base_yaw.pos": "1",
    "elbow_pitch.pos": "3",
    "wrist_roll.pos": "4",
    "wrist_pitch.pos": "5",
}
_JOINT_NAME_TO_CSV: dict[str, str] = {
    "base_yaw": "base_yaw.pos",
    "base_pitch": "base_pitch.pos",
    "elbow_pitch": "elbow_pitch.pos",
    "wrist_roll": "wrist_roll.pos",
    "wrist_pitch": "wrist_pitch.pos",
}


class MujocoMotorBackend:
    """Drives a MuJoCo model in place of the real bus — for sim + CI.

    Accepts an already-loaded `MujocoRunner` so the same model can be reused across
    services. play(recording) replays the CSV; apply_joint_deltas() applies a single
    instantaneous control change (and forwards the sim).
    """

    def __init__(self, runner: object, recordings_dir: str | Path):
        # `runner` is intentionally typed as object so importing this module doesn't
        # require mujoco. The real type is ailamp.simulation.mujoco_runner.MujocoRunner.
        self.runner = runner
        self.recordings_dir = Path(recordings_dir)
        self.limiter = JointSafetyLimiter()
        self._current_state: dict[str, float] = {}
        self._connected = False

    def connect(self) -> None:
        load = getattr(self.runner, "load", None)
        if callable(load):
            load()
        self._connected = True
        logger.info("MujocoMotorBackend connected")

    def close(self) -> None:
        self._connected = False
        logger.info("MujocoMotorBackend closed")

    def play(self, recording_name: str) -> None:
        if not self._connected:
            raise RuntimeError("MujocoMotorBackend is not connected")
        frames = self.runner.replay_recording(recording_name, self.recordings_dir)
        logger.debug("MujocoMotorBackend played %s (%d frames)", recording_name, frames)

    def apply_joint_deltas(
        self, deltas: Iterable[JointDeltaCommand]
    ) -> dict[str, float]:
        if not self._connected:
            raise RuntimeError("MujocoMotorBackend is not connected")
        deltas_t = tuple(deltas)
        if not deltas_t:
            return dict(self._current_state)

        target = self.limiter.apply(self._current_state, deltas_t)
        import mujoco  # type: ignore  # local import: only needed when actually applying.

        model = self.runner.model
        data = self.runner.data
        for joint_name, csv_name in _JOINT_NAME_TO_CSV.items():
            value_deg = target.get(csv_name)
            if value_deg is None:
                continue
            actuator_name = _CSV_TO_ACTUATOR[csv_name]
            actuator_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name)
            if actuator_id >= 0:
                data.ctrl[actuator_id] = math.radians(value_deg)
        mujoco.mj_forward(model, data)
        self._current_state = dict(target)
        return target


# ---------- Factory ----------------------------------------------------------


def create_motor_backend(
    config,
    *,
    backend_name: str | None = None,
    mujoco_runner: object | None = None,
) -> MotorBackend:
    """Pick a MotorBackend based on config or explicit override.

    - 'lelamp' (default): drives real ST3215 bus through upstream lelamp_runtime
    - 'mujoco': drives the MuJoCo sim — requires a `mujoco_runner` instance
    """
    selected = (backend_name or getattr(getattr(config, "motors", None), "backend", None) or "lelamp").lower()
    recordings_dir = resolve_project_path(config.simulation.recordings_dir)

    if selected == "mujoco":
        if mujoco_runner is None:
            raise ValueError("'mujoco' backend requires a mujoco_runner argument")
        return MujocoMotorBackend(mujoco_runner, recordings_dir)
    if selected == "lelamp":
        return LeLampMotorBackend(
            port=config.motors.port,
            lamp_id=config.system.project_name.lower(),
            recordings_dir=recordings_dir,
        )
    raise ValueError(f"unknown motor backend: {selected!r}")
