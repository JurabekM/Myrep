"""Single dark theme: palette, stylesheet and status colours."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase

#: Core palette of the application.
COLORS = {
    "bg": "#111827",
    "bg_alt": "#151B26",
    "sidebar": "#0B1220",
    "surface": "#1E293B",
    "surface_alt": "#243044",
    "surface_hover": "#2B3A52",
    "border": "#2C3A50",
    "border_strong": "#3A4A64",
    "text": "#E5EAF3",
    "text_muted": "#94A3B8",
    "text_dim": "#64748B",
    "accent": "#3B82F6",
    "accent_hover": "#60A5FA",
    "accent_pressed": "#2563EB",
    "accent_soft": "#1E3A8A",
    "success": "#22C55E",
    "success_soft": "#14532D",
    "warning": "#F59E0B",
    "warning_soft": "#78350F",
    "danger": "#EF4444",
    "danger_soft": "#7F1D1D",
    "info": "#38BDF8",
    "purple": "#A78BFA",
}

#: Status -> (foreground, background) used by badges and table highlighting.
STATUS_COLORS: dict[str, tuple[str, str]] = {
    # neutral / draft
    "draft": (COLORS["text_muted"], "#232F44"),
    "new": (COLORS["info"], "#0C3A52"),
    "planning": (COLORS["text_muted"], "#232F44"),
    "open": (COLORS["info"], "#0C3A52"),
    "unverified": (COLORS["text_muted"], "#232F44"),
    # in progress
    "in_review": (COLORS["warning"], COLORS["warning_soft"]),
    "review_required": (COLORS["warning"], COLORS["warning_soft"]),
    "qualified": (COLORS["accent"], COLORS["accent_soft"]),
    "rfq_received": (COLORS["accent"], COLORS["accent_soft"]),
    "quotation_sent": (COLORS["accent"], COLORS["accent_soft"]),
    "sample_sent": (COLORS["purple"], "#3B2A63"),
    "negotiation": (COLORS["purple"], "#3B2A63"),
    "under_negotiation": (COLORS["purple"], "#3B2A63"),
    "contract_preparation": (COLORS["warning"], COLORS["warning_soft"]),
    "booking_requested": (COLORS["warning"], COLORS["warning_soft"]),
    "booked": (COLORS["accent"], COLORS["accent_soft"]),
    "ready_to_ship": (COLORS["accent"], COLORS["accent_soft"]),
    "in_customs": (COLORS["warning"], COLORS["warning_soft"]),
    "in_transit": (COLORS["accent"], COLORS["accent_soft"]),
    "in_execution": (COLORS["accent"], COLORS["accent_soft"]),
    "sent": (COLORS["accent"], COLORS["accent_soft"]),
    "viewed": (COLORS["accent"], COLORS["accent_soft"]),
    "buyer_replied": (COLORS["purple"], "#3B2A63"),
    "queued": (COLORS["text_muted"], "#232F44"),
    "follow_up": (COLORS["warning"], COLORS["warning_soft"]),
    "expiring": (COLORS["warning"], COLORS["warning_soft"]),
    "in_progress": (COLORS["accent"], COLORS["accent_soft"]),
    "replied": (COLORS["accent"], COLORS["accent_soft"]),
    # success
    "active": (COLORS["success"], COLORS["success_soft"]),
    "approved": (COLORS["success"], COLORS["success_soft"]),
    "accepted": (COLORS["success"], COLORS["success_soft"]),
    "closed_won": (COLORS["success"], COLORS["success_soft"]),
    "contract_signed": (COLORS["success"], COLORS["success_soft"]),
    "signed": (COLORS["success"], COLORS["success_soft"]),
    "delivered": (COLORS["success"], COLORS["success_soft"]),
    "arrived": (COLORS["success"], COLORS["success_soft"]),
    "completed": (COLORS["success"], COLORS["success_soft"]),
    "cleared": (COLORS["success"], COLORS["success_soft"]),
    "valid": (COLORS["success"], COLORS["success_soft"]),
    "verified": (COLORS["success"], COLORS["success_soft"]),
    "done": (COLORS["success"], COLORS["success_soft"]),
    "connected": (COLORS["success"], COLORS["success_soft"]),
    "quoted": (COLORS["success"], COLORS["success_soft"]),
    # danger
    "closed_lost": (COLORS["danger"], COLORS["danger_soft"]),
    "rejected": (COLORS["danger"], COLORS["danger_soft"]),
    "cancelled": (COLORS["danger"], COLORS["danger_soft"]),
    "expired": (COLORS["danger"], COLORS["danger_soft"]),
    "failed": (COLORS["danger"], COLORS["danger_soft"]),
    "delayed": (COLORS["danger"], COLORS["danger_soft"]),
    "held": (COLORS["danger"], COLORS["danger_soft"]),
    "revoked": (COLORS["danger"], COLORS["danger_soft"]),
    "spam": (COLORS["danger"], COLORS["danger_soft"]),
    "declined": (COLORS["danger"], COLORS["danger_soft"]),
    "blacklisted": (COLORS["danger"], COLORS["danger_soft"]),
    "error": (COLORS["danger"], COLORS["danger_soft"]),
    "archived": (COLORS["text_dim"], "#1B2333"),
    "inactive": (COLORS["text_dim"], "#1B2333"),
    "closed": (COLORS["text_dim"], "#1B2333"),
    "not_started": (COLORS["text_dim"], "#1B2333"),
    "demo": (COLORS["info"], "#0C3A52"),
    "not_configured": (COLORS["text_dim"], "#1B2333"),
    "configured": (COLORS["accent"], COLORS["accent_soft"]),
    # priorities
    "low": (COLORS["text_muted"], "#232F44"),
    "normal": (COLORS["info"], "#0C3A52"),
    "high": (COLORS["warning"], COLORS["warning_soft"]),
    "critical": (COLORS["danger"], COLORS["danger_soft"]),
    "cold": (COLORS["info"], "#0C3A52"),
    "warm": (COLORS["warning"], COLORS["warning_soft"]),
    "hot": (COLORS["danger"], COLORS["danger_soft"]),
    "medium": (COLORS["warning"], COLORS["warning_soft"]),
}


def status_colors(value: str | None) -> tuple[str, str]:
    """Foreground/background pair for a status badge."""
    return STATUS_COLORS.get(value or "", (COLORS["text_muted"], "#232F44"))


def qcolor(name: str) -> QColor:
    """Palette lookup returning a ``QColor``."""
    return QColor(COLORS.get(name, name))


def base_font() -> QFont:
    """Preferred UI font: Segoe UI, falling back to Inter."""
    families = set(QFontDatabase.families())
    for family in ("Segoe UI", "Inter", "Roboto"):
        if family in families:
            return QFont(family, 9)
    return QFont("Sans Serif", 9)


STYLESHEET = """
* {{
    font-family: "Segoe UI", "Inter", sans-serif;
    outline: none;
}}

