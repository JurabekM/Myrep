"""Single dark theme: palette tokens, icon helpers and the global stylesheet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap

# --------------------------------------------------------------------------- #
# Palette tokens
# --------------------------------------------------------------------------- #
BG = "#111827"
BG_ALT = "#151B26"
SIDEBAR = "#0B1220"
PANEL = "#1E293B"
PANEL_ALT = "#232F45"
CARD = "#1A2334"
BORDER = "#2B3648"
BORDER_STRONG = "#3A465C"
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2F73E0"
ACCENT_PRESSED = "#2563EB"
ACCENT_SOFT = "#1D3A6B"
SUCCESS = "#22C55E"
SUCCESS_SOFT = "#14361F"
WARNING = "#F59E0B"
WARNING_SOFT = "#3A2C0B"
DANGER = "#EF4444"
DANGER_SOFT = "#3B1616"
INFO = "#38BDF8"
PURPLE = "#A78BFA"

TEXT = "#E5E9F0"
TEXT_MUTED = "#94A3B8"
TEXT_DISABLED = "#5A6779"
TEXT_INVERSE = "#0B1220"

RADIUS = 10
RADIUS_SM = 8
RADIUS_LG = 12

#: Semantic colours used by tables and badges.
STATUS_COLORS: dict[str, str] = {
    "new": INFO,
    "ai_conversation": PURPLE,
    "waiting_operator": WARNING,
    "operator_working": ACCENT,
    "booked": "#0EA5E9",
    "arrived": "#06B6D4",
    "won": SUCCESS,
    "lost": DANGER,
    "callback": WARNING,
    "spam": TEXT_DISABLED,
}

INTENT_COLORS: dict[str, str] = {"cold": INFO, "warm": WARNING, "hot": DANGER}

CHANNEL_COLORS: dict[str, str] = {
    "telegram": "#2AABEE",
    "whatsapp": "#25D366",
    "instagram": "#E1306C",
    "website": "#60A5FA",
    "phone": "#A78BFA",
    "manual": TEXT_MUTED,
    "demo": "#64748B",
}

INTEGRATION_COLORS: dict[str, str] = {
    "connected": SUCCESS,
    "demo": INFO,
    "not_configured": TEXT_DISABLED,
    "error": DANGER,
    "disabled": TEXT_DISABLED,
}

PRIORITY_COLORS: dict[str, str] = {
    "low": TEXT_MUTED,
    "normal": INFO,
    "high": WARNING,
    "critical": DANGER,
}

BOOKING_COLORS: dict[str, str] = {
    "pending": WARNING,
    "confirmed": SUCCESS,
    "not_confirmed": WARNING,
    "cancelled": TEXT_DISABLED,
    "arrived": ACCENT,
    "no_show": DANGER,
    "completed": SUCCESS,
}


def pick_font() -> str:
    """Return the best available UI font family."""
    families = set(QFontDatabase.families())
    for candidate in ("Inter", "Segoe UI Variable Text", "Segoe UI", "Roboto", "Arial"):
        if candidate in families:
            return candidate
    return "Sans Serif"


def base_font(size: int = 10, weight: int = QFont.Weight.Normal) -> QFont:
    """Build a themed font."""
    font = QFont(pick_font(), size)
    font.setWeight(weight)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def icon(name: str, color: str = TEXT_MUTED, size: int = 18) -> QIcon:
    """Return a themed icon, falling back to a coloured dot without qtawesome."""
    try:
        import qtawesome as qta

        return qta.icon(name, color=color)
    except Exception:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(3, 3, size - 6, size - 6)
        painter.end()
        return QIcon(pixmap)


def status_color(status: str) -> str:
    """Colour for a lead status chip."""
    return STATUS_COLORS.get(status, TEXT_MUTED)


def with_alpha(hex_color: str, alpha: int) -> str:
    """Return an ``rgba(...)`` string for a hex colour."""
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


# --------------------------------------------------------------------------- #
# Global stylesheet
# --------------------------------------------------------------------------- #
def build_stylesheet() -> str:
    """Return the application-wide Qt stylesheet."""
    family = pick_font()
    return f"""
* {{
    font-family: "{family}";
    font-size: 13px;
    color: {TEXT};
    outline: none;
}}

QWidget#RootWindow {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_LG}px;
}}

QWidget {{
    background: transparent;
}}

QMainWindow, QDialog {{
    background: {BG};
}}

