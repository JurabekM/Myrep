-- Sxema v16 (K7): Kasb-kor — kengayish darvozasi, «Hisob kuni» konvertlari, zakot hisobi, yillik
-- inventarizatsiya va tarozi tekshiruvi (docs/kasbkor/SPEC.md 6, 8).

-- Sozlamalar: darvoza chegaralari (OQ-K6), «Zakot kuni» (hijriy oy/kun), oltin narxi va nisob (OQ-D7),
-- tovarni baholash usuli (OQ-D5), tarozi eslatmasi.
CREATE TABLE kk_growth_settings (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL UNIQUE REFERENCES spaces(id),
    reserve_months INTEGER NOT NULL DEFAULT 3 CHECK (reserve_months BETWEEN 1 AND 24),
    max_bad_bp INTEGER NOT NULL DEFAULT 1000 CHECK (max_bad_bp BETWEEN 0 AND 10000),
    zakat_month INTEGER CHECK (zakat_month IS NULL OR zakat_month BETWEEN 1 AND 12),
    zakat_day INTEGER CHECK (zakat_day IS NULL OR zakat_day BETWEEN 1 AND 30),
    gold_price_minor INTEGER CHECK (gold_price_minor IS NULL OR gold_price_minor > 0),
    nisab_grams INTEGER NOT NULL DEFAULT 85 CHECK (nisab_grams BETWEEN 1 AND 1000),
    stock_valuation TEXT NOT NULL DEFAULT 'REPLACEMENT' CHECK (stock_valuation IN ('REPLACEMENT', 'BOOK')),
    scale_reminder INTEGER NOT NULL DEFAULT 0 CHECK (scale_reminder IN (0, 1)),
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK ((zakat_month IS NULL) = (zakat_day IS NULL))
);

-- Konvertdan foydalanish (o'zgarmas): pul harakati emas — hamyondagi pulning qaysi maqsadga ketgani.
-- Soliq zaxirasidan foydalanish — «Soliq» kategoriyasidagi chiqim bilan avtomatik, bu yerda yo'q.
CREATE TABLE kk_fund_uses (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    fund TEXT NOT NULL CHECK (fund IN ('RESERVE', 'WORKING', 'EXPANSION', 'SADAQA')),
    used_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

-- Tarozi tekshiruvi (o'zgarmas): ilova tarozini o'lchamaydi — odatni eslatadi va qayd etadi (SPEC 8.1).
CREATE TABLE kk_scale_checks (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    checked_on TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('OK', 'ADJUSTED', 'FAULTY')),
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

-- Zakot hisobi snapshot'i (o'zgarmas): kiritilgan qiymatlar va natija — hisob, fatvo emas (SPEC 8.3).
CREATE TABLE kk_zakat_calcs (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    calculated_on TEXT NOT NULL,
    hijri_date TEXT NOT NULL,
    currency TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    base_minor INTEGER NOT NULL,
    nisab_minor INTEGER NOT NULL CHECK (nisab_minor > 0),
    zakat_minor INTEGER NOT NULL CHECK (zakat_minor >= 0),
    reason TEXT CHECK (reason IS NULL OR reason IN ('BASE_NOT_POSITIVE', 'BELOW_NISAB', 'HAWL_NOT_COMPLETE')),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    CHECK ((reason IS NULL) OR zakat_minor = 0)
);

-- Yillik inventarizatsiya (o'zgarmas): sanalgan miqdorlar; farqlar `kk_stock_moves` da `ADJUST` (SPEC 8.4).
CREATE TABLE kk_stock_counts (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    counted_on TEXT NOT NULL,
    currency TEXT NOT NULL,
    lines_json TEXT NOT NULL,
    value_before_minor INTEGER NOT NULL CHECK (value_before_minor >= 0),
    value_after_minor INTEGER NOT NULL CHECK (value_after_minor >= 0),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

CREATE TRIGGER kk_fund_uses_no_update BEFORE UPDATE ON kk_fund_uses
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;

CREATE TRIGGER kk_fund_uses_no_delete BEFORE DELETE ON kk_fund_uses
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;

CREATE TRIGGER kk_scale_checks_no_update BEFORE UPDATE ON kk_scale_checks
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;

CREATE TRIGGER kk_scale_checks_no_delete BEFORE DELETE ON kk_scale_checks
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;

CREATE TRIGGER kk_zakat_calcs_no_update BEFORE UPDATE ON kk_zakat_calcs
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;

CREATE TRIGGER kk_zakat_calcs_no_delete BEFORE DELETE ON kk_zakat_calcs
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;

CREATE TRIGGER kk_stock_counts_no_update BEFORE UPDATE ON kk_stock_counts
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;

CREATE TRIGGER kk_stock_counts_no_delete BEFORE DELETE ON kk_stock_counts
BEGIN
    SELECT RAISE(ABORT, 'KK_GROWTH_IMMUTABLE');
END;
