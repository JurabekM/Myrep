-- Sxema v2 (U8): qarz inventari, bergan qarzlar, to'lov rejalari, to'lovlar, maqsadlar.
-- Pul: amount_minor INTEGER + currency TEXT. Sana: lokal 'YYYY-MM-DD'.

-- Kelishuv ma'lumotlari (tilxat: tomonlar, joy, guvohlar). PDF shundan qayta yaratiladi.
ALTER TABLE agreements ADD COLUMN payload_json TEXT;

CREATE TABLE debts (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    creditor_type TEXT NOT NULL CHECK (creditor_type IN ('BANK', 'SHOP', 'RELATIVE', 'FRIEND', 'OTHER')),
    creditor TEXT NOT NULL,
    reason TEXT,
    currency TEXT NOT NULL,
    -- Reja tuzilgan summa (ilovaga kiritilgandagi qoldiq).
    principal_minor INTEGER NOT NULL CHECK (principal_minor > 0),
    original_principal_minor INTEGER NOT NULL CHECK (original_principal_minor >= principal_minor),
    paid_before_minor INTEGER NOT NULL DEFAULT 0 CHECK (paid_before_minor >= 0),
    plan_kind TEXT NOT NULL CHECK (plan_kind IN ('ANNUITY', 'DIFFERENTIATED', 'FIXED_MARKUP', 'MANUAL')),
    annual_bp INTEGER NOT NULL DEFAULT 0 CHECK (annual_bp BETWEEN 0 AND 100000),
    markup_minor INTEGER NOT NULL DEFAULT 0 CHECK (markup_minor >= 0),
    months INTEGER NOT NULL DEFAULT 0 CHECK (months BETWEEN 0 AND 600),
    started_on TEXT NOT NULL,
    early_repayment_terms TEXT,
    priority INTEGER,
    -- «To'xta va o'yla» natijasi (uy/SPEC 2D.6): javoblar, oylik yuk, ogohlantirishlar.
    borrow_check_json TEXT,
    agreement_id TEXT REFERENCES agreements(id),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

-- Bergan qarzlar. Foiz yoki ustama ustuni ataylab yo'q (uy/SPEC 2D.5).
CREATE TABLE receivables (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    debtor TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    lent_on TEXT NOT NULL,
    note TEXT,
    agreement_id TEXT REFERENCES agreements(id),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE repayment_plan_lines (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    owner_type TEXT NOT NULL CHECK (owner_type IN ('DEBT', 'RECEIVABLE')),
    owner_id TEXT NOT NULL,
    seq INTEGER NOT NULL CHECK (seq >= 1),
    due_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    UNIQUE (owner_type, owner_id, seq)
);

-- Tilxatga bog'langan qarzlarda har bir to'lov jurnal yozuviga ham ega (journal_entry_id).
CREATE TABLE repayments (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    owner_type TEXT NOT NULL CHECK (owner_type IN ('DEBT', 'RECEIVABLE')),
    owner_id TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    paid_on TEXT NOT NULL,
    is_prepayment INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    journal_entry_id TEXT REFERENCES journal_entries(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX repayments_owner ON repayments(owner_type, owner_id, paid_on);

CREATE TABLE goals (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    title TEXT NOT NULL,
    target_minor INTEGER NOT NULL CHECK (target_minor > 0),
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
