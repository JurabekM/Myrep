"""Ilova belgisi: server shkafi (uch blok, holat chiroqlari). Kodda chiziladi.

`srv1.ico` (yorliq uchun) shu rasmdan olinadi: `python -m srv1_shell.icon`.
"""

import sys
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPixmap

ICON_FILE = Path(__file__).with_name("srv1.ico")
_BACKGROUND = QColor("#16202b")
_UNIT = QColor("#2b3b4d")
_SLOT = QColor("#5d7186")
_LEDS = (QColor("#3ddc84"), QColor("#3ddc84"), QColor("#f5b942"))


def draw_icon(size: int) -> QImage:
    """`size`×`size` shaffof fonli rasm."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    unit = size / 16
    painter.setBrush(_BACKGROUND)
    painter.drawRoundedRect(QRectF(0, 0, size, size), unit * 3, unit * 3)
    for row, led in enumerate(_LEDS):
        top = unit * (2.5 + row * 4)
        painter.setBrush(_UNIT)
        painter.drawRoundedRect(QRectF(unit * 2, top, unit * 12, unit * 3), unit, unit)
        painter.setBrush(_SLOT)
        painter.drawRoundedRect(
            QRectF(unit * 3.2, top + unit * 1.1, unit * 5, unit * 0.8), unit * 0.4, unit * 0.4
        )
        painter.setBrush(led)
        painter.drawEllipse(QRectF(unit * 11, top + unit * 0.9, unit * 1.2, unit * 1.2))
    painter.end()
    return image


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 256):
        icon.addPixmap(QPixmap.fromImage(draw_icon(size)))
    return icon


def write_ico(target: Path = ICON_FILE) -> bool:
    return draw_icon(256).save(str(target), "ICO")


if __name__ == "__main__":
    _app = QGuiApplication(sys.argv)
    sys.exit(0 if write_ico() else 1)
