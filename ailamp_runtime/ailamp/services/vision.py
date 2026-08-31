from __future__ import annotations

from typing import Optional

from ailamp.models import BoundingBox, VisionEvent, VisionEventType


def classify_person_position(
    bbox: Optional[BoundingBox],
    frame_size: tuple[int, int],
    *,
    left_threshold: float = -0.20,
    right_threshold: float = 0.20,
    close_area_ratio: float = 0.35,
    far_area_ratio: float = 0.02,
) -> VisionEvent:
    if bbox is None:
        return VisionEvent(VisionEventType.NO_PERSON)

    frame_width, frame_height = frame_size
    frame_area = frame_width * frame_height
    normalized_offset = (bbox.center_x - frame_width / 2.0) / (frame_width / 2.0)
    area_ratio = bbox.area / frame_area if frame_area else 0.0

    if area_ratio > close_area_ratio:
        event_type = VisionEventType.PERSON_CLOSE
    elif area_ratio < far_area_ratio:
        event_type = VisionEventType.PERSON_FAR
    elif normalized_offset < left_threshold:
        event_type = VisionEventType.PERSON_LEFT
    elif normalized_offset > right_threshold:
        event_type = VisionEventType.PERSON_RIGHT
    else:
        event_type = VisionEventType.PERSON_CENTER

    return VisionEvent(
        event_type=event_type,
        confidence=bbox.confidence,
        bbox=bbox,
        normalized_offset=normalized_offset,
        area_ratio=area_ratio,
    )


class DetectorService:
    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.45):
        self.model_name = model_name
        self.confidence = confidence
        self._model = None

    def load(self) -> None:
        from ultralytics import YOLO  # type: ignore

        self._model = YOLO(self.model_name)

    def detect_person(self, frame) -> Optional[BoundingBox]:
        if self._model is None:
            raise RuntimeError("DetectorService model is not loaded")
        results = self._model(frame, verbose=False)
        best: Optional[BoundingBox] = None
        for result in results:
            names = result.names
            for box in result.boxes:
                confidence = float(box.conf[0])
                label = names[int(box.cls[0])]
                if label != "person" or confidence < self.confidence:
                    continue
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0]]
                candidate = BoundingBox(x1, y1, x2 - x1, y2 - y1, confidence, label)
                if best is None or candidate.confidence > best.confidence:
                    best = candidate
        return best
