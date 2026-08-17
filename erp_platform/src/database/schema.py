# -*- coding: utf-8 -*-
"""
Ma'lumotlar bazasi sxemasi — barcha ERP jadvallari va boshlang'ich ma'lumotlar.

Dizayn qoidalari:
* Sana/vaqt ustunlari TEXT sifatida saqlanadi (``YYYY-MM-DD [HH:MM:SS]``) va
  har doim ilova tomonidan yoziladi — dvigatellar orasida to'liq moslik.
* Pul/miqdor ustunlari DECIMAL(18,2) — SQLite da ro'yxatdan o'tgan converter
  orqali, PostgreSQL da tabiiy ravishda ``Decimal`` bo'lib o'qiladi.
* Bayroqlar INTEGER (0/1) — ikkala dvigatelda ham bir xil.
"""
from __future__ import annotations

from src.core.utils import now_str


def _tokens(engine: str) -> dict[str, str]:
    """Dvigatelga xos DDL bo'laklari."""
    if engine == "postgresql":
        return {"pk": "BIGSERIAL PRIMARY KEY"}
    return {"pk": "INTEGER PRIMARY KEY AUTOINCREMENT"}


def initial_schema(engine: str) -> list[str]:
    """Versiya 1: butun ERP sxemasi (jadvallar + indekslar)."""
    t = _tokens(engine)
    pk = t["pk"]

    return [
        # ------------------------------------------------------------- #
        #  Tizim: foydalanuvchilar, sessiyalar, audit, sozlamalar
        # ------------------------------------------------------------- #
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {pk},
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            role TEXT NOT NULL DEFAULT 'guest',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            last_login TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS sessions (
            id {pk},
            token TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            ip TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            created_at TEXT,
            expires_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS audit_log (
            id {pk},
            user_id INTEGER,
            username TEXT DEFAULT '',
            action TEXT NOT NULL,
            entity TEXT DEFAULT '',
            entity_id TEXT DEFAULT '',
            details TEXT DEFAULT '',
            ip TEXT DEFAULT '',
            category TEXT NOT NULL DEFAULT 'audit',
            created_at TEXT
        )""",
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT '',
            updated_at TEXT
        )""",
        """
        CREATE TABLE IF NOT EXISTS sequences (
            name TEXT NOT NULL,
            year INTEGER NOT NULL,
            last_value INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (name, year)
        )""",

        # ------------------------------------------------------------- #
        #  Katalog: kategoriya, mahsulot, ombor
        # ------------------------------------------------------------- #
        f"""
        CREATE TABLE IF NOT EXISTS categories (
            id {pk},
            name TEXT NOT NULL,
            parent_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS products (
            id {pk},
            sku TEXT UNIQUE,
            barcode TEXT DEFAULT '',
            name TEXT NOT NULL,
            category_id INTEGER,
            unit TEXT NOT NULL DEFAULT 'dona',
            cost_price DECIMAL(18,2) NOT NULL DEFAULT 0,
            sale_price DECIMAL(18,2) NOT NULL DEFAULT 0,
            vat_rate DECIMAL(18,2) NOT NULL DEFAULT 12,
            min_stock DECIMAL(18,2) NOT NULL DEFAULT 0,
            description TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS warehouses (
            id {pk},
            name TEXT NOT NULL,
            address TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS stock (
            id {pk},
            product_id INTEGER NOT NULL REFERENCES products(id),
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            quantity DECIMAL(18,2) NOT NULL DEFAULT 0,
            UNIQUE (product_id, warehouse_id)
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS stock_moves (
            id {pk},
            move_type TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            warehouse_from INTEGER,
            warehouse_to INTEGER,
            quantity DECIMAL(18,2) NOT NULL,
            unit_cost DECIMAL(18,2) NOT NULL DEFAULT 0,
            ref_type TEXT DEFAULT '',
            ref_id INTEGER,
            note TEXT DEFAULT '',
            user_id INTEGER,
            created_at TEXT
        )""",

        # ------------------------------------------------------------- #
        #  Kontragentlar: mijozlar, ta'minotchilar, leadlar
        # ------------------------------------------------------------- #
        f"""
        CREATE TABLE IF NOT EXISTS customers (
            id {pk},
            code TEXT DEFAULT '',
            name TEXT NOT NULL,
            tin TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            credit_limit DECIMAL(18,2) NOT NULL DEFAULT 0,
            discount_percent DECIMAL(18,2) NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS suppliers (
            id {pk},
            code TEXT DEFAULT '',
            name TEXT NOT NULL,
            tin TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            note TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS leads (
            id {pk},
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            source TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            customer_id INTEGER,
            assigned_to INTEGER,
            note TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT
        )""",

        # ------------------------------------------------------------- #
        #  Savdo va xarid hujjatlari
        # ------------------------------------------------------------- #
        f"""
        CREATE TABLE IF NOT EXISTS sales_docs (
            id {pk},
            doc_type TEXT NOT NULL,
            number TEXT NOT NULL UNIQUE,
            customer_id INTEGER,
            warehouse_id INTEGER,
            status TEXT NOT NULL DEFAULT 'draft',
            subtotal DECIMAL(18,2) NOT NULL DEFAULT 0,
            discount DECIMAL(18,2) NOT NULL DEFAULT 0,
            vat_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
            total DECIMAL(18,2) NOT NULL DEFAULT 0,
            paid_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'UZS',
            note TEXT DEFAULT '',
            user_id INTEGER,
            parent_id INTEGER,
            doc_date TEXT,
            created_at TEXT,
            updated_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS sales_items (
            id {pk},
            doc_id INTEGER NOT NULL REFERENCES sales_docs(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL,
            quantity DECIMAL(18,2) NOT NULL DEFAULT 1,
            price DECIMAL(18,2) NOT NULL DEFAULT 0,
            discount DECIMAL(18,2) NOT NULL DEFAULT 0,
            vat_rate DECIMAL(18,2) NOT NULL DEFAULT 12,
            vat_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
            total DECIMAL(18,2) NOT NULL DEFAULT 0
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS purchases (
            id {pk},
            number TEXT NOT NULL UNIQUE,
            supplier_id INTEGER,
            warehouse_id INTEGER,
            status TEXT NOT NULL DEFAULT 'draft',
            subtotal DECIMAL(18,2) NOT NULL DEFAULT 0,
            vat_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
            total DECIMAL(18,2) NOT NULL DEFAULT 0,
            paid_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            user_id INTEGER,
            doc_date TEXT,
            created_at TEXT,
            updated_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS purchase_items (
            id {pk},
            purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL,
            quantity DECIMAL(18,2) NOT NULL DEFAULT 1,
            price DECIMAL(18,2) NOT NULL DEFAULT 0,
            vat_rate DECIMAL(18,2) NOT NULL DEFAULT 12,
            vat_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
            total DECIMAL(18,2) NOT NULL DEFAULT 0
        )""",

        # ------------------------------------------------------------- #
        #  Buxgalteriya: hisoblar rejasi, jurnal, to'lovlar, aktivlar
        # ------------------------------------------------------------- #
        f"""
        CREATE TABLE IF NOT EXISTS accounts (
            id {pk},
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            is_cash INTEGER NOT NULL DEFAULT 0,
            is_bank INTEGER NOT NULL DEFAULT 0,
            parent_code TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id {pk},
            number TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            memo TEXT DEFAULT '',
            ref_type TEXT DEFAULT '',
            ref_id INTEGER,
            user_id INTEGER,
            is_posted INTEGER NOT NULL DEFAULT 1,
            created_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS journal_lines (
            id {pk},
            entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            account_id INTEGER NOT NULL,
            debit DECIMAL(18,2) NOT NULL DEFAULT 0,
            credit DECIMAL(18,2) NOT NULL DEFAULT 0,
            partner_type TEXT DEFAULT '',
            partner_id INTEGER
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS payments (
            id {pk},
            number TEXT NOT NULL UNIQUE,
            payment_type TEXT NOT NULL,
            method TEXT NOT NULL DEFAULT 'cash',
            account_id INTEGER,
            corr_account_id INTEGER,
            partner_type TEXT DEFAULT '',
            partner_id INTEGER,
            ref_type TEXT DEFAULT '',
            ref_id INTEGER,
            amount DECIMAL(18,2) NOT NULL DEFAULT 0,
            payment_date TEXT,
            note TEXT DEFAULT '',
            user_id INTEGER,
            created_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS assets (
            id {pk},
            code TEXT DEFAULT '',
            name TEXT NOT NULL,
            purchase_date TEXT,
            cost DECIMAL(18,2) NOT NULL DEFAULT 0,
            salvage_value DECIMAL(18,2) NOT NULL DEFAULT 0,
            useful_life_months INTEGER NOT NULL DEFAULT 60,
            depreciation_method TEXT NOT NULL DEFAULT 'straight_line',
            accumulated_depreciation DECIMAL(18,2) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            note TEXT DEFAULT '',
            created_at TEXT
        )""",

        # ------------------------------------------------------------- #
        #  HR: bo'lim, xodim, davomat, ta'til, ish haqi
        # ------------------------------------------------------------- #
        f"""
        CREATE TABLE IF NOT EXISTS departments (
            id {pk},
            name TEXT NOT NULL,
            parent_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS employees (
            id {pk},
            code TEXT DEFAULT '',
            full_name TEXT NOT NULL,
            department_id INTEGER,
            position TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            hire_date TEXT,
            birth_date TEXT,
            salary DECIMAL(18,2) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            tin TEXT DEFAULT '',
            address TEXT DEFAULT '',
            user_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS attendance (
            id {pk},
            employee_id INTEGER NOT NULL,
            work_date TEXT NOT NULL,
            check_in TEXT DEFAULT '',
            check_out TEXT DEFAULT '',
            hours DECIMAL(18,2) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'present',
            note TEXT DEFAULT '',
            UNIQUE (employee_id, work_date)
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS leaves (
            id {pk},
            employee_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL DEFAULT 'annual',
            date_from TEXT NOT NULL,
            date_to TEXT NOT NULL,
            days INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            approved_by INTEGER,
            note TEXT DEFAULT '',
            created_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS payroll_runs (
            id {pk},
            period TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'draft',
            total_gross DECIMAL(18,2) NOT NULL DEFAULT 0,
            total_tax DECIMAL(18,2) NOT NULL DEFAULT 0,
            total_net DECIMAL(18,2) NOT NULL DEFAULT 0,
            created_by INTEGER,
            created_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS payroll_items (
            id {pk},
            run_id INTEGER NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
            employee_id INTEGER NOT NULL,
            gross DECIMAL(18,2) NOT NULL DEFAULT 0,
            income_tax DECIMAL(18,2) NOT NULL DEFAULT 0,
            pension DECIMAL(18,2) NOT NULL DEFAULT 0,
            other_deductions DECIMAL(18,2) NOT NULL DEFAULT 0,
            net DECIMAL(18,2) NOT NULL DEFAULT 0,
            note TEXT DEFAULT ''
        )""",

        # ------------------------------------------------------------- #
        #  CRM va inventarizatsiya
        # ------------------------------------------------------------- #
        f"""
        CREATE TABLE IF NOT EXISTS crm_activities (
            id {pk},
            activity_type TEXT NOT NULL DEFAULT 'note',
            customer_id INTEGER,
            lead_id INTEGER,
            subject TEXT NOT NULL,
            details TEXT DEFAULT '',
            due_at TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            assigned_to INTEGER,
            created_by INTEGER,
            created_at TEXT,
            done_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS inventory_counts (
            id {pk},
            number TEXT NOT NULL UNIQUE,
            warehouse_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            note TEXT DEFAULT '',
            user_id INTEGER,
            created_at TEXT,
            completed_at TEXT
        )""",
        f"""
        CREATE TABLE IF NOT EXISTS inventory_count_items (
            id {pk},
            count_id INTEGER NOT NULL REFERENCES inventory_counts(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL,
            expected_qty DECIMAL(18,2) NOT NULL DEFAULT 0,
            actual_qty DECIMAL(18,2) NOT NULL DEFAULT 0,
            difference DECIMAL(18,2) NOT NULL DEFAULT 0
        )""",

        # ------------------------------------------------------------- #
        #  Indekslar
        # ------------------------------------------------------------- #
        "CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions (token)",
        "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at)",
        "CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_log (category)",
        "CREATE INDEX IF NOT EXISTS idx_products_barcode ON products (barcode)",
        "CREATE INDEX IF NOT EXISTS idx_products_name ON products (name)",
        "CREATE INDEX IF NOT EXISTS idx_stock_prod ON stock (product_id, warehouse_id)",
        "CREATE INDEX IF NOT EXISTS idx_moves_product ON stock_moves (product_id)",
        "CREATE INDEX IF NOT EXISTS idx_moves_created ON stock_moves (created_at)",
        "CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales_docs (customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_sales_type_status ON sales_docs (doc_type, status)",
        "CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_docs (doc_date)",
        "CREATE INDEX IF NOT EXISTS idx_sales_items_doc ON sales_items (doc_id)",
        "CREATE INDEX IF NOT EXISTS idx_purchases_supplier ON purchases (supplier_id)",
        "CREATE INDEX IF NOT EXISTS idx_purchase_items_doc ON purchase_items (purchase_id)",
        "CREATE INDEX IF NOT EXISTS idx_jlines_entry ON journal_lines (entry_id)",
        "CREATE INDEX IF NOT EXISTS idx_jlines_account ON journal_lines (account_id)",
        "CREATE INDEX IF NOT EXISTS idx_jentries_date ON journal_entries (entry_date)",
        "CREATE INDEX IF NOT EXISTS idx_payments_date ON payments (payment_date)",
        "CREATE INDEX IF NOT EXISTS idx_payments_partner ON payments (partner_type, partner_id)",
        "CREATE INDEX IF NOT EXISTS idx_attendance_emp ON attendance (employee_id, work_date)",
        "CREATE INDEX IF NOT EXISTS idx_crm_customer ON crm_activities (customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_crm_status ON crm_activities (status)",
    ]


# ------------------------------------------------------------------ #
#  Boshlang'ich ma'lumotlar (seed)
# ------------------------------------------------------------------ #

#: O'zbekiston buxgalteriya hisobi milliy standarti (NAS-21) asosidagi
#: soddalashtirilgan hisoblar rejasi: (kod, nom, tur, is_cash, is_bank)
CHART_OF_ACCOUNTS: list[tuple[str, str, str, int, int]] = [
    ("0100", "Asosiy vositalar", "asset", 0, 0),
    ("0200", "Asosiy vositalar eskirishi (amortizatsiya)", "contra_asset", 0, 0),
    ("1000", "Materiallar", "asset", 0, 0),
    ("2900", "Tovarlar", "asset", 0, 0),
    ("4010", "Xaridorlar va buyurtmachilar qarzi", "asset", 0, 0),
    ("4310", "Ta'minotchilarga berilgan avanslar", "asset", 0, 0),
    ("4410", "Hisobga olinadigan QQS (kirim QQS)", "asset", 0, 0),
    ("5010", "Kassa (milliy valyuta)", "asset", 1, 0),
    ("5110", "Hisob-kitob raqami (bank)", "asset", 0, 1),
    ("6010", "Ta'minotchilarga to'lanadigan qarz", "liability", 0, 0),
    ("6310", "Xaridorlardan olingan avanslar", "liability", 0, 0),
    ("6410", "Byudjetga to'lovlar bo'yicha qarz (soliqlar)", "liability", 0, 0),
    ("6520", "QQS bo'yicha qarz", "liability", 0, 0),
    ("6710", "Mehnat haqi bo'yicha xodimlarga qarz", "liability", 0, 0),
    ("8330", "Ustav kapitali", "equity", 0, 0),
    ("8710", "Taqsimlanmagan foyda", "equity", 0, 0),
    ("9010", "Mahsulot (tovar) sotishdan daromad", "income", 0, 0),
    ("9110", "Sotilgan mahsulot tannarxi", "expense", 0, 0),
    ("9410", "Davr xarajatlari (ma'muriy, savdo)", "expense", 0, 0),
    ("9430", "Boshqa operatsion xarajatlar", "expense", 0, 0),
    ("9910", "Yakuniy moliyaviy natija", "equity", 0, 0),
]


def seed_defaults(db) -> None:
    """
    Boshlang'ich ma'lumotlar (idempotent — qayta ishga tushirishda takrorlamaydi):
    hisoblar rejasi, standart ombor, bo'lim, kategoriya, tizim sozlamalari.
    """
    ts = now_str()

    for code, name, acc_type, is_cash, is_bank in CHART_OF_ACCOUNTS:
        exists = db.query_one("SELECT id FROM accounts WHERE code = ?", (code,))
        if not exists:
            db.insert("accounts", {
                "code": code, "name": name, "type": acc_type,
                "is_cash": is_cash, "is_bank": is_bank, "is_active": 1,
            })

    if not db.query_one("SELECT id FROM warehouses LIMIT 1"):
        db.insert("warehouses", {"name": "Asosiy ombor", "address": "", "is_active": 1})

    if not db.query_one("SELECT id FROM departments LIMIT 1"):
        db.insert("departments", {"name": "Asosiy bo'lim", "is_active": 1})

    if not db.query_one("SELECT id FROM categories LIMIT 1"):
        db.insert("categories", {"name": "Umumiy", "is_active": 1})

    for key, value in (
        ("company_name", "Mening kompaniyam"),
        ("company_tin", ""),
        ("company_address", ""),
        ("company_phone", ""),
        ("receipt_footer", "Xaridingiz uchun rahmat!"),
    ):
        if not db.query_one("SELECT key FROM settings WHERE key = ?", (key,)):
            db.insert_no_id("settings", {"key": key, "value": value, "updated_at": ts})