/* ------------------------------------------------------------------ bars -- */
QWidget#TopBar {{
    background: {SIDEBAR};
    border-bottom: 1px solid {BORDER};
    border-top-left-radius: {RADIUS_LG}px;
    border-top-right-radius: {RADIUS_LG}px;
}}

QLabel#TopBarTitle {{
    font-size: 14px;
    font-weight: 700;
    color: {TEXT};
}}

QLabel#TopBarSubtitle {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}

QPushButton#WindowButton {{
    background: transparent;
    border: none;
    border-radius: {RADIUS_SM}px;
    padding: 6px 10px;
    color: {TEXT_MUTED};
}}
QPushButton#WindowButton:hover {{ background: {PANEL}; color: {TEXT}; }}
QPushButton#WindowCloseButton {{
    background: transparent; border: none; border-radius: {RADIUS_SM}px;
    padding: 6px 10px; color: {TEXT_MUTED};
}}
QPushButton#WindowCloseButton:hover {{ background: {DANGER}; color: #FFFFFF; }}

QWidget#Sidebar {{
    background: {SIDEBAR};
    border-right: 1px solid {BORDER};
}}

QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-radius: {RADIUS}px;
    padding: 10px 12px;
    text-align: left;
    color: {TEXT_MUTED};
    font-size: 13px;
}}
QPushButton#NavButton:hover {{ background: {PANEL}; color: {TEXT}; }}
QPushButton#NavButton:checked {{
    background: {ACCENT_SOFT};
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton#NavButton:disabled {{ color: {TEXT_DISABLED}; }}

/* --------------------------------------------------------------- panels -- */
QFrame#Panel, QWidget#Panel {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_LG}px;
}}
QFrame#Card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
QFrame#Separator {{ background: {BORDER}; max-height: 1px; border: none; }}

QLabel#PageTitle {{ font-size: 18px; font-weight: 700; }}
QLabel#PageSubtitle {{ font-size: 12px; color: {TEXT_MUTED}; }}
QLabel#SectionTitle {{ font-size: 13px; font-weight: 600; color: {TEXT}; }}
QLabel#Muted {{ color: {TEXT_MUTED}; }}
QLabel#MetricValue {{ font-size: 20px; font-weight: 700; }}
QLabel#MetricLabel {{ font-size: 11px; color: {TEXT_MUTED}; }}

/* -------------------------------------------------------------- buttons -- */
QPushButton {{
    background: {PANEL_ALT};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS_SM}px;
    padding: 7px 14px;
    color: {TEXT};
}}
QPushButton:hover {{ background: #2A374F; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: #202B40; }}
QPushButton:disabled {{ background: #1A2231; color: {TEXT_DISABLED}; border-color: {BORDER}; }}
QPushButton:focus {{ border: 1px solid {ACCENT}; }}

QPushButton#Primary {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: #FFFFFF; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#Primary:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton#Primary:disabled {{ background: #24405F; color: #8FA6C4; border-color: #24405F; }}

QPushButton#Success {{ background: {SUCCESS}; border-color: {SUCCESS}; color: #06210F; font-weight: 600; }}
QPushButton#Success:hover {{ background: #1FB255; }}
QPushButton#Danger {{ background: {DANGER}; border-color: {DANGER}; color: #FFFFFF; font-weight: 600; }}
QPushButton#Danger:hover {{ background: #DC2626; }}
QPushButton#Ghost {{ background: transparent; border: 1px solid {BORDER_STRONG}; color: {TEXT_MUTED}; }}
QPushButton#Ghost:hover {{ background: {PANEL_ALT}; color: {TEXT}; }}
QPushButton#Link {{ background: transparent; border: none; color: {ACCENT}; padding: 2px 4px; }}
QPushButton#Link:hover {{ color: {ACCENT_HOVER}; text-decoration: underline; }}
QPushButton#IconButton {{ background: transparent; border: none; padding: 6px; border-radius: {RADIUS_SM}px; }}
QPushButton#IconButton:hover {{ background: {PANEL_ALT}; }}

QPushButton#FilterChip {{
    background: transparent; border: 1px solid {BORDER_STRONG};
    border-radius: 14px; padding: 5px 12px; color: {TEXT_MUTED}; font-size: 12px;
}}
QPushButton#FilterChip:hover {{ border-color: {ACCENT}; color: {TEXT}; }}
QPushButton#FilterChip:checked {{
    background: {ACCENT_SOFT}; border-color: {ACCENT}; color: #FFFFFF; font-weight: 600;
}}

