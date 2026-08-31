from __future__ import annotations

from dataclasses import dataclass

from ailamp.models import VisionEvent, VisionEventType
from ailamp.services.behavior import BehaviorService
from ailamp.services.motor import JointDeltaCommand


@dataclass(frozen=True)
class AIDecision:
    event: VisionEvent
    motion: str
    rgb: tuple[int, int, int]
    reason: str
    joint_deltas: tuple[JointDeltaCommand, ...] = ()
    semantic_reason: str = ""


class DecisionService:
    def __init__(
        self,
        *,
        behavior: BehaviorService | None = None,
        yaw_deadzone: float = 0.12,
        yaw_step_deg: float = 4.0,
        pitch_step_deg: float = 2.5,
    ):
        self.behavior = behavior or BehaviorService()
        self.yaw_deadzone = yaw_deadzone
        self.yaw_step_deg = yaw_step_deg
        self.pitch_step_deg = pitch_step_deg

    def decide(self, event: VisionEvent, user_text: str | None = None) -> AIDecision:
        voice_decision = self._voice_decision(event, user_text)
        if voice_decision is not None:
            return voice_decision

        tracking = self._tracking_deltas(event)
        if tracking:
            return AIDecision(
                event=event,
                motion="track",
                rgb=self._tracking_rgb(event),
                joint_deltas=tracking,
                reason=self._tracking_reason(event),
                semantic_reason=event.semantic_reason,
            )

        action = self.behavior.decide(event)
        return AIDecision(
            event=event,
            motion=action.motion,
            rgb=action.rgb,
            reason=f"behavior_map:{event.event_type.value}",
            semantic_reason=event.semantic_reason,
        )

    def _voice_decision(self, event: VisionEvent, user_text: str | None) -> AIDecision | None:
        if not user_text:
            return None
        text = user_text.lower()
        if any(keyword in text for keyword in ("专注", "学习", "study", "focus")):
            return AIDecision(event, "idle", (255, 235, 190), "voice:focus_mode", semantic_reason=event.semantic_reason)
        if any(keyword in text for keyword in ("点头", "nod")):
            return AIDecision(event, "nod", (255, 210, 130), "voice:nod", semantic_reason=event.semantic_reason)
        if any(keyword in text for keyword in ("害羞", "shy")):
            return AIDecision(event, "shy", (255, 80, 120), "voice:shy", semantic_reason=event.semantic_reason)
        if any(keyword in text for keyword in ("休息", "待机", "idle", "rest")):
            return AIDecision(event, "idle", (30, 30, 80), "voice:idle", semantic_reason=event.semantic_reason)
        if any(keyword in text for keyword in ("跟随", "看着我", "follow", "track")):
            tracking = self._tracking_deltas(event)
            if tracking:
                return AIDecision(event, "track", self._tracking_rgb(event), "voice:track", tracking, event.semantic_reason)
        return None

    def _tracking_deltas(self, event: VisionEvent) -> tuple[JointDeltaCommand, ...]:
        if event.event_type in {VisionEventType.PERSON_LEFT, VisionEventType.GESTURE_LEFT}:
            offset = event.normalized_offset if event.normalized_offset else -1.0
            if offset < -self.yaw_deadzone:
                return (JointDeltaCommand("base_yaw", -self._scaled_yaw_step(offset)),)
        if event.event_type in {VisionEventType.PERSON_RIGHT, VisionEventType.GESTURE_RIGHT}:
            offset = event.normalized_offset if event.normalized_offset else 1.0
            if offset > self.yaw_deadzone:
                return (JointDeltaCommand("base_yaw", self._scaled_yaw_step(offset)),)
        if event.event_type == VisionEventType.PERSON_CLOSE:
            return (JointDeltaCommand("wrist_pitch", -self.pitch_step_deg),)
        if event.event_type == VisionEventType.PERSON_FAR:
            return (JointDeltaCommand("wrist_pitch", self.pitch_step_deg),)
        if event.event_type == VisionEventType.GESTURE_UP:
            return (JointDeltaCommand("wrist_pitch", self.pitch_step_deg),)
        if event.event_type == VisionEventType.GESTURE_DOWN:
            return (JointDeltaCommand("wrist_pitch", -self.pitch_step_deg),)
        return ()

    def _scaled_yaw_step(self, offset: float) -> float:
        return min(self.yaw_step_deg, max(1.0, abs(offset) * self.yaw_step_deg))

    def _tracking_rgb(self, event: VisionEvent) -> tuple[int, int, int]:
        if event.event_type == VisionEventType.PERSON_CLOSE:
            return (255, 120, 150)
        if event.event_type == VisionEventType.PERSON_FAR:
            return (180, 220, 255)
        return (90, 150, 255)

    def _tracking_reason(self, event: VisionEvent) -> str:
        if event.event_type in {VisionEventType.PERSON_LEFT, VisionEventType.GESTURE_LEFT}:
            return "track:left base_yaw"
        if event.event_type in {VisionEventType.PERSON_RIGHT, VisionEventType.GESTURE_RIGHT}:
            return "track:right base_yaw"
        if event.event_type == VisionEventType.PERSON_CLOSE:
            return "track:person_close tilt head back"
        if event.event_type == VisionEventType.PERSON_FAR:
            return "track:person_far tilt head forward"
        if event.event_type == VisionEventType.GESTURE_UP:
            return "track:gesture_up tilt head up"
        if event.event_type == VisionEventType.GESTURE_DOWN:
            return "track:gesture_down tilt head down"
        return f"track:{event.event_type.value}"
