-- Sxema v15 (K6): Kasb-kor — xodim (`EMPLOYMENT`) va ta'minotchi (`SUPPLY`) kelishuvlari, avans va haq
-- to'lovlari, yetkazish va ta'minotchiga to'lovlar (docs/kasbkor/SPEC.md 7). Umumiy `agreements` jadvali
-- turlari CHECK bilan qotirilgan (SQLite'da o'zgartirish — jadvalni qayta qurish), shuning uchun alohida
-- jadvallar (K4 dagi nasiya kabi). Foiz, ustama yoki jarima ustuni yo'q.

-- Kelishuvning joriy (tahrirlanadigan) holati; imzolangan versiyalar — `kk_agreement_versions` da.
CREATE TABLE kk_agreements (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    kind TEXT NOT NULL CHECK (kind IN ('EMPLOYMENT', 'SUPPLY')),
    party_name TEXT NOT NULL CHECK (length(party_name) BETWEEN 1 AND 100),
    -- Telefon — faqat rozilik belgisi bilan (OQ-Y3).
    phone TEXT,
    phone_consent INTEGER NOT NULL DEFAULT 0 CHECK (phone_consent IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SIGNED', 'ENDED')),
    currency TEXT NOT NULL,
    -- Shartlar (JSON, `kasbkor_staff.rs`); imzolangandan keyin o'zgarsa — yangi versiya imzolanadi.
    terms_json TEXT NOT NULL,
    started_on TEXT NOT NULL,
    ended_on TEXT,
    -- Xodimga ilovagacha qolgan qarz (musbat) yoki ortiq to'langan (manfiy).
    opening_balance_minor INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (phone IS NULL OR phone_consent = 1),
    CHECK (ended_on IS NULL OR ended_on >= started_on),
    CHECK ((status = 'ENDED') = (ended_on IS NOT NULL))
);

-- Imzolangan versiyalar (o'zgarmas): shartlar, xesh, shablon versiyasi, qachondan amal qiladi.
CREATE TABLE kk_agreement_versions (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL REFERENCES kk_agreements(id),
    seq INTEGER NOT NULL CHECK (seq >= 1),
    terms_json TEXT NOT NULL,
    terms_hash TEXT NOT NULL,
    template_version INTEGER NOT NULL CHECK (template_version >= 1),
    template_review TEXT NOT NULL CHECK (template_review IN ('PENDING', 'APPROVED')),
    effective_from TEXT NOT NULL,
    signed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (agreement_id, seq)
);

CREATE TRIGGER kk_agreement_versions_no_update BEFORE UPDATE ON kk_agreement_versions
BEGIN
    SELECT RAISE(ABORT, 'KK_AGREEMENT_VERSION_IMMUTABLE');
END;

CREATE TRIGGER kk_agreement_versions_no_delete BEFORE DELETE ON kk_agreement_versions
BEGIN
    SELECT RAISE(ABORT, 'KK_AGREEMENT_VERSION_IMMUTABLE');
END;

-- Xodim hodisalari (o'zgarmas): avans (foizsiz, `installments` oyda `start_month` dan ushlanadi) va haq
-- to'lovi. Har biri — Kasb-kor chiqimi (`category.kk.wages`), bitta tranzaksiyada.
CREATE TABLE kk_staff_events (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL REFERENCES kk_agreements(id),
    kind TEXT NOT NULL CHECK (kind IN ('ADVANCE', 'WAGE')),
    occurred_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    installments INTEGER CHECK (installments IS NULL OR installments BETWEEN 1 AND 24),
    -- Ushlash boshlanadigan davr boshi (`YYYY-MM-DD`).
    start_month TEXT,
    wallet TEXT NOT NULL CHECK (wallet IN ('CASH', 'CARD')),
    expense_id TEXT NOT NULL REFERENCES expenses(id),
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    CHECK ((kind = 'ADVANCE') = (installments IS NOT NULL)),
    CHECK ((kind = 'ADVANCE') = (start_month IS NOT NULL))
);
CREATE INDEX kk_staff_events_agreement ON kk_staff_events(agreement_id, occurred_on);

CREATE TRIGGER kk_staff_events_no_update BEFORE UPDATE ON kk_staff_events
BEGIN
    SELECT RAISE(ABORT, 'KK_STAFF_EVENT_IMMUTABLE');
END;

CREATE TRIGGER kk_staff_events_no_delete BEFORE DELETE ON kk_staff_events
BEGIN
    SELECT RAISE(ABORT, 'KK_STAFF_EVENT_IMMUTABLE');
END;

-- Ta'minotchidan yetkazish (o'zgarmas): nasiyaga olingan tovar; tovar bog'langan bo'lsa — hamyonsiz xarid.
CREATE TABLE kk_supply_deliveries (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL REFERENCES kk_agreements(id),
    delivered_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    due_days INTEGER NOT NULL CHECK (due_days BETWEEN 0 AND 365),
    stock_move_id TEXT REFERENCES kk_stock_moves(id),
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);
CREATE INDEX kk_supply_deliveries_agreement ON kk_supply_deliveries(agreement_id, delivered_on);

-- Ta'minotchiga to'lov (o'zgarmas): hamyondan. Tovarsiz ta'minotda — chiqim (`expense_id`), aks holda
-- tovar xaridi kabi (pul oqimiga kirmaydi, tannarx sotilganda).
CREATE TABLE kk_supply_payments (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL REFERENCES kk_agreements(id),
    paid_on TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    wallet TEXT NOT NULL CHECK (wallet IN ('CASH', 'CARD')),
    expense_id TEXT REFERENCES expenses(id),
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);
CREATE INDEX kk_supply_payments_agreement ON kk_supply_payments(agreement_id, paid_on);

CREATE TRIGGER kk_supply_deliveries_no_update BEFORE UPDATE ON kk_supply_deliveries
BEGIN
    SELECT RAISE(ABORT, 'KK_SUPPLY_IMMUTABLE');
END;

CREATE TRIGGER kk_supply_deliveries_no_delete BEFORE DELETE ON kk_supply_deliveries
BEGIN
    SELECT RAISE(ABORT, 'KK_SUPPLY_IMMUTABLE');
END;

CREATE TRIGGER kk_supply_payments_no_update BEFORE UPDATE ON kk_supply_payments
BEGIN
    SELECT RAISE(ABORT, 'KK_SUPPLY_IMMUTABLE');
END;

CREATE TRIGGER kk_supply_payments_no_delete BEFORE DELETE ON kk_supply_payments
BEGIN
    SELECT RAISE(ABORT, 'KK_SUPPLY_IMMUTABLE');
END;
