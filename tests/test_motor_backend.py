"""Unit tests for the MotorBackend Protocol + create_motor_backend factory."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ailamp.services.motor import JointDeltaCommand
from ailamp.services.motor_backend import (
    LeLampMotorBackend,
    MotorBackend,
    MujocoMotorBackend,
    create_motor_backend,
)


def test_lelamp_backend_satisfies_protocol() -> None:
    backend = LeLampMotorBackend(port="/dev/null", lamp_id="ailamp", recordings_dir="/tmp")
    assert isinstance(backend, MotorBackend)


def test_mujoco_backend_satisfies_protocol() -> None:
    backend = MujocoMotorBackend(runner=MagicMock(), recordings_dir="/tmp")
    assert isinstance(backend, MotorBackend)


def test_factory_returns_lelamp_by_default() -> None:
    config = MagicMock()
    config.motors.port = "/dev/null"
    config.motors.backend = None
    config.system.project_name = "AILamp"
    config.simulation.recordings_dir = "ailamp_runtime/ailamp/recordings"

    backend = create_motor_backend(config)

    assert isinstance(backend, LeLampMotorBackend)
    assert backend.port == "/dev/null"
    assert backend.lamp_id == "ailamp"


def test_factory_returns_mujoco_when_requested() -> None:
    config = MagicMock()
    config.simulation.recordings_dir = "/tmp/recs"

    backend = create_motor_backend(config, backend_name="mujoco", mujoco_runner=MagicMock())

    assert isinstance(backend, MujocoMotorBackend)


def test_factory_rejects_mujoco_without_runner() -> None:
    config = MagicMock()
    config.simulation.recordings_dir = "/tmp/recs"

    with pytest.raises(ValueError, match="mujoco_runner"):
        create_motor_backend(config, backend_name="mujoco")


def test_factory_rejects_unknown_backend() -> None:
    config = MagicMock()
    config.simulation.recordings_dir = "/tmp/recs"

    with pytest.raises(ValueError, match="unknown motor backend"):
        create_motor_backend(config, backend_name="ros2")


# ---------- MujocoMotorBackend behavior --------------------------------------


def test_mujoco_backend_play_routes_through_runner_replay() -> None:
    runner = MagicMock()
    runner.replay_recording.return_value = 30
    backend = MujocoMotorBackend(runner=runner, recordings_dir="/tmp/recs")
    backend.connect()
    backend.play("wake_up")
    runner.replay_recording.assert_called_once()
    args, _ = runner.replay_recording.call_args
    assert args[0] == "wake_up"


def test_mujoco_backend_apply_joint_deltas_with_empty_input_is_noop() -> None:
    runner = MagicMock()
    backend = MujocoMotorBackend(runner=runner, recordings_dir="/tmp/recs")
    backend.connect()
    result = backend.apply_joint_deltas([])
    assert result == {}


def test_mujoco_backend_apply_requires_connect() -> None:
    runner = MagicMock()
    backend = MujocoMotorBackend(runner=runner, recordings_dir="/tmp/recs")
    with pytest.raises(RuntimeError, match="not connected"):
        backend.apply_joint_deltas([JointDeltaCommand("base_yaw", 1.0)])


def test_mujoco_backend_close_is_idempotent() -> None:
    runner = MagicMock()
    backend = MujocoMotorBackend(runner=runner, recordings_dir="/tmp/recs")
    backend.connect()
    backend.close()
    backend.close()  # Calling twice must not raise.
