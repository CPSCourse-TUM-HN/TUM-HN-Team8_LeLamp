"""Unit tests for VisionRuntime supervised step — transient retry + graceful degradation."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ailamp.models import VisionEvent, VisionEventType
from ailamp.services.vision_runtime import VisionLoopResult, VisionRuntime


@pytest.fixture
def supervised_runtime(tmp_path) -> VisionRuntime:
    """Build a VisionRuntime instance with all heavy deps stubbed so we can poke step()."""
    obj = VisionRuntime.__new__(VisionRuntime)
    obj.config = MagicMock()
    obj.backend = "local_yolo"
    obj.camera = MagicMock()
    obj.detector = MagicMock()
    obj.pose_detector = None
    obj.api_vision = None
    obj.behavior = MagicMock()
    obj.decision_service = MagicMock()
    obj.state_store = MagicMock()
    obj.state_store.path = tmp_path / "state.json"
    obj.led_service = None
    obj.motor_service = None
    obj.clock = lambda: 0.0
    obj._frame_index = 0
    obj._last_applied_event = None
    obj._last_applied_time = -1_000_000.0
    obj._last_seen_person = False
    obj._retry_delays_s = (0.0, 0.0, 0.0)  # zero-delay retries for fast tests
    obj.errors_total = 0
    obj.last_error = None
    return obj


def test_step_retries_on_transient_oserror_then_succeeds(supervised_runtime: VisionRuntime) -> None:
    rt = supervised_runtime
    # Camera.read fails twice with OSError, then returns a frame on the 3rd try.
    rt.camera.read.side_effect = [OSError("usb hiccup"), OSError("usb hiccup"), None]
    rt.detector.detect_person.return_value = None  # No person → NO_PERSON event.
    rt.decision_service.decide.return_value = MagicMock(
        event=VisionEvent(VisionEventType.NO_PERSON),
        motion="idle", rgb=(0, 0, 0), joint_deltas=(), reason="x", semantic_reason="",
    )

    result = rt.step()

    assert isinstance(result, VisionLoopResult)
    assert rt.errors_total == 2
    assert rt.last_error is not None
    assert "OSError" in rt.last_error
    assert rt.camera.read.call_count == 3


def test_step_gives_up_after_all_retries_and_emits_degraded_snapshot(
    supervised_runtime: VisionRuntime,
) -> None:
    rt = supervised_runtime
    # All attempts (1 + 3 retries = 4 tries) fail.
    rt.camera.read.side_effect = OSError("usb dead")

    result = rt.step()

    assert isinstance(result, VisionLoopResult)
    assert result.snapshot.event.event_type == VisionEventType.NO_PERSON
    assert result.snapshot.event.semantic_reason.startswith("step_error:")
    assert "OSError" in result.snapshot.event.semantic_reason
    assert result.applied is False
    assert rt.errors_total == 4  # 1 initial + 3 retries
    assert rt.camera.read.call_count == 4
    # The state store should still be updated so monitoring can see degraded health.
    rt.state_store.write.assert_called()


def test_step_does_not_retry_on_non_transient_error(supervised_runtime: VisionRuntime) -> None:
    rt = supervised_runtime
    rt.camera.read.side_effect = ValueError("programmer mistake")

    with pytest.raises(ValueError):
        rt.step()

    assert rt.camera.read.call_count == 1  # No retry for non-transient class.
    assert rt.errors_total == 0


def test_step_increments_frame_index_even_on_degraded_path(supervised_runtime: VisionRuntime) -> None:
    rt = supervised_runtime
    rt.camera.read.side_effect = OSError("dead")

    rt.step()
    rt.step()

    assert rt._frame_index == 2
