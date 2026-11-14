"""Tungi (dark) mavzu: neytral to'q fon, bitta aksent rang, to'liq boshqaruvlar uslubi.

Uslub Claude Code tungi rejimiga yaqin: yumshoq qora-kulrang fon, ko'zni charchatmaydigan matn, aksent faqat
tanlangan/faol joylarda. Ranglar bitta joyda (TOKENS); yorug' rejim yo'q: dastur har doim tungi.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

TOKENS = {
    "bg": "#111315",  # oyna foni
    "surface": "#1A1D21",  # ro'yxat, jadval, kiritish maydoni
    "surface_2": "#23272D",  # tugma, sarlavha, tooltip
    "border": "#2F353D",
    "text": "#E6E8EB",
    "muted": "#9AA3AD",
    "accent": "#4FD1C5",  # tanlangan/faol (teal)
    "accent_text": "#0B1214",
    "danger": "#F87171",  # xato, bloklangan, uzilgan
    "success": "#34D399",  # ulangan, ochiq
    "warning": "#FBBF24",
}


def stylesheet(t: dict[str, str] = TOKENS) -> str:
    return f"""
QWidget {{ background-color: {t["bg"]}; color: {t["text"]}; font-size: 13px; }}
QMainWindow, QDialog {{ background-color: {t["bg"]}; }}
QLabel {{ background: transparent; color: {t["text"]}; }}
QToolTip {{ background-color: {t["surface_2"]}; color: {t["text"]}; border: 1px solid {t["border"]};
            padding: 6px; border-radius: 6px; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background-color: {t["surface"]}; color: {t["text"]}; border: 1px solid {t["border"]};
    border-radius: 8px; padding: 6px 10px; selection-background-color: {t["accent"]};
    selection-color: {t["accent_text"]}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {t["accent"]}; }}
QLineEdit:disabled {{ color: {t["muted"]}; }}
QComboBox QAbstractItemView {{ background-color: {t["surface"]}; border: 1px solid {t["border"]};
    selection-background-color: {t["accent"]}; selection-color: {t["accent_text"]}; }}
QPushButton {{
    background-color: {t["surface_2"]}; color: {t["text"]}; border: 1px solid {t["border"]};
    border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ border-color: {t["accent"]}; }}
QPushButton:pressed {{ background-color: {t["surface"]}; }}
QPushButton:focus {{ border-color: {t["accent"]}; }}
QPushButton:disabled {{
    color: {t["muted"]}; background-color: {t["surface"]}; border-color: {t["surface"]}; }}
QTableWidget, QTableView, QListWidget, QListView, QTreeView {{
    background-color: {t["surface"]}; alternate-background-color: {t["surface_2"]};
    border: 1px solid {t["border"]}; border-radius: 8px; gridline-color: {t["border"]};
    selection-background-color: {t["accent"]}; selection-color: {t["accent_text"]}; outline: 0; }}
QTableWidget::item, QListWidget::item {{ padding: 4px; }}
QHeaderView::section {{
    background-color: {t["surface_2"]}; color: {t["muted"]}; border: none;
    border-bottom: 1px solid {t["border"]}; padding: 6px 8px; font-weight: 600; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {t["border"]}; border-radius: 5px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{ background: {t["muted"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QSplitter::handle {{ background: {t["border"]}; }}
QStatusBar {{ background: {t["surface"]}; color: {t["muted"]}; border-top: 1px solid {t["border"]}; }}
QMenu {{ background-color: {t["surface"]}; border: 1px solid {t["border"]}; padding: 4px; }}
QMenu::item:selected {{ background-color: {t["accent"]}; color: {t["accent_text"]}; }}
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QGroupBox {{ border: 1px solid {t["border"]}; border-radius: 8px; margin-top: 12px; padding-top: 8px; }}
QGroupBox::title {{ color: {t["muted"]}; subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QMessageBox {{ background-color: {t["bg"]}; }}
"""


def _palette(t: dict[str, str]) -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: t["bg"],
        QPalette.ColorRole.WindowText: t["text"],
        QPalette.ColorRole.Base: t["surface"],
        QPalette.ColorRole.AlternateBase: t["surface_2"],
        QPalette.ColorRole.Text: t["text"],
        QPalette.ColorRole.Button: t["surface_2"],
        QPalette.ColorRole.ButtonText: t["text"],
        QPalette.ColorRole.BrightText: t["danger"],
        QPalette.ColorRole.Highlight: t["accent"],
        QPalette.ColorRole.HighlightedText: t["accent_text"],
        QPalette.ColorRole.ToolTipBase: t["surface_2"],
        QPalette.ColorRole.ToolTipText: t["text"],
        QPalette.ColorRole.PlaceholderText: t["muted"],
        QPalette.ColorRole.Link: t["accent"],
    }
    for role, value in roles.items():
        palette.setColor(role, QColor(value))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(t["muted"]))
    return palette


def apply_theme(app: QApplication) -> None:
    """Fusion + tungi palitra + QSS. Yorug' rejim tizim sozlamasiga bog'liq emas."""
    app.setStyle("Fusion")
    app.setPalette(_palette(TOKENS))
    app.setStyleSheet(stylesheet(TOKENS))
    font = QFont(app.font())
    font.setPointSize(max(font.pointSize(), 11))
    app.setFont(font)
