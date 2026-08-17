"""Icon helpers.

``qtawesome`` is used when installed; otherwise a compact vector fallback is
painted so the application never ships with empty buttons.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from app.ui.styles.theme import COLORS

try:  # pragma: no cover - optional dependency
    import qtawesome as qta

    _HAS_QTA = True
except Exception:  # pragma: no cover
    qta = None  # type: ignore[assignment]
    _HAS_QTA = False

#: Logical name -> Font Awesome 5 identifier.
ICON_MAP: dict[str, str] = {
    "projects": "fa5s.city",
    "estimate": "fa5s.list-ol",
    "purchase": "fa5s.shopping-cart",
    "warehouse": "fa5s.warehouse",
    "materials": "fa5s.boxes",
    "counterparty": "fa5s.handshake",
    "expense": "fa5s.money-bill-wave",
    "report": "fa5s.chart-bar",
    "audit": "fa5s.history",
    "settings": "fa5s.cog",
    "stage": "fa5s.tasks",
    "add": "fa5s.plus",
    "edit": "fa5s.pen",
    "delete": "fa5s.trash",
    "archive": "fa5s.box-open",
    "refresh": "fa5s.sync-alt",
    "search": "fa5s.search",
    "filter": "fa5s.filter",
    "excel": "fa5s.file-excel",
    "pdf": "fa5s.file-pdf",
    "approve": "fa5s.check",
    "reject": "fa5s.times",
    "back": "fa5s.arrow-left",
    "open": "fa5s.external-link-alt",
    "up": "fa5s.arrow-up",
    "down": "fa5s.arrow-down",
    "user": "fa5s.user",
    "logout": "fa5s.sign-out-alt",
    "menu": "fa5s.bars",
    "calendar": "fa5s.calendar-alt",
    "attach": "fa5s.paperclip",
    "money": "fa5s.coins",
    "warning": "fa5s.exclamation-triangle",
    "info": "fa5s.info-circle",
    "doc": "fa5s.file-alt",
    "save": "fa5s.save",
    "copy": "fa5s.copy",
    "compare": "fa5s.code-branch",
}

#: Single-glyph fallback used when qtawesome is missing.
_FALLBACK_GLYPH: dict[str, str] = {
    "projects": "▦",
    "estimate": "≡",
    "purchase": "🛒",
    "warehouse": "▣",
    "materials": "▤",
    "counterparty": "◫",
    "expense": "₮",
    "report": "▥",
    "audit": "◷",
    "settings": "⚙",
    "stage": "▷",
    "add": "+",
    "edit": "✎",
    "delete": "🗑",
    "archive": "▽",
    "refresh": "⟳",
    "search": "⌕",
    "filter": "⚟",
    "excel": "X",
    "pdf": "P",
    "approve": "✓",
    "reject": "✕",
    "back": "←",
    "open": "↗",
    "up": "↑",
    "down": "↓",
    "user": "◍",
    "logout": "⏻",
    "menu": "☰",
    "calendar": "▤",
    "attach": "📎",
    "money": "₮",
    "warning": "!",
    "info": "i",
    "doc": "▢",
    "save": "▣",
    "copy": "⧉",
    "compare": "⇄",
}


def icon(name: str, color: str | None = None, size: int = 18) -> QIcon:
    """Return the icon registered under ``name`` in the requested ``color``."""
    tint = color or COLORS.text_muted
    if _HAS_QTA and name in ICON_MAP:
        try:
            return qta.icon(ICON_MAP[name], color=tint)
        except Exception:  # pragma: no cover - font not available
            pass
    return _fallback_icon(name, tint, size)


def _fallback_icon(name: str, color: str, size: int) -> QIcon:
    """Paint a simple glyph pixmap as a stand-in icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(QColor(color)))
    font = painter.font()
    font.setPointSizeF(size * 0.62)
    painter.setFont(font)
    painter.drawText(
        QRectF(0, 0, size, size),
        Qt.AlignmentFlag.AlignCenter,
        _FALLBACK_GLYPH.get(name, "•"),
    )
    painter.end()
    return QIcon(pixmap)
