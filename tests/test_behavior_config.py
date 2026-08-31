"""Verify BehaviorService can layer config-driven overrides on top of code defaults."""
from __future__ import annotations

from unittest.mock import MagicMock

from ailamp.config import BehaviorEntry
from ailamp.models import VisionEvent, VisionEventType
from ailamp.services.behavior import DEFAULT_BEHAVIOR_MAP, BehaviorService, _merge_config_with_default


def test_no_config_returns_default_map() -> None:
    merged = _merge_config_with_default(None)
    assert merged == DEFAULT_BEHAVIOR_MAP


def test_config_overrides_specific_entries_only() -> None:
    custom = {
        "person_center": BehaviorEntry(motion="happy_wiggle", rgb=(1, 2, 3)),
    }
    merged = _merge_config_with_default(custom)
    # Override applied:
    assert merged[VisionEventType.PERSON_CENTER] == ("happy_wiggle", (1, 2, 3))
    # Untouched entries remain at defaults:
    assert merged[VisionEventType.NO_PERSON] == DEFAULT_BEHAVIOR_MAP[VisionEventType.NO_PERSON]


def test_unknown_event_key_is_ignored_not_fatal(caplog) -> None:
    custom = {
        "person_center": BehaviorEntry(motion="x", rgb=(0, 0, 0)),
        "alien_landed": BehaviorEntry(motion="nope", rgb=(0, 0, 0)),  # not a real event
    }
    with caplog.at_level("WARNING"):
        merged = _merge_config_with_default(custom)
    assert "alien_landed" in caplog.text
    # The valid override still applies:
    assert merged[VisionEventType.PERSON_CENTER] == ("x", (0, 0, 0))


def test_behavior_service_from_config_uses_overrides() -> None:
    config = MagicMock()
    config.behavior_map = {
        "person_close": BehaviorEntry(motion="custom_close_motion", rgb=(10, 20, 30)),
    }
    service = BehaviorService.from_config(config)
    action = service.decide(VisionEvent(VisionEventType.PERSON_CLOSE))
    assert action.motion == "custom_close_motion"
    assert action.rgb == (10, 20, 30)


def test_behavior_service_from_config_with_no_config_uses_defaults() -> None:
    config = MagicMock()
    config.behavior_map = None
    service = BehaviorService.from_config(config)
    action = service.decide(VisionEvent(VisionEventType.PERSON_CENTER))
    assert action.motion == DEFAULT_BEHAVIOR_MAP[VisionEventType.PERSON_CENTER][0]


def test_default_map_covers_all_vision_event_types() -> None:
    """Drift guard: every VisionEventType must have a default entry."""
    for event_type in VisionEventType:
        assert event_type in DEFAULT_BEHAVIOR_MAP, (
            f"{event_type.value} missing from DEFAULT_BEHAVIOR_MAP — add it before shipping."
        )
