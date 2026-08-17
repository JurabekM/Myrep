"""Modern dark theme — QSS and colors."""
from __future__ import annotations

from ..config import PALETTE as P

QSS = f"""
* {{
    font-family: 'Segoe UI Variable', 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
    color: {P['text']};
    outline: none;
}}
QWidget {{ background: {P['bg']}; }}
QMainWindow, QDialog {{ background: {P['bg']}; }}
/* Labels must never paint their own background — let the card show through */
QLabel {{ background: transparent; }}

/* ---------------- Sidebar ---------------- */
#Sidebar {{
    background: {P['surface']};
    border-right: 1px solid {P['border']};
}}
#Brand {{
    font-size: 18px; font-weight: 700; color: {P['text']};
    padding: 18px 18px 4px; letter-spacing: -0.3px;
}}
#BrandSub {{
    font-size: 11px; color: {P['faint']}; padding: 0 18px 14px;
    letter-spacing: 0.6px; text-transform: uppercase;
}}
#NavButton {{
    background: transparent; border: none; border-radius: 9px;
    text-align: left; padding: 10px 14px; margin: 2px 10px;
    color: {P['muted']}; font-size: 13.5px; font-weight: 500;
}}
#NavButton:hover {{ background: {P['surface2']}; color: {P['text']}; }}
#NavButton:checked {{
    background: {P['surface3']}; color: {P['text']}; font-weight: 600;
    border-left: 3px solid {P['accent']};
}}
#NavSection {{
    color: {P['faint']}; font-size: 10.5px; font-weight: 700;
    padding: 14px 20px 4px; letter-spacing: 1.1px; text-transform: uppercase;
    background: transparent;
}}

/* ---------------- Cards ---------------- */
#Card {{
    background: {P['surface']};
    border: 1px solid {P['border']};
    border-radius: 14px;
}}
#CardTitle {{
    font-size: 14px; font-weight: 650; color: {P['text']};
    background: transparent; padding: 0;
}}
#CardHint {{ font-size: 11.5px; color: {P['muted']}; background: transparent; }}
#StatKey {{
    font-size: 10.5px; color: {P['muted']}; letter-spacing: 0.8px;
    text-transform: uppercase; background: transparent;
}}
#StatValue {{
    font-size: 24px; font-weight: 700; color: {P['text']}; background: transparent;
}}
#StatDelta {{ font-size: 11.5px; color: {P['muted']}; background: transparent; }}
#PageTitle {{
    font-size: 22px; font-weight: 700; letter-spacing: -0.3px;
    background: transparent;
}}
#PageSub {{ font-size: 12.5px; color: {P['muted']}; background: transparent; }}
#Hint {{ color: {P['muted']}; font-size: 12px; background: transparent; }}
#Mono {{ font-family: 'Cascadia Mono', 'Consolas', monospace; font-size: 12px; }}

/* ---------------- Buttons ---------------- */
QPushButton {{
    background: {P['surface2']};
    border: 1px solid {P['border2']};
    border-radius: 8px;
    padding: 7px 15px;
    color: {P['text']};
    font-weight: 500;
}}
QPushButton:hover {{ background: {P['surface3']}; border-color: {P['accent']}; }}
QPushButton:pressed {{ background: {P['surface']}; }}
QPushButton:disabled {{ color: {P['faint']}; background: {P['surface']};
                        border-color: {P['border']}; }}
QPushButton#Primary {{
    background: {P['accent']}; border: none; color: #06121F; font-weight: 650;
}}
QPushButton#Primary:hover {{ background: #6BAEFF; }}
QPushButton#Primary:disabled {{ background: {P['surface2']}; color: {P['faint']}; }}
QPushButton#Success {{ background: {P['success']}; border: none; color: #06211A;
                       font-weight: 650; }}
QPushButton#Danger {{ background: transparent; border: 1px solid {P['danger']};
                      color: {P['danger']}; }}
QPushButton#Danger:hover {{ background: rgba(248,113,113,0.12); }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {P['border2']}; }}
QPushButton#Ghost:hover {{ background: {P['surface2']}; }}
QPushButton#Chip {{
    background: {P['surface2']}; border: 1px solid {P['border2']};
    border-radius: 15px; padding: 5px 13px; font-size: 12px; color: {P['muted']};
}}
QPushButton#Chip:hover {{ color: {P['text']}; border-color: {P['accent']}; }}

QToolButton {{
    background: transparent; border: 1px solid transparent; border-radius: 7px;
    padding: 5px 9px; color: {P['muted']};
}}
QToolButton:hover {{ background: {P['surface2']}; color: {P['text']}; }}
QToolButton:checked {{ background: {P['surface3']}; color: {P['accent']}; }}

/* ---------------- Inputs ---------------- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {P['surface2']};
    border: 1px solid {P['border2']};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {P['accent']};
    selection-color: #06121F;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {P['accent']}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {P['faint']}; }}
QLineEdit[state="error"] {{ border-color: {P['danger']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {P['muted']}; margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {P['surface2']}; border: 1px solid {P['border2']};
    border-radius: 8px; padding: 4px;
    selection-background-color: {P['surface3']};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {P['surface3']}; border: none; width: 16px;
}}

QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {P['border2']};
    background: {P['surface2']};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {P['accent']}; border-color: {P['accent']};
}}

/* ---------------- Tables ---------------- */
QTableView, QTreeView, QListView {{
    background: {P['surface']};
    alternate-background-color: {P['surface2']};
    border: 1px solid {P['border']};
    border-radius: 10px;
    gridline-color: {P['border']};
    selection-background-color: rgba(76,154,255,0.28);
    selection-color: {P['text']};
}}
QTableView::item, QTreeView::item, QListView::item {{ padding: 4px 6px; }}
QTableView::item:selected {{ background: rgba(76,154,255,0.28); }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background: {P['surface2']};
    color: {P['muted']};
    padding: 7px 9px;
    border: none;
    border-right: 1px solid {P['border']};
    border-bottom: 1px solid {P['border']};
    font-weight: 600; font-size: 11.5px;
}}
QHeaderView::section:hover {{ background: {P['surface3']}; color: {P['text']}; }}
QTableCornerButton::section {{ background: {P['surface2']}; border: none; }}

/* ---------------- Tabs ---------------- */
QTabWidget::pane {{
    border: 1px solid {P['border']}; border-radius: 12px;
    background: {P['surface']}; top: -1px;
}}
QTabBar::tab {{
    background: transparent; color: {P['muted']};
    padding: 8px 16px; margin-right: 3px;
    border-top-left-radius: 9px; border-top-right-radius: 9px;
    border: 1px solid transparent; border-bottom: none;
}}
QTabBar::tab:selected {{
    background: {P['surface']}; color: {P['text']};
    border-color: {P['border']}; font-weight: 600;
}}
QTabBar::tab:hover:!selected {{ color: {P['text']}; background: {P['surface2']}; }}

/* ---------------- Scrollbars ---------------- */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {P['border2']}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {P['faint']}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background: {P['border2']}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {P['faint']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------------- Misc ---------------- */
QProgressBar {{
    background: {P['surface2']}; border: none; border-radius: 5px;
    height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {P['accent']}; border-radius: 5px; }}

QSplitter::handle {{ background: {P['border']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

QGroupBox {{
    border: 1px solid {P['border']}; border-radius: 11px;
    margin-top: 14px; padding-top: 12px; background: {P['surface']};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 14px; padding: 0 6px;
    color: {P['muted']}; font-weight: 600; font-size: 11.5px;
}}

QMenu {{
    background: {P['surface2']}; border: 1px solid {P['border2']};
    border-radius: 9px; padding: 5px;
}}
QMenu::item {{ padding: 7px 26px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {P['surface3']}; }}
QMenu::separator {{ height: 1px; background: {P['border']}; margin: 5px 8px; }}

QMenuBar {{ background: {P['surface']}; border-bottom: 1px solid {P['border']}; }}
QMenuBar::item {{ padding: 6px 12px; border-radius: 6px; background: transparent; }}
QMenuBar::item:selected {{ background: {P['surface2']}; }}

QStatusBar {{
    background: {P['surface']}; border-top: 1px solid {P['border']};
    color: {P['muted']};
}}
QStatusBar::item {{ border: none; }}

QToolTip {{
    background: {P['surface3']}; color: {P['text']};
    border: 1px solid {P['border2']}; border-radius: 7px; padding: 6px 9px;
}}

QListWidget#DatasetList::item {{
    padding: 9px 11px; border-radius: 8px; margin: 2px 0;
}}
QListWidget#DatasetList::item:selected {{ background: {P['surface3']}; }}

#Toast {{
    background: {P['surface3']}; border: 1px solid {P['border2']};
    border-radius: 11px; padding: 12px 18px; font-size: 13px;
}}
#Overlay {{ background: rgba(11,15,20,0.72); }}
"""


def badge_style(color: str) -> str:
    return (f"background: rgba(255,255,255,0.04); color: {color};"
            f"border: 1px solid {color}; border-radius: 11px;"
            f"padding: 2px 10px; font-size: 11px; font-weight: 600;")
