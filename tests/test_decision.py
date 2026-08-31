from ailamp.models import VisionEvent, VisionEventType
from ailamp.services.decision import DecisionService


def test_decision_tracks_person_left_and_right_with_base_yaw_delta():
    service = DecisionService()

    left = service.decide(VisionEvent(VisionEventType.PERSON_LEFT, confidence=0.9, normalized_offset=-0.55))
    right = service.decide(VisionEvent(VisionEventType.PERSON_RIGHT, confidence=0.9, normalized_offset=0.65))

    assert left.motion == "track"
    assert left.joint_deltas[0].joint == "base_yaw"
    assert left.joint_deltas[0].delta_deg < 0
    assert "left" in left.reason
    assert right.motion == "track"
    assert right.joint_deltas[0].joint == "base_yaw"
    assert right.joint_deltas[0].delta_deg > 0


def test_decision_tilts_head_for_close_and_far_person():
    service = DecisionService()

    close = service.decide(VisionEvent(VisionEventType.PERSON_CLOSE, confidence=0.9, area_ratio=0.45))
    far = service.decide(VisionEvent(VisionEventType.PERSON_FAR, confidence=0.9, area_ratio=0.05))

    assert close.motion == "track"
    assert close.joint_deltas[0].joint == "wrist_pitch"
    assert close.joint_deltas[0].delta_deg < 0
    assert "back" in close.reason
    assert far.motion == "track"
    assert far.joint_deltas[0].joint == "wrist_pitch"
    assert far.joint_deltas[0].delta_deg > 0


def test_decision_uses_voice_intent_for_focus_and_direct_reactions():
    service = DecisionService()

    focus = service.decide(VisionEvent(VisionEventType.PERSON_RIGHT, normalized_offset=0.6), user_text="我在低头学习，进入专注模式")
    nod = service.decide(VisionEvent(VisionEventType.PERSON_LEFT, normalized_offset=-0.6), user_text="向我点头")

    assert focus.motion == "idle"
    assert focus.rgb == (255, 235, 190)
    assert not focus.joint_deltas
    assert "voice" in focus.reason
    assert nod.motion == "nod"
    assert nod.rgb == (255, 210, 130)
    assert not nod.joint_deltas


def test_decision_follows_when_voice_asks_to_track():
    service = DecisionService()

    decision = service.decide(VisionEvent(VisionEventType.PERSON_RIGHT, normalized_offset=0.45), user_text="看着我并跟随我")

    assert decision.motion == "track"
    assert decision.joint_deltas[0].joint == "base_yaw"
    assert decision.joint_deltas[0].delta_deg > 0
