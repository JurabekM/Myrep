"""§16.4 — dark tema (v2 ranglari), shriftlar, loyihaga xos tanga ikonka."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import QApplication

R = {
    "fon": "#0F1115", "panel": "#171A21", "panel_alt": "#1E222B", "chegara": "#252A36",
    "matn": "#E6E8EE", "xira": "#98A0B3", "aksent": "#D98A5B", "aksent_toq": "#43281A",
    "ok": "#4ADE80", "ogoh": "#FBBF24", "xavf": "#F87171",
}
MONO = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "monospace"]
SANS = ["Segoe UI", "Inter", "Noto Sans", "DejaVu Sans", "Helvetica", "Arial"]
IKONKA = Path(__file__).resolve().parent / "assets" / "zarbxona.ico"
OLCHAMLAR = (16, 24, 32, 48, 64, 128, 256)

QSS = """
QWidget {{ background: {fon}; color: {matn}; }}
QMainWindow, QDialog {{ background: {fon}; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {fon}; border: none; }}
QFrame#karta {{ background: {panel}; border: 1px solid {chegara}; border-radius: 10px; }}
QFrame#karta QLabel, QFrame#karta QCheckBox, QFrame#karta QRadioButton {{
    background: transparent; }}
QLabel#sarlavha {{ font-size: 20px; font-weight: 600; background: transparent; }}
QLabel#karta_sarlavha {{ color: {aksent}; font-weight: 600; font-size: 14px; }}
QLabel#xira {{ color: {xira}; }}
QLabel#katta {{ font-size: 22px; font-weight: 600; }}
QLabel#ok {{ color: {ok}; }} QLabel#ogoh {{ color: {ogoh}; }} QLabel#xavf {{ color: {xavf}; }}
QListWidget#menyu {{ background: {panel}; border: none; border-right: 1px solid {chegara};
    padding: 8px 6px; outline: none; }}
QListWidget#menyu::item {{ padding: 10px 12px; border-radius: 8px; margin: 2px 0; color: {xira}; }}
QListWidget#menyu::item:selected {{ background: {aksent_toq}; color: {aksent}; }}
QListWidget#menyu::item:hover:!selected {{ background: {panel_alt}; color: {matn}; }}
QPushButton {{ background: {panel_alt}; border: 1px solid {chegara}; border-radius: 8px;
    padding: 7px 14px; color: {matn}; }}
QPushButton:hover {{ border-color: {aksent}; }}
QPushButton:pressed {{ background: {aksent_toq}; }}
QPushButton#asosiy {{ background: {aksent}; color: #1A0F08; border: none; font-weight: 600; }}
QPushButton#asosiy:hover {{ background: #E59C70; }}
QPushButton#xavfli {{ border-color: {xavf}; color: {xavf}; }}
QPushButton:disabled, QPushButton#asosiy:disabled, QPushButton#xavfli:disabled {{
    background: {panel}; color: #4B5263; border-color: {chegara}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit, QPlainTextEdit, QTextEdit {{
    background: {panel_alt}; border: 1px solid {chegara}; border-radius: 6px; padding: 5px 8px;
    selection-background-color: {aksent_toq}; selection-color: {matn}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateTimeEdit:focus {{
    border-color: {aksent}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled,
QDateTimeEdit:disabled {{ background: {panel}; color: #4B5263; border-color: {panel_alt}; }}
QCheckBox:disabled, QRadioButton:disabled, QLabel:disabled {{ color: #4B5263; }}
QComboBox QAbstractItemView {{ background: {panel_alt}; border: 1px solid {chegara};
    selection-background-color: {aksent_toq}; }}
QProgressBar {{ background: {panel_alt}; border: 1px solid {chegara}; border-radius: 6px;
    text-align: center; height: 18px; }}
QProgressBar::chunk {{ background: {aksent}; border-radius: 5px; }}
QPlainTextEdit#monitor {{ background: #000000; color: {ok}; border: 1px solid {chegara}; }}
QTableWidget {{ background: {panel}; gridline-color: {chegara}; border: 1px solid {chegara};
    border-radius: 6px; alternate-background-color: {panel_alt}; }}
QHeaderView::section {{ background: {panel_alt}; color: {xira}; border: none;
    border-bottom: 1px solid {chegara}; padding: 6px; }}
QTableWidget::item:selected {{ background: {aksent_toq}; color: {matn}; }}
QStatusBar {{ background: {panel}; color: {xira}; border-top: 1px solid {chegara}; }}
QScrollBar:vertical {{ background: {fon}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {chegara}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QToolTip {{ background: {panel_alt}; color: {matn}; border: 1px solid {chegara}; }}
QMessageBox {{ background: {panel}; }}
""".format(**R)


def mono_shrift(olcham: int = 10) -> QFont:
    f = QFont()
    f.setFamilies(MONO)
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSize(olcham)
    return f


def mavzuni_qol(ilova: QApplication) -> None:
    f = QFont()
    f.setFamilies(SANS)      # QSS orqali emas (§16.4)
    f.setPointSize(10)
    ilova.setFont(f)
    ilova.setStyle("Fusion")
    ilova.setStyleSheet(QSS)


def tanga(olcham: int) -> QPixmap:
    """Zarb qilingan tanga: mis gradient, bo'rtma halqa va «Z» harfi."""
    px = QPixmap(olcham, olcham)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(olcham)
    m = max(1.0, s * 0.04)
    doira = QRectF(m, m, s - 2 * m, s - 2 * m)
    g = QRadialGradient(QPointF(s * 0.35, s * 0.3), s * 0.75)
    g.setColorAt(0, QColor("#F2B48A"))
    g.setColorAt(0.55, QColor(R["aksent"]))
    g.setColorAt(1, QColor("#7A4225"))
    p.setBrush(QBrush(g))
    p.setPen(QPen(QColor("#43281A"), max(1.0, s * 0.03)))
    p.drawEllipse(doira)
    if olcham >= 24:
        ichki = doira.adjusted(s * 0.1, s * 0.1, -s * 0.1, -s * 0.1)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 230, 200, 140), max(1.0, s * 0.025), Qt.PenStyle.DotLine))
        p.drawEllipse(ichki)
    lg = QLinearGradient(0, 0, 0, s)
    lg.setColorAt(0, QColor("#2A160C"))
    lg.setColorAt(1, QColor("#43281A"))
    p.setPen(QPen(QBrush(lg), max(1.5, s * 0.11), Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    a, b = s * 0.34, s * 0.66
    p.drawPolyline([QPointF(a, a), QPointF(b, a), QPointF(a, b), QPointF(b, b)])
    p.end()
    return px


def ico_baytlari(olchamlar=OLCHAMLAR) -> bytes:
    """Ko'p o'lchamli ICO (PNG yozuvlar bilan) — Windows Vista+ standarti."""
    pnglar = []
    for o in olchamlar:
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        tanga(o).save(buf, "PNG")
        buf.close()
        pnglar.append((o, bytes(ba.data())))
    bosh = struct.pack("<HHH", 0, 1, len(pnglar))
    joy = 6 + 16 * len(pnglar)
    katalog, malumot = b"", b""
    for o, png in pnglar:
        katalog += struct.pack("<BBBBHHII", o % 256, o % 256, 0, 0, 1, 32, len(png),
                               joy + len(malumot))
        malumot += png
    return bosh + katalog + malumot


def ikonka() -> QIcon:
    if IKONKA.exists():
        i = QIcon(str(IKONKA))
        if not i.isNull():
            return i
    i = QIcon()
    for o in OLCHAMLAR:
        i.addPixmap(tanga(o))
    return i
