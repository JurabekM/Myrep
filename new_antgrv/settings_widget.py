from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, 
    QPushButton, QGroupBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
import database

class SettingsWidget(QWidget):
    profile_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_profile()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_lbl = QLabel("User Profile & Personalization")
        title_lbl.setObjectName("title-lbl")
        main_layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Configure your startup/company profile. These details are automatically "
            "provided as system context to the Virtual Advisor, guaranteeing highly "
            "localized and industry-tailored compliance, legal, and tax suggestions."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setObjectName("desc-lbl")
        main_layout.addWidget(desc_lbl)

        # Profile Group
        profile_group = QGroupBox("Company Profile Details")
        form_layout = QFormLayout(profile_group)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(None)

        # Fields
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter legal company name (e.g., MChJ SmartTech)")

        self.industry_combo = QComboBox()
        self.industry_combo.addItems([
            "Information Technology (Software / IT Services)",
            "Manufacturing",
            "Retail / E-commerce",
            "Agriculture / Agrotech",
            "Services / Consulting",
            "Construction & Real Estate",
            "Logistics & Transport",
            "Healthcare & Pharmaceutics",
            "Other"
        ])

        self.capital_input = QDoubleSpinBox()
        self.capital_input.setRange(0.0, 9999999999999.0) # Limit up to 10 Trillion UZS
        self.capital_input.setSingleStep(10000000.0)      # 10 Million step
        self.capital_input.setSuffix(" UZS")
        self.capital_input.setDecimals(2)
        self.capital_input.setGroupSeparatorShown(True)

        self.employees_input = QSpinBox()
        self.employees_input.setRange(1, 1000000)
        self.employees_input.setSingleStep(1)
        self.employees_input.setSuffix(" employees")

        self.region_combo = QComboBox()
        self.region_combo.addItems([
            "Tashkent City",
            "Tashkent Region",
            "Samarkand",
            "Bukhara",
            "Andijan",
            "Fergana",
            "Namangan",
            "Navoiy",
            "Qashqadaryo",
            "Surxondaryo",
            "Jizzakh",
            "Sirdaryo",
            "Xorazm",
            "Republic of Karakalpakstan"
        ])

        form_layout.addRow(QLabel("Company / Brand Name:"), self.name_input)
        form_layout.addRow(QLabel("Industry Sector:"), self.industry_combo)
        form_layout.addRow(QLabel("Initial Capital:"), self.capital_input)
        form_layout.addRow(QLabel("Total Employees:"), self.employees_input)
        form_layout.addRow(QLabel("Operational Region (Uzbekistan):"), self.region_combo)

        main_layout.addWidget(profile_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings Profile")
        self.save_btn.setObjectName("accent-btn")
        self.save_btn.clicked.connect(self.save_profile)
        btn_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("Reset to Default")
        self.reset_btn.clicked.connect(self.reset_profile)
        btn_layout.addWidget(self.reset_btn)
        
        main_layout.addLayout(btn_layout)
        
        # Status Label
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #00f0ff; font-weight: bold;")
        main_layout.addWidget(self.status_lbl)

        main_layout.addStretch()

    def load_profile(self):
        settings = database.get_settings()
        self.name_input.setText(settings.get("company_name", "MChJ Yangi Biznes"))
        
        # Match Industry Combo
        ind_text = settings.get("industry", "Manufacturing")
        index = self.industry_combo.findText(ind_text)
        if index >= 0:
            self.industry_combo.setCurrentIndex(index)
        else:
            # Check for partial match if database holds abbreviated string
            for idx in range(self.industry_combo.count()):
                if ind_text in self.industry_combo.itemText(idx):
                    self.industry_combo.setCurrentIndex(idx)
                    break

        self.capital_input.setValue(settings.get("capital", 50000000.0))
        self.employees_input.setValue(settings.get("employees", 5))
        
        # Match Region Combo
        reg_text = settings.get("region", "Tashkent City")
        r_index = self.region_combo.findText(reg_text)
        if r_index >= 0:
            self.region_combo.setCurrentIndex(r_index)

    def save_profile(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Company name cannot be empty.")
            return

        industry = self.industry_combo.currentText()
        capital = self.capital_input.value()
        employees = self.employees_input.value()
        region = self.region_combo.currentText()

        database.save_settings(name, industry, capital, employees, region)
        self.status_lbl.setText("✓ Settings saved successfully and active profile updated.")
        self.profile_updated.emit()
        
        # Clear status text after a short time
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(4000, lambda: self.status_lbl.setText(""))

    def reset_profile(self):
        reply = QMessageBox.question(
            self, 'Confirm Reset', 
            'Are you sure you want to reset the company profile to default?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.save_settings("MChJ Yangi Biznes", "Manufacturing", 50000000.0, 5, "Tashkent City")
            self.load_profile()
            self.status_lbl.setText("✓ Profile reset to default values.")
            self.profile_updated.emit()
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(4000, lambda: self.status_lbl.setText(""))
