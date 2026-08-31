from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ailamp.models import VisionEvent, VisionEventType


COCO_KEYPOINT_NAMES = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


@dataclass(frozen=True)
class PosePoint:
    x: float
    y: float
    confidence: float = 1.0


@dataclass(frozen=True)
class PoseKeypoints:
    frame_size: tuple[int, int]
    points: dict[str, PosePoint]

    @classmethod
    def from_named(cls, frame_size: tuple[int, int], **points: tuple[float, float] | tuple[float, float, float]):
        parsed = {}
        for name, values in points.items():
            if len(values) == 2:
                x, y = values
                confidence = 1.0
            else:
                x, y, confidence = values
            parsed[name] = PosePoint(float(x), float(y), float(confidence))
        return cls(frame_size=frame_size, points=parsed)

    @classmethod
    def from_coco(cls, frame_size: tuple[int, int], keypoints: Iterable[Iterable[float]]):
        parsed = {}
        for name, values in zip(COCO_KEYPOINT_NAMES, keypoints):
            coords = list(values)
            if len(coords) < 2:
                continue
            confidence = float(coords[2]) if len(coords) > 2 else 1.0
            parsed[name] = PosePoint(float(coords[0]), float(coords[1]), confidence)
        return cls(frame_size=frame_size, points=parsed)

    def get(self, name: str, *, min_confidence: float = 0.25) -> PosePoint | None:
        point = self.points.get(name)
        if point is None or point.confidence < min_confidence:
            return None
        return point


def classify_pose_gesture(pose: PoseKeypoints | None) -> VisionEvent:
    if pose is None:
        return VisionEvent(VisionEventType.NO_PERSON)

    nose = pose.get("nose")
    left_shoulder = pose.get("left_shoulder")
    right_shoulder = pose.get("right_shoulder")
    if nose is None or left_shoulder is None or right_shoulder is None:
        return VisionEvent(VisionEventType.PERSON_CENTER)

    frame_width, frame_height = pose.frame_size
    shoulder_y = (left_shoulder.y + right_shoulder.y) / 2.0
    shoulder_width = max(abs(right_shoulder.x - left_shoulder.x), frame_width * 0.15)
    wrist_event = _classify_wrist_gesture(pose, nose, shoulder_y, shoulder_width)
    if wrist_event is not None:
        return wrist_event

    left_eye = pose.get("left_eye")
    right_eye = pose.get("right_eye")
    eye_y = None
    if left_eye is not None and right_eye is not None:
        eye_y = (left_eye.y + right_eye.y) / 2.0

    if nose.y > shoulder_y - frame_height * 0.04:
        return VisionEvent(VisionEventType.POSTURE_STUDYING, confidence=nose.confidence)

    if eye_y is not None and nose.y < shoulder_y - frame_height * 0.18:
        return VisionEvent(VisionEventType.LOOKING_AT_LAMP, confidence=min(nose.confidence, left_eye.confidence, right_eye.confidence))

    return VisionEvent(VisionEventType.PERSON_CENTER, confidence=nose.confidence)


def _classify_wrist_gesture(
    pose: PoseKeypoints,
    nose: PosePoint,
    shoulder_y: float,
    shoulder_width: float,
) -> VisionEvent | None:
    frame_width, frame_height = pose.frame_size
    wrists = [point for name in ("left_wrist", "right_wrist") if (point := pose.get(name)) is not None]
    if not wrists:
        return None

    for wrist in wrists:
        horizontal_offset = wrist.x - nose.x
        if wrist.y < shoulder_y + frame_height * 0.08 and horizontal_offset < -max(shoulder_width * 0.9, frame_width * 0.18):
            return VisionEvent(VisionEventType.GESTURE_LEFT, confidence=wrist.confidence, normalized_offset=-1.0)
        if wrist.y < shoulder_y + frame_height * 0.08 and horizontal_offset > max(shoulder_width * 0.9, frame_width * 0.18):
            return VisionEvent(VisionEventType.GESTURE_RIGHT, confidence=wrist.confidence, normalized_offset=1.0)

    for wrist in wrists:
        if abs(wrist.x - nose.x) < frame_width * 0.25 and wrist.y < nose.y - frame_height * 0.12:
            return VisionEvent(VisionEventType.GESTURE_UP, confidence=wrist.confidence)
        if abs(wrist.x - nose.x) < frame_width * 0.30 and wrist.y > shoulder_y + frame_height * 0.20:
            return VisionEvent(VisionEventType.GESTURE_DOWN, confidence=wrist.confidence)

    return None


class PoseDetectorService:
    def __init__(self, model_name: str = "yolov8n-pose.pt", confidence: float = 0.45):
        self.model_name = model_name
        self.confidence = confidence
        self._model = None

    def load(self) -> None:
        from ultralytics import YOLO  # type: ignore

        self._model = YOLO(self.model_name)

    def detect_pose(self, frame) -> PoseKeypoints | None:
        if self._model is None:
            raise RuntimeError("PoseDetectorService model is not loaded")
        results = self._model(frame, verbose=False)
        best_pose = None
        best_confidence = 0.0
        frame_size = (frame.shape[1], frame.shape[0])
        for result in results:
            keypoints = getattr(result, "keypoints", None)
            if keypoints is None or keypoints.data is None:
                continue
            for raw_keypoints in keypoints.data:
                rows = raw_keypoints.tolist()
                confidences = [float(row[2]) for row in rows if len(row) > 2]
                pose_confidence = max(confidences, default=0.0)
                if pose_confidence < self.confidence or pose_confidence < best_confidence:
                    continue
                best_pose = PoseKeypoints.from_coco(frame_size, rows)
                best_confidence = pose_confidence
        return best_pose
