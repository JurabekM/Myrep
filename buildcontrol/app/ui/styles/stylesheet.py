"""Global Qt stylesheet generated from the design tokens."""

from __future__ import annotations

from app.ui.styles.theme import (
    COLORS,
    FONT_FAMILY,
    FONT_SIZE,
    RADIUS,
    RADIUS_SM,
    ROW_HEIGHT,
)


def build_stylesheet() -> str:
    """Return the application-wide QSS."""
    c = COLORS
    return f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}px;
    color: {c.text};
    outline: 0;
}}

QWidget {{ background-color: transparent; }}

#RootWindow {{
    background-color: {c.bg};
    border: 1px solid {c.border};
    border-radius: {RADIUS}px;
}}

#ContentArea {{ background-color: {c.bg}; }}

/* ---------------------------------------------------------------- title bar */
#TitleBar {{
    background-color: {c.bg_alt};
    border-top-left-radius: {RADIUS}px;
    border-top-right-radius: {RADIUS}px;
    border-bottom: 1px solid {c.border};
}}
#TitleBarAppName {{ font-size: 14px; font-weight: 700; letter-spacing: 0.4px; }}
#TitleBarContext {{ color: {c.text_muted}; }}
#TitleBarUser {{ color: {c.text}; font-weight: 600; }}
#TitleBarRole {{ color: {c.text_faint}; font-size: 11px; }}

QPushButton#WinButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    min-width: 34px; max-width: 34px;
    min-height: 28px; max-height: 28px;
    color: {c.text_muted};
    font-size: 14px;
}}
QPushButton#WinButton:hover {{ background: {c.surface_hover}; color: {c.text}; }}
QPushButton#WinButtonClose:hover {{ background: {c.danger}; color: #fff; }}

/* ------------------------------------------------------------------ sidebar */
#Sidebar {{
    background-color: {c.sidebar};
    border-right: 1px solid {c.border};
}}
QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: 9px 12px;
    text-align: left;
    color: {c.text_muted};
    font-size: 13px;
}}
QPushButton#NavButton:hover {{ background: {c.surface}; color: {c.text}; }}
QPushButton#NavButton:checked {{
    background: {c.accent_soft};
    color: {c.text};
    font-weight: 600;
    border-left: 3px solid {c.accent};
}}
QPushButton#NavButton:disabled {{ color: {c.text_faint}; }}
#SidebarSection {{ color: {c.text_faint}; font-size: 11px; letter-spacing: 1px; }}
#SidebarFooter {{ color: {c.text_faint}; font-size: 11px; }}

/* -------------------------------------------------------------------- cards */
#Card, #Panel {{
    background-color: {c.surface};
    border: 1px solid {c.border};
    border-radius: {RADIUS}px;
}}
#CardTitle {{ color: {c.text_muted}; font-size: 12px; letter-spacing: 0.3px; }}
#CardValue {{ font-size: 20px; font-weight: 700; }}
#CardHint {{ color: {c.text_faint}; font-size: 11px; }}
#PageTitle {{ font-size: 20px; font-weight: 700; }}
#PageSubtitle {{ color: {c.text_muted}; }}
#SectionTitle {{ font-size: 14px; font-weight: 600; }}
#Separator {{ background: {c.border}; max-height: 1px; border: none; }}

/* ------------------------------------------------------------------ buttons */
QPushButton {{
    background-color: {c.surface_alt};
    border: 1px solid {c.border_strong};
    border-radius: {RADIUS_SM}px;
    padding: 7px 14px;
    color: {c.text};
}}
QPushButton:hover {{ background-color: {c.surface_hover}; }}
QPushButton:pressed {{ background-color: {c.elevated}; }}
QPushButton:disabled {{ color: {c.text_faint}; background-color: {c.bg_alt};
                        border-color: {c.border}; }}

QPushButton#Primary {{
    background-color: {c.accent}; border-color: {c.accent}; color: #FFFFFF; font-weight: 600;
}}
QPushButton#Primary:hover {{ background-color: {c.accent_hover}; border-color: {c.accent_hover}; }}
QPushButton#Primary:pressed {{ background-color: {c.accent_pressed}; }}
QPushButton#Primary:disabled {{ background-color: {c.accent_soft}; border-color: {c.accent_soft};
                                color: {c.text_faint}; }}

QPushButton#Danger {{ background-color: {c.danger_soft}; border-color: {c.danger};
                      color: {c.danger}; }}
QPushButton#Danger:hover {{ background-color: {c.danger}; color: #FFFFFF; }}
QPushButton#Success {{ background-color: {c.success_soft}; border-color: {c.success};
                       color: {c.success}; }}
QPushButton#Success:hover {{ background-color: {c.success}; color: {c.text_inverse}; }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {c.border};
                     color: {c.text_muted}; }}
QPushButton#Ghost:hover {{ background: {c.surface}; color: {c.text}; }}
QPushButton#LinkButton {{ background: transparent; border: none; color: {c.accent};
                          padding: 2px 4px; }}
