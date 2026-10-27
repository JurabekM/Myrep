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
        self._next_sweep = float("-inf")

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
        now = self._clock()
        self._prune(key).append(now)
        if len(self._failures) > 100_000 and now >= self._next_sweep:
            # Xotira chegarasi: muddati o'tgan yozuvlar har bir kalitda tozalanadi — daqiqasiga ko'pi bilan bir marta
            # (har so'rovda O(n) aylanish hujumchiga CPU'ni band qilish imkonini berardi).
            self._next_sweep = now + 60
            for k in [k for k in self._failures if not self._prune(k)]:
                del self._failures[k]

    def succeeded(self, key: str) -> None:
        self._failures.pop(key, None)
