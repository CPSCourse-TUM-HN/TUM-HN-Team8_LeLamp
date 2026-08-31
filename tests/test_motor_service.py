import builtins

import pytest

from ailamp.services.motor import JointDeltaCommand, JointSafetyLimiter, MotorService


def test_motor_service_reports_missing_upstream_runtime(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "lelamp.service.motors.animation_service":
            raise ModuleNotFoundError(name)
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    service = MotorService("/dev/null", "ailamp", "ailamp_runtime/ailamp/recordings")

    with pytest.raises(RuntimeError, match="upstream LeLamp runtime"):
        service.connect()


def test_joint_safety_limiter_clips_delta_targets():
    limiter = JointSafetyLimiter({"base_yaw": (-10.0, 10.0), "wrist_pitch": (-5.0, 5.0)})

    target = limiter.apply(
        {"base_yaw.pos": 9.0, "wrist_pitch.pos": -4.0},
        [JointDeltaCommand("base_yaw", 5.0), JointDeltaCommand("wrist_pitch", -5.0)],
    )

    assert target["base_yaw.pos"] == 10.0
    assert target["wrist_pitch.pos"] == -5.0
