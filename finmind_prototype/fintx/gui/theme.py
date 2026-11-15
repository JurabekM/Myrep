"""Desktop mavzusi: Claude Code dark uslubidagi ranglar va ilova ichidagi shrift.

Ranglar repo qoidasidagi (CLAUDE.md, "UI dizayn qoidasi") tokenlar bilan bir xil;
yangi rang qo'shilmagan, shuning uchun kontrast juftliklari ham o'sha: matn
`ink`/`inkMuted`/`accentText`/`danger`/`info` — `paper`, `sidebar`, `surface`
ustida ≥ 4.5:1; `accent`, `fieldLine`, `chart` — ≥ 3:1.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

PAPER = "#262624"
SIDEBAR = "#1F1E1D"
SURFACE = "#30302E"
LINE = "#4A4945"
FIELD_LINE = "#7D7B74"
INK = "#FAF9F5"
INK_MUTED = "#A6A39A"
ACCENT = "#D97757"
ACCENT_HOVER = "#E08A6D"
ACCENT_INK = "#1F1E1D"
ACCENT_TEXT = "#E8957A"
INFO = "#7FA9D6"
DANGER = "#E5786D"
CHART = "#3987E5"

FONT_FAMILY = "Noto Sans"
_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

STYLESHEET = f"""
* {{
    font-family: "{FONT_FAMILY}";
    font-size: 14px;
    color: {INK};
    outline: none;
}}
QMainWindow, QWidget#paper {{ background: {PAPER}; }}
QWidget#sidebar {{ background: {SIDEBAR}; border-right: 1px solid {LINE}; }}
QFrame#card {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 10px;
}}
QLabel {{ background: transparent; }}
QLabel#brand {{ font-size: 20px; font-weight: 700; }}
QLabel#pageTitle {{ font-size: 22px; font-weight: 700; }}
QLabel#cardTitle {{ font-size: 15px; font-weight: 700; }}
QLabel#muted, QLabel#fieldLabel {{ color: {INK_MUTED}; font-size: 13px; }}
QLabel#kpiValue {{ color: {ACCENT}; font-size: 24px; font-weight: 700; }}
QLabel#kpiUnit {{ color: {INK_MUTED}; font-size: 12px; }}
QLabel#error {{ color: {DANGER}; font-size: 13px; }}
QLabel#success {{ color: {INFO}; font-size: 13px; }}

QLineEdit, QComboBox, QDateEdit {{
    background: {PAPER};
    border: 1px solid {FIELD_LINE};
    border-radius: 6px;
    padding: 7px 10px;
    min-height: 20px;
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_INK};
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
    border: 2px solid {ACCENT};
    padding: 6px 9px;
}}
QComboBox::drop-down, QDateEdit::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {LINE};
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_INK};
}}

QPushButton {{
    background: transparent;
    border: 1px solid {FIELD_LINE};
    border-radius: 6px;
    padding: 8px 14px;
}}
QPushButton:hover {{ border-color: {INK}; }}
QPushButton:focus {{ border: 2px solid {ACCENT}; padding: 7px 13px; }}
QPushButton:disabled {{ color: {INK_MUTED}; border-color: {LINE}; }}
QPushButton#primary {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: {ACCENT_INK};
    font-weight: 700;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#primary:focus {{ border: 2px solid {INK}; }}
QPushButton#danger {{ color: {DANGER}; border-color: {DANGER}; }}
QPushButton#segment {{ border-radius: 0; border-color: {FIELD_LINE}; padding: 7px 12px; }}
QPushButton#segment:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: {ACCENT_INK};
    font-weight: 700;
}}
QPushButton#nav {{
    border: none;
    border-radius: 6px;
    padding: 9px 12px;
    text-align: left;
    color: {INK_MUTED};
}}
QPushButton#nav:hover {{ color: {INK}; background: {PAPER}; }}
QPushButton#nav:checked {{ color: {INK}; background: {SURFACE}; font-weight: 700; }}
QPushButton#nav:focus {{ border: 2px solid {ACCENT}; padding: 7px 10px; }}

QTableWidget {{
    background: {SURFACE};
    border: none;
    gridline-color: {LINE};
    selection-background-color: {LINE};
    selection-color: {INK};
}}
QTableWidget::item {{ padding: 6px; border-bottom: 1px solid {LINE}; }}
QHeaderView::section {{
    background: {SURFACE};
    color: {INK_MUTED};
    font-size: 12px;
    font-weight: 700;
    border: none;
    border-bottom: 1px solid {FIELD_LINE};
    padding: 6px 8px;
}}
QTableCornerButton::section {{ background: {SURFACE}; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {LINE}; border-radius: 5px; min-width: 24px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QMessageBox, QDialog {{ background: {SURFACE}; }}
QToolTip {{
    background: {SIDEBAR};
    color: {INK};
    border: 1px solid {FIELD_LINE};
    padding: 4px 6px;
}}
QCalendarWidget QWidget {{ background: {SURFACE}; alternate-background-color: {PAPER}; }}
QCalendarWidget QAbstractItemView {{
    selection-background-color: {ACCENT};
    selection-color: {ACCENT_INK};
}}
"""


def apply_theme(app: QApplication) -> None:
    """Shriftni yuklaydi va dark mavzuni butun ilovaga qo'llaydi."""
    for name in ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"):
        QFontDatabase.addApplicationFont(str(_FONT_DIR / name))
    app.setStyle("Fusion")
    app.setFont(QFont(FONT_FAMILY))
    # Oyna ochilganda oq "chaqnamasligi" uchun palitra ham darhol qoraytiriladi.
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, PAPER),
        (QPalette.ColorRole.Base, PAPER),
        (QPalette.ColorRole.AlternateBase, SURFACE),
        (QPalette.ColorRole.Button, SURFACE),
        (QPalette.ColorRole.ToolTipBase, SIDEBAR),
        (QPalette.ColorRole.WindowText, INK),
        (QPalette.ColorRole.Text, INK),
        (QPalette.ColorRole.ButtonText, INK),
        (QPalette.ColorRole.ToolTipText, INK),
        (QPalette.ColorRole.PlaceholderText, INK_MUTED),
        (QPalette.ColorRole.Highlight, ACCENT),
        (QPalette.ColorRole.HighlightedText, ACCENT_INK),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
