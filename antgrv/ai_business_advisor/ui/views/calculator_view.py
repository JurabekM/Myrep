from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QFormLayout, QTextEdit
)
from services.finance_service import finance_service

class CalculatorView(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        header = QLabel("Soliq va Moliya Kalkulyatori")
        header.setObjectName("HeaderLabel")
        main_layout.addWidget(header)

        # Tax Calculator Section
        tax_layout = QFormLayout()
        
        self.revenue_input = QLineEdit()
        self.costs_input = QLineEdit()
        
        self.tax_type_combo = QComboBox()
        self.tax_type_combo.addItems([
            "Aylanmadan olinadigan soliq (4%)",
            "QQS (12%) va Foyda solig'i (15%)"
        ])

        tax_layout.addRow("Umumiy tushum (UZS):", self.revenue_input)
        tax_layout.addRow("Umumiy xarajatlar (UZS):", self.costs_input)
        tax_layout.addRow("Soliq turi:", self.tax_type_combo)

        btn_calc = QPushButton("Hisoblash")
        btn_calc.setObjectName("PrimaryButton")
        btn_calc.clicked.connect(self.calculate_taxes)

        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)

        main_layout.addLayout(tax_layout)
        main_layout.addWidget(btn_calc)
        main_layout.addWidget(QLabel("Natija:"))
        main_layout.addWidget(self.result_display)

    def calculate_taxes(self):
        try:
            revenue = float(self.revenue_input.text() or 0)
            costs = float(self.costs_input.text() or 0)
            
            tax_type_map = {
                0: "turnover",
                1: "vat_profit"
            }
            tax_type = tax_type_map[self.tax_type_combo.currentIndex()]
            
            res = finance_service.calculate_uzb_taxes(revenue, costs, tax_type)
            
            text = f"Yalpi foyda (Gross Profit): {res['gross_profit']:,.2f} UZS\n"
            text += f"Umumiy Soliq: {res['total_tax']:,.2f} UZS\n"
            for k, v in res['details'].items():
                text += f" - {k}: {v:,.2f} UZS\n"
            text += f"Sof foyda (Net Profit): {res['net_profit']:,.2f} UZS\n\n"
            text += "Diqqat: Ushbu hisob-kitoblar faqat taxminiy bo'lib, yuridik kuchga ega emas."
            
            self.result_display.setPlainText(text)
            
        except ValueError:
            self.result_display.setPlainText("Iltimos, to'g'ri son kiriting.")
