"""Zamonaviy dark tema.

Klassik OS uslubidagi kulrang widget'lar emas — yumshoq kontrastli,
tinch dark palitra. Kun bo'yi jadval va formaga qarab ishlaydigan
sotuvchi uchun ko'z charchashi asosiy mezon.

Ranglar bitta joyda; UI kodi hech qachon `#rrggbb` yozmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    # Fon qatlamlari — chuqurlik uchun uchta daraja.
    base: str = "#0f1219"          # eng orqa fon
    surface: str = "#161a23"       # panellar, kartochkalar
    surface_alt: str = "#1d2230"   # jadval qatorlari, hover
    elevated: str = "#242a3a"      # dialoglar, menyular

    border: str = "#2a3142"
    border_strong: str = "#3a4257"

    # Matn — uchta ahamiyat darajasi.
    text: str = "#e6e9f0"
    text_muted: str = "#98a2b8"
    text_faint: str = "#6b7488"

    # Asosiy urg'u: sovuq ko'k-siyoh, savdo dasturi uchun tinch.
    accent: str = "#4f7cff"
    accent_hover: str = "#6b91ff"
    accent_press: str = "#3d63d8"
    accent_soft: str = "#1e2a4a"

    # Holat ranglari — `status.StatusLabel.tone` bilan mos.
    ok: str = "#3ecf8e"
    ok_soft: str = "#12301f"
    progress: str = "#4f9cff"
    progress_soft: str = "#132840"
    warning: str = "#f0b04a"
    warning_soft: str = "#3a2a10"
    error: str = "#ff5f56"
    error_soft: str = "#3a1614"

    def tone_color(self, tone: str) -> str:
        return {
            "ok": self.ok, "progress": self.progress,
            "warning": self.warning, "error": self.error,
        }.get(tone, self.text_muted)

    def tone_background(self, tone: str) -> str:
        return {
            "ok": self.ok_soft, "progress": self.progress_soft,
            "warning": self.warning_soft, "error": self.error_soft,
        }.get(tone, self.surface_alt)


PALETTE = Palette()

#: Asosiy o'lchamlar — bo'shliq ritmi 4px asosida.
SPACE_XS, SPACE_SM, SPACE_MD, SPACE_LG, SPACE_XL = 4, 8, 12, 16, 24
RADIUS_SM, RADIUS_MD, RADIUS_LG = 6, 10, 14


def stylesheet(palette: Palette = PALETTE) -> str:
    """Butun ilova uchun Qt stylesheet."""
    p = palette
    return f"""
* {{
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 14px;
    outline: none;
}}

QWidget {{
    background-color: {p.base};
    color: {p.text};
}}

QMainWindow, QDialog {{ background-color: {p.base}; }}

/* --- chap navigatsiya --- */
#NavPanel {{
    background-color: {p.surface};
    border-right: 1px solid {p.border};
}}
#NavBrand {{
    color: {p.text};
    font-size: 17px;
    font-weight: 600;
    padding: {SPACE_LG}px {SPACE_LG}px {SPACE_SM}px {SPACE_LG}px;
}}
#NavSubtitle {{
    color: {p.text_faint};
    font-size: 12px;
    padding: 0 {SPACE_LG}px {SPACE_LG}px {SPACE_LG}px;
}}
#NavSection {{
    color: {p.text_faint};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    padding: {SPACE_LG}px {SPACE_LG}px {SPACE_XS}px {SPACE_LG}px;
}}
QPushButton#NavItem {{
    background: transparent;
    border: none;
    border-radius: {RADIUS_MD}px;
    color: {p.text_muted};
    text-align: left;
    padding: 10px {SPACE_MD}px;
    margin: 2px {SPACE_MD}px;
    font-size: 14px;
}}
QPushButton#NavItem:hover {{
    background-color: {p.surface_alt};
    color: {p.text};
}}
QPushButton#NavItem:checked {{
    background-color: {p.accent_soft};
    color: {p.accent_hover};
    font-weight: 600;
}}

/* --- sahifa sarlavhasi --- */
#PageTitle {{ font-size: 22px; font-weight: 600; color: {p.text}; }}
#PageSubtitle {{ font-size: 13px; color: {p.text_muted}; }}

/* --- kartochka --- */
#Card {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS_LG}px;
}}
#CardTitle {{ font-size: 13px; font-weight: 600; color: {p.text_muted}; }}
#CardValue {{ font-size: 26px; font-weight: 600; color: {p.text}; }}

/* --- tugmalar --- */
QPushButton {{
    background-color: {p.surface_alt};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS_MD}px;
    padding: 8px {SPACE_LG}px;
    min-height: 20px;
}}
QPushButton:hover {{ background-color: {p.elevated}; border-color: {p.accent}; }}
QPushButton:pressed {{ background-color: {p.accent_press}; }}
QPushButton:disabled {{
    background-color: {p.surface};
    color: {p.text_faint};
    border-color: {p.border};
}}
QPushButton#Primary {{
    background-color: {p.accent};
    border-color: {p.accent};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#Primary:hover {{ background-color: {p.accent_hover}; }}
