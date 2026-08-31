from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CameraFrameInfo:
    opened: bool
    readable: bool
    width: int
    height: int
    fps: float


class CameraService:
    def __init__(
        self,
        device: int | str = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        pixel_format: str = "MJPG",
    ):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.pixel_format = pixel_format
        self._capture: Any = None

    def open(self) -> None:
        import cv2  # type: ignore

        self._capture = cv2.VideoCapture(self.device)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._capture.set(cv2.CAP_PROP_FPS, self.fps)
        self._capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.pixel_format))

    def read(self):
        if self._capture is None:
            raise RuntimeError("CameraService is not open")
        readable, frame = self._capture.read()
        if not readable:
            return None
        return frame

    def probe(self) -> CameraFrameInfo:
        if self._capture is None:
            self.open()
        frame = self.read()
        opened = bool(self._capture.isOpened())
        actual_width = int(self._capture.get(3))
        actual_height = int(self._capture.get(4))
        actual_fps = float(self._capture.get(5))
        return CameraFrameInfo(opened, frame is not None, actual_width, actual_height, actual_fps)

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
