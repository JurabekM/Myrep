# -*- coding: utf-8 -*-
"""
gui/theme.py
============
PyQt6 uchun zamonaviy Dark Theme (qorong'i mavzu) stil varag'i (QSS).
"""

from __future__ import annotations

# Rang palitrasi
COLORS = {
    "bg": "#1e1e2e",
    "bg_alt": "#252537",
    "surface": "#2a2a3c",
    "border": "#3a3a4e",
    "text": "#e0e0e8",
    "text_dim": "#9a9ab0",
    "accent": "#7c6cf5",
    "accent_hover": "#8f80ff",
    "success": "#4ade80",
    "warning": "#fbbf24",
    "error": "#f87171",
}


DARK_QSS = f"""
* {{
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
    color: {COLORS['text']};
}}

QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
}}

/* Yon menyu (sidebar) */
QListWidget#sidebar {{
    background-color: {COLORS['bg_alt']};
    border: none;
    outline: 0;
    padding-top: 10px;
}}
QListWidget#sidebar::item {{
    padding: 14px 20px;
    margin: 2px 8px;
    border-radius: 8px;
}}
QListWidget#sidebar::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}
QListWidget#sidebar::item:hover:!selected {{
    background-color: {COLORS['surface']};
}}

/* Kartochkalar */
QFrame.card {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}

QLabel#statValue {{
    font-size: 28px;
    font-weight: bold;
    color: {COLORS['accent']};
}}
QLabel#statLabel {{
    color: {COLORS['text_dim']};
    font-size: 12px;
}}
QLabel#pageTitle {{
    font-size: 22px;
    font-weight: bold;
    padding: 8px 0;
}}

/* Kiritish maydonlari */
QLineEdit, QComboBox, QTextEdit, QSpinBox, QPlainTextEdit {{
    background-color: {COLORS['bg_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: {COLORS['accent']};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent']};
}}

/* Tugmalar */
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
QPushButton:pressed {{ background-color: {COLORS['accent']}; }}
QPushButton:disabled {{ background-color: {COLORS['border']}; color: {COLORS['text_dim']}; }}

QPushButton.secondary {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
}}
QPushButton.secondary:hover {{ background-color: {COLORS['border']}; }}
QPushButton.danger {{ background-color: {COLORS['error']}; }}

/* Jadval */
QTableWidget, QTableView {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    gridline-color: {COLORS['border']};
    selection-background-color: {COLORS['accent']};
}}
QHeaderView::section {{
    background-color: {COLORS['bg_alt']};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 600;
}}
QTableWidget::item {{ padding: 6px; }}

/* Progress bar */
QProgressBar {{
    background-color: {COLORS['bg_alt']};
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 6px;
}}

/* Scrollbar */
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {COLORS['accent']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

/* Loglar konsoli */
QPlainTextEdit#logConsole {{
    background-color: #14141f;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    color: #c0c0d0;
}}

QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 4px;
    border: 1px solid {COLORS['border']};
    background: {COLORS['bg_alt']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
}}

QLabel.badge_success {{ color: {COLORS['success']}; font-weight: bold; }}
QLabel.badge_error {{ color: {COLORS['error']}; font-weight: bold; }}
"""