QPushButton#Primary:pressed {{ background-color: {p.accent_press}; }}
QPushButton#Danger {{
    background-color: {p.error_soft};
    border-color: {p.error};
    color: {p.error};
}}
QPushButton#Ghost {{
    background: transparent;
    border-color: transparent;
    color: {p.text_muted};
}}
QPushButton#Ghost:hover {{ color: {p.text}; background-color: {p.surface_alt}; }}

/* --- kiritish maydonlari --- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
QDateEdit, QDateTimeEdit, QComboBox {{
    background-color: {p.surface_alt};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS_MD}px;
    padding: 8px {SPACE_MD}px;
    color: {p.text};
    selection-background-color: {p.accent};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {{
    border-color: {p.accent};
    background-color: {p.elevated};
}}
QLineEdit:disabled, QComboBox:disabled {{ color: {p.text_faint}; }}
QLineEdit[invalid="true"] {{ border-color: {p.error}; }}

QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {p.elevated};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS_MD}px;
    selection-background-color: {p.accent_soft};
    padding: {SPACE_XS}px;
}}

/* --- jadval --- */
QTableView, QTreeView, QListView {{
    background-color: {p.surface};
    alternate-background-color: {p.surface_alt};
    border: 1px solid {p.border};
    border-radius: {RADIUS_LG}px;
    gridline-color: {p.border};
    selection-background-color: {p.accent_soft};
    selection-color: {p.text};
}}
QTableView::item, QTreeView::item {{ padding: 6px {SPACE_SM}px; }}
QHeaderView::section {{
    background-color: {p.surface_alt};
    color: {p.text_muted};
    border: none;
    border-bottom: 1px solid {p.border_strong};
    padding: 10px {SPACE_SM}px;
    font-weight: 600;
    font-size: 12px;
}}
QTableCornerButton::section {{ background-color: {p.surface_alt}; border: none; }}

/* --- scrollbar --- */
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {p.border_strong}; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {p.text_faint}; }}
QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {p.border_strong}; border-radius: 5px; min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* --- tab --- */
QTabWidget::pane {{
    border: 1px solid {p.border};
    border-radius: {RADIUS_LG}px;
    background-color: {p.surface};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {p.text_muted};
    padding: 9px {SPACE_LG}px;
    margin-right: {SPACE_XS}px;
    border-radius: {RADIUS_MD}px;
}}
QTabBar::tab:selected {{ background-color: {p.accent_soft}; color: {p.accent_hover}; }}
QTabBar::tab:hover:!selected {{ background-color: {p.surface_alt}; color: {p.text}; }}

/* --- holat chizig'i --- */
QStatusBar {{
    background-color: {p.surface};
    border-top: 1px solid {p.border};
    color: {p.text_muted};
}}
QStatusBar::item {{ border: none; }}

/* --- boshqalar --- */
QGroupBox {{
    border: 1px solid {p.border};
    border-radius: {RADIUS_LG}px;
    margin-top: {SPACE_MD}px;
    padding-top: {SPACE_MD}px;
    color: {p.text_muted};
    font-weight: 600;
}}
QGroupBox::title {{ left: {SPACE_MD}px; padding: 0 {SPACE_SM}px; }}

QCheckBox, QRadioButton {{ spacing: {SPACE_SM}px; color: {p.text}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 17px; height: 17px;
    border: 1px solid {p.border_strong};
    background-color: {p.surface_alt};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {p.accent}; border-color: {p.accent};
}}

QProgressBar {{
    background-color: {p.surface_alt};
    border: none; border-radius: 4px;
    height: 8px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background-color: {p.accent}; border-radius: 4px; }}

QToolTip {{
    background-color: {p.elevated};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS_SM}px;
    padding: {SPACE_SM}px;
}}

QMenu {{
    background-color: {p.elevated};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS_MD}px;
    padding: {SPACE_XS}px;
}}
QMenu::item {{ padding: 8px {SPACE_LG}px; border-radius: {RADIUS_SM}px; }}
QMenu::item:selected {{ background-color: {p.accent_soft}; }}

QSplitter::handle {{ background-color: {p.border}; }}

#Badge {{
    border-radius: {RADIUS_SM}px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
}}

#WarningBanner {{
    background-color: {p.warning_soft};
    border: 1px solid {p.warning};
    border-radius: {RADIUS_MD}px;
    color: {p.text};
    padding: {SPACE_MD}px;
}}

#Separator {{ background-color: {p.border}; max-height: 1px; border: none; }}
"""


def badge_style(tone: str, palette: Palette = PALETTE) -> str:
    """Bitta belgi (badge) uchun rang."""
    return (
        f"background-color: {palette.tone_background(tone)};"
        f"color: {palette.tone_color(tone)};"
    )
