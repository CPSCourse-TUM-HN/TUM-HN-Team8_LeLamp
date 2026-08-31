from __future__ import annotations

import logging

from ailamp.config import BehaviorEntry, HardwareConfig
from ailamp.models import BehaviorAction, VisionEvent, VisionEventType


logger = logging.getLogger(__name__)


# Code fallback used when no [behavior_map] config is supplied. Each new
# VisionEventType added to models.py MUST get an entry here so the lamp degrades
# gracefully even if the operator's TOML is missing rows.
DEFAULT_BEHAVIOR_MAP: dict[VisionEventType, tuple[str, tuple[int, int, int]]] = {
    VisionEventType.NO_PERSON: ("scanning", (30, 30, 80)),
    VisionEventType.PERSON_LEFT: ("headshake", (80, 120, 255)),
    VisionEventType.PERSON_CENTER: ("nod", (255, 180, 80)),
    VisionEventType.PERSON_RIGHT: ("scanning", (80, 120, 255)),
    VisionEventType.PERSON_CLOSE: ("shy", (255, 80, 120)),
    VisionEventType.PERSON_FAR: ("curious", (80, 255, 160)),
    VisionEventType.PERSON_LEFT_SEAT: ("idle", (30, 30, 80)),
    VisionEventType.GESTURE_LEFT: ("headshake", (90, 150, 255)),
    VisionEventType.GESTURE_RIGHT: ("scanning", (90, 150, 255)),
    VisionEventType.GESTURE_UP: ("curious", (180, 220, 255)),
    VisionEventType.GESTURE_DOWN: ("idle", (180, 220, 255)),
    VisionEventType.POSTURE_STUDYING: ("idle", (255, 235, 190)),
    VisionEventType.LOOKING_AT_LAMP: ("nod", (255, 210, 130)),
    VisionEventType.EXPRESSION_SMILE: ("happy_wiggle", (255, 210, 130)),
    VisionEventType.EXPRESSION_TIRED: ("idle", (255, 235, 190)),
    VisionEventType.EXPRESSION_NEUTRAL: ("idle", (180, 220, 255)),
}


def _merge_config_with_default(
    config_map: dict[str, BehaviorEntry] | None,
) -> dict[VisionEventType, tuple[str, tuple[int, int, int]]]:
    """Overlay user [behavior_map] config on top of DEFAULT_BEHAVIOR_MAP.

    Config keys are lowercase strings matching VisionEventType values. Unknown keys
    are dropped with a warning. Missing keys keep the default fallback so we never
    raise KeyError at runtime when a new event type ships before the config is updated.
    """
    merged: dict[VisionEventType, tuple[str, tuple[int, int, int]]] = dict(DEFAULT_BEHAVIOR_MAP)
    if not config_map:
        return merged
    for raw_key, entry in config_map.items():
        try:
            event_type = VisionEventType(raw_key)
        except ValueError:
            logger.warning("Unknown behavior_map key %r — ignored", raw_key)
            continue
        merged[event_type] = (entry.motion, entry.rgb)
    return merged


class BehaviorService:
    def __init__(
        self,
        behavior_map: dict[VisionEventType, tuple[str, tuple[int, int, int]]] | None = None,
    ):
        self.behavior_map = behavior_map or DEFAULT_BEHAVIOR_MAP

    @classmethod
    def from_config(cls, config: HardwareConfig) -> "BehaviorService":
        """Construct a BehaviorService whose map is layered config-over-defaults."""
        return cls(behavior_map=_merge_config_with_default(config.behavior_map))

    def decide(self, event: VisionEvent) -> BehaviorAction:
        motion, rgb = self.behavior_map[event.event_type]
        return BehaviorAction(event=event, motion=motion, rgb=rgb)

    def apply(self, event: VisionEvent, motor_service, led_service) -> BehaviorAction:
        action = self.decide(event)
        motor_service.play(action.motion)
        led_service.solid(*action.rgb)
        return action