/* --------------------------------------------------------------- inputs -- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit,
QDateTimeEdit, QTimeEdit, QComboBox {{
    background: {BG_ALT};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS_SM}px;
    padding: 7px 10px;
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
}}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover,
QDoubleSpinBox:hover, QDateEdit:hover, QDateTimeEdit:hover {{ border-color: #46536B; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background: #161D2B; color: {TEXT_DISABLED}; border-color: {BORDER};
}}
QLineEdit[invalid="true"], QComboBox[invalid="true"], QDateEdit[invalid="true"] {{
    border: 1px solid {DANGER};
}}
QLineEdit#SearchInput {{ padding-left: 12px; border-radius: 16px; }}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_MUTED}; margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {PANEL};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS_SM}px;
    selection-background-color: {ACCENT_SOFT};
    padding: 4px;
}}

QCheckBox, QRadioButton {{ spacing: 8px; color: {TEXT}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER_STRONG}; border-radius: 4px; background: {BG_ALT};
}}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT}; border-color: {ACCENT};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:disabled {{ background: #161D2B; border-color: {BORDER}; }}

/* --------------------------------------------------------------- tables -- */
QTableView, QTreeView, QListView {{
    background: {PANEL};
    alternate-background-color: {PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
    gridline-color: {BORDER};
    selection-background-color: {ACCENT_SOFT};
    selection-color: #FFFFFF;
}}
QTableView::item, QTreeView::item {{ padding: 6px 8px; border: none; }}
QTableView::item:hover, QTreeView::item:hover {{ background: #26334A; }}
QTableView::item:selected, QTreeView::item:selected {{ background: {ACCENT_SOFT}; }}

QHeaderView::section {{
    background: {BG_ALT};
    color: {TEXT_MUTED};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    border-right: 1px solid {BORDER};
    font-weight: 600;
    font-size: 12px;
}}
QHeaderView::section:hover {{ color: {TEXT}; }}
QTableCornerButton::section {{ background: {BG_ALT}; border: none; }}

QListWidget {{
    background: transparent; border: none;
}}
QListWidget::item {{ border-radius: {RADIUS}px; margin: 2px 4px; padding: 0px; }}
QListWidget::item:hover {{ background: {PANEL_ALT}; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; }}

/* ------------------------------------------------------------ scrollbars -- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3A465C; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #4A5A75; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #3A465C; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------------------------------------------------------------- tabs --- */
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: {RADIUS}px; top: -1px; }}
QTabBar::tab {{
    background: transparent; color: {TEXT_MUTED};
    padding: 9px 16px; margin-right: 4px;
    border-top-left-radius: {RADIUS_SM}px; border-top-right-radius: {RADIUS_SM}px;
}}
QTabBar::tab:hover {{ color: {TEXT}; background: {PANEL_ALT}; }}
QTabBar::tab:selected {{
    color: #FFFFFF; background: {PANEL}; border-bottom: 2px solid {ACCENT}; font-weight: 600;
}}

/* -------------------------------------------------------------- tooltip -- */
QToolTip {{
    background: {SIDEBAR};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS_SM}px;
    padding: 6px 9px;
}}

/* ---------------------------------------------------------------- menus -- */
QMenu {{
    background: {PANEL};
    border: 1px solid {BORDER_STRONG};
    border-radius: {RADIUS}px;
    padding: 6px;
}}
QMenu::item {{ padding: 7px 24px 7px 14px; border-radius: {RADIUS_SM}px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 6px 8px; }}

/* ------------------------------------------------------------- progress -- */
QProgressBar {{
    background: {BG_ALT}; border: 1px solid {BORDER}; border-radius: 6px;
    height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}

QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QSplitter::handle:hover {{ background: {ACCENT}; }}

QGroupBox {{
    border: 1px solid {BORDER}; border-radius: {RADIUS}px;
    margin-top: 14px; padding-top: 10px; font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {TEXT_MUTED}; }}

QCalendarWidget QWidget {{ background: {PANEL}; color: {TEXT}; }}
QCalendarWidget QAbstractItemView:enabled {{
    background: {PANEL}; selection-background-color: {ACCENT}; selection-color: #FFFFFF;
}}
QCalendarWidget QToolButton {{ background: transparent; color: {TEXT}; border-radius: 6px; }}
QCalendarWidget QToolButton:hover {{ background: {PANEL_ALT}; }}
"""
