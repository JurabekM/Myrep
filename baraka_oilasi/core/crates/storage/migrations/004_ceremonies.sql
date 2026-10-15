-- Sxema v4 (U10): marosim rejalovchisi, stsenariylar, byudjet qatorlari, oilaviy muhokama,
-- maqsadga (yosh oila jamg'armasiga) mehmonlar hissasi.

CREATE TABLE ceremonies (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    kind TEXT NOT NULL CHECK (kind IN ('TOY', 'BESHIK_TOY', 'SUNNAT_TOY', 'MARAKA', 'OTHER')),
    title TEXT NOT NULL,
    planned_on TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'DISCUSSED', 'CONFIRMED')),
    selected_scenario_id TEXT,
    currency TEXT NOT NULL,
    -- Qarzni uzish uchun oylik ajratma (bo'lmasa — «Qarzdan chiqish» 20% ulushi).
    monthly_capacity_minor INTEGER CHECK (monthly_capacity_minor IS NULL OR monthly_capacity_minor >= 0),
    -- «Buni qarzsiz qanday o'tkazamiz?» savollariga javoblar: {"guests": "...", ...}.
    discussion_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE ceremony_scenarios (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    ceremony_id TEXT NOT NULL REFERENCES ceremonies(id),
    name TEXT NOT NULL,
    guests INTEGER NOT NULL CHECK (guests >= 0),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE ceremony_lines (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    scenario_id TEXT NOT NULL REFERENCES ceremony_scenarios(id),
    title TEXT NOT NULL,
    line_kind TEXT NOT NULL CHECK (line_kind IN ('ONE_OFF', 'PER_GUEST')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('SAVINGS', 'FAMILY', 'EXPECTED_GIFTS', 'DEBT')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

-- Oilaviy muhokamada har bir katta a'zoning roziligi. Reja o'zgarsa — o'chiriladi (soft delete).
CREATE TABLE ceremony_signoffs (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    ceremony_id TEXT NOT NULL REFERENCES ceremonies(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    agreed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

-- To'yona o'rniga jamg'arma: mehmonlar hissasi (MVP'da qo'lda yoziladi).
CREATE TABLE goal_contributions (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    goal_id TEXT NOT NULL REFERENCES goals(id),
    contributor TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    given_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
