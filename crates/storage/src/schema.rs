use rusqlite_migration::{M, Migrations};

/// Sxema v1 (DESKTOP_PROMPT.md 9-bo'lim, D3). Har jadvalda umumiy ustunlar (6.1):
/// `created_at`, `updated_at` (UTC), `deleted_at` (mantiqiy o'chirish), `version`, `origin_device_id`.
/// Pul summalari butun minor birliklarda (`*_minor`), valyuta ISO kodi bilan; kasr sonlar yo'q.
/// Kelajak maydonlari (masalan, `necessity`) hozirdan nullable.
pub const SCHEMA_V1: &str = r#"
CREATE TABLE households (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;

CREATE TABLE members (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    role TEXT NOT NULL CHECK (role IN ('ADULT', 'CHILD')),
    pin_verifier BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX members_by_household ON members (household_id);

CREATE TABLE categories (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    default_necessity TEXT CHECK (default_necessity IN ('ZARUR', 'KERAK', 'HAVAS')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX categories_by_household ON categories (household_id);

CREATE TABLE incomes (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    member_id TEXT NOT NULL REFERENCES members (id),
    source TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('CASH', 'CARD')),
    source_type TEXT CHECK (source_type IN ('TER', 'MOL', 'TAVAKKAL', 'RIBO')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    occurred_on TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX incomes_by_household ON incomes (household_id);

CREATE TABLE expenses (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    member_id TEXT NOT NULL REFERENCES members (id),
    category_id TEXT REFERENCES categories (id),
    channel TEXT NOT NULL CHECK (channel IN ('CASH', 'CARD')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    occurred_on TEXT NOT NULL,
    necessity TEXT CHECK (necessity IN ('ZARUR', 'KERAK', 'HAVAS')),
    envelope_id TEXT,
    is_gift INTEGER NOT NULL DEFAULT 0 CHECK (is_gift IN (0, 1)),
    is_ostentation INTEGER NOT NULL DEFAULT 0 CHECK (is_ostentation IN (0, 1)),
    funded_by_debt INTEGER NOT NULL DEFAULT 0 CHECK (funded_by_debt IN (0, 1)),
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX expenses_by_household ON expenses (household_id);

CREATE TABLE assets (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    type TEXT NOT NULL CHECK (type IN ('CASH', 'BANK_CARD', 'VAULT', 'GOLD', 'SILVER', 'FOREIGN_CURRENCY', 'RECEIVABLE', 'TRADE_GOODS', 'BUSINESS_SHARE')),
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    unit TEXT NOT NULL,
    currency TEXT CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    acquired_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX assets_by_household ON assets (household_id);

CREATE TABLE asset_snapshots (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    asset_id TEXT NOT NULL REFERENCES assets (id),
    snapshot_at TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    amount_minor INTEGER CHECK (amount_minor >= 0),
    currency TEXT CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX asset_snapshots_by_asset ON asset_snapshots (asset_id);

CREATE TABLE vault_transactions (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    asset_id TEXT NOT NULL REFERENCES assets (id),
    vault_type TEXT CHECK (vault_type IN ('QOROVUL', 'OSADIGAN')),
    kind TEXT NOT NULL CHECK (kind IN ('INITIAL', 'DEPOSIT', 'WITHDRAWAL')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    occurred_on TEXT NOT NULL,
    reason TEXT,
    member_id TEXT REFERENCES members (id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL,
    CHECK (kind <> 'WITHDRAWAL' OR (reason IS NOT NULL AND length(trim(reason)) > 0))
) STRICT;
CREATE INDEX vault_transactions_by_household ON vault_transactions (household_id);

CREATE TABLE allocation_rules (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('PERCENT', 'FIXED')),
    value INTEGER NOT NULL CHECK (value >= 0),
    progressive INTEGER NOT NULL DEFAULT 0 CHECK (progressive IN (0, 1)),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL,
    CHECK (mode <> 'PERCENT' OR value <= 10000)
) STRICT;
CREATE INDEX allocation_rules_by_household ON allocation_rules (household_id);

CREATE TABLE obligations (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    title TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    due_day INTEGER CHECK (due_day IS NULL OR due_day BETWEEN 1 AND 31),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX obligations_by_household ON obligations (household_id);

CREATE TABLE fx_rates (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    from_currency TEXT NOT NULL CHECK (from_currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    to_currency TEXT NOT NULL CHECK (to_currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    rate_num INTEGER NOT NULL CHECK (rate_num > 0),
    rate_den INTEGER NOT NULL CHECK (rate_den > 0),
    rate_date TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL,
    CHECK (from_currency <> to_currency)
) STRICT;
CREATE INDEX fx_rates_by_household ON fx_rates (household_id);
"#;

/// Barcha migratsiyalar, tartib bilan. Yangi sxema o'zgarishi — yangi `M::up` (eski migratsiyani o'zgartirmang).
pub fn migrations() -> Migrations<'static> {
    Migrations::new(vec![M::up(SCHEMA_V1)])
}

/// Sxemadagi jadvallar (testlar va hujjat uchun).
pub const TABLES: &[&str] = &[
    "households",
    "members",
    "categories",
    "incomes",
    "expenses",
    "assets",
    "asset_snapshots",
    "vault_transactions",
    "allocation_rules",
    "obligations",
    "fx_rates",
];
