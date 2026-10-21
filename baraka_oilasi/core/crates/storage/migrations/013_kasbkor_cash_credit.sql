-- Sxema v13 (K4): Kasb-kor — kunlik kassa yopish va nasiya daftari (docs/kasbkor/SPEC.md 5).

-- Kunlik kassa yopish (SPEC 5.1). Yopilgan kun o'zgarmaydi; farq naqd kassani tuzatadi (pul oqimiga
-- kirmaydi), shu bilan keyingi kunning ochilish qoldig'i sanalgan summaga teng bo'ladi.
CREATE TABLE kk_cash_days (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    day TEXT NOT NULL,
    currency TEXT NOT NULL,
    opening_minor INTEGER NOT NULL CHECK (opening_minor >= 0),
    expected_minor INTEGER NOT NULL,
    counted_minor INTEGER NOT NULL CHECK (counted_minor >= 0),
    difference_minor INTEGER NOT NULL,
    reason TEXT CHECK (reason IS NULL OR reason IN ('UNRECORDED_EXPENSE', 'CHANGE_ERROR', 'GIVEN_ON_CREDIT', 'OWNER_TOOK', 'UNKNOWN')),
    note TEXT,
    result_json TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (space_id, day),
    CHECK (difference_minor = counted_minor - expected_minor),
    CHECK ((difference_minor = 0) = (reason IS NULL))
);

CREATE TRIGGER kk_cash_days_no_update BEFORE UPDATE ON kk_cash_days
BEGIN
    SELECT RAISE(ABORT, 'KK_CASH_DAY_IMMUTABLE');
END;

CREATE TRIGGER kk_cash_days_no_delete BEFORE DELETE ON kk_cash_days
BEGIN
    SELECT RAISE(ABORT, 'KK_CASH_DAY_IMMUTABLE');
END;

-- Mijozlar (SPEC 5.2, OQ-Y3): telefon ixtiyoriy, saqlansa — rozilik belgisi shart.
CREATE TABLE kk_customers (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    phone TEXT,
    phone_consent INTEGER NOT NULL DEFAULT 0 CHECK (phone_consent IN (0, 1)),
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (phone IS NULL OR phone_consent = 1)
);

-- Nasiya — mijoz bilan savdo kelishuvi (SPEC 5.2). Narx va jadval qotiriladi.
-- Kechikish uchun ustama, jarima yoki foiz ustuni ataylab yo'q.
CREATE TABLE kk_credit_sales (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    customer_id TEXT NOT NULL REFERENCES kk_customers(id),
    item TEXT NOT NULL CHECK (length(item) BETWEEN 1 AND 200),
    currency TEXT NOT NULL,
    -- Naqd narx — faqat ma'lumot uchun (farqi — OQ-D5).
    cash_price_minor INTEGER CHECK (cash_price_minor IS NULL OR cash_price_minor > 0),
    credit_price_minor INTEGER NOT NULL CHECK (credit_price_minor > 0),
    installments INTEGER NOT NULL CHECK (installments BETWEEN 1 AND 120),
    sold_on TEXT NOT NULL,
    first_due TEXT NOT NULL CHECK (first_due >= sold_on),
    witness TEXT,
    note TEXT,
    -- «Bu hafta kim bilan gaplashaman» belgisi: belgilangan hafta boshi.
    review_week TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX kk_credit_sales_customer ON kk_credit_sales(customer_id);

CREATE TRIGGER kk_credit_terms_immutable
BEFORE UPDATE OF customer_id, item, currency, cash_price_minor, credit_price_minor, installments, sold_on, first_due ON kk_credit_sales
BEGIN
    SELECT RAISE(ABORT, 'KK_CREDIT_TERMS_IMMUTABLE');
END;

-- Nasiya hodisalari: to'lov (Kasb-kor tushumi bilan bog'langan), kechirish, muddatni uzaytirish.
CREATE TABLE kk_credit_events (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    sale_id TEXT NOT NULL REFERENCES kk_credit_sales(id),
    kind TEXT NOT NULL CHECK (kind IN ('PAYMENT', 'FORGIVE', 'EXTEND')),
    occurred_on TEXT NOT NULL,
    amount_minor INTEGER CHECK (amount_minor IS NULL OR amount_minor > 0),
    months INTEGER CHECK (months IS NULL OR months BETWEEN 1 AND 24),
    wallet TEXT CHECK (wallet IS NULL OR wallet IN ('CASH', 'CARD')),
    income_id TEXT REFERENCES incomes(id),
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    CHECK ((kind = 'EXTEND') = (months IS NOT NULL)),
    CHECK ((kind = 'EXTEND') = (amount_minor IS NULL)),
    CHECK ((kind = 'PAYMENT') = (wallet IS NOT NULL)),
    CHECK ((kind = 'PAYMENT') = (income_id IS NOT NULL))
);
CREATE INDEX kk_credit_events_sale ON kk_credit_events(sale_id, occurred_on);

CREATE TRIGGER kk_credit_events_no_update BEFORE UPDATE ON kk_credit_events
BEGIN
    SELECT RAISE(ABORT, 'KK_CREDIT_EVENT_IMMUTABLE');
END;

CREATE TRIGGER kk_credit_events_no_delete BEFORE DELETE ON kk_credit_events
BEGIN
    SELECT RAISE(ABORT, 'KK_CREDIT_EVENT_IMMUTABLE');
END;
