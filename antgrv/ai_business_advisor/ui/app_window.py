import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, 
    QStackedWidget, QVBoxLayout, QLabel
)
from PyQt6.QtGui import QIcon
from core.config import APP_NAME, APP_VERSION
from ui.components.sidebar import Sidebar
from ui.views.chat_view import ChatView
from ui.views.calculator_view import CalculatorView
from ui.views.marketing_view import MarketingView
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        
        self._load_styles()
        self._setup_ui()

    def _load_styles(self):
        QApplication.setStyle("Fusion")
        
        # Apply our custom QSS
        style_path = Path(__file__).resolve().parent / "styles" / "dark_theme.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.navigation_requested.connect(self.navigate)
        main_layout.addWidget(self.sidebar)

        # Stacked Widget for Views
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, stretch=1)

        # Initialize Views
        self.views = {
            "chat": ChatView(),
            "calculator": CalculatorView(),
            "marketing": MarketingView(),
            "documents": QWidget() # Placeholder for Document management (RAG)
        }
        
        # Setup placeholder for documents
        doc_layout = QVBoxLayout(self.views["documents"])
        doc_layout.addWidget(QLabel("Hujjatlar bazasini boshqarish (Tez orada...)"))

        # Add to stack
        for view in self.views.values():
            self.stacked_widget.addWidget(view)

        # Set default view
        self.navigate("chat")

    def navigate(self, view_name: str):
        if view_name in self.views:
            self.stacked_widget.setCurrentWidget(self.views[view_name])

def start_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
