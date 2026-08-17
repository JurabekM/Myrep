"""Kadrlararo kuzatuv — deteksiya o'tkazilmagan kadrlar uchun.

`detect_every=N` bo'lganda N-1 ta kadrda model umuman ishlamaydi. O'sha
kadrlarda nima ko'rsatish kerak? Uch strategiya:

  * ``none``  — hech narsa (faqat deteksiya kadrida quti chiziladi, miltiraydi).
  * ``cache`` — oxirgi qutilarni shundayligicha qayta chizish. **CPU ~0.**
                IP kamera (statsionar) uchun amalda eng yaxshi tanlov.
  * ``light`` — OpenCV ning yengil trackerlari (MOSSE/KCF). Qutilar harakatga
                ergashadi, lekin har obyekt uchun CPU sarflanadi.

`light` rejimida tracker soni `max_tracks` bilan cheklanadi — 20 ta MOSSE
tracker ~1 ta YOLOv8n inference'iga teng CPU yeydi.
"""

from __future__ import annotations

import logging
from typing import List, Sequence, Tuple

import cv2
import numpy as np

from .config import TrackerKind
from .detector import Detection

logger = logging.getLogger(__name__)


def _make_cv_tracker():
    """Mavjud eng yengil OpenCV trackerni qaytaradi (versiyaga chidamli)."""
    for factory in (
        getattr(getattr(cv2, "legacy", None), "TrackerMOSSE_create", None),
        getattr(cv2, "TrackerMOSSE_create", None),
        getattr(cv2, "TrackerKCF_create", None),
        getattr(getattr(cv2, "legacy", None), "TrackerKCF_create", None),
    ):
        if callable(factory):
            return factory()
    return None


class BoxTracker:
    """Deteksiyalar orasidagi kadrlarda qutilarni saqlab/yangilab turadi."""

    def __init__(self, kind: TrackerKind = "cache", max_tracks: int = 20) -> None:
        self.kind: TrackerKind = kind
        self.max_tracks = max_tracks
        self._dets: List[Detection] = []
        self._trackers: List[Tuple[object, Detection]] = []
        self._warned = False

    # ------------------------------------------------------------------ API
    def reset(self, frame: np.ndarray, detections: Sequence[Detection]) -> List[Detection]:
        """Yangi deteksiya natijasi bilan holatni yangilaydi."""
        self._dets = list(detections)
        if self.kind != "light":
            return self._dets

        # Eski trackerlarni bo'shatish — Python ref hisobi darhol tozalasin
        self._trackers.clear()
        h, w = frame.shape[:2]
        for det in self._dets[: self.max_tracks]:
            tr = _make_cv_tracker()
            if tr is None:
                if not self._warned:
                    logger.warning(
                        "OpenCV tracker mavjud emas (opencv-contrib kerak) — "
                        "'cache' rejimiga o'tildi"
                    )
                    self._warned = True
                self.kind = "cache"
                self._trackers.clear()
                break
            x, y, bw, bh = det.xywh
            if bw <= 1 or bh <= 1:
                continue
            # ROI kadr chegarasidan chiqmasligi kerak, aks holda init() yiqiladi
            x, y = max(0, x), max(0, y)
            bw, bh = min(bw, w - x), min(bh, h - y)
            if bw <= 1 or bh <= 1:
                continue
            try:
                tr.init(frame, (x, y, bw, bh))
                self._trackers.append((tr, det))
            except cv2.error:
                continue
        return self._dets

    def update(self, frame: np.ndarray) -> List[Detection]:
        """Oraliq kadr uchun joriy qutilar ro'yxatini qaytaradi."""
        if self.kind == "none":
            return []
        if self.kind == "cache" or not self._trackers:
            return self._dets  # nusxa emas — faqat o'qish uchun

        out: List[Detection] = []
        alive: List[Tuple[object, Detection]] = []
        for tr, det in self._trackers:
            ok, box = tr.update(frame)  # type: ignore[union-attr]
            if not ok:
                continue  # yo'qolgan track tashlanadi
            x, y, bw, bh = (int(v) for v in box)
            out.append(
                Detection(x, y, x + bw, y + bh, det.score, det.class_id, det.label)
            )
            alive.append((tr, det))
        self._trackers = alive
        self._dets = out
        return out

    def clear(self) -> None:
        """Xotirani bo'shatish (graceful shutdown yoki reconnect'da)."""
        self._trackers.clear()
        self._dets = []

    @property
    def current(self) -> List[Detection]:
        return self._dets
