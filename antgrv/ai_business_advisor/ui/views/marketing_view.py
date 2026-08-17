from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, 
    QPushButton, QTextEdit, QHBoxLayout
)
from services.marketing_service import marketing_service

class MarketingView(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel("Marketing Strategiya Generatori")
        header.setObjectName("HeaderLabel")
        layout.addWidget(header)

        # Funnel Section
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Voronka (Funnel) turi:"))
        
        self.funnel_combo = QComboBox()
        self.funnel_combo.addItems(["lead_magnet", "webinar", "direct_sale"])
        h_layout.addWidget(self.funnel_combo)
        
        btn_funnel = QPushButton("Ko'rsatish")
        btn_funnel.clicked.connect(self.show_funnel)
        h_layout.addWidget(btn_funnel)
        
        layout.addLayout(h_layout)

        self.display = QTextEdit()
        self.display.setReadOnly(True)
        layout.addWidget(self.display)

    def show_funnel(self):
        f_type = self.funnel_combo.currentText()
        res = marketing_service.get_funnel_strategy(f_type)
        
        text = f"Tanlangan voronka: {f_type}\n\nStruktura:\n{res}\n\n"
        text += "Ushbu tuzilmani AI Chat sahifasiga o'tib, 'Ushbu voronka asosida mening biznesim uchun batafsil reja tuzib ber' deb yozish orqali to'ldirishingiz mumkin."
        self.display.setPlainText(text)