QWidget {{
    background-color: {bg};
    color: {text};
    font-size: 13px;
}}

QWidget#RootWindow {{
    background-color: {bg};
    border: 1px solid {border_strong};
    border-radius: 10px;
}}

QToolTip {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border_strong};
    padding: 5px 8px;
    border-radius: 6px;
}}

/* ------------------------------------------------------------- title bar */
QWidget#TitleBar {{
    background-color: {sidebar};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border-bottom: 1px solid {border};
}}
QLabel#TitleAppName {{ font-size: 15px; font-weight: 700; color: {text}; }}
QLabel#TitleMeta {{ color: {text_muted}; font-size: 12px; }}
QPushButton#WindowButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    color: {text_muted};
    font-size: 14px;
}}
QPushButton#WindowButton:hover {{ background-color: {surface}; color: {text}; }}
QPushButton#WindowClose:hover {{ background-color: {danger}; color: #ffffff; }}

/* --------------------------------------------------------------- sidebar */
QWidget#Sidebar {{
    background-color: {sidebar};
    border-right: 1px solid {border};
}}
QLabel#SidebarGroup {{
    color: {text_dim};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 14px 16px 4px 16px;
}}
QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {text_muted};
    text-align: left;
    padding: 9px 14px;
    margin: 1px 8px;
    font-size: 13px;
}}
QPushButton#NavButton:hover {{ background-color: {surface}; color: {text}; }}
QPushButton#NavButton:checked {{
    background-color: {accent_soft};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#NavButton:disabled {{ color: {text_dim}; }}

