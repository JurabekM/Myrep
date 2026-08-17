#!/usr/bin/env python3
"""
AI-Powered Business Advisory Platform - Uzbekistan MVP
Author: Expert Senior Python Developer & Software Architect
Requirements: PyQt6, requests, beautifulsoup4, pypdf
Run Command: python main.py
"""

import sys
import subprocess
import importlib

# 1. Automatic Dependency Verification & Installation
REQUIRED_DEPENDENCIES = {
    "PyQt6": "PyQt6",
    "pypdf": "pypdf",
    "bs4": "beautifulsoup4",
    "requests": "requests"
}

print("[System] Auditing standard dependencies...")
for module_name, pip_package in REQUIRED_DEPENDENCIES.items():
    try:
        importlib.import_module(module_name)
    except ImportError:
        print(f"[System] Missing dependency '{pip_package}'. Fetching via pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_package])
            print(f"[System] Successfully installed {pip_package}.")
        except Exception as e:
            print(f"[System] Critical: Failed to install {pip_package} automatically: {e}")
            print("[System] Please execute: pip install PyQt6 requests beautifulsoup4 pypdf")
            sys.exit(1)

# 2. Complete PyQt6 Core Imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, 
    QVBoxLayout, QPushButton, QStackedWidget, QLabel, 
    QFrame, QButtonGroup
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

# Local imports
import database
import theme
from settings_widget import SettingsWidget
from calculator_widget import CalculatorWidget
from legal_widget import LegalWidget
from chat_widget import ChatWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Uzbekistan AI Business Advisory Platform (MVP)")
        self.setMinimumSize(1100, 720)
        
        # Initialize Database file
        database.init_db()
        
        self.init_ui()
        self.update_active_profile_card()

    def init_ui(self):
        # Global Central Widget & Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # -------------------------------------------------------------
        # Left Side Navigation Panel (Cyber Sidebar)
        # -------------------------------------------------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: {theme.COLORS["bg_panel"]};
                border-right: 1px solid {theme.COLORS["border_subtle"]};
                min-width: 250px;
                max-width: 250px;
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 15)
        sidebar_layout.setSpacing(20)

        # Brand / Logo Header
        brand_lbl = QLabel("❖ BIZADVISOR")
        brand_lbl.setStyleSheet(f"""
            color: {theme.COLORS["accent"]}; 
            font-size: 18px; 
            font-weight: bold; 
            letter-spacing: 2px;
        """)
        brand_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(brand_lbl)

        # Active Profile Info Card (Displays loaded SQLite configs)
        self.profile_card = QFrame()
        self.profile_card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.COLORS["bg_card"]};
                border: 1px solid {theme.COLORS["border_subtle"]};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        profile_layout = QVBoxLayout(self.profile_card)
        profile_layout.setContentsMargins(8, 8, 8, 8)
        profile_layout.setSpacing(4)
        
        lbl_active = QLabel("ACTIVE PROFILE:")
        lbl_active.setStyleSheet(f"font-size: 9px; font-weight: bold; color: {theme.COLORS["accent"]};")
        profile_layout.addWidget(lbl_active)

        self.lbl_profile_name = QLabel("MChJ Yangi Biznes")
        self.lbl_profile_name.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        profile_layout.addWidget(self.lbl_profile_name)

        self.lbl_profile_meta = QLabel("Manufacturing\nTashkent City")
        self.lbl_profile_meta.setStyleSheet(f"font-size: 11px; color: {theme.COLORS["text_secondary"]};")
        self.lbl_profile_meta.setWordWrap(True)
        profile_layout.addWidget(self.lbl_profile_meta)

        sidebar_layout.addWidget(self.profile_card)

        # Sidebar navigation buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        # Define Navigation Items
        self.nav_buttons = []
        nav_configs = [
            ("💬 Virtual Advisor", 0),
            ("⚖️ Legal & Compliance", 1),
            ("🧮 Financial Advisor", 2),
            ("⚙️ Settings Profile", 3)
        ]

        for text, index in nav_configs:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Custom QSS overrides to simulate tab toggle states
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding-left: 15px;
                    background-color: transparent;
                    color: {theme.COLORS["text_secondary"]};
                    font-weight: 600;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                }}
                QPushButton:hover {{
                    background-color: {theme.COLORS["bg_input"]};
                    color: #ffffff;
                }}
                QPushButton:checked {{
                    background-color: {theme.COLORS["accent_dim"]};
                    color: {theme.COLORS["accent"]};
                    border-left: 3px solid {theme.COLORS["accent"]};
                }}
            """)
            
            btn.clicked.connect(lambda checked, idx=index: self.stack.setCurrentIndex(idx))
            self.nav_group.addButton(btn)
            btn_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Check the first tab (Advisor Chat) by default
        self.nav_buttons[0].setChecked(True)
        
        sidebar_layout.addLayout(btn_layout)
        sidebar_layout.addStretch()

        # Footer version label
        footer_lbl = QLabel("Uzbekistan Platform MVP v1.0.0")
        footer_lbl.setStyleSheet(f"color: {theme.COLORS["text_dark"]}; font-size: 10px;")
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(footer_lbl)

        main_layout.addWidget(sidebar)

        # -------------------------------------------------------------
        # Right Side Workspace Stack (Navigation target views)
        # -------------------------------------------------------------
        self.stack = QStackedWidget()
        
        # Instantiate widgets
        self.chat_view = ChatWidget()
        self.legal_view = LegalWidget()
        self.calc_view = CalculatorWidget()
        self.settings_view = SettingsWidget()

        # Connect settings change to update active profile cards instantly
        self.settings_view.profile_updated.connect(self.update_active_profile_card)

        # Add to stack
        self.stack.addWidget(self.chat_view)
        self.stack.addWidget(self.legal_view)
        self.stack.addWidget(self.calc_view)
        self.stack.addWidget(self.settings_view)

        main_layout.addWidget(self.stack)

    def update_active_profile_card(self):
        settings = database.get_settings()
        comp_name = settings.get("company_name", "MChJ Yangi Biznes")
        industry = settings.get("industry", "Manufacturing")
        region = settings.get("region", "Tashkent City")
        
        # Trim long name
        if len(comp_name) > 22:
            comp_name = comp_name[:19] + "..."
            
        self.lbl_profile_name.setText(comp_name)
        self.lbl_profile_meta.setText(f"{industry}\n📍 {region}")

def main():
    app = QApplication(sys.argv)
    
    # Apply standard high density styles globally
    app.setStyleSheet(theme.get_stylesheet())
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
