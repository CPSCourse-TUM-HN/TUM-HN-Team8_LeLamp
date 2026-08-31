from ailamp.models import VisionEvent, VisionEventType
from ailamp.services.behavior import BehaviorService
from ailamp.services.motor import RecordingStore


def test_behavior_maps_vision_events_to_motion_and_led():
    service = BehaviorService()

    action = service.decide(VisionEvent(VisionEventType.NO_PERSON))
    assert action.motion == "scanning"
    assert action.rgb == (30, 30, 80)

    action = service.decide(VisionEvent(VisionEventType.PERSON_CENTER, confidence=0.9))
    assert action.motion == "nod"
    assert action.rgb == (255, 180, 80)

    action = service.decide(VisionEvent(VisionEventType.PERSON_LEFT, confidence=0.9))
    assert action.motion == "headshake"

    action = service.decide(VisionEvent(VisionEventType.PERSON_CLOSE, confidence=0.9))
    assert action.motion == "shy"
    assert action.rgb == (255, 80, 120)

    action = service.decide(VisionEvent(VisionEventType.POSTURE_STUDYING, confidence=0.9))
    assert action.motion == "idle"
    assert action.rgb == (255, 235, 190)

    action = service.decide(VisionEvent(VisionEventType.LOOKING_AT_LAMP, confidence=0.9))
    assert action.motion == "nod"

    action = service.decide(VisionEvent(VisionEventType.GESTURE_LEFT, confidence=0.9))
    assert action.motion == "headshake"

    action = service.decide(VisionEvent(VisionEventType.GESTURE_UP, confidence=0.9))
    assert action.motion == "curious"


def test_behavior_motions_exist_in_recordings():
    recordings = RecordingStore("ailamp_runtime/ailamp/recordings").list_names()
    service = BehaviorService()

    motions = {service.decide(VisionEvent(event_type)).motion for event_type in VisionEventType}

    assert motions.issubset(set(recordings))