/* ----------------------------------------------------------------- pages */
QWidget#PageHeader {{ background-color: {bg}; }}
QLabel#PageTitle {{ font-size: 20px; font-weight: 700; color: {text}; }}
QLabel#PageSubtitle {{ font-size: 12px; color: {text_muted}; }}
QLabel#SectionTitle {{ font-size: 14px; font-weight: 600; color: {text}; }}
QLabel#Muted {{ color: {text_muted}; }}
QLabel#Hint {{ color: {text_dim}; font-size: 11px; }}

QFrame#Card, QWidget#Card {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}
QFrame#StatCard {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}
QLabel#StatValue {{ font-size: 22px; font-weight: 700; color: {text}; }}
QLabel#StatLabel {{ font-size: 11px; color: {text_muted}; }}

QFrame#Separator {{ background-color: {border}; max-height: 1px; border: none; }}

/* ---------------------------------------------------------------- inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {{
    background-color: {bg_alt};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 7px 10px;
    color: {text};
    selection-background-color: {accent};
    selection-color: #ffffff;
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover,
QDoubleSpinBox:hover, QDateEdit:hover, QComboBox:hover {{
    border-color: {border_strong};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
    border-color: {accent};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QDateEdit:disabled, QComboBox:disabled {{
    background-color: #16202F;
    color: {text_dim};
    border-color: #222E42;
}}
QLineEdit[invalid="true"], QComboBox[invalid="true"], QDateEdit[invalid="true"],
QDoubleSpinBox[invalid="true"], QSpinBox[invalid="true"] {{
    border-color: {danger};
    background-color: #2A1A1F;
}}
QLineEdit#SearchInput {{
    background-color: {surface};
    border-radius: 9px;
    padding-left: 12px;
}}

QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text_muted};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {surface};
    border: 1px solid {border_strong};
    border-radius: 8px;
    selection-background-color: {accent_soft};
    selection-color: #ffffff;
    padding: 4px;
}}

QDateEdit::drop-down {{ border: none; width: 20px; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {surface_alt};
    border: none;
    width: 16px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {accent_soft};
}}

QCheckBox, QRadioButton {{ spacing: 8px; color: {text}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {border_strong};
    background-color: {bg_alt};
    border-radius: 4px;
}}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {accent}; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background-color: #1A2334; border-color: #26324A;
}}

/* --------------------------------------------------------------- buttons */
QPushButton {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border_strong};
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: {surface_hover}; border-color: {accent}; }}
QPushButton:pressed {{ background-color: {bg_alt}; }}
QPushButton:disabled {{ background-color: #1A2334; color: {text_dim}; border-color: #26324A; }}

QPushButton#Primary {{
    background-color: {accent};
    color: #ffffff;
    border: 1px solid {accent};
    font-weight: 600;
}}
QPushButton#Primary:hover {{ background-color: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#Primary:pressed {{ background-color: {accent_pressed}; }}
QPushButton#Primary:disabled {{ background-color: #24334D; color: {text_dim}; border-color: #24334D; }}

QPushButton#Success {{ background-color: {success}; color: #06210F; border-color: {success}; font-weight: 600; }}
QPushButton#Success:hover {{ background-color: #34D07B; }}
QPushButton#Danger {{ background-color: {danger}; color: #ffffff; border-color: {danger}; font-weight: 600; }}
QPushButton#Danger:hover {{ background-color: #F87171; }}
QPushButton#Ghost {{ background: transparent; border-color: {border}; color: {text_muted}; }}
QPushButton#Ghost:hover {{ color: {text}; border-color: {accent}; background-color: {surface}; }}
QPushButton#LinkButton {{
    background: transparent; border: none; color: {accent}; padding: 2px 4px; text-align: left;
}}
QPushButton#LinkButton:hover {{ color: {accent_hover}; text-decoration: underline; }}

QPushButton#ChipButton {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 5px 12px;
    color: {text_muted};
    font-size: 12px;
}}
QPushButton#ChipButton:checked {{
    background-color: {accent_soft}; color: #ffffff; border-color: {accent};
}}

