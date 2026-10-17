-- Sxema v10 (K1): Kasb-kor makoni — «ikki cho'ntak» (docs/kasbkor/SPEC.md 2).
-- Tushum va chiqim — `incomes` / `expenses` (space_id = Kasb-kor makoni; kanal CASH/CARD — hamyon).
-- Bu yerda faqat egasi bilan biznes orasidagi harakatlar va hamyonlar orasidagi o'tkazmalar.

CREATE TABLE kk_settings (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL UNIQUE REFERENCES spaces(id),
    -- Egasining oylik qat'iy maoshi (0 — belgilanmagan).
    owner_salary_minor INTEGER NOT NULL DEFAULT 0 CHECK (owner_salary_minor >= 0),
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE kk_moves (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    -- OPENING — ilovagacha bo'lgan qoldiq; OWNER_DRAW — «egasi oldi» (maoshdan avans);
    -- OWNER_CONTRIBUTION — egasi kiritgan kapital; OWNER_SALARY — Uy makoniga maosh;
    -- TRANSFER — hamyonlar orasida (masalan, kassadan kartaga).
    kind TEXT NOT NULL CHECK (kind IN ('OPENING', 'OWNER_DRAW', 'OWNER_CONTRIBUTION', 'OWNER_SALARY', 'TRANSFER')),
    wallet TEXT NOT NULL CHECK (wallet IN ('CASH', 'CARD')),
    to_wallet TEXT CHECK (to_wallet IS NULL OR to_wallet IN ('CASH', 'CARD')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    occurred_on TEXT NOT NULL,
    note TEXT,
    -- OWNER_SALARY: Uy makonidagi daromad bilan umumiy `transfer_id` (BARAKA_OILASI.md 4.6).
    transfer_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK ((kind = 'TRANSFER') = (to_wallet IS NOT NULL)),
    CHECK (to_wallet IS NULL OR to_wallet <> wallet),
    CHECK ((kind = 'OWNER_SALARY') = (transfer_id IS NOT NULL))
);
CREATE INDEX kk_moves_space_date ON kk_moves(space_id, occurred_on);
