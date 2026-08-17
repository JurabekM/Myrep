# -*- coding: utf-8 -*-
"""Desktop GUI uchun professional dark theme (Qt Style Sheet)."""

# Web interfeys bilan bir xil rang palitrasi (uyg'unlik uchun)
COLORS = {
    "bg": "#0e1117",
    "panel": "#161b26",
    "panel2": "#1c2333",
    "border": "#283044",
    "text": "#e4e9f2",
    "muted": "#8d99ae",
    "accent": "#4f8cff",
    "accent_h": "#6ba0ff",
    "green": "#34d399",
    "red": "#f87171",
    "amber": "#fbbf24",
    "violet": "#a78bfa",
}

QSS = """
* { font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px;
    color: #e4e9f2; outline: none; }
QMainWindow, QDialog { background: #0e1117; }
QWidget#Sidebar { background: #161b26; border-right: 1px solid #283044; }
QWidget#Ribbon { background: #161b26; border-bottom: 1px solid #283044; }
QWidget#Content { background: #0e1117; }
QWidget#Card { background: #161b26; border: 1px solid #283044;
               border-radius: 10px; }
QLabel#Brand { font-size: 17px; font-weight: 800; color: #e4e9f2; }
QLabel#Ver { color: #8d99ae; font-size: 10px; }
QLabel#PageTitle { font-size: 20px; font-weight: 700; }
QLabel#StatLabel { color: #8d99ae; font-size: 11px; }
QLabel#StatValue { font-size: 22px; font-weight: 700; }
QLabel#StatSub { color: #8d99ae; font-size: 10px; }
QLabel#SectionTitle { color: #8d99ae; font-size: 10px; font-weight: 600;
                      letter-spacing: 1px; }

/* Sidebar tugmalari */
QPushButton#NavBtn {
    text-align: left; padding: 9px 14px; border: none; border-radius: 0;
    background: transparent; color: #e4e9f2; font-size: 13px;
    border-left: 3px solid transparent;
}
QPushButton#NavBtn:hover { background: #1c2333; }
QPushButton#NavBtn:checked {
    background: #1c2333; border-left: 3px solid #4f8cff; color: #6ba0ff;
    font-weight: 600;
}

/* Ribbon tugmalari */
QPushButton#RibbonBtn {
    background: #1c2333; border: 1px solid #283044; border-radius: 8px;
    padding: 8px 16px; color: #e4e9f2;
}
QPushButton#RibbonBtn:hover { border-color: #4f8cff; color: #6ba0ff; }
QPushButton#PrimaryBtn {
    background: #4f8cff; border: 1px solid #4f8cff; border-radius: 8px;
    padding: 8px 16px; color: white; font-weight: 600;
}
QPushButton#PrimaryBtn:hover { background: #6ba0ff; }

QPushButton {
    background: #1c2333; border: 1px solid #283044; border-radius: 7px;
    padding: 7px 14px; color: #e4e9f2;
}
QPushButton:hover { border-color: #4f8cff; }

/* Jadvallar */
QTableWidget, QTableView {
    background: #161b26; border: 1px solid #283044; border-radius: 8px;
    gridline-color: #283044; selection-background-color: #1c2333;
    selection-color: #6ba0ff;
}
QHeaderView::section {
    background: #161b26; color: #8d99ae; padding: 8px;
    border: none; border-bottom: 1px solid #283044;
    font-size: 11px; font-weight: 600;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #1c2333; }
QTableCornerButton::section { background: #161b26; border: none; }

/* Input maydonlari */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {
    background: #0e1117; border: 1px solid #283044; border-radius: 7px;
    padding: 7px 10px; color: #e4e9f2; selection-background-color: #4f8cff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QDateEdit:focus { border-color: #4f8cff; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #161b26; border: 1px solid #283044; color: #e4e9f2;
    selection-background-color: #1c2333; selection-color: #6ba0ff;
}

/* Scrollbar */
QScrollBar:vertical { background: #0e1117; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #283044; border-radius: 5px;
                              min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #3a4560; }
QScrollBar:horizontal { background: #0e1117; height: 10px; }
QScrollBar::handle:horizontal { background: #283044; border-radius: 5px;
                                min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }

/* Tab, menyu */
QTabWidget::pane { border: 1px solid #283044; border-radius: 8px; }
QTabBar::tab {
    background: #161b26; color: #8d99ae; padding: 8px 18px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
}
QTabBar::tab:selected { background: #1c2333; color: #6ba0ff; }

QMenu { background: #161b26; border: 1px solid #283044; color: #e4e9f2; }
QMenu::item:selected { background: #1c2333; color: #6ba0ff; }
QToolTip { background: #1c2333; color: #e4e9f2; border: 1px solid #283044;
           padding: 4px; }

/* Statusbar */
QStatusBar { background: #161b26; color: #8d99ae;
             border-top: 1px solid #283044; }
"""
