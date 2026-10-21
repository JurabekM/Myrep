-- Sxema v1 (docs/BARAKA_OILASI.md 8.1, Y5).
-- Har bir jadvalda: household_id, space_id (makon jadvallarida), created_at, updated_at,
-- deleted_at (soft delete), version, origin_device_id, updated_by_device_id.
-- Pul: amount_minor INTEGER + currency TEXT. Sana: lokal 'YYYY-MM-DD'. Vaqt: UTC ISO-8601.

CREATE TABLE households (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    name TEXT NOT NULL,
    base_currency TEXT NOT NULL DEFAULT 'UZS',
    locale TEXT NOT NULL DEFAULT 'uz',
    tz TEXT NOT NULL DEFAULT 'Asia/Tashkent',
    month_start_day INTEGER NOT NULL DEFAULT 1 CHECK (month_start_day BETWEEN 1 AND 28),
    week_anchor TEXT NOT NULL DEFAULT 'FRI',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (household_id = id)
);

CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    paired_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE spaces (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    kind TEXT NOT NULL CHECK (kind IN ('UY', 'KASBKOR', 'MUSOFIR')),
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE members (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADULT', 'CHILD')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE space_members (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    role TEXT NOT NULL DEFAULT 'MEMBER',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    UNIQUE (space_id, member_id)
);

CREATE TABLE categories (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    name_key TEXT NOT NULL,
    custom_name TEXT,
    default_necessity TEXT CHECK (default_necessity IN ('ZARUR', 'KERAK', 'HAVAS')),
    is_system INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE incomes (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    member_id TEXT REFERENCES members(id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    source TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('CASH', 'CARD')),
    source_type TEXT CHECK (source_type IN ('TER', 'MOL', 'TAVAKKAL', 'RIBO')),
    occurred_on TEXT NOT NULL,
    note TEXT,
    transfer_id TEXT,
    visibility TEXT NOT NULL DEFAULT 'SHARED' CHECK (visibility IN ('SHARED', 'PRIVATE')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX incomes_space_date ON incomes(space_id, occurred_on);

CREATE TABLE obligations (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    currency TEXT NOT NULL,
    due_day INTEGER CHECK (due_day BETWEEN 1 AND 31),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE expenses (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    category_id TEXT NOT NULL REFERENCES categories(id),
    member_id TEXT REFERENCES members(id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('CASH', 'CARD')),
    occurred_on TEXT NOT NULL,
    necessity TEXT CHECK (necessity IN ('ZARUR', 'KERAK', 'HAVAS')),
    envelope_id TEXT,
    obligation_id TEXT REFERENCES obligations(id),
    is_gift INTEGER NOT NULL DEFAULT 0,
    is_ostentation INTEGER NOT NULL DEFAULT 0,
    funded_by_debt INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    visibility TEXT NOT NULL DEFAULT 'SHARED' CHECK (visibility IN ('SHARED', 'PRIVATE')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX expenses_space_date ON expenses(space_id, occurred_on);

CREATE TABLE assets (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    type TEXT NOT NULL CHECK (type IN ('CASH', 'BANK_CARD', 'VAULT', 'GOLD', 'SILVER', 'FOREIGN_CURRENCY', 'RECEIVABLE', 'TRADE_GOODS', 'BUSINESS_SHARE')),
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    currency TEXT,
    vault_type TEXT CHECK (vault_type IN ('QOROVUL', 'OSADIGAN')),
    owner_member_id TEXT REFERENCES members(id),
    visibility TEXT NOT NULL DEFAULT 'SHARED' CHECK (visibility IN ('SHARED', 'PRIVATE')),
    acquired_on TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE asset_snapshots (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    asset_id TEXT NOT NULL REFERENCES assets(id),
    quantity INTEGER NOT NULL,
    taken_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE vault_transactions (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    asset_id TEXT NOT NULL REFERENCES assets(id),
    amount_minor INTEGER NOT NULL CHECK (amount_minor <> 0),
    currency TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('INITIAL', 'ALLOCATION', 'MANUAL', 'WITHDRAWAL', 'RESCUE')),
    income_id TEXT REFERENCES incomes(id),
    note TEXT,
    occurred_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK ((reason = 'WITHDRAWAL') = (amount_minor < 0)),
    CHECK (reason <> 'WITHDRAWAL' OR (note IS NOT NULL AND length(trim(note)) > 0))
);
CREATE INDEX vault_tx_asset ON vault_transactions(asset_id, occurred_on);

CREATE TABLE allocation_rules (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    kind TEXT NOT NULL CHECK (kind IN ('PERCENT', 'FIXED')),
    bp INTEGER CHECK (bp BETWEEN 0 AND 10000),
    amount_minor INTEGER,
    currency TEXT,
    progressive INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK ((kind = 'PERCENT' AND bp IS NOT NULL) OR (kind = 'FIXED' AND amount_minor IS NOT NULL AND currency IS NOT NULL))
);

CREATE TABLE fx_rates (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    rate_num INTEGER NOT NULL CHECK (rate_num > 0),
    rate_den INTEGER NOT NULL CHECK (rate_den > 0),
    rate_date TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE agreements (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    type TEXT NOT NULL CHECK (type IN ('PARTNERSHIP', 'LOAN', 'RENT', 'SERVICE', 'FAMILY', 'OTHER')),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SIGNED', 'ACTIVE', 'IN_DISPUTE', 'CLOSED')),
    title TEXT NOT NULL,
    keeper_device_id TEXT NOT NULL REFERENCES devices(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

-- Append-only jurnal (6-bo'lim). UPDATE va DELETE DB darajasida taqiqlangan.
CREATE TABLE journal_entries (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL REFERENCES agreements(id),
    seq INTEGER NOT NULL CHECK (seq >= 1),
    kind TEXT NOT NULL,
    party_id TEXT,
    amount_minor INTEGER,
    currency TEXT,
    entry_date TEXT NOT NULL,
    note TEXT,
    corrects_entry_id TEXT REFERENCES journal_entries(id),
    refs_json TEXT,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (agreement_id, seq),
    CHECK ((amount_minor IS NULL) = (currency IS NULL))
);

CREATE TRIGGER journal_entries_no_update BEFORE UPDATE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'JOURNAL_IMMUTABLE');
END;

CREATE TRIGGER journal_entries_no_delete BEFORE DELETE ON journal_entries
BEGIN
    SELECT RAISE(ABORT, 'JOURNAL_IMMUTABLE');
END;

CREATE TABLE sync_peers (
    peer_device_id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    last_export_at TEXT,
    last_import_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Vidjet va tray yozadigan, lekin o'qiy olmaydigan navbat (7.5): sealed box shifrlangan.
CREATE TABLE quick_entry_queue (
    id TEXT PRIMARY KEY,
    sealed BLOB NOT NULL,
    created_at TEXT NOT NULL
);
