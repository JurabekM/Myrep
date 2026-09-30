"""Jonli grafik — bitta o'lchov vaqt bo'yicha (§3.2 taklif): chiziq, nishon/chegara
chizig'i, sovutish va pauza oraliqlari, kursor chizig'i + tooltip.

Dizayn qoidalari (dataviz qo'llanmasi): bitta y-o'q (ikki o'lchov — ikki grafik),
2px chiziq, soch-tolali setka, qiymat — oxirida to'g'ridan-to'g'ri yorliq,
matn seriya rangida emas. Ranglar qorong'i panel foni (#171A21) ga nisbatan
validator bilan tekshirilgan: #3987e5 / #199e70 — hamma tekshiruv PASS.
"""

from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from app.theme import R, SANS

TEZLIK_RANG = "#3987e5"       # kategoriya 1 (qorong'i qadam)
CPU_RANG = "#199e70"          # kategoriya 3 (qorong'i qadam)
SETKA = "#252A36"
OQ_MATN = R["matn"]
XIRA = R["xira"]
SOVUTISH_FON = QColor(152, 160, 179, 28)
PAUZA_FON = QColor(250, 178, 25, 34)
MAX_NAMUNA = 600              # ~10 daqiqa (1 namuna/s)
CHAP, ONG, TEPA, PAST = 48, 64, 30, 26


def chiroyli_qadam(v: float) -> float:
    """1, 2, 5 × 10ⁿ dan v dan kichik bo'lmagan eng kichigi."""
    if v <= 0:
        return 1.0
    k = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 5, 10):
        if v <= m * k + 1e-12:
            return m * k
    return 10 * k


def chiroyli_oq(v: float, belgilar: int = 4) -> tuple[float, float]:
    """(yuqori chegara, qadam): belgilar butun «chiroyli» sonlarda — 0, 5, 10, 15, 20…"""
    qadam = chiroyli_qadam(max(v, 1e-9) / belgilar)
    return qadam * max(1, math.ceil(v / qadam - 1e-9)), qadam


def qiymat_matni(v: float, birlik: str) -> str:
    if birlik == "%":
        return f"{v:.0f} %" if v >= 1 or v == 0 else f"{v:.1f} %"
    if v >= 100 or float(v).is_integer():
        return f"{v:,.0f}".replace(",", " ")
    return f"{v:.1f}"


