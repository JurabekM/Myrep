-- Sxema v3 (U9): qarzdan chiqish rejimi, yopish tartibi, to'lovchilar, sotiladigan buyumlar.

-- Muddatidan oldin to'lash jarimasi/komissiyasi: qo'shimcha to'lovdan bp (taxminiy hisob uchun).
ALTER TABLE debts ADD COLUMN prepayment_fee_bp INTEGER NOT NULL DEFAULT 0
    CHECK (prepayment_fee_bp BETWEEN 0 AND 10000);

-- Bitta qarzni bir necha kishi to'lashi (uy/SPEC 2D.4). MVP'da oddiy yozuv.
CREATE TABLE debt_contributors (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    debt_id TEXT NOT NULL REFERENCES debts(id),
    name TEXT NOT NULL,
    monthly_share_minor INTEGER CHECK (monthly_share_minor IS NULL OR monthly_share_minor > 0),
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

ALTER TABLE repayments ADD COLUMN contributor_id TEXT REFERENCES debt_contributors(id);

-- Byudjet rejimi (uy/SPEC 2D.1): makon uchun bitta joriy yozuv.
CREATE TABLE budget_settings (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL UNIQUE REFERENCES spaces(id),
    mode TEXT NOT NULL CHECK (mode IN ('STANDARD', 'DEBT_RECOVERY')),
    household_bp INTEGER NOT NULL,
    extra_debt_bp INTEGER NOT NULL,
    savings_bp INTEGER NOT NULL CHECK (savings_bp >= 100),
    changed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (household_bp >= 0 AND extra_debt_bp >= 0 AND household_bp + extra_debt_bp + savings_bp = 10000)
);

-- Sotiladigan buyumlar (uy/SPEC 2D.7).
CREATE TABLE sellable_items (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    title TEXT NOT NULL,
    estimated_minor INTEGER NOT NULL CHECK (estimated_minor > 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'LISTED' CHECK (status IN ('LISTED', 'SOLD')),
    sold_minor INTEGER CHECK (sold_minor IS NULL OR sold_minor > 0),
    sold_on TEXT,
    debt_id TEXT REFERENCES debts(id),
    repayment_id TEXT REFERENCES repayments(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK ((status = 'SOLD') = (sold_minor IS NOT NULL AND sold_on IS NOT NULL))
);
