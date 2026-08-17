from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
    QSpinBox, QDoubleSpinBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QTabWidget, QGroupBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
import database

class CalculatorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_lbl = QLabel("Financial & Tax Advisory Calculators")
        title_lbl.setObjectName("title-lbl")
        main_layout.addWidget(title_lbl)

        # Tab Widget
        self.tabs = QTabWidget()
        
        # 1. Microloan Calculator Tab
        self.loan_tab = QWidget()
        self.setup_loan_tab()
        self.tabs.addTab(self.loan_tab, "Microloan Repayments")
        
        # 2. Tax Estimator Tab
        self.tax_tab = QWidget()
        self.setup_tax_tab()
        self.tabs.addTab(self.tax_tab, "Startup Tax Estimator")

        # 3. Statutory Fund Tracker Tab
        self.ustav_tab = QWidget()
        self.setup_ustav_tab()
        self.tabs.addTab(self.ustav_tab, "Statutory Fund (Ustav Fondi)")

        main_layout.addWidget(self.tabs)

    # --- Microloan Tab ---
    def setup_loan_tab(self):
        layout = QHBoxLayout(self.loan_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Left Panel (Inputs)
        left_panel = QGroupBox("Loan Parameters")
        left_layout = QFormLayout(left_panel)
        left_layout.setSpacing(10)

        self.loan_amount = QDoubleSpinBox()
        self.loan_amount.setRange(1000000.0, 10000000000.0) # Up to 10 Billion UZS
        self.loan_amount.setSingleStep(10000000.0)
        self.loan_amount.setValue(100000000.0) # 100M UZS default
        self.loan_amount.setSuffix(" UZS")
        self.loan_amount.setDecimals(0)
        self.loan_amount.setGroupSeparatorShown(True)

        self.loan_rate = QDoubleSpinBox()
        self.loan_rate.setRange(1.0, 100.0)
        self.loan_rate.setSingleStep(0.5)
        self.loan_rate.setValue(24.0) # 24% standard commercial rate
        self.loan_rate.setSuffix(" % APR")

        self.loan_term = QSpinBox()
        self.loan_term.setRange(1, 120) # Up to 10 years
        self.loan_term.setValue(24) # 2 years default
        self.loan_term.setSuffix(" months")

        self.loan_type = QComboBox()
        self.loan_type.addItems(["Annuity (Equal monthly payments)", "Differentiated (Declining payments)"])

        left_layout.addRow(QLabel("Loan Amount:"), self.loan_amount)
        left_layout.addRow(QLabel("Annual Interest Rate:"), self.loan_rate)
        left_layout.addRow(QLabel("Loan Term:"), self.loan_term)
        left_layout.addRow(QLabel("Repayment Type:"), self.loan_type)

        calc_btn = QPushButton("Calculate Schedule")
        calc_btn.setObjectName("accent-btn")
        calc_btn.clicked.connect(self.calculate_loan)
        left_layout.addRow(calc_btn)

        # Totals Panel
        totals_group = QGroupBox("Payment Summary")
        totals_layout = QFormLayout(totals_group)
        self.lbl_monthly_pay = QLabel("0 UZS")
        self.lbl_monthly_pay.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.lbl_total_interest = QLabel("0 UZS")
        self.lbl_total_interest.setStyleSheet("color: #ff1744;")
        self.lbl_total_cost = QLabel("0 UZS")
        self.lbl_total_cost.setStyleSheet("font-weight: bold; color: #00f0ff;")
        
        totals_layout.addRow(QLabel("Monthly Payment:"), self.lbl_monthly_pay)
        totals_layout.addRow(QLabel("Total Interest Paid:"), self.lbl_total_interest)
        totals_layout.addRow(QLabel("Total Repayment Cost:"), self.lbl_total_cost)

        left_layout.addRow(totals_group)

        layout.addWidget(left_panel, 2)

        # Right Panel (Amortization Schedule Table)
        right_panel = QGroupBox("Amortization Table")
        right_layout = QVBoxLayout(right_panel)
        
        self.loan_table = QTableWidget()
        self.loan_table.setColumnCount(5)
        self.loan_table.setHorizontalHeaderLabels(["Month", "Start Balance", "Principal", "Interest", "End Balance"])
        self.loan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.loan_table)

        layout.addWidget(right_panel, 3)

    def calculate_loan(self):
        p = self.loan_amount.value()
        annual_rate = self.loan_rate.value()
        months = self.loan_term.value()
        is_annuity = self.loan_type.currentIndex() == 0

        r = annual_rate / 12.0 / 100.0  # Monthly interest rate

        self.loan_table.setRowCount(0)
        self.loan_table.setRowCount(months)

        total_interest = 0.0
        remaining_balance = p

        if is_annuity:
            # Annuity formula: PMT = P * r * (1+r)^n / ((1+r)^n - 1)
            if r == 0:
                monthly_payment = p / months
            else:
                monthly_payment = p * (r * (1 + r)**months) / ((1 + r)**months - 1)
            
            for m in range(1, months + 1):
                interest_payment = remaining_balance * r
                principal_payment = monthly_payment - interest_payment
                start_bal = remaining_balance
                remaining_balance -= principal_payment
                if remaining_balance < 0.01:
                    remaining_balance = 0.0
                
                total_interest += interest_payment
                
                # Fill table
                self.loan_table.setItem(m-1, 0, QTableWidgetItem(f"{m}"))
                self.loan_table.setItem(m-1, 1, QTableWidgetItem(f"{start_bal:,.0f} UZS"))
                self.loan_table.setItem(m-1, 2, QTableWidgetItem(f"{principal_payment:,.0f} UZS"))
                self.loan_table.setItem(m-1, 3, QTableWidgetItem(f"{interest_payment:,.0f} UZS"))
                self.loan_table.setItem(m-1, 4, QTableWidgetItem(f"{remaining_balance:,.0f} UZS"))
            
            self.lbl_monthly_pay.setText(f"{monthly_payment:,.2f} UZS")
            self.lbl_total_interest.setText(f"{total_interest:,.2f} UZS")
            self.lbl_total_cost.setText(f"{(p + total_interest):,.2f} UZS")
        
        else:
            # Differentiated formula:
            principal_payment = p / months
            max_payment = 0.0
            min_payment = 0.0
            
            for m in range(1, months + 1):
                interest_payment = remaining_balance * r
                monthly_payment = principal_payment + interest_payment
                start_bal = remaining_balance
                remaining_balance -= principal_payment
                if remaining_balance < 0.01:
                    remaining_balance = 0.0
                
                total_interest += interest_payment
                if m == 1:
                    max_payment = monthly_payment
                if m == months:
                    min_payment = monthly_payment
                
                # Fill table
                self.loan_table.setItem(m-1, 0, QTableWidgetItem(f"{m}"))
                self.loan_table.setItem(m-1, 1, QTableWidgetItem(f"{start_bal:,.0f} UZS"))
                self.loan_table.setItem(m-1, 2, QTableWidgetItem(f"{principal_payment:,.0f} UZS"))
                self.loan_table.setItem(m-1, 3, QTableWidgetItem(f"{interest_payment:,.0f} UZS"))
                self.loan_table.setItem(m-1, 4, QTableWidgetItem(f"{remaining_balance:,.0f} UZS"))

            self.lbl_monthly_pay.setText(f"{max_payment:,.0f} UZS ... {min_payment:,.0f} UZS")
            self.lbl_total_interest.setText(f"{total_interest:,.2f} UZS")
            self.lbl_total_cost.setText(f"{(p + total_interest):,.2f} UZS")

    # --- Tax Estimator Tab ---
    def setup_tax_tab(self):
        layout = QHBoxLayout(self.tax_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Left Panel (Inputs)
        left_panel = QGroupBox("Tax Simulator Inputs")
        left_layout = QFormLayout(left_panel)
        left_layout.setSpacing(10)

        self.tax_revenue = QDoubleSpinBox()
        self.tax_revenue.setRange(0.0, 9999999999999.0)
        self.tax_revenue.setSingleStep(50000000.0)
        self.tax_revenue.setValue(500000000.0) # 500M UZS default
        self.tax_revenue.setSuffix(" UZS")
        self.tax_revenue.setDecimals(0)
        self.tax_revenue.setGroupSeparatorShown(True)

        self.tax_expenses = QDoubleSpinBox()
        self.tax_expenses.setRange(0.0, 9999999999999.0)
        self.tax_expenses.setSingleStep(50000000.0)
        self.tax_expenses.setValue(300000000.0) # 300M UZS default
        self.tax_expenses.setSuffix(" UZS")
        self.tax_expenses.setDecimals(0)
        self.tax_expenses.setGroupSeparatorShown(True)

        self.tax_payroll = QDoubleSpinBox()
        self.tax_payroll.setRange(0.0, 9999999999999.0)
        self.tax_payroll.setSingleStep(10000000.0)
        self.tax_payroll.setValue(80000000.0) # 80M UZS default
        self.tax_payroll.setSuffix(" UZS")
        self.tax_payroll.setDecimals(0)
        self.tax_payroll.setGroupSeparatorShown(True)

        self.tax_regime = QComboBox()
        self.tax_regime.addItems([
            "Turnover Tax (Aylanmadan olinadigan soliq) - 4%",
            "General Taxes (VAT 12% + Profit 15% + Social 12%)",
            "IT-Park Resident Regime (Profit 0% + VAT 0% + Social 7.5%)"
        ])
        # Auto-change regime based on revenue limit if desired, but user selection is default
        self.tax_revenue.valueChanged.connect(self.check_revenue_limit)

        left_layout.addRow(QLabel("Annual Revenue:"), self.tax_revenue)
        left_layout.addRow(QLabel("Annual Operating Expenses:"), self.tax_expenses)
        left_layout.addRow(QLabel("Annual Payroll (Included in Expenses):"), self.tax_payroll)
        left_layout.addRow(QLabel("Target Tax Regime:"), self.tax_regime)

        calc_btn = QPushButton("Simulate Tax Liability")
        calc_btn.setObjectName("accent-btn")
        calc_btn.clicked.connect(self.calculate_taxes)
        left_layout.addRow(calc_btn)

        layout.addWidget(left_panel, 2)

        # Right Panel (Results)
        right_panel = QGroupBox("Financial Summary After Tax")
        right_layout = QFormLayout(right_panel)
        right_layout.setSpacing(12)

        self.lbl_calc_revenue = QLabel("0 UZS")
        self.lbl_calc_expenses = QLabel("0 UZS")
        
        # Taxes Breakdown
        self.lbl_tax_turnover = QLabel("0 UZS")
        self.lbl_tax_vat = QLabel("0 UZS")
        self.lbl_tax_profit = QLabel("0 UZS")
        self.lbl_tax_social = QLabel("0 UZS")
        
        self.lbl_tax_total = QLabel("0 UZS")
        self.lbl_tax_total.setStyleSheet("font-weight: bold; color: #ff1744;")
        self.lbl_net_profit = QLabel("0 UZS")
        self.lbl_net_profit.setStyleSheet("font-weight: bold; color: #00e676; font-size: 14px;")
        self.lbl_effective_rate = QLabel("0 %")

        right_layout.addRow(QLabel("Gross Revenue:"), self.lbl_calc_revenue)
        right_layout.addRow(QLabel("Total Expenses:"), self.lbl_calc_expenses)
        right_layout.addRow(QLabel("----------------------------------------"), QLabel(""))
        right_layout.addRow(QLabel("Turnover Tax (4%):"), self.lbl_tax_turnover)
        right_layout.addRow(QLabel("VAT (QQS) (12%):"), self.lbl_tax_vat)
        right_layout.addRow(QLabel("Profit Tax (Foyda solig'i) (15%):"), self.lbl_tax_profit)
        right_layout.addRow(QLabel("Social Tax (Ijtimoiy soliq) (12% or 7.5%):"), self.lbl_tax_social)
        right_layout.addRow(QLabel("----------------------------------------"), QLabel(""))
        right_layout.addRow(QLabel("Total Combined Tax:"), self.lbl_tax_total)
        right_layout.addRow(QLabel("Net Income After Tax:"), self.lbl_net_profit)
        right_layout.addRow(QLabel("Effective Tax Rate:"), self.lbl_effective_rate)

        layout.addWidget(right_panel, 3)

    def check_revenue_limit(self):
        rev = self.tax_revenue.value()
        # 1 Billion UZS limit warning
        if rev > 1000000000.0 and self.tax_regime.currentIndex() == 0:
            self.tax_regime.setCurrentIndex(1) # Automatically select General Taxes
            QMessageBox.information(
                self, "Regulatory Note", 
                "Under Uzbekistan law, once annual revenues cross 1,000,000,000 UZS, "
                "the business MUST transition from Turnover Tax to the General Tax Regime."
            )

    def calculate_taxes(self):
        rev = self.tax_revenue.value()
        exp = self.tax_expenses.value()
        payroll = self.tax_payroll.value()
        regime_idx = self.tax_regime.currentIndex()

        if exp > rev:
            QMessageBox.warning(
                self, "Warning", 
                "Expenses exceed revenues. Note that some taxes (like Turnover Tax and Social Tax) "
                "are owed even if the business is unprofitable."
            )

        # Clear labels
        self.lbl_tax_turnover.setText("0 UZS")
        self.lbl_tax_vat.setText("0 UZS")
        self.lbl_tax_profit.setText("0 UZS")
        self.lbl_tax_social.setText("0 UZS")

        turnover_tax = 0.0
        vat = 0.0
        profit_tax = 0.0
        social_tax = 0.0

        if regime_idx == 0:
            # Turnover tax
            turnover_tax = rev * 0.04
            # Social tax still applies on payroll (12%)
            social_tax = payroll * 0.12
            self.lbl_tax_turnover.setText(f"{turnover_tax:,.0f} UZS")
            self.lbl_tax_social.setText(f"{social_tax:,.0f} UZS")
        
        elif regime_idx == 1:
            # General taxes
            # VAT: 12% on added value. Usually computed as 12% on sales minus 12% offset on inputs.
            # Simplified VAT model: 12% of (Revenue - non-payroll expenses)
            added_value = max(0.0, rev - (exp - payroll))
            vat = added_value * 0.12
            
            # Social tax on payroll: 12%
            social_tax = payroll * 0.12
            
            # Profit tax: 15% on taxable profit (Revenue - Expenses - VAT - Social Tax)
            taxable_profit = max(0.0, rev - exp - vat - social_tax)
            profit_tax = taxable_profit * 0.15
            
            self.lbl_tax_vat.setText(f"{vat:,.0f} UZS")
            self.lbl_tax_social.setText(f"{social_tax:,.0f} UZS")
            self.lbl_tax_profit.setText(f"{profit_tax:,.0f} UZS")
            
        elif regime_idx == 2:
            # IT-Park Resident regime
            # Profit tax is 0%, VAT is 0%.
            # Social tax on payroll is reduced to 7.5%
            social_tax = payroll * 0.075
            self.lbl_tax_social.setText(f"{social_tax:,.0f} UZS")

        total_tax = turnover_tax + vat + profit_tax + social_tax
        net_profit = rev - exp - total_tax
        effective_rate = (total_tax / rev * 100) if rev > 0 else 0.0

        self.lbl_calc_revenue.setText(f"{rev:,.0f} UZS")
        self.lbl_calc_expenses.setText(f"{exp:,.0f} UZS")
        self.lbl_tax_total.setText(f"{total_tax:,.0f} UZS")
        self.lbl_net_profit.setText(f"{net_profit:,.0f} UZS")
        self.lbl_effective_rate.setText(f"{effective_rate:.2f} %")

    # --- Statutory Fund Tab ---
    def setup_ustav_tab(self):
        layout = QHBoxLayout(self.ustav_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Left Panel (Add Shareholder)
        left_panel = QGroupBox("Add Founder Contribution")
        left_layout = QFormLayout(left_panel)
        left_layout.setSpacing(10)

        self.founder_name = QLineEdit()
        self.founder_name.setPlaceholderText("Full Name / Entity Name")

        self.founder_share = QDoubleSpinBox()
        self.founder_share.setRange(0.01, 100.0)
        self.founder_share.setValue(50.0)
        self.founder_share.setSuffix(" %")

        self.founder_contrib = QDoubleSpinBox()
        self.founder_contrib.setRange(1000.0, 10000000000.0)
        self.founder_contrib.setSingleStep(10000000.0)
        self.founder_contrib.setValue(10000000.0)
        self.founder_contrib.setSuffix(" UZS")
        self.founder_contrib.setDecimals(0)
        self.founder_contrib.setGroupSeparatorShown(True)

        left_layout.addRow(QLabel("Founder Name:"), self.founder_name)
        left_layout.addRow(QLabel("Equity Share (%):"), self.founder_share)
        left_layout.addRow(QLabel("Contribution Value:"), self.founder_contrib)

        add_btn = QPushButton("Record Entry")
        add_btn.setObjectName("accent-btn")
        add_btn.clicked.connect(self.record_ustav_entry)
        left_layout.addRow(add_btn)

        clear_btn = QPushButton("Wipe Ledger")
        clear_btn.clicked.connect(self.wipe_ustav_ledger)
        left_layout.addRow(clear_btn)

        # Status Summary Box
        status_box = QGroupBox("Ustav Status Check")
        status_layout = QVBoxLayout(status_box)
        self.lbl_ustav_total = QLabel("Total Capital: 0 UZS")
        self.lbl_ustav_total.setStyleSheet("font-weight: bold; color: #00f0ff;")
        self.lbl_ustav_shares = QLabel("Total Shares Logged: 0%")
        self.lbl_ustav_shares.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.lbl_ustav_alert = QLabel("No records found.")
        self.lbl_ustav_alert.setWordWrap(True)
        status_layout.addWidget(self.lbl_ustav_total)
        status_layout.addWidget(self.lbl_ustav_shares)
        status_layout.addWidget(self.lbl_ustav_alert)

        left_layout.addRow(status_box)

        layout.addWidget(left_panel, 2)

        # Right Panel (Ledger Table)
        right_panel = QGroupBox("Immutable Ustav Fondi Capital Ledger")
        right_layout = QVBoxLayout(right_panel)

        self.ustav_table = QTableWidget()
        self.ustav_table.setColumnCount(4)
        self.ustav_table.setHorizontalHeaderLabels(["Founder Name", "Share (%)", "Contribution", "Date Logged"])
        self.ustav_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.ustav_table)

        layout.addWidget(right_panel, 3)

        self.refresh_ustav_table()

    def record_ustav_entry(self):
        name = self.founder_name.text().strip()
        share = self.founder_share.value()
        contrib = self.founder_contrib.value()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Founder Name is required.")
            return

        # Check aggregate shares limit
        entries = database.get_ustav_entries()
        total_shares = sum(e["share_percentage"] for e in entries)
        
        if total_shares + share > 100.001:  # Allow minimal float margin
            QMessageBox.warning(
                self, "Validation Error", 
                f"Cannot add share. Sum of shares would exceed 100% (Current total: {total_shares}%)."
            )
            return

        database.add_ustav_entry(name, share, contrib)
        self.founder_name.clear()
        self.refresh_ustav_table()

    def wipe_ustav_ledger(self):
        reply = QMessageBox.question(
            self, 'Confirm Ledger Wipe', 
            'Are you sure you want to wipe the Statutory Fund ledger? This action is destructive.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            database.clear_ustav_entries()
            self.refresh_ustav_table()

    def refresh_ustav_table(self):
        entries = database.get_ustav_entries()
        self.ustav_table.setRowCount(len(entries))

        total_capital = 0.0
        total_shares = 0.0

        for idx, entry in enumerate(entries):
            total_capital += entry["contribution_amount"]
            total_shares += entry["share_percentage"]

            self.ustav_table.setItem(idx, 0, QTableWidgetItem(entry["founder_name"]))
            self.ustav_table.setItem(idx, 1, QTableWidgetItem(f"{entry['share_percentage']:.2f} %"))
            self.ustav_table.setItem(idx, 2, QTableWidgetItem(f"{entry['contribution_amount']:,.0f} UZS"))
            
            # Format datetime
            dt_str = entry["date_logged"]
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                dt_str = dt.strftime("%d.%m.%Y")
            except Exception:
                pass
            self.ustav_table.setItem(idx, 3, QTableWidgetItem(dt_str))

        self.lbl_ustav_total.setText(f"Total Capital: {total_capital:,.2f} UZS")
        self.lbl_ustav_shares.setText(f"Total Shares Logged: {total_shares:.2f} %")

        # Set status warnings based on the ustav rules
        if len(entries) == 0:
            self.lbl_ustav_alert.setText("No founders registered. statutory fund is currently empty.")
            self.lbl_ustav_alert.setStyleSheet("color: #ff1744; font-weight: bold;")
        elif abs(total_shares - 100.0) < 0.01:
            self.lbl_ustav_alert.setText("✓ Perfect Allocation. Total shares allocated equal exactly 100%. Ready for public notarization.")
            self.lbl_ustav_alert.setStyleSheet("color: #00e676; font-weight: bold;")
        else:
            diff = 100.0 - total_shares
            self.lbl_ustav_alert.setText(f"⚠️ Incomplete Allocation: {diff:.2f}% remaining to reach full 100% statutory requirement.")
            self.lbl_ustav_alert.setStyleSheet("color: #ffb74d; font-weight: bold;")
