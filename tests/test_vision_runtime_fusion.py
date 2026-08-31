"""Unit tests for VisionRuntime._choose_event — base/pose fusion + seat-left transition."""
from __future__ import annotations

import pytest

from ailamp.models import VisionEvent, VisionEventType
from ailamp.services.vision_runtime import VisionRuntime


class _StubCamera:
    def open(self) -> None: ...
    def close(self) -> None: ...
    def read(self): ...


class _StubDetector:
    def load(self) -> None: ...


@pytest.fixture
def runtime() -> VisionRuntime:
    # Build a minimal runtime with all collaborators stubbed — only _choose_event under test.
    class _MinimalConfig:
        class vision:
            backend = "local_yolo"
            left_threshold = -0.2
            right_threshold = 0.2
            close_area_ratio = 0.35
            far_area_ratio = 0.02
            pose_enabled = False

        class camera:
            device_path = "/dev/null"
            width = 640
            height = 480
            fps = 30
            pixel_format = "MJPG"

        class runtime:
            vision_state_file = "/tmp/ailamp_test_state.json"
            vision_interval_s = 0.1
            action_cooldown_s = 0.5

    # The real __init__ touches a lot of services — bypass it.
    obj = VisionRuntime.__new__(VisionRuntime)
    obj._last_seen_person = False
    obj._last_applied_event = None
    obj._last_applied_time = -1_000_000.0
    obj._frame_index = 0
    return obj


# ---------- NO_PERSON edge cases ---------------------------------------------


def test_no_person_with_no_prior_history_passes_through(runtime: VisionRuntime) -> None:
    base = VisionEvent(VisionEventType.NO_PERSON, semantic_reason="empty_frame")
    result = runtime._choose_event(base, None)
    assert result.event_type == VisionEventType.NO_PERSON
    assert result.semantic_reason == "empty_frame"
    assert runtime._last_seen_person is False


def test_no_person_after_having_seen_person_emits_seat_left(runtime: VisionRuntime) -> None:
    runtime._last_seen_person = True
    base = VisionEvent(VisionEventType.NO_PERSON, semantic_reason="no_bbox")
    result = runtime._choose_event(base, None)
    assert result.event_type == VisionEventType.PERSON_LEFT_SEAT
    assert result.semantic_reason == "no_bbox"
    assert runtime._last_seen_person is False


def test_no_person_api_error_does_not_emit_seat_left(runtime: VisionRuntime) -> None:
    runtime._last_seen_person = True
    base = VisionEvent(VisionEventType.NO_PERSON, semantic_reason="api_error:timeout")
    result = runtime._choose_event(base, None)
    # API failure should not be mistaken for a person leaving.
    assert result.event_type == VisionEventType.NO_PERSON
    assert runtime._last_seen_person is False


def test_no_person_no_frame_does_not_emit_seat_left(runtime: VisionRuntime) -> None:
    runtime._last_seen_person = True
    base = VisionEvent(VisionEventType.NO_PERSON, semantic_reason="no_frame")
    result = runtime._choose_event(base, None)
    assert result.event_type == VisionEventType.NO_PERSON


# ---------- Base + pose fusion ------------------------------------------------


def test_seeing_person_updates_last_seen_person(runtime: VisionRuntime) -> None:
    assert runtime._last_seen_person is False
    base = VisionEvent(VisionEventType.PERSON_CENTER)
    runtime._choose_event(base, None)
    assert runtime._last_seen_person is True


def test_person_close_dominates_over_any_pose_event(runtime: VisionRuntime) -> None:
    base = VisionEvent(VisionEventType.PERSON_CLOSE, area_ratio=0.5)
    pose = VisionEvent(VisionEventType.GESTURE_UP)
    result = runtime._choose_event(base, pose)
    assert result.event_type == VisionEventType.PERSON_CLOSE


def test_pose_gesture_overrides_neutral_base_event(runtime: VisionRuntime) -> None:
    base = VisionEvent(VisionEventType.PERSON_LEFT, normalized_offset=-0.5)
    pose = VisionEvent(VisionEventType.GESTURE_UP)
    result = runtime._choose_event(base, pose)
    # Pose gesture is more semantically rich than positional event.
    assert result.event_type == VisionEventType.GESTURE_UP


def test_pose_center_does_not_override_positional_base(runtime: VisionRuntime) -> None:
    base = VisionEvent(VisionEventType.PERSON_LEFT, normalized_offset=-0.5)
    pose = VisionEvent(VisionEventType.PERSON_CENTER)
    result = runtime._choose_event(base, pose)
    # PERSON_CENTER from pose is a degenerate fallback — keep base.
    assert result.event_type == VisionEventType.PERSON_LEFT


def test_pose_no_person_does_not_override_positional_base(runtime: VisionRuntime) -> None:
    base = VisionEvent(VisionEventType.PERSON_RIGHT, normalized_offset=0.5)
    pose = VisionEvent(VisionEventType.NO_PERSON)
    result = runtime._choose_event(base, pose)
    assert result.event_type == VisionEventType.PERSON_RIGHT


def test_pose_none_uses_base(runtime: VisionRuntime) -> None:
    base = VisionEvent(VisionEventType.PERSON_LEFT, normalized_offset=-0.5)
    result = runtime._choose_event(base, None)
    assert result.event_type == VisionEventType.PERSON_LEFT


@pytest.mark.parametrize(
    "pose_event",
    [
        VisionEventType.GESTURE_LEFT,
        VisionEventType.GESTURE_RIGHT,
        VisionEventType.GESTURE_UP,
        VisionEventType.GESTURE_DOWN,
        VisionEventType.POSTURE_STUDYING,
        VisionEventType.LOOKING_AT_LAMP,
    ],
)
def test_each_pose_event_overrides_positional_base(
    runtime: VisionRuntime, pose_event: VisionEventType
) -> None:
    base = VisionEvent(VisionEventType.PERSON_CENTER)
    pose = VisionEvent(pose_event)
    result = runtime._choose_event(base, pose)
    assert result.event_type == pose_event
