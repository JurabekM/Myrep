-- Sxema v20 (M3): yo'l qarzi, qaytish va sovutish davri, katta qarorlar jurnali (docs/musofir/SPEC.md 6).

-- Musofirning shaxsiy sozlamalari (oilaga yuborilmaydi, ADR-0004): yo'l qarzi — Uy makonidagi U8 qarzi;
-- «Qaytdim» — sana va olib kelingan summa (uy valyutasida).
ALTER TABLE mf_settings ADD COLUMN travel_debt_id TEXT REFERENCES debts(id);
ALTER TABLE mf_settings ADD COLUMN travel_target_months INTEGER CHECK (travel_target_months IS NULL OR travel_target_months BETWEEN 1 AND 60);
ALTER TABLE mf_settings ADD COLUMN returned_on TEXT;
ALTER TABLE mf_settings ADD COLUMN brought_home_minor INTEGER CHECK (brought_home_minor IS NULL OR brought_home_minor > 0);
ALTER TABLE mf_settings ADD COLUMN brought_home_currency TEXT;

-- «Qarz to'lovi» maqsadidan qilingan U8 to'lovi (o'zgarmas): maqsadlar qoldig'ida `DEBT` sarfi.
CREATE TABLE mf_debt_payments (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    repayment_id TEXT NOT NULL UNIQUE REFERENCES repayments(id),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

-- Katta qaror tekshiruvi va musofirning tanlovi (o'zgarmas; shaxsiy).
CREATE TABLE mf_decisions (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    decided_on TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('LEND', 'PARTNERSHIP', 'INVEST', 'PURCHASE', 'OTHER')),
    title TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    answers_json TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('GREEN', 'YELLOW', 'RED')),
    flags_json TEXT NOT NULL,
    in_cooling INTEGER NOT NULL CHECK (in_cooling IN (0, 1)),
    wait_until TEXT,
    choice TEXT NOT NULL CHECK (choice IN ('WAIT', 'PROCEED', 'DECLINE')),
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

CREATE TRIGGER mf_debt_payments_no_update BEFORE UPDATE ON mf_debt_payments
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
CREATE TRIGGER mf_debt_payments_no_delete BEFORE DELETE ON mf_debt_payments
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
CREATE TRIGGER mf_decisions_no_update BEFORE UPDATE ON mf_decisions
BEGIN
    SELECT RAISE(ABORT, 'MF_DECISION_IMMUTABLE');
END;
CREATE TRIGGER mf_decisions_no_delete BEFORE DELETE ON mf_decisions
BEGIN
    SELECT RAISE(ABORT, 'MF_DECISION_IMMUTABLE');
END;
