"""Ilova belgilarini chizadi. Uchinchi tomon logotipi ishlatilmagan: dark fon, accent ustunlar.

Ikki xil ko'rinish kerak, chunki bitta rasm hamma joyga yaramaydi:

- "to'liq" — macOS uchun (`packaging/icon.png`, 1024 px): Apple panjarasidagi hoshiya
  bilan, ostida "FinTx" yozuvi. Dock'da katta ko'rsatiladi.
- "ixcham" — Windows va oyna sarlavhasi uchun: hoshiyasiz, yozuvsiz, yo'g'on ustunlar.
  16–32 px da ham o'qiladi. Undan `packaging/icon.ico` (exe va o'rnatuvchi) hamda
  `fintx/assets/icons/fintx-<o'lcham>.png` (ishlayotgan oyna va vazifalar paneli) olinadi.

Qayta yaratish:  QT_QPA_PLATFORM=offscreen python packaging/make_icon.py
Talab: PySide6 va Pillow (faqat shu skript uchun; ilovaning o'zi Pillow'siz ishlaydi).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter, QPen

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "fintx" / "assets"
FONT = ASSETS / "fonts" / "NotoSans-Bold.ttf"
CANVAS = 1024
SURFACE, BORDER, ACCENT, INK = "#30302E", "#7D7B74", "#D97757", "#FAF9F5"
WINDOW_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def _canvas() -> tuple[QImage, QPainter]:
    image = QImage(CANVAS, CANVAS, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    return image, painter


def _bars(painter: QPainter, *, width: float, gap: float, base: float, heights, radius) -> None:
    left = CANVAS / 2 - (3 * width + 2 * gap) / 2
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(ACCENT))
    for index, height in enumerate(heights):
        x = left + index * (width + gap)
        painter.drawRoundedRect(QRectF(x, base - height, width, height), radius, radius)


def draw_full(family: str) -> QImage:
    """macOS: 100 px hoshiya, burchak radiusi ~22%, ostida yozuv."""
    image, painter = _canvas()
    margin = 100
    painter.setBrush(QColor(SURFACE))
    painter.drawRoundedRect(
        QRectF(margin, margin, CANVAS - 2 * margin, CANVAS - 2 * margin), 185, 185
    )
    _bars(painter, width=96, gap=44, base=600, heights=(120, 200, 290), radius=22)
    font = QFont(family)
    font.setPixelSize(150)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(INK))
    painter.drawText(
        QRectF(margin, 620, CANVAS - 2 * margin, 170), Qt.AlignmentFlag.AlignCenter, "FinTx"
    )
    painter.end()
    return image


def draw_compact() -> QImage:
    """Windows va oyna sarlavhasi: butun maydonni egallaydi, faqat yo'g'on ustunlar."""
    image, painter = _canvas()
    inset, border = 36, 30
    painter.setBrush(QColor(SURFACE))
    # Och chegara belgini qora vazifalar panelida fondan ajratadi.
    painter.setPen(QPen(QColor(BORDER), border))
    painter.drawRoundedRect(QRectF(inset, inset, CANVAS - 2 * inset, CANVAS - 2 * inset), 210, 210)
    _bars(painter, width=176, gap=72, base=812, heights=(280, 440, 600), radius=40)
    painter.end()
    return image


def _to_pillow(image: QImage, folder: Path, name: str) -> Image.Image:
    path = folder / name
    image.save(str(path))
    return Image.open(path).convert("RGBA")


def main() -> int:
    app = QGuiApplication(sys.argv[:1])
    family = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(FONT)))[0]

    with tempfile.TemporaryDirectory() as tmp:
        full = _to_pillow(draw_full(family), Path(tmp), "full.png")
        compact = _to_pillow(draw_compact(), Path(tmp), "compact.png")

        full.save(HERE / "icon.png")
        compact.save(HERE / "icon.ico", sizes=[(size, size) for size in ICO_SIZES])

        icons = ASSETS / "icons"
        icons.mkdir(exist_ok=True)
        for old in icons.glob("fintx-*.png"):
            old.unlink()
        for size in WINDOW_SIZES:
            compact.resize((size, size), Image.Resampling.LANCZOS).save(icons / f"fintx-{size}.png")
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
