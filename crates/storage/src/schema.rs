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

/// Sxema v2 (D4): daromad, «Kelajagim», audit va majburiyatlar uchun ustunlar va jadvallar.
///
/// Mavjud jadvallarga faqat `ADD COLUMN` qo'shiladi (v1 ma'lumotlari saqlanadi). Yangi jadvallar:
/// nasiya (`debts`, `debt_payments`) va oylik hisobot (`monthly_reports`, o'zgarmas).
pub const SCHEMA_V2: &str = r#"
ALTER TABLE households ADD COLUMN month_start_day INTEGER NOT NULL DEFAULT 1
    CHECK (month_start_day BETWEEN 1 AND 31);

ALTER TABLE categories ADD COLUMN system_key TEXT
    CHECK (system_key IS NULL OR system_key IN (
        'RENT', 'CREDIT', 'GROCERIES', 'DAILY_SMALL', 'SNACKS', 'UTILITIES', 'PHONE',
        'FUEL', 'TRANSPORT', 'SADAQA', 'CHILDREN', 'CAFE', 'OTHER'));
CREATE UNIQUE INDEX categories_system_key_per_household
    ON categories (household_id, system_key) WHERE system_key IS NOT NULL;

ALTER TABLE obligations ADD COLUMN kind TEXT NOT NULL DEFAULT 'OTHER'
    CHECK (kind IN ('RENT', 'CREDIT', 'UTILITY', 'PHONE', 'FUEL', 'OTHER'));
ALTER TABLE obligations ADD COLUMN category_id TEXT REFERENCES categories (id);

ALTER TABLE vault_transactions ADD COLUMN income_id TEXT REFERENCES incomes (id);

ALTER TABLE allocation_rules ADD COLUMN progression_offered_on TEXT;

