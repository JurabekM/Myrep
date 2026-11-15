"""Ilova belgisini chizadi: packaging/icon.png (1024 px) va packaging/icon.ico.

Belgi loyihaning o'z uslubida (dark fon, accent rang, Noto Sans) — hech qanday
uchinchi tomon logotipi ishlatilmagan. Qayta yaratish:

    QT_QPA_PLATFORM=offscreen python packaging/make_icon.py

Talab: PySide6 va Pillow (faqat shu skript uchun; ilovaning o'zi Pillow'siz ishlaydi).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / "fintx" / "assets" / "fonts" / "NotoSans-Bold.ttf"
SIZE = 1024
SURFACE, ACCENT, INK = "#30302E", "#D97757", "#FAF9F5"


def main() -> int:
    app = QGuiApplication(sys.argv[:1])
    family = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(FONT)))[0]

    image = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)

    # macOS belgi panjarasi: 1024 dan 100 px hoshiya, burchak radiusi ~22%.
    margin = 100
    body = QRectF(margin, margin, SIZE - 2 * margin, SIZE - 2 * margin)
    painter.setBrush(QColor(SURFACE))
    painter.drawRoundedRect(body, 185, 185)

    # Uchta ustun — o'sib boruvchi balans.
    bar_width, gap, base = 96, 44, 600
    left = 512 - (3 * bar_width + 2 * gap) / 2
    painter.setBrush(QColor(ACCENT))
    for index, height in enumerate((120, 200, 290)):
        x = left + index * (bar_width + gap)
        painter.drawRoundedRect(QRectF(x, base - height, bar_width, height), 22, 22)

    font = QFont(family)
    font.setPixelSize(150)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(INK))
    painter.drawText(
        QRectF(margin, 620, SIZE - 2 * margin, 170), Qt.AlignmentFlag.AlignCenter, "FinTx"
    )
    painter.end()

    png = HERE / "icon.png"
    image.save(str(png))
    Image.open(png).save(
        HERE / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
