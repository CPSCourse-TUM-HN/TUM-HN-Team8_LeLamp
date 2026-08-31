from types import SimpleNamespace

from ailamp.models import VisionEventType
from ailamp.services.api_vision import APIVisionService


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return SimpleNamespace(output_text=output)


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


def test_api_vision_parses_openai_json_event():
    client = FakeClient(['{"event_type":"person_left","confidence":0.82,"normalized_offset":-0.55,"area_ratio":0.12,"reason":"person is left"}'])
    service = APIVisionService(client=client, model="gpt-4.1-mini", clock=lambda: 10.0)

    event = service.detect_event(b"jpeg")

    assert event.event_type == VisionEventType.PERSON_LEFT
    assert event.confidence == 0.82
    assert event.normalized_offset == -0.55
    assert event.area_ratio == 0.12
    assert event.semantic_reason == "person is left"
    assert client.responses.calls[0]["model"] == "gpt-4.1-mini"
    assert client.responses.calls[0]["input"][0]["content"][1]["type"] == "input_image"


def test_api_vision_reuses_cached_event_then_falls_back_to_no_person():
    times = iter([0.0, 0.5, 3.0])
    client = FakeClient(
        [
            '{"event_type":"looking_at_lamp","confidence":0.77,"normalized_offset":0.0,"area_ratio":0.20,"reason":"head up"}',
            RuntimeError("network down"),
            RuntimeError("network down"),
        ]
    )
    service = APIVisionService(client=client, interval_s=0.0, event_ttl_s=2.0, clock=lambda: next(times))

    first = service.detect_event(b"jpeg")
    cached = service.detect_event(b"jpeg")
    expired = service.detect_event(b"jpeg")

    assert first.event_type == VisionEventType.LOOKING_AT_LAMP
    assert cached.event_type == VisionEventType.LOOKING_AT_LAMP
    assert cached.semantic_reason == "cached_after_api_error:network down"
    assert expired.event_type == VisionEventType.NO_PERSON
    assert expired.semantic_reason == "api_error:network down"


def test_api_vision_respects_minimum_api_interval():
    times = iter([0.0, 0.5, 1.2])
    client = FakeClient(
        [
            '{"event_type":"person_right","confidence":0.8,"normalized_offset":0.5,"area_ratio":0.1,"reason":"right"}',
            '{"event_type":"person_left","confidence":0.8,"normalized_offset":-0.5,"area_ratio":0.1,"reason":"left"}',
        ]
    )
    service = APIVisionService(client=client, interval_s=1.0, clock=lambda: next(times))

    first = service.detect_event(b"jpeg")
    cached = service.detect_event(b"jpeg")
    second = service.detect_event(b"jpeg")

    assert first.event_type == VisionEventType.PERSON_RIGHT
    assert cached.event_type == VisionEventType.PERSON_RIGHT
    assert cached.semantic_reason == "cached_before_api_interval"
    assert second.event_type == VisionEventType.PERSON_LEFT
    assert len(client.responses.calls) == 2


def test_api_vision_filters_low_confidence_events():
    client = FakeClient(['{"event_type":"person_left","confidence":0.10,"normalized_offset":-0.6,"area_ratio":0.1,"reason":"uncertain"}'])
    service = APIVisionService(client=client, confidence_threshold=0.45, clock=lambda: 0.0)

    event = service.detect_event(b"jpeg")

    assert event.event_type == VisionEventType.NO_PERSON
    assert event.semantic_reason == "low_confidence:person_left:0.10"


def test_api_vision_frame_miss_clears_cached_person_event():
    times = iter([0.0, 0.5, 0.6])
    client = FakeClient(
        [
            '{"event_type":"person_right","confidence":0.8,"normalized_offset":0.5,"area_ratio":0.1,"reason":"right"}',
            '{"event_type":"person_left","confidence":0.8,"normalized_offset":-0.5,"area_ratio":0.1,"reason":"left"}',
        ]
    )
    service = APIVisionService(client=client, interval_s=1.0, clock=lambda: next(times))

    assert service.detect_event(b"jpeg").event_type == VisionEventType.PERSON_RIGHT
    no_frame = service.detect_event(None)
    after_miss = service.detect_event(b"jpeg")

    assert no_frame.event_type == VisionEventType.NO_PERSON
    assert no_frame.semantic_reason == "no_frame"
    assert after_miss.event_type == VisionEventType.NO_PERSON
    assert after_miss.semantic_reason == "cached_before_api_interval"


def test_api_vision_unknown_event_type_falls_back_to_no_person_without_cache_reuse():
    client = FakeClient(
        [
            '{"event_type":"person_right","confidence":0.8,"normalized_offset":0.5,"area_ratio":0.1,"reason":"right"}',
            '{"event_type":"wave_fast","confidence":0.9,"normalized_offset":0.0,"area_ratio":0.1,"reason":"unsupported"}',
        ]
    )
    service = APIVisionService(client=client, interval_s=0.0, clock=lambda: 0.0)

    assert service.detect_event(b"jpeg").event_type == VisionEventType.PERSON_RIGHT
    unsupported = service.detect_event(b"jpeg")

    assert unsupported.event_type == VisionEventType.NO_PERSON
    assert unsupported.semantic_reason == "unsupported_event_type:wave_fast"
