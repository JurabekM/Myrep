"""Hisob bo'yicha parol tanlashdan himoya (ADR-0014): telefon raqamiga noto'g'ri urinishlar IP dan qat'i nazar sanaladi.

Bitta jarayon xotirasida (rate limiter kabi; bir necha nusxada — Redis). Muvaffaqiyatli kirish hisobni tozalaydi.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable


class LoginGuard:
    def __init__(self, max_failures: int, window_seconds: int, clock: Callable[[], float]) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        q = self._failures[key]
        cutoff = self._clock() - self._window
        while q and q[0] <= cutoff:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        if key not in self._failures:  # tekshiruvning o'zi yozuv yaratmaydi (xotira o'smaydi)
            return False
        return len(self._prune(key)) >= self._max

    def failed(self, key: str) -> None:
        self._prune(key).append(self._clock())
        if len(self._failures) > 100_000:
            # Xotira chegarasi: muddati o'tgan yozuvlar har bir kalitda tozalanadi (faqat bo'sh navbatlar emas).
            for k in [k for k in self._failures if not self._prune(k)]:
                del self._failures[k]

    def succeeded(self, key: str) -> None:
        self._failures.pop(key, None)
