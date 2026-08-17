"""Zamonaviy dark tema."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

BG = "#0B0E14"
SURFACE = "#141A24"
SURFACE_2 = "#1B2330"
SURFACE_3 = "#232C3B"
BORDER = "#2A3547"
BORDER_SOFT = "#1F2836"

TEXT = "#E6EDF3"
MUTED = "#8B98A9"
DIM = "#5F6D80"

PRIMARY = "#6E8BFF"
ACCENT = "#3FD5C8"
VIOLET = "#A371F7"
OK = "#3FB950"
WARN = "#E3B341"
FAIL = "#F85149"
ATTACK = "#FF7B72"
INFO = "#58A6FF"

SEVERITY = {
    "KRITIK": FAIL,
    "YUQORI": "#FF9E64",
    "O'RTA": WARN,
    "NAZORAT": DIM,
}

OUTCOME = {
    "BROKEN": FAIL,
    "SAFE": OK,
    "STRUCTURAL": WARN,
    "INFO": INFO,
    "N/A": DIM,
}


def mono_font(size: int = 10) -> QFont:
    for name in ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"):
        if name in QFontDatabase.families():
            f = QFont(name, size)
            f.setStyleHint(QFont.StyleHint.Monospace)
            return f
    f = QFont("monospace", size)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def ui_font(size: int = 10, bold: bool = False) -> QFont:
    for name in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Arial"):
        if name in QFontDatabase.families():
            f = QFont(name, size)
            f.setBold(bold)
            return f
    f = QFont()
    f.setPointSize(size)
    f.setBold(bold)
    return f


def apply_palette(app) -> None:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(BG))
    p.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Base, QColor(SURFACE))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE_2))
    p.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Button, QColor(SURFACE_2))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    p.setColor(QPalette.ColorRole.Highlight, QColor(PRIMARY))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#0B0E14"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(SURFACE_3))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    app.setPalette(p)
    app.setFont(ui_font(10))


QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow, QDialog {{ background: {BG}; }}

/* ---------- Sidebar ---------- */
#Sidebar {{
    background: {SURFACE};
    border-right: 1px solid {BORDER_SOFT};
}}
#SidebarTitle {{
    color: {TEXT};
    font-size: 17px;
    font-weight: 700;
    padding: 18px 18px 2px 18px;
}}
#SidebarSub {{
    color: {DIM};
    font-size: 11px;
    padding: 0 18px 14px 18px;
}}
#NavButton {{
    background: transparent;
    border: none;
    border-left: 3px solid transparent;
    text-align: left;
    padding: 11px 16px;
    color: {MUTED};
    font-size: 13px;
    border-radius: 0;
}}
#NavButton:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
#NavButton:checked {{
    background: {SURFACE_2};
    color: {TEXT};
    border-left: 3px solid {PRIMARY};
    font-weight: 600;
}}

/* ---------- Cards ---------- */
#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 12px;
}}
#CardTitle {{ font-size: 14px; font-weight: 600; color: {TEXT}; }}
#CardSub   {{ font-size: 11px; color: {DIM}; }}
#PageTitle {{ font-size: 22px; font-weight: 700; color: {TEXT}; }}
#PageSub   {{ font-size: 12px; color: {MUTED}; }}

#StatValue {{ font-size: 26px; font-weight: 700; color: {TEXT}; }}
#StatLabel {{ font-size: 11px; color: {DIM}; text-transform: uppercase; }}

/* ---------- Buttons ---------- */
QPushButton {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    color: {TEXT};
}}
QPushButton:hover  {{ background: {SURFACE_3}; border-color: {PRIMARY}; }}
QPushButton:pressed{{ background: {BORDER}; }}
QPushButton:disabled {{ color: {DIM}; border-color: {BORDER_SOFT}; background: {SURFACE}; }}
QPushButton#Primary {{
    background: {PRIMARY}; border: none; color: #0B0E14; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: #8AA1FF; }}
QPushButton#Danger {{ background: transparent; border: 1px solid {FAIL}; color: {FAIL}; }}
QPushButton#Danger:hover {{ background: rgba(248,81,73,0.12); }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {BORDER}; color: {MUTED}; }}
QPushButton#Ghost:hover {{ color: {TEXT}; border-color: {PRIMARY}; }}

/* ---------- Segmented (mode) ---------- */
QPushButton#Seg {{
    background: {SURFACE_2}; border: 1px solid {BORDER};
    border-radius: 0; padding: 7px 20px; color: {MUTED};
}}
QPushButton#Seg:checked {{
    background: {PRIMARY}; color: #0B0E14; font-weight: 600; border-color: {PRIMARY};
}}
QPushButton#SegFirst {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
QPushButton#SegLast  {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}

/* ---------- Inputs ---------- */
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QComboBox {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {PRIMARY};
    selection-color: #0B0E14;
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: {PRIMARY}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2}; border: 1px solid {BORDER};
    selection-background-color: {PRIMARY}; selection-color: #0B0E14;
}}

/* ---------- Tables ---------- */
QTableWidget, QTreeWidget, QListWidget {{
    background: {SURFACE};
    border: 1px solid {BORDER_SOFT};
    border-radius: 10px;
    gridline-color: {BORDER_SOFT};
    alternate-background-color: {SURFACE_2};
}}
QTableWidget::item, QTreeWidget::item, QListWidget::item {{ padding: 5px 6px; }}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
    background: {SURFACE_3}; color: {TEXT};
}}
QHeaderView::section {{
    background: {SURFACE_2};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 6px;
    font-size: 11px;
    font-weight: 600;
}}
QTableCornerButton::section {{ background: {SURFACE_2}; border: none; }}

/* ---------- Misc ---------- */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {BORDER}; background: {SURFACE_2};
}}
QCheckBox::indicator:checked {{ background: {PRIMARY}; border-color: {PRIMARY}; }}
QProgressBar {{
    background: {SURFACE_2}; border: none; border-radius: 5px;
    height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 5px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {DIM}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 5px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QSplitter::handle {{ background: {BORDER_SOFT}; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical {{ height: 3px; }}
QToolTip {{
    background: {SURFACE_3}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 6px; padding: 6px;
}}
QStatusBar {{ background: {SURFACE}; color: {MUTED}; border-top: 1px solid {BORDER_SOFT}; }}
QScrollArea {{ border: none; background: transparent; }}
QGroupBox {{
    border: 1px solid {BORDER_SOFT}; border-radius: 10px;
    margin-top: 14px; padding-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {MUTED};
}}
"""
