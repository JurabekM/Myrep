"""Visualizer — ixtiyoriy (opsional) chizish/oyna qatlami.

Headless rejimda bu sinf umuman yaratilmaydi: `cv2.imshow` bir kadr uchun
~2-5 ms CPU va oyna uchun qo'shimcha RAM oladi. Server/edge qurilmada bu
sof isrof.

Chizish `frame` **ustida** (in-place) bajariladi. Bu ataylab: `frame.copy()`
har kadrda 1080p uchun ~6 MB allokatsiya va GC bosimini bildiradi.
`copy_frame=True` faqat original kadr keyin ham kerak bo'lsa yoqiladi.
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

from .detector import Detection

logger = logging.getLogger(__name__)

# Class id -> BGR rang (deterministik, har safar bir xil)
_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (56, 176, 0), (0, 165, 255), (255, 128, 0), (180, 105, 255),
    (0, 215, 255), (255, 191, 0), (60, 76, 231), (128, 200, 60),
)


def color_for(class_id: int) -> Tuple[int, int, int]:
    """Class uchun barqaror rang."""
    return _PALETTE[class_id % len(_PALETTE)]


class Visualizer:
    """OpenCV oynasi va bounding-box chizish."""

    _FONT = cv2.FONT_HERSHEY_SIMPLEX

    def __init__(
        self,
        window_name: str = "IPCam Detect",
        show: bool = True,
        copy_frame: bool = False,
        max_width: int = 1280,
    ) -> None:
        self.window_name = window_name
        self.show = show
        self.copy_frame = copy_frame
        self.max_width = max_width
        self._created = False

    def _ensure_window(self) -> None:
        if self._created or not self.show:
            return
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        self._created = True

    # ---------------------------------------------------------------- draw
    def draw(
        self,
        frame: np.ndarray,
        detections: Sequence[Detection],
        hud: Optional[str] = None,
        stale: bool = False,
    ) -> np.ndarray:
        """Qutilarni va HUD matnini chizadi (default: in-place)."""
        canvas = frame.copy() if self.copy_frame else frame
        for det in detections:
            color = color_for(det.class_id)
            # Kuzatuv (deteksiya emas) kadrida chiziq ingichkaroq — vizual farq
            cv2.rectangle(canvas, (det.x1, det.y1), (det.x2, det.y2), color, 1 if stale else 2)
            label = f"{det.label} {det.score:.2f}"
            (tw, th), base = cv2.getTextSize(label, self._FONT, 0.45, 1)
            ty = max(det.y1, th + 4)
            cv2.rectangle(
                canvas, (det.x1, ty - th - base), (det.x1 + tw + 4, ty), color, -1
            )
            cv2.putText(
                canvas, label, (det.x1 + 2, ty - base + 1),
                self._FONT, 0.45, (20, 20, 20), 1, cv2.LINE_AA,
            )

        if hud:
            cv2.putText(canvas, hud, (8, 20), self._FONT, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, hud, (8, 20), self._FONT, 0.5, (0, 255, 128), 1, cv2.LINE_AA)
        return canvas

    # --------------------------------------------------------------- window
    def render(self, frame: np.ndarray) -> bool:
        """Oynaga chiqaradi. ``False`` qaytsa — foydalanuvchi chiqishni so'radi."""
        if not self.show:
            return True
        self._ensure_window()
        if frame.shape[1] > self.max_width:
            scale = self.max_width / frame.shape[1]
            frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        cv2.imshow(self.window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        return key not in (27, ord("q"))  # ESC yoki 'q'

    def close(self) -> None:
        """Oynani yopadi — GUI resurslari sizib qolmasligi uchun."""
        if self._created:
            try:
                cv2.destroyWindow(self.window_name)
                cv2.waitKey(1)  # Windows'da oyna haqiqatan yopilishi uchun
            except cv2.error:
                pass
            self._created = False

    def __enter__(self) -> "Visualizer":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