QPushButton#LinkButton:hover {{ color: {c.accent_hover}; text-decoration: underline; }}

/* -------------------------------------------------------------------- input */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {{
    background-color: {c.bg_alt};
    border: 1px solid {c.border_strong};
    border-radius: {RADIUS_SM}px;
    padding: 6px 10px;
    selection-background-color: {c.accent};
    selection-color: #FFFFFF;
    min-height: 20px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
    border-color: {c.accent};
    background-color: {c.surface};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QDateEdit:disabled, QTextEdit:disabled {{
    color: {c.text_faint}; background-color: {c.bg}; border-color: {c.border};
}}
QLineEdit[invalid="true"], QComboBox[invalid="true"], QDoubleSpinBox[invalid="true"] {{
    border-color: {c.danger}; background-color: {c.danger_soft};
}}
QLineEdit#SearchBox {{ padding-left: 30px; }}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c.text_muted};
    margin-right: 9px;
}}
QComboBox::down-arrow:on {{ border-top-color: {c.accent}; }}
QComboBox QAbstractItemView {{
    background-color: {c.surface};
    border: 1px solid {c.border_strong};
    border-radius: {RADIUS_SM}px;
    selection-background-color: {c.accent_soft};
    padding: 4px;
}}
QDateEdit::drop-down {{ border: none; width: 20px; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 16px; border: none;
                                                          background: {c.surface_alt}; }}

QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c.border_strong};
    border-radius: 4px;
    background: {c.bg_alt};
}}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {c.accent}; border-color: {c.accent};
}}
QCheckBox::indicator:disabled {{ background: {c.bg}; border-color: {c.border}; }}

QLabel#FieldLabel {{ color: {c.text_muted}; font-size: 12px; }}
QLabel#FieldError {{ color: {c.danger}; font-size: 11px; }}
QLabel#Hint {{ color: {c.text_faint}; font-size: 11px; }}

/* ------------------------------------------------------------------- tables */
QTableView, QTreeView, QListView {{
    background-color: {c.surface};
    alternate-background-color: {c.surface_alt};
    border: 1px solid {c.border};
    border-radius: {RADIUS}px;
    gridline-color: {c.border};
    selection-background-color: {c.accent_soft};
    selection-color: {c.text};
}}
QTableView::item, QTreeView::item {{ padding: 4px 6px; min-height: {ROW_HEIGHT}px; }}
QTableView::item:hover, QTreeView::item:hover {{ background: {c.surface_hover}; }}
QTableView::item:selected, QTreeView::item:selected {{ background: {c.accent_soft}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    background-color: {c.bg_alt};
    color: {c.text_muted};
    border: none;
    border-right: 1px solid {c.border};
    border-bottom: 1px solid {c.border};
    padding: 8px 8px;
    font-weight: 600;
}}
QHeaderView::section:hover {{ color: {c.text}; }}
QTableView QTableCornerButton::section {{ background: {c.bg_alt}; border: none; }}
QTreeView::branch {{ background: transparent; }}

/* --------------------------------------------------------------- scrollbars */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c.border_strong}; border-radius: 5px;
                               min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c.accent}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {c.border_strong}; border-radius: 5px;
                                 min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {c.accent}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* --------------------------------------------------------------------- tabs */
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent;
    color: {c.text_muted};
    padding: 9px 16px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {c.text}; }}
QTabBar::tab:selected {{ color: {c.text}; border-bottom: 2px solid {c.accent}; font-weight: 600; }}

/* ------------------------------------------------------------------ dialogs */
QDialog {{ background-color: {c.bg_alt}; }}
#DialogHeader {{ font-size: 16px; font-weight: 700; }}
QMenu {{
    background: {c.surface}; border: 1px solid {c.border_strong};
    border-radius: {RADIUS_SM}px; padding: 6px;
}}
QMenu::item {{ padding: 7px 22px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c.accent_soft}; }}
QMenu::separator {{ height: 1px; background: {c.border}; margin: 5px 6px; }}

QToolTip {{
    background: {c.elevated}; color: {c.text};
    border: 1px solid {c.border_strong}; border-radius: 6px; padding: 6px 8px;
}}

QProgressBar {{
    background: {c.bg_alt}; border: 1px solid {c.border};
    border-radius: 6px; height: 10px; text-align: center; color: {c.text_muted};
}}
QProgressBar::chunk {{ background: {c.accent}; border-radius: 5px; }}

QSplitter::handle {{ background: {c.border}; }}
QScrollArea {{ border: none; background: transparent; }}

/* ------------------------------------------------------------------ badges */
#Badge {{ border-radius: 9px; padding: 2px 9px; font-size: 11px; font-weight: 600; }}
#Toast {{
    background: {c.elevated}; border: 1px solid {c.border_strong};
    border-radius: {RADIUS}px;
}}
#EmptyState {{ color: {c.text_faint}; font-size: 13px; }}
"""
