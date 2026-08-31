"""Unit tests for the DecisionService — voice override, tracking deltas, fallback."""
from __future__ import annotations

import pytest

from ailamp.models import VisionEvent, VisionEventType
from ailamp.services.behavior import BehaviorService
from ailamp.services.decision import DecisionService
from ailamp.services.motor import JointDeltaCommand


# ---------- Fixtures ---------------------------------------------------------


@pytest.fixture
def decision() -> DecisionService:
    return DecisionService(behavior=BehaviorService())


def _event(event_type: VisionEventType, *, offset: float = 0.0, area_ratio: float = 0.1) -> VisionEvent:
    return VisionEvent(event_type=event_type, normalized_offset=offset, area_ratio=area_ratio)


# ---------- Voice keyword override -----------------------------------------


@pytest.mark.parametrize(
    "user_text,expected_motion,expected_reason_prefix",
    [
        ("请专注", "idle", "voice:focus_mode"),
        ("我要学习", "idle", "voice:focus_mode"),
        ("focus please", "idle", "voice:focus_mode"),
        ("can you study with me", "idle", "voice:focus_mode"),
        ("点头一下", "nod", "voice:nod"),
        ("nod for me", "nod", "voice:nod"),
        ("你害羞了", "shy", "voice:shy"),
        ("act shy", "shy", "voice:shy"),
        ("休息一下", "idle", "voice:idle"),
        ("go to idle", "idle", "voice:idle"),
        ("rest now", "idle", "voice:idle"),
    ],
)
def test_voice_keyword_override_for_static_events(
    decision: DecisionService,
    user_text: str,
    expected_motion: str,
    expected_reason_prefix: str,
) -> None:
    event = _event(VisionEventType.PERSON_CENTER)
    result = decision.decide(event, user_text=user_text)
    assert result.motion == expected_motion
    assert result.reason.startswith(expected_reason_prefix)


@pytest.mark.parametrize(
    "user_text",
    ["跟随我", "请看着我", "follow me", "track the target"],
)
def test_voice_track_keyword_engages_tracking_when_event_supports_it(
    decision: DecisionService, user_text: str
) -> None:
    event = _event(VisionEventType.PERSON_LEFT, offset=-0.5)
    result = decision.decide(event, user_text=user_text)
    assert result.motion == "track"
    assert result.reason == "voice:track"
    assert any(cmd.joint == "base_yaw" for cmd in result.joint_deltas)


def test_voice_track_keyword_falls_through_when_event_has_no_tracking(
    decision: DecisionService,
) -> None:
    event = _event(VisionEventType.NO_PERSON)
    result = decision.decide(event, user_text="follow me")
    # No tracking available → falls through to behavior map for NO_PERSON.
    assert result.motion == "scanning"
    assert result.joint_deltas == ()


def test_no_user_text_skips_voice_layer(decision: DecisionService) -> None:
    event = _event(VisionEventType.PERSON_CENTER)
    result = decision.decide(event, user_text=None)
    assert not result.reason.startswith("voice:")


def test_unknown_user_text_falls_through_to_tracking_or_behavior(
    decision: DecisionService,
) -> None:
    event = _event(VisionEventType.PERSON_CENTER)
    result = decision.decide(event, user_text="weather today")
    assert not result.reason.startswith("voice:")
    assert result.motion == "nod"  # PERSON_CENTER → behavior map default


# ---------- Tracking deltas --------------------------------------------------


def test_person_left_outside_deadzone_yaws_negative(decision: DecisionService) -> None:
    event = _event(VisionEventType.PERSON_LEFT, offset=-0.6)
    result = decision.decide(event)
    assert result.motion == "track"
    assert len(result.joint_deltas) == 1
    assert result.joint_deltas[0] == JointDeltaCommand("base_yaw", pytest.approx(-2.4, abs=0.01))


def test_person_right_outside_deadzone_yaws_positive(decision: DecisionService) -> None:
    event = _event(VisionEventType.PERSON_RIGHT, offset=0.6)
    result = decision.decide(event)
    assert result.motion == "track"
    assert result.joint_deltas[0].joint == "base_yaw"
    assert result.joint_deltas[0].delta_deg > 0


def test_person_left_inside_deadzone_falls_through_to_behavior_map(
    decision: DecisionService,
) -> None:
    event = _event(VisionEventType.PERSON_LEFT, offset=-0.05)  # < yaw_deadzone (0.12)
    result = decision.decide(event)
    assert result.motion != "track"
    assert result.joint_deltas == ()


def test_person_close_pitches_wrist_back(decision: DecisionService) -> None:
    event = _event(VisionEventType.PERSON_CLOSE)
    result = decision.decide(event)
    assert result.motion == "track"
    assert result.joint_deltas == (JointDeltaCommand("wrist_pitch", -2.5),)


def test_person_far_pitches_wrist_forward(decision: DecisionService) -> None:
    event = _event(VisionEventType.PERSON_FAR)
    result = decision.decide(event)
    assert result.motion == "track"
    assert result.joint_deltas == (JointDeltaCommand("wrist_pitch", 2.5),)


def test_gesture_up_pitches_wrist_forward(decision: DecisionService) -> None:
    event = _event(VisionEventType.GESTURE_UP)
    result = decision.decide(event)
    assert result.motion == "track"
    assert result.joint_deltas == (JointDeltaCommand("wrist_pitch", 2.5),)


def test_gesture_down_pitches_wrist_back(decision: DecisionService) -> None:
    event = _event(VisionEventType.GESTURE_DOWN)
    result = decision.decide(event)
    assert result.motion == "track"
    assert result.joint_deltas == (JointDeltaCommand("wrist_pitch", -2.5),)


def test_yaw_step_scales_with_offset_magnitude() -> None:
    service = DecisionService(yaw_step_deg=10.0, yaw_deadzone=0.1)
    small = service.decide(_event(VisionEventType.PERSON_RIGHT, offset=0.2))
    large = service.decide(_event(VisionEventType.PERSON_RIGHT, offset=1.0))
    assert small.joint_deltas[0].delta_deg < large.joint_deltas[0].delta_deg
    assert large.joint_deltas[0].delta_deg == pytest.approx(10.0, abs=0.01)


# ---------- Behavior fallback ------------------------------------------------


@pytest.mark.parametrize(
    "event_type,expected_motion",
    [
        (VisionEventType.NO_PERSON, "scanning"),
        (VisionEventType.PERSON_CENTER, "nod"),
        (VisionEventType.PERSON_LEFT_SEAT, "idle"),
        (VisionEventType.POSTURE_STUDYING, "idle"),
        (VisionEventType.LOOKING_AT_LAMP, "nod"),
        (VisionEventType.EXPRESSION_SMILE, "happy_wiggle"),
    ],
)
def test_falls_through_to_behavior_map_for_non_tracking_events(
    decision: DecisionService, event_type: VisionEventType, expected_motion: str
) -> None:
    event = _event(event_type)
    result = decision.decide(event)
    assert result.motion == expected_motion
    assert result.reason.startswith("behavior_map:")
    assert result.joint_deltas == ()


def test_decision_preserves_semantic_reason_from_event(decision: DecisionService) -> None:
    event = VisionEvent(VisionEventType.PERSON_CENTER, semantic_reason="api_test:explanation")
    result = decision.decide(event)
    assert result.semantic_reason == "api_test:explanation"
