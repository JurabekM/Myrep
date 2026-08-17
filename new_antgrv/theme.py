# Styling system for PyQt6 - Ultra Dark Mode with Neon Cyan Accents

COLORS = {
    "bg_main": "#121212",       # Primary window background
    "bg_panel": "#1a1a1a",      # Sidebar, headers, and intermediate frames
    "bg_card": "#1e1e1e",       # Content containers, chat bubbles, calculator panels
    "bg_input": "#252525",      # Form elements, search fields
    "border_subtle": "#2d2d2d", # Default border color
    "accent": "#00f0ff",        # Neon Cyan highlight
    "accent_hover": "#00b8cc",  # Hover state for active elements
    "accent_dim": "rgba(0, 240, 255, 0.1)", # Selected states backdrops
    "text_primary": "#ffffff",  # Pure white for headers/active labels
    "text_secondary": "#b3b3b3",# Light gray for standard body and description text
    "text_dark": "#666666",     # Muted text for guidelines or placeholder text
    "green_accent": "#00e676",  # Positive cash flow / success state
    "red_accent": "#ff1744"     # Negative cash flow / error state
}

def get_stylesheet():
    return f"""
        /* Main application window background */
        QMainWindow {{
            background-color: {COLORS["bg_main"]};
            color: {COLORS["text_primary"]};
        }}

        QWidget {{
            color: {COLORS["text_secondary"]};
            font-family: "Segoe UI", -apple-system, Roboto, Helvetica, sans-serif;
            font-size: 13px;
        }}

        /* Scrollbars - Slim & Neon accents on hover */
        QScrollBar:vertical {{
            border: none;
            background: {COLORS["bg_main"]};
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #333333;
            min-height: 25px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {COLORS["accent"]};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            border: none;
            background: {COLORS["bg_main"]};
            height: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: #333333;
            min-width: 25px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {COLORS["accent"]};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* Tab bar customization */
        QTabWidget::pane {{
            border: 1px solid {COLORS["border_subtle"]};
            background: {COLORS["bg_card"]};
            border-radius: 6px;
        }}
        QTabBar::tab {{
            background: {COLORS["bg_panel"]};
            border: 1px solid {COLORS["border_subtle"]};
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            color: {COLORS["text_secondary"]};
        }}
        QTabBar::tab:selected {{
            background: {COLORS["bg_card"]};
            border-bottom: 2px solid {COLORS["accent"]};
            color: {COLORS["text_primary"]};
        }}
        QTabBar::tab:hover {{
            color: {COLORS["text_primary"]};
            border-color: {COLORS["accent"]};
        }}

        /* Form Controls - Input, Combo, SpinBox */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {COLORS["bg_input"]};
            border: 1px solid {COLORS["border_subtle"]};
            border-radius: 4px;
            padding: 8px 10px;
            color: {COLORS["text_primary"]};
            selection-background-color: {COLORS["accent"]};
            selection-color: {COLORS["bg_main"]};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {COLORS["accent"]};
        }}

        QComboBox {{
            background-color: {COLORS["bg_input"]};
            border: 1px solid {COLORS["border_subtle"]};
            border-radius: 4px;
            padding: 8px 12px;
            color: {COLORS["text_primary"]};
            combobox-popup: 0;
        }}
        QComboBox:focus, QComboBox:hover {{
            border: 1px solid {COLORS["accent"]};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left-width: 0px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {COLORS["accent"]};
            background-color: {COLORS["bg_input"]};
            selection-background-color: {COLORS["accent_dim"]};
            selection-color: {COLORS["accent"]};
            color: {COLORS["text_secondary"]};
            outline: none;
            padding: 4px;
        }}

        /* Buttons: Normal State, Hover State, Pressed State */
        QPushButton {{
            background-color: {COLORS["bg_panel"]};
            border: 1px solid {COLORS["border_subtle"]};
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 600;
            color: {COLORS["text_primary"]};
        }}
        QPushButton:hover {{
            background-color: {COLORS["bg_input"]};
            border: 1px solid {COLORS["accent"]};
        }}
        QPushButton:pressed {{
            background-color: {COLORS["accent_dim"]};
            color: {COLORS["accent"]};
        }}
        QPushButton:disabled {{
            background-color: #151515;
            color: {COLORS["text_dark"]};
            border-color: #202020;
        }}

        /* Accent/Neon Buttons for High Action */
        QPushButton#accent-btn {{
            background-color: {COLORS["accent_dim"]};
            border: 1px solid {COLORS["accent"]};
            color: {COLORS["accent"]};
        }}
        QPushButton#accent-btn:hover {{
            background-color: {COLORS["accent"]};
            color: {COLORS["bg_main"]};
        }}
        QPushButton#accent-btn:pressed {{
            background-color: {COLORS["accent_hover"]};
            color: {COLORS["bg_main"]};
        }}

        /* Table view styling */
        QTableWidget {{
            background-color: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border_subtle"]};
            gridline-color: {COLORS["border_subtle"]};
            border-radius: 6px;
            outline: none;
        }}
        QTableWidget::item {{
            padding: 6px;
            color: {COLORS["text_secondary"]};
        }}
        QTableWidget::item:selected {{
            background-color: {COLORS["accent_dim"]};
            color: {COLORS["accent"]};
        }}
        QHeaderView::section {{
            background-color: {COLORS["bg_panel"]};
            color: {COLORS["text_primary"]};
            padding: 8px;
            border: 1px solid {COLORS["border_subtle"]};
            font-weight: bold;
        }}

        /* Labels and Headings */
        QLabel {{
            color: {COLORS["text_secondary"]};
        }}
        QLabel#title-lbl {{
            font-size: 18px;
            font-weight: bold;
            color: {COLORS["text_primary"]};
        }}
        QLabel#section-lbl {{
            font-size: 14px;
            font-weight: bold;
            color: {COLORS["accent"]};
            border-bottom: 1px solid {COLORS["border_subtle"]};
            padding-bottom: 4px;
        }}

        /* List widget */
        QListWidget {{
            background-color: {COLORS["bg_card"]};
            border: 1px solid {COLORS["border_subtle"]};
            border-radius: 6px;
            padding: 5px;
        }}
        QListWidget::item {{
            padding: 8px;
            border-radius: 4px;
            margin-bottom: 2px;
        }}
        QListWidget::item:hover {{
            background-color: {COLORS["bg_input"]};
            color: {COLORS["text_primary"]};
        }}
        QListWidget::item:selected {{
            background-color: {COLORS["accent_dim"]};
            color: {COLORS["accent"]};
            border: 1px solid {COLORS["accent"]};
        }}

        /* Group box styling */
        QGroupBox {{
            border: 1px solid {COLORS["border_subtle"]};
            border-radius: 6px;
            margin-top: 1.5ex;
            background: {COLORS["bg_card"]};
            font-weight: bold;
            padding: 15px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0px 5px;
            color: {COLORS["accent"]};
        }}
    """
