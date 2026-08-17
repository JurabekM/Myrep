"""Global QSS (Qt Style Sheet) — Ultra Dark tema.

Palitradagi ranglardan to'liq stil qatorini quradi. Bu butun ilovaga bir
marta qo'llaniladi (``app.setStyleSheet``), shuning uchun oq/yorug' elementlar
qolib ketmaydi — scrollbar, menyu, combobox, tooltip ham qamrab olingan.
"""

from __future__ import annotations

from app.ui.theme.palette import Colors as C


def build_stylesheet() -> str:
    return f"""
    * {{
        font-family: "Segoe UI", "Inter", Arial, sans-serif;
        font-size: 14px;
        color: {C.TEXT_PRIMARY};
        outline: none;
    }}

    QWidget {{
        background-color: {C.BG_BASE};
    }}

    QMainWindow, QDialog {{
        background-color: {C.BG_BASE};
    }}

    /* --- Sidebar --- */
    #Sidebar {{
        background-color: {C.BG_SURFACE};
        border-right: 1px solid {C.BORDER};
    }}
    #SidebarButton {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        color: {C.TEXT_SECONDARY};
    }}
    #SidebarButton:hover {{
        background-color: {C.BG_HOVER};
        color: {C.TEXT_PRIMARY};
    }}
    #SidebarButton:checked {{
        background-color: {C.ACCENT_MUTED};
        color: {C.TEXT_PRIMARY};
        font-weight: 600;
    }}
    #BrandLabel {{
        font-size: 16px;
        font-weight: 700;
        color: {C.TEXT_PRIMARY};
        padding: 4px;
    }}
    #BrandSub {{
        font-size: 11px;
        color: {C.TEXT_MUTED};
    }}

    /* --- Sarlavhalar --- */
    #PageTitle {{
        font-size: 22px;
        font-weight: 700;
        color: {C.TEXT_PRIMARY};
    }}
    #PageSubtitle {{
        font-size: 13px;
        color: {C.TEXT_SECONDARY};
    }}
    #SectionTitle {{
        font-size: 15px;
        font-weight: 600;
        color: {C.TEXT_PRIMARY};
    }}

    /* --- Kartalar --- */
    #Card {{
        background-color: {C.BG_SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 12px;
    }}
    QLabel {{
        background: transparent;
    }}
    #Muted {{ color: {C.TEXT_SECONDARY}; }}
    #StatValue {{ font-size: 24px; font-weight: 700; color: {C.TEXT_PRIMARY}; }}
    #StatLabel {{ font-size: 12px; color: {C.TEXT_MUTED}; }}

    /* --- Tugmalar --- */
    QPushButton {{
        background-color: {C.BG_ELEVATED};
        border: 1px solid {C.BORDER_STRONG};
        border-radius: 8px;
        padding: 8px 16px;
        color: {C.TEXT_PRIMARY};
    }}
    QPushButton:hover {{ background-color: {C.BG_HOVER}; }}
    QPushButton:pressed {{ background-color: {C.BG_ACTIVE}; }}
    QPushButton:disabled {{ color: {C.TEXT_MUTED}; background-color: {C.BG_SURFACE}; }}

    QPushButton#Primary {{
        background-color: {C.ACCENT};
        border: none;
        color: #ffffff;
        font-weight: 600;
    }}
    QPushButton#Primary:hover {{ background-color: {C.ACCENT_HOVER}; }}
    QPushButton#Primary:disabled {{ background-color: {C.ACCENT_MUTED}; color: {C.TEXT_MUTED}; }}

    /* --- Kiritish maydonlari --- */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {C.BG_ELEVATED};
        border: 1px solid {C.BORDER_STRONG};
        border-radius: 8px;
        padding: 8px 10px;
        color: {C.TEXT_PRIMARY};
        selection-background-color: {C.ACCENT};
        selection-color: #ffffff;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {C.ACCENT};
    }}
    QTextEdit, QPlainTextEdit {{ padding: 10px; }}

    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background-color: {C.BG_ELEVATED};
        border: 1px solid {C.BORDER_STRONG};
        selection-background-color: {C.ACCENT_MUTED};
        color: {C.TEXT_PRIMARY};
        outline: none;
    }}

    /* --- Scrollbar --- */
    QScrollBar:vertical {{
        background: {C.BG_BASE};
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {C.BORDER_STRONG};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {C.TEXT_MUTED}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

    QScrollBar:horizontal {{
        background: {C.BG_BASE};
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {C.BORDER_STRONG};
        border-radius: 5px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {C.TEXT_MUTED}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    /* --- Ro'yxatlar / jadvallar --- */
    QListWidget, QTableWidget, QTableView, QTreeWidget {{
        background-color: {C.BG_SURFACE};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        alternate-background-color: {C.BG_ELEVATED};
    }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; }}
    QListWidget::item:hover {{ background-color: {C.BG_HOVER}; }}
    QListWidget::item:selected {{ background-color: {C.ACCENT_MUTED}; color: {C.TEXT_PRIMARY}; }}

    QHeaderView::section {{
        background-color: {C.BG_ELEVATED};
        color: {C.TEXT_SECONDARY};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {C.BORDER};
        font-weight: 600;
    }}
    QTableWidget {{ gridline-color: {C.BORDER}; }}
    QTableWidget::item {{ padding: 6px; }}

    /* --- Tab --- */
    QTabWidget::pane {{ border: 1px solid {C.BORDER}; border-radius: 8px; top: -1px; }}
    QTabBar::tab {{
        background: transparent;
        color: {C.TEXT_SECONDARY};
        padding: 8px 16px;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {C.TEXT_PRIMARY};
        border-bottom: 2px solid {C.ACCENT};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{ color: {C.TEXT_PRIMARY}; }}

    /* --- Tooltip / menyu --- */
    QToolTip {{
        background-color: {C.BG_ELEVATED};
        color: {C.TEXT_PRIMARY};
        border: 1px solid {C.BORDER_STRONG};
        border-radius: 6px;
        padding: 6px;
    }}
    QMenu {{
        background-color: {C.BG_ELEVATED};
        border: 1px solid {C.BORDER_STRONG};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{ padding: 8px 24px; border-radius: 6px; }}
    QMenu::item:selected {{ background-color: {C.ACCENT_MUTED}; }}

    /* --- Progress / checkbox --- */
    QProgressBar {{
        background-color: {C.BG_ELEVATED};
        border: none;
        border-radius: 6px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{ background-color: {C.ACCENT}; border-radius: 6px; }}

    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border: 1px solid {C.BORDER_STRONG};
        border-radius: 4px;
        background: {C.BG_ELEVATED};
    }}
    QCheckBox::indicator:checked {{ background: {C.ACCENT}; border-color: {C.ACCENT}; }}

    QSplitter::handle {{ background: {C.BORDER}; }}
    """
