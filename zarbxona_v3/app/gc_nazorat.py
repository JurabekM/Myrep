"""Python GC faqat ASOSIY (GUI) oqimda ishlasin.

Avtomatik GC ob'ekt ajratayotgan istalgan oqimda ishga tushadi — masalan, zarb ishchisida.
U yerda halqali axlat ichidagi Qt ob'ektlari (vidjetlar, eski QThread'lar) noto'g'ri
oqimda yo'q qilinadi va PySide6 yiqiladi (PYSIDE-810; PySide6 6.12 da CI'da segfault
sifatida ko'rindi). Yechim: avtomatik GC o'chiriladi va asosiy oqimdagi taymer
`gc.collect()` ni chaqiradi. Oddiy ob'ektlar baribir havola sanog'i bilan darhol
bo'shaydi, taymerni faqat halqalar kutadi.
"""

from __future__ import annotations

import gc

from PySide6.QtCore import QObject, QTimer

ORALIQ_MS = 5000


def ornat(ota: QObject, oraliq_ms: int = ORALIQ_MS) -> QTimer:
    gc.disable()
    t = QTimer(ota)
    t.setInterval(oraliq_ms)
    t.timeout.connect(lambda: gc.collect())
    t.start()
    return t