CREATE TABLE debts (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    kind TEXT NOT NULL CHECK (kind IN ('SHOP')),
    creditor TEXT NOT NULL CHECK (length(trim(creditor)) > 0),
    principal_minor INTEGER NOT NULL CHECK (principal_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    incurred_on TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX debts_by_household ON debts (household_id);

CREATE TABLE debt_payments (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    debt_id TEXT NOT NULL REFERENCES debts (id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    paid_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX debt_payments_by_debt ON debt_payments (debt_id);

CREATE TABLE monthly_reports (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    income_minor INTEGER NOT NULL,
    expenses_minor INTEGER NOT NULL,
    obligations_minor INTEGER NOT NULL,
    obligations_unrecorded_minor INTEGER NOT NULL,
    net_savings_minor INTEGER NOT NULL,
    unexplained_minor INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (household_id, period_start)
) STRICT;
"#;

/// Sxema v3 (D5, kontent dvigateli): haftalik vazifa bajarilishi va «Daftar sahifasi».
/// Vazifa belgisi mantiqiy o'chiriladi — birinchi bajarilish tarixi bob ochilishi uchun saqlanadi.
/// Bob uchun «Daftar sahifasi» bitta (`UNIQUE (household_id, chapter_id)`).
pub const SCHEMA_V3: &str = r#"
CREATE TABLE task_completions (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    task_id TEXT NOT NULL CHECK (length(trim(task_id)) > 0),
    week_start TEXT NOT NULL,
    is_auto INTEGER NOT NULL CHECK (is_auto IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX task_completions_by_week ON task_completions (household_id, week_start);
CREATE INDEX task_completions_by_task ON task_completions (household_id, task_id);

CREATE TABLE daftar_pages (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    chapter_id TEXT NOT NULL CHECK (length(trim(chapter_id)) > 0),
    law_number INTEGER NOT NULL CHECK (law_number >= 1),
    body TEXT NOT NULL CHECK (length(trim(body)) > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL,
    UNIQUE (household_id, chapter_id)
) STRICT;
"#;

/// Sxema v4 (D6): toifa tarixi, havas chegarasi va rozilik, a'zo PIN urinishlari, Juma shirinligi.
/// Toifa ustunlari v1 da bor (`default_necessity`, `expenses.necessity`): ular faqat to'ldiriladi.
pub const SCHEMA_V4: &str = r#"
UPDATE categories SET default_necessity = CASE system_key
    WHEN 'RENT' THEN 'ZARUR'
    WHEN 'CREDIT' THEN 'ZARUR'
    WHEN 'GROCERIES' THEN 'ZARUR'
    WHEN 'UTILITIES' THEN 'ZARUR'
    WHEN 'FUEL' THEN 'ZARUR'
    WHEN 'TRANSPORT' THEN 'ZARUR'
    WHEN 'SNACKS' THEN 'HAVAS'
    WHEN 'CAFE' THEN 'HAVAS'
    ELSE 'KERAK' END
WHERE default_necessity IS NULL;

CREATE TABLE necessity_changes (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    category_id TEXT NOT NULL REFERENCES categories (id),
    from_necessity TEXT NOT NULL CHECK (from_necessity IN ('ZARUR', 'KERAK', 'HAVAS')),
    to_necessity TEXT NOT NULL CHECK (to_necessity IN ('ZARUR', 'KERAK', 'HAVAS')),
    changed_by TEXT NOT NULL REFERENCES members (id),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX necessity_changes_by_category ON necessity_changes (category_id);

UPDATE expenses SET necessity = COALESCE(
    (SELECT c.default_necessity FROM categories c WHERE c.id = expenses.category_id), 'KERAK')
WHERE necessity IS NULL;

CREATE TABLE havas_limits (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    monthly_minor INTEGER NOT NULL CHECK (monthly_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX havas_limits_by_household ON havas_limits (household_id);

CREATE TABLE limit_consents (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    limit_id TEXT NOT NULL REFERENCES havas_limits (id),
    member_id TEXT NOT NULL REFERENCES members (id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL,
    UNIQUE (limit_id, member_id)
) STRICT;

ALTER TABLE members ADD COLUMN pin_failed_attempts INTEGER NOT NULL DEFAULT 0
    CHECK (pin_failed_attempts >= 0);
ALTER TABLE members ADD COLUMN pin_failed_at TEXT;

CREATE TABLE scheduled_treats (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX scheduled_treats_by_household ON scheduled_treats (household_id);
"#;

/// Sxema v5 (D6, odat statistikasi): kategoriya odat sifatida kuzatiladimi (SPEC 2B.9).
pub const SCHEMA_V5: &str = r#"
ALTER TABLE categories ADD COLUMN is_habit INTEGER NOT NULL DEFAULT 0 CHECK (is_habit IN (0, 1));
"#;

/// Sxema v6 (D7, byudjet): obunalar, konvertlar, «Qutqarilgan pul» yozuvlari va xonadon sozlamalari (SPEC 2B.5–2B.7).
/// «Qutqarilgan pul»dan «Kelajagim»ga o'tkazish — `vault_transactions` da DEPOSIT, sababida manba yozuvi.
pub const SCHEMA_V6: &str = r#"
CREATE TABLE subscriptions (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    monthly_minor INTEGER NOT NULL CHECK (monthly_minor > 0),
    yearly_minor INTEGER CHECK (yearly_minor IS NULL OR yearly_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    last_used_on TEXT,
    cancelled_on TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX subscriptions_by_household ON subscriptions (household_id);

CREATE TABLE envelopes (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    weekly_limit_minor INTEGER NOT NULL CHECK (weekly_limit_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    category_id TEXT REFERENCES categories (id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX envelopes_by_household ON envelopes (household_id);

CREATE TABLE savings_rescues (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    kind TEXT NOT NULL CHECK (kind IN ('SUBSCRIPTION', 'ENVELOPE_LEFTOVER', 'TRANSFER')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    occurred_on TEXT NOT NULL,
    source_id TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX savings_rescues_by_household ON savings_rescues (household_id, occurred_on);

CREATE TABLE household_settings (
    household_id TEXT NOT NULL REFERENCES households (id),
    key TEXT NOT NULL CHECK (length(trim(key)) > 0),
    value TEXT NOT NULL,
    PRIMARY KEY (household_id, key)
) STRICT;
"#;

/// Sxema v7 (D8, «Qorovul»): eski «Kelajagim» yozuvlarida pul turi bo'lmasa, u `QOROVUL` deb belgilanadi.
/// Balans o'zgarmaydi: faqat `vault_type` to'ldiriladi. Aktiv turi (`assets.type = 'VAULT'`) saqlanadi —
/// uni o'zgartirish jadval qayta yaratishni talab qiladi, pul esa bunga muhtoj emas.
pub const SCHEMA_V7: &str = r#"
UPDATE vault_transactions SET vault_type = 'QOROVUL' WHERE vault_type IS NULL;
"#;

/// Sxema v8 (D8A, kelishuv dvigateli): kelishuvlar va append-only jurnal (SPEC 2F.6).
/// Jurnal yozuvlari faqat qo'shiladi: `UPDATE` va `DELETE` triggerlar bilan rad etiladi.
/// Tuzatish — yangi `CORRECTION` yozuvi. Xesh zanjiri domen tomonida (`domain::journal`) hisoblanadi.
pub const SCHEMA_V8: &str = r#"
CREATE TABLE agreements (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    type TEXT NOT NULL CHECK (type IN ('LOAN', 'PARTNERSHIP', 'FAMILY', 'OTHER')),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    status TEXT NOT NULL CHECK (status IN ('DRAFT', 'SIGNED', 'IN_DISPUTE', 'ENDED')),
    version INTEGER NOT NULL CHECK (version >= 1),
    answers_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX agreements_by_household ON agreements (household_id);

CREATE TABLE journal_entries (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    seq INTEGER NOT NULL CHECK (seq >= 1),
    kind TEXT NOT NULL CHECK (kind IN ('OPENING_BALANCE', 'CONTRIBUTION', 'PROFIT_DISTRIBUTION', 'LOAN_PAYMENT', 'CORRECTION')),
    party_id TEXT NOT NULL CHECK (length(trim(party_id)) > 0),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    entry_date TEXT NOT NULL,
    note TEXT,
    prev_hash TEXT NOT NULL CHECK (length(prev_hash) = 64),
    hash TEXT NOT NULL CHECK (length(hash) = 64),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (agreement_id, seq)
) STRICT;

CREATE TRIGGER journal_entries_no_update BEFORE UPDATE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'journal is append-only');
END;

CREATE TRIGGER journal_entries_no_delete BEFORE DELETE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'journal is append-only');
END;
"#;

/// Sxema v9 (D8 UI, «Narx daftari»): mahsulot narxlari — bazaviy va joriy, bazaviy xarajatdagi ulush (bp).
pub const SCHEMA_V9: &str = r#"
CREATE TABLE price_items (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    base_minor INTEGER NOT NULL CHECK (base_minor > 0),
    current_minor INTEGER NOT NULL CHECK (current_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    weight_bp INTEGER NOT NULL CHECK (weight_bp BETWEEN 0 AND 10000),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX price_items_by_household ON price_items (household_id);
"#;

/// Sxema v10 (D8A ustasi): kelishuvning amal qilish sanasi va imzolar (versiyaga bog'langan).
/// Imzo rasmi PNG data URL (matn); baza shifrlangan, alohida shifrlash kerak emas.
pub const SCHEMA_V10: &str = r#"
ALTER TABLE agreements ADD COLUMN effective_from TEXT;

CREATE TABLE signatures (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    party_id TEXT NOT NULL CHECK (length(trim(party_id)) > 0),
    role TEXT NOT NULL CHECK (role IN ('PARTY', 'WITNESS', 'ARBITER')),
    version INTEGER NOT NULL CHECK (version >= 1),
    image TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (agreement_id, party_id, role, version)
) STRICT;
"#;

/// Sxema v11 (D9): qarzlar (olingan) va bergan qarzlar — to'lash rejasi bilan. Foiz maydoni yo'q (SPEC 2D.5).
/// `has_markup` — mavjud foizli qarzni kuzatish belgisi (faqat chiqish uchun); `loans.agreement_id` — tilxat.
pub const SCHEMA_V11: &str = r#"
CREATE TABLE loans (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    direction TEXT NOT NULL CHECK (direction IN ('TAKEN', 'GIVEN')),
    counterparty TEXT NOT NULL CHECK (length(trim(counterparty)) > 0),
    counterparty_type TEXT NOT NULL CHECK (counterparty_type IN ('BANK', 'SHOP', 'RELATIVE', 'FRIEND', 'OTHER')),
    reason TEXT,
    principal_minor INTEGER NOT NULL CHECK (principal_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    has_markup INTEGER NOT NULL DEFAULT 0 CHECK (has_markup IN (0, 1)),
    incurred_on TEXT NOT NULL,
    borrow_verdict TEXT CHECK (borrow_verdict IS NULL OR borrow_verdict IN ('OK', 'CAUTION', 'STOP')),
    friction_necessity INTEGER CHECK (friction_necessity IS NULL OR friction_necessity IN (0, 1)),
    friction_alternative INTEGER CHECK (friction_alternative IS NULL OR friction_alternative IN (0, 1)),
    agreement_id TEXT REFERENCES agreements (id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX loans_by_household ON loans (household_id, direction);

CREATE TABLE loan_installments (
    loan_id TEXT NOT NULL REFERENCES loans (id),
    seq INTEGER NOT NULL CHECK (seq >= 1),
    due_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    PRIMARY KEY (loan_id, seq)
) STRICT;

CREATE TABLE loan_payments (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    loan_id TEXT NOT NULL REFERENCES loans (id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    paid_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX loan_payments_by_loan ON loan_payments (loan_id);
"#;

pub const SCHEMA_V12: &str = r#"
CREATE TABLE ceremonies (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    kind TEXT NOT NULL CHECK (kind IN ('TOY', 'BESHIK', 'SUNNAT', 'MARAKA', 'OTHER')),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    event_on TEXT,
    status TEXT NOT NULL CHECK (status IN ('PLANNED', 'CONFIRMED')),
    family_discussed INTEGER NOT NULL DEFAULT 0 CHECK (family_discussed IN (0, 1)),
    chosen_scenario_id TEXT,
    goal_name TEXT,
    goal_target_minor INTEGER CHECK (goal_target_minor IS NULL OR goal_target_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX ceremonies_by_household ON ceremonies (household_id);

CREATE TABLE ceremony_scenarios (
    id TEXT PRIMARY KEY NOT NULL,
    ceremony_id TEXT NOT NULL REFERENCES ceremonies (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    guests INTEGER NOT NULL CHECK (guests >= 0),
    days INTEGER NOT NULL CHECK (days >= 1),
    seq INTEGER NOT NULL CHECK (seq >= 1),
    created_at TEXT NOT NULL
) STRICT;
CREATE INDEX ceremony_scenarios_by_ceremony ON ceremony_scenarios (ceremony_id);

CREATE TABLE ceremony_lines (
    id TEXT PRIMARY KEY NOT NULL,
    scenario_id TEXT NOT NULL REFERENCES ceremony_scenarios (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_minor INTEGER NOT NULL CHECK (unit_minor >= 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    funding TEXT NOT NULL CHECK (funding IN ('SAVINGS', 'FAMILY', 'EXPECTED_GIFTS', 'DEBT')),
    seq INTEGER NOT NULL CHECK (seq >= 1)
) STRICT;
CREATE INDEX ceremony_lines_by_scenario ON ceremony_lines (scenario_id);
"#;

pub const SCHEMA_V13: &str = r#"
CREATE TABLE partnerships (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL UNIQUE REFERENCES agreements (id),
    kind TEXT NOT NULL CHECK (kind IN ('MUDARABA', 'MUSHARAKA')),
    my_role TEXT NOT NULL CHECK (my_role IN ('CAPITAL_PROVIDER', 'WORKER')),
    buyout_total_minor INTEGER CHECK (buyout_total_minor IS NULL OR buyout_total_minor > 0),
    buyout_months INTEGER CHECK (buyout_months IS NULL OR buyout_months >= 1),
    buyout_start TEXT,
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    consent_member TEXT,
    consent_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX partnerships_by_household ON partnerships (household_id);

CREATE TABLE partnership_buyout_payments (
    id TEXT PRIMARY KEY NOT NULL,
    partnership_id TEXT NOT NULL REFERENCES partnerships (id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    paid_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX partnership_buyout_payments_by_partnership ON partnership_buyout_payments (partnership_id);
"#;

/// Sxema v14 (D13): jurnal turlari kengaytirildi (ledger, zarar taqsimoti, buyout) — jadval qayta quriladi
/// (SQLite CHECK o'zgarmaydi); yopilgan sheriklik davrlari (`venture_periods`), o'zgarmas.
pub const SCHEMA_V14: &str = r#"
CREATE TABLE journal_entries_v14 (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    seq INTEGER NOT NULL CHECK (seq >= 1),
    kind TEXT NOT NULL CHECK (kind IN ('OPENING_BALANCE', 'CONTRIBUTION', 'PROFIT_DISTRIBUTION', 'LOAN_PAYMENT', 'CORRECTION',
        'VENTURE_INCOME', 'VENTURE_EXPENSE', 'FORCE_MAJEURE', 'LOSS_DISTRIBUTION', 'BUYOUT_PAYMENT')),
    party_id TEXT NOT NULL CHECK (length(trim(party_id)) > 0),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    entry_date TEXT NOT NULL,
    note TEXT,
    prev_hash TEXT NOT NULL CHECK (length(prev_hash) = 64),
    hash TEXT NOT NULL CHECK (length(hash) = 64),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (agreement_id, seq)
) STRICT;
INSERT INTO journal_entries_v14 SELECT id, household_id, agreement_id, seq, kind, party_id, amount_minor, currency,
    entry_date, note, prev_hash, hash, created_at, origin_device_id FROM journal_entries;
DROP TRIGGER journal_entries_no_update;
DROP TRIGGER journal_entries_no_delete;
DROP TABLE journal_entries;
ALTER TABLE journal_entries_v14 RENAME TO journal_entries;

CREATE TRIGGER journal_entries_no_update BEFORE UPDATE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'journal is append-only');
END;

CREATE TRIGGER journal_entries_no_delete BEFORE DELETE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'journal is append-only');
END;

CREATE TABLE venture_periods (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    partnership_id TEXT NOT NULL REFERENCES partnerships (id),
    start_on TEXT NOT NULL,
    end_on TEXT NOT NULL,
    income_minor INTEGER NOT NULL CHECK (income_minor >= 0),
    expense_minor INTEGER NOT NULL CHECK (expense_minor >= 0),
    net_minor INTEGER NOT NULL,
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    chain_head TEXT NOT NULL CHECK (length(chain_head) = 64),
    force_majeure_note TEXT,
    distribution_json TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (partnership_id, end_on)
) STRICT;
CREATE INDEX venture_periods_by_partnership ON venture_periods (partnership_id, end_on);

CREATE TRIGGER venture_periods_no_update BEFORE UPDATE ON venture_periods
BEGIN
    SELECT RAISE(ABORT, 'closed period is immutable');
END;

CREATE TRIGGER venture_periods_no_delete BEFORE DELETE ON venture_periods
BEGIN
    SELECT RAISE(ABORT, 'closed period is immutable');
END;
"#;

/// Sxema v15 (D13A): vazifa hodisalari, ochiq hisob ko'riklari va belgilar, nizolar, oilaviy tasdiqlar,
/// versiya izohlari.
pub const SCHEMA_V15: &str = r#"
CREATE TABLE duty_incidents (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    duty_id TEXT NOT NULL,
    party_id TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    proposed_fix TEXT,
    occurred_on TEXT NOT NULL,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX duty_incidents_by_agreement ON duty_incidents (agreement_id);

CREATE TABLE reviews (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    chain_head TEXT NOT NULL CHECK (length(chain_head) = 64),
    chain_ok INTEGER NOT NULL CHECK (chain_ok IN (0, 1)),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX reviews_by_agreement ON reviews (agreement_id, created_at);

CREATE TABLE review_marks (
    review_id TEXT NOT NULL REFERENCES reviews (id),
    party_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('AGREE', 'OBJECT')),
    comment TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (review_id, party_id)
) STRICT;

CREATE TABLE disputes (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    opened_by_party_id TEXT NOT NULL,
    subject TEXT NOT NULL CHECK (length(trim(subject)) > 0),
    clauses TEXT NOT NULL,
    claim TEXT NOT NULL,
    opened_on TEXT NOT NULL,
    decision TEXT,
    decided_on TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX disputes_by_agreement ON disputes (agreement_id);

CREATE TABLE family_consents (
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    member_id TEXT NOT NULL REFERENCES members (id),
    version INTEGER NOT NULL CHECK (version >= 1),
    created_at TEXT NOT NULL,
    PRIMARY KEY (agreement_id, member_id, version)
) STRICT;

CREATE TABLE version_notes (
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    version INTEGER NOT NULL CHECK (version >= 1),
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (agreement_id, version)
) STRICT;
"#;

/// Sxema v16 (D10+ qoldiqlari): to'lovda oila a'zosining hissasi, sotiladigan buyumlar, ongli chetlab o'tish
/// yozuvlari, ledger yozuviga chek rasmi.
pub const SCHEMA_V16: &str = r#"
ALTER TABLE loan_payments ADD COLUMN contributor_member_id TEXT REFERENCES members (id);

CREATE TABLE sellable_items (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    estimate_minor INTEGER NOT NULL CHECK (estimate_minor > 0),
    currency TEXT NOT NULL CHECK (currency IN ('UZS', 'USD', 'EUR', 'RUB')),
    note TEXT,
    sold_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX sellable_items_by_household ON sellable_items (household_id);

CREATE TABLE gate_overrides (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    action TEXT NOT NULL,
    target_id TEXT,
    reason TEXT NOT NULL CHECK (length(trim(reason)) >= 20),
    member_id TEXT NOT NULL REFERENCES members (id),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX gate_overrides_by_target ON gate_overrides (target_id);

CREATE TABLE venture_attachments (
    id TEXT PRIMARY KEY NOT NULL,
    household_id TEXT NOT NULL REFERENCES households (id),
    agreement_id TEXT NOT NULL REFERENCES agreements (id),
    seq INTEGER NOT NULL CHECK (seq >= 1),
    image TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
) STRICT;
CREATE INDEX venture_attachments_by_agreement ON venture_attachments (agreement_id, seq);
"#;

/// Barcha migratsiyalar, tartib bilan. Yangi sxema o'zgarishi — yangi `M::up` (eski migratsiyani o'zgartirmang).
pub fn migrations() -> Migrations<'static> {
    Migrations::new(vec![
        M::up(SCHEMA_V1),
        M::up(SCHEMA_V2),
        M::up(SCHEMA_V3),
        M::up(SCHEMA_V4),
        M::up(SCHEMA_V5),
        M::up(SCHEMA_V6),
        M::up(SCHEMA_V7),
        M::up(SCHEMA_V8),
        M::up(SCHEMA_V9),
        M::up(SCHEMA_V10),
        M::up(SCHEMA_V11),
        M::up(SCHEMA_V12),
        M::up(SCHEMA_V13),
        M::up(SCHEMA_V14),
        M::up(SCHEMA_V15),
        M::up(SCHEMA_V16),
    ])
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
    "debts",
    "debt_payments",
    "monthly_reports",
    "task_completions",
    "daftar_pages",
    "necessity_changes",
    "havas_limits",
    "limit_consents",
    "scheduled_treats",
    "subscriptions",
    "envelopes",
    "savings_rescues",
    "household_settings",
    "agreements",
    "journal_entries",
    "price_items",
    "signatures",
    "loans",
    "loan_installments",
    "loan_payments",
    "ceremonies",
    "ceremony_scenarios",
    "ceremony_lines",
    "partnerships",
    "partnership_buyout_payments",
    "venture_periods",
    "duty_incidents",
    "reviews",
    "review_marks",
    "disputes",
    "family_consents",
    "version_notes",
    "sellable_items",
    "gate_overrides",
    "venture_attachments",
];
