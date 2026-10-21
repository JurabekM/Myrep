-- Sxema v18 (M1): Musofir makoni — ko'p valyuta, o'z ulushi va qaytish jamg'armasi (docs/musofir/SPEC.md 2–4).
-- Maosh va xarajat — `incomes` / `expenses` (space_id = Musofir makoni, valyuta = ish valyutasi;
-- maosh — `source_type = 'TER'`). Bu yerda sozlamalar, kurslar va pul harakatlari.

CREATE TABLE mf_settings (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL UNIQUE REFERENCES spaces(id),
    country TEXT,
    -- Ish valyutasi: yozuvlar paydo bo'lgach o'zgarmaydi (ilova tekshiradi).
    work_currency TEXT NOT NULL,
    -- O'z ulushi: daromaddan qaytish jamg'armasiga (bp).
    share_bp INTEGER NOT NULL CHECK (share_bp BETWEEN 0 AND 10000),
    -- Qaytish jamg'armasi maqsadi — uy valyutasida.
    target_minor INTEGER CHECK (target_minor IS NULL OR target_minor > 0),
    target_currency TEXT,
    return_on TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK ((target_minor IS NULL) = (target_currency IS NULL))
);

-- Foydalanuvchi kiritgan kurs (o'zgarmas): 1 `from_currency` = rate_num / rate_den `to_currency`.
-- Bir sanada bir nechta bo'lsa — oxirgi kiritilgani amalda.
CREATE TABLE mf_rates (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    rate_on TEXT NOT NULL,
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    rate_num INTEGER NOT NULL CHECK (rate_num > 0),
    rate_den INTEGER NOT NULL CHECK (rate_den > 0),
    source TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);
CREATE INDEX mf_rates_space_date ON mf_rates(space_id, rate_on);

CREATE TRIGGER mf_rates_no_update BEFORE UPDATE ON mf_rates
BEGIN
    SELECT RAISE(ABORT, 'MF_RATE_IMMUTABLE');
END;

CREATE TRIGGER mf_rates_no_delete BEFORE DELETE ON mf_rates
BEGIN
    SELECT RAISE(ABORT, 'MF_RATE_IMMUTABLE');
END;

-- OPENING — qo'ldagi boshlang'ich pul; SENT_HOME — uyga yuborilgan (komissiya va uyda olingan summa
-- bilan); FUND_IN / FUND_OUT — qaytish jamg'armasiga / undan (sabab majburiy); FUND_OPENING — jamg'arma
-- boshlang'ich qoldig'i. Summalar ish valyutasida, `received_minor` — uy valyutasida.
CREATE TABLE mf_moves (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    kind TEXT NOT NULL CHECK (kind IN ('OPENING', 'SENT_HOME', 'FUND_IN', 'FUND_OUT', 'FUND_OPENING')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    fee_minor INTEGER NOT NULL DEFAULT 0 CHECK (fee_minor >= 0),
    received_minor INTEGER CHECK (received_minor IS NULL OR received_minor > 0),
    received_currency TEXT,
    occurred_on TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (kind = 'SENT_HOME' OR (fee_minor = 0 AND received_minor IS NULL)),
    CHECK ((received_minor IS NULL) = (received_currency IS NULL)),
    CHECK (kind <> 'FUND_OUT' OR length(trim(coalesce(note, ''))) > 0)
);
CREATE INDEX mf_moves_space_date ON mf_moves(space_id, occurred_on);