/* ---------------------------------------------------------------- tables */
QTableView, QTreeView, QListView {{
    background-color: {surface};
    alternate-background-color: #1B2637;
    border: 1px solid {border};
    border-radius: 10px;
    gridline-color: {border};
    selection-background-color: {accent_soft};
    selection-color: #ffffff;
}}
QTableView::item, QTreeView::item, QListView::item {{ padding: 5px 6px; border: none; }}
QTableView::item:hover, QTreeView::item:hover {{ background-color: {surface_hover}; }}
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
    background-color: {accent_soft}; color: #ffffff;
}}
QHeaderView::section {{
    background-color: {bg_alt};
    color: {text_muted};
    padding: 8px 8px;
    border: none;
    border-right: 1px solid {border};
    border-bottom: 1px solid {border};
    font-weight: 600;
    font-size: 12px;
}}
QHeaderView::section:hover {{ color: {text}; }}
QTableCornerButton::section {{ background-color: {bg_alt}; border: none; }}

/* ------------------------------------------------------------------ tabs */
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 10px;
    top: -1px;
    background-color: {surface};
}}
QTabBar::tab {{
    background: transparent;
    color: {text_muted};
    padding: 9px 16px;
    margin-right: 2px;
    border: 1px solid transparent;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:hover {{ color: {text}; background-color: {surface}; }}
QTabBar::tab:selected {{
    color: #ffffff;
    background-color: {surface};
    border-color: {border};
    border-bottom-color: {surface};
    font-weight: 600;
}}

/* ------------------------------------------------------------- scrollbars */
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background-color: {border_strong}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background-color: {accent}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{
    background-color: {border_strong}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: {accent}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------------------------------------------------------------- dialogs */
QDialog {{ background-color: {bg_alt}; }}
QGroupBox {{
    border: 1px solid {border};
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {text_muted};
}}
QMenu {{
    background-color: {surface};
    border: 1px solid {border_strong};
    border-radius: 8px;
    padding: 5px;
}}
QMenu::item {{ padding: 7px 22px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background-color: {accent_soft}; color: #ffffff; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}

QSplitter::handle {{ background-color: {border}; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical {{ height: 3px; }}

QProgressBar {{
    background-color: {bg_alt};
    border: 1px solid {border};
    border-radius: 7px;
    height: 14px;
    text-align: center;
    color: {text_muted};
    font-size: 10px;
}}
QProgressBar::chunk {{ background-color: {accent}; border-radius: 6px; }}

QScrollArea {{ border: none; background: transparent; }}
QStatusBar {{ background-color: {sidebar}; color: {text_muted}; border-top: 1px solid {border}; }}

/* -------------------------------------------------------------- kanban */
QWidget#KanbanColumn {{
    background-color: {bg_alt};
    border: 1px solid {border};
    border-radius: 10px;
}}
QLabel#KanbanHeader {{ font-weight: 700; color: {text}; padding: 2px; }}
QFrame#KanbanCard {{
    background-color: {surface};
    border: 1px solid {border};
    border-left: 3px solid {accent};
    border-radius: 8px;
}}
QFrame#KanbanCard:hover {{ border-color: {accent}; background-color: {surface_alt}; }}
QLabel#KanbanTitle {{ font-weight: 600; color: {text}; }}
QLabel#KanbanMeta {{ color: {text_muted}; font-size: 11px; }}

/* ------------------------------------------------------------- detail */
QWidget#DetailPanel {{
    background-color: {bg_alt};
    border-left: 1px solid {border};
}}
QLabel#DetailTitle {{ font-size: 16px; font-weight: 700; color: {text}; }}
QLabel#DetailKey {{ color: {text_muted}; font-size: 12px; }}
QLabel#DetailValue {{ color: {text}; font-size: 12px; font-weight: 500; }}

QLabel#Banner {{
    background-color: {accent_soft};
    color: #ffffff;
    border-radius: 8px;
    padding: 9px 14px;
}}
QLabel#BannerWarning {{
    background-color: {warning_soft};
    color: #FDE68A;
    border-radius: 8px;
    padding: 9px 14px;
}}
QLabel#BannerDanger {{
    background-color: {danger_soft};
    color: #FECACA;
    border-radius: 8px;
    padding: 9px 14px;
}}
"""


def build_stylesheet() -> str:
    """Return the formatted application stylesheet."""
    return STYLESHEET.format(**COLORS)