class JonliGrafik(QWidget):
    """`qosh(t, qiymat, holat)` — namuna; `chegara` — gorizontal nishon chizig'i."""

    def __init__(self, sarlavha: str, birlik: str, rang: str, chegara_nomi: str):
        super().__init__()
        self.sarlavha, self.birlik, self.rang, self.chegara_nomi = \
            sarlavha, birlik, QColor(rang), chegara_nomi
        self.namunalar: deque[tuple[float, float, str]] = deque(maxlen=MAX_NAMUNA)
        self.chegara: float | None = None
        self.kursor: int | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    # --- ma'lumot -----------------------------------------------------------------

    def qosh(self, t: float, qiymat: float, holat: str, chegara: float | None) -> None:
        self.namunalar.append((t, qiymat, holat))
        self.chegara = chegara
        self.update()

    def tozala(self) -> None:
        self.namunalar.clear()
        self.chegara = None
        self.kursor = None
        self.update()

    def y_max(self) -> float:
        m = max((v for _, v, _ in self.namunalar), default=0.0)
        if self.chegara:
            m = max(m, self.chegara)
        return chiroyli_oq(m * 1.1)[0]

    # --- geometriya ---------------------------------------------------------------

    def _maydon(self) -> QRectF:
        return QRectF(CHAP, TEPA, max(10, self.width() - CHAP - ONG),
                      max(10, self.height() - TEPA - PAST))

    def _x(self, t: float, m: QRectF, t0: float, t1: float) -> float:
        return m.left() + (t - t0) / max(1e-9, t1 - t0) * m.width()

    def _y(self, v: float, m: QRectF, ymax: float) -> float:
        return m.bottom() - v / ymax * m.height()

    def _oraliq(self) -> tuple[float, float]:
        t0 = self.namunalar[0][0] if self.namunalar else 0.0
        t1 = self.namunalar[-1][0] if self.namunalar else 1.0
        return t0, max(t1, t0 + 10.0)

    # --- chizish ------------------------------------------------------------------

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = QFont()
        f.setFamilies(SANS)
        f.setPointSize(9)
        p.setFont(f)
        m = self._maydon()
        ymax = self.y_max()
        ymax, qadam = chiroyli_oq(ymax)
        t0, t1 = self._oraliq()

        p.setPen(QColor(OQ_MATN))
        p.drawText(QRectF(0, 4, self.width(), 20), Qt.AlignmentFlag.AlignLeft,
                   f"  {self.sarlavha}")

        # sovutish/pauza oraliqlari — fon bo'yog'i (seriya emas)
        for i, (t, _, h) in enumerate(self.namunalar):
            if h == "ish" or i == 0:
                continue
            tp = self.namunalar[i - 1][0]
            x0, x1 = self._x(tp, m, t0, t1), self._x(t, m, t0, t1)
            p.fillRect(QRectF(x0, m.top(), max(1.0, x1 - x0), m.height()),
                       PAUZA_FON if h == "pauza" else SOVUTISH_FON)

        # setka — soch-tolali, yaxlit
        p.setPen(QPen(QColor(SETKA), 1))
        for k in range(round(ymax / qadam) + 1):
            v = k * qadam
            y = self._y(v, m, ymax)
            p.drawLine(QPointF(m.left(), y), QPointF(m.right(), y))
            p.setPen(QColor(XIRA))
            p.drawText(QRectF(0, y - 8, CHAP - 6, 16), Qt.AlignmentFlag.AlignRight
                       | Qt.AlignmentFlag.AlignVCenter, qiymat_matni(v, self.birlik))
            p.setPen(QPen(QColor(SETKA), 1))
        p.setPen(QColor(XIRA))
        for t, al in ((t0, Qt.AlignmentFlag.AlignLeft), (t1, Qt.AlignmentFlag.AlignRight)):
            p.drawText(QRectF(m.left(), m.bottom() + 4, m.width(), 18), al, f"{t:.0f} s")

        # nishon / chegara — uzuq chiziq (bu setka emas, chegara) + yorliq
        if self.chegara:
            y = self._y(self.chegara, m, ymax)
            p.setPen(QPen(QColor(XIRA), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(m.left(), y), QPointF(m.right(), y))
            p.setPen(QColor(XIRA))
            p.drawText(QRectF(m.right() + 4, y - 16, ONG - 4, 16),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                       self.chegara_nomi)

        if not self.namunalar:
            p.setPen(QColor(XIRA))
            p.drawText(m, Qt.AlignmentFlag.AlignCenter, "zarb boshlanganda grafik chiziladi")
            return

        # chiziq — 2px, yumaloq
        yol = QPainterPath()
        for i, (t, v, _) in enumerate(self.namunalar):
            pt = QPointF(self._x(t, m, t0, t1), self._y(v, m, ymax))
            yol.moveTo(pt) if i == 0 else yol.lineTo(pt)
        p.setPen(QPen(self.rang, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.drawPath(yol)

        # oxirgi qiymat — to'g'ridan-to'g'ri yorliq (matn siyohda, rang — nuqtada)
        t, v, _ = self.namunalar[-1]
        oxir = QPointF(self._x(t, m, t0, t1), self._y(v, m, ymax))
        p.setBrush(self.rang)
        p.setPen(QPen(QColor(R["panel"]), 2))
        p.drawEllipse(oxir, 4.5, 4.5)
        p.setPen(QColor(OQ_MATN))
        y_yorliq = oxir.y() - 1
        if self.chegara:
            yc = self._y(self.chegara, m, ymax)
            if yc - 18 <= y_yorliq <= yc + 16:      # nishon yorlig'i bilan to'qnashmasin
                y_yorliq = yc + 2 if oxir.y() >= yc else yc - 34
        p.drawText(QRectF(m.right() + 4, y_yorliq, ONG - 4, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                   qiymat_matni(v, self.birlik))

        # kursor chizig'i
        if self.kursor is not None and self.kursor < len(self.namunalar):
            tk, vk, _ = self.namunalar[self.kursor]
            x = self._x(tk, m, t0, t1)
            p.setPen(QPen(QColor(XIRA), 1))
            p.drawLine(QPointF(x, m.top()), QPointF(x, m.bottom()))
            p.setBrush(self.rang)
            p.setPen(QPen(QColor(R["panel"]), 2))
            p.drawEllipse(QPointF(x, self._y(vk, m, ymax)), 4.5, 4.5)

    # --- hover: kursor X ni topadi --------------------------------------------------

    def eng_yaqin(self, x: float) -> int | None:
        if not self.namunalar:
            return None
        m = self._maydon()
        t0, t1 = self._oraliq()
        return min(range(len(self.namunalar)),
                   key=lambda i: abs(self._x(self.namunalar[i][0], m, t0, t1) - x))

    def tooltip_matni(self, i: int) -> str:
        t, v, h = self.namunalar[i]
        holat = {"ish": "", "sovutish": " · sovutish", "pauza": " · pauza"}[h]
        qator = (f"<b style='font-size:13px'>{qiymat_matni(v, self.birlik)}</b> "
                 f"<span style='color:{XIRA}'>{self.sarlavha.lower()}</span>")
        if self.chegara:
            qator += (f"<br>{qiymat_matni(self.chegara, self.birlik)} "
                      f"<span style='color:{XIRA}'>{self.chegara_nomi}</span>")
        return f"{qator}<br><span style='color:{XIRA}'>{t:.0f} s{holat}</span>"

    def mouseMoveEvent(self, e) -> None:
        i = self.eng_yaqin(e.position().x())
        self.kursor = i
        self.update()
        if i is not None:
            QToolTip.showText(e.globalPosition().toPoint(), self.tooltip_matni(i), self)

    def leaveEvent(self, _e) -> None:
        self.kursor = None
        QToolTip.hideText()
        self.update()
