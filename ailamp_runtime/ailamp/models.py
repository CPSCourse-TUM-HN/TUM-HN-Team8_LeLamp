from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class VisionEventType(StrEnum):
    NO_PERSON = "no_person"
    PERSON_LEFT = "person_left"
    PERSON_CENTER = "person_center"
    PERSON_RIGHT = "person_right"
    PERSON_CLOSE = "person_close"
    PERSON_FAR = "person_far"
    PERSON_LEFT_SEAT = "person_left_seat"
    GESTURE_LEFT = "gesture_left"
    GESTURE_RIGHT = "gesture_right"
    GESTURE_UP = "gesture_up"
    GESTURE_DOWN = "gesture_down"
    POSTURE_STUDYING = "posture_studying"
    LOOKING_AT_LAMP = "looking_at_lamp"
    EXPRESSION_SMILE = "expression_smile"
    EXPRESSION_TIRED = "expression_tired"
    EXPRESSION_NEUTRAL = "expression_neutral"


@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float
    confidence: float
    label: str = "person"

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class VisionEvent:
    event_type: VisionEventType
    confidence: float = 0.0
    bbox: Optional[BoundingBox] = None
    normalized_offset: float = 0.0
    area_ratio: float = 0.0
    semantic_reason: str = ""


@dataclass(frozen=True)
class BehaviorAction:
    event: VisionEvent
    motion: str
    rgb: tuple[int, int, int]
    priority: int = 1
