from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

class Sidebar(QWidget):
    navigation_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(250)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)

        # Buttons
        self.btn_chat = QPushButton("💬 AI Konsultant (Chat)")
        self.btn_calculator = QPushButton("🧮 Soliq va Moliya")
        self.btn_marketing = QPushButton("📈 Marketing Strategiya")
        self.btn_documents = QPushButton("📄 Hujjatlar (RAG)")

        buttons = {
            "chat": self.btn_chat,
            "calculator": self.btn_calculator,
            "marketing": self.btn_marketing,
            "documents": self.btn_documents
        }

        for name, btn in buttons.items():
            # Use default button style defined in QSS
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked, n=name: self.navigation_requested.emit(n))
            layout.addWidget(btn)

        layout.addStretch()
