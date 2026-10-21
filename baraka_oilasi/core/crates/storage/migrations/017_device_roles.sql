-- Sxema v17 (K8, ADR-0003): ko'p qurilma va rollar. Rol qurilmaga beriladi; uni faqat egasining
-- (rolsiz) qurilmasi yozadi. Rolsiz qurilma — egasi (U14 dagi kabi to'liq).

-- Qurilma roli va u bog'langan Kasb-kor makoni (sinxronlanadi; birlamchi kalit — qurilma).
CREATE TABLE device_access (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    device_id TEXT NOT NULL UNIQUE REFERENCES devices(id),
    role TEXT NOT NULL CHECK (role IN ('SELLER', 'ACCOUNTANT')),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    revoked_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (id = device_id)
);

-- Ulash taklifidagi rol (faqat shu qurilmada): yangi qurilma birinchi faylida shu eksportni
-- tasdiqlaganda (`ackExportId`) egasi uni rolga bog'laydi.
ALTER TABLE sync_exports ADD COLUMN role TEXT CHECK (role IS NULL OR role IN ('SELLER', 'ACCOUNTANT'));
ALTER TABLE sync_exports ADD COLUMN role_space_id TEXT;

-- Shu qurilma rolli ulash faylidan qo'shilgan bo'lsa — egasining `device_access` yozuvi kelguncha
-- rolni shu yerdan biladi (sinxronlanmaydi).
CREATE TABLE local_device_role (
    household_id TEXT PRIMARY KEY REFERENCES households(id),
    role TEXT NOT NULL CHECK (role IN ('SELLER', 'ACCOUNTANT')),
    space_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Sotuvchi smenasi (o'zgarmas): o'z naqd tushumi va nasiya to'lovlari bilan kutilgan kassa,
-- sanalgan, farq va sabab, egasiga topshirilgan. Qurilmada kuniga bitta.
CREATE TABLE kk_shifts (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    device_id TEXT NOT NULL REFERENCES devices(id),
    day TEXT NOT NULL,
    currency TEXT NOT NULL,
    opening_minor INTEGER NOT NULL CHECK (opening_minor >= 0),
    cash_sales_minor INTEGER NOT NULL CHECK (cash_sales_minor >= 0),
    credit_payments_minor INTEGER NOT NULL CHECK (credit_payments_minor >= 0),
    card_in_minor INTEGER NOT NULL CHECK (card_in_minor >= 0),
    expected_minor INTEGER NOT NULL,
    counted_minor INTEGER NOT NULL CHECK (counted_minor >= 0),
    difference_minor INTEGER NOT NULL,
    reason TEXT CHECK (reason IS NULL OR reason IN ('UNRECORDED_EXPENSE', 'CHANGE_ERROR', 'GIVEN_ON_CREDIT', 'OWNER_TOOK', 'UNKNOWN')),
    handed_over_minor INTEGER NOT NULL CHECK (handed_over_minor BETWEEN 0 AND counted_minor),
    note TEXT,
    closed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (device_id, day),
    CHECK (expected_minor = opening_minor + cash_sales_minor + credit_payments_minor),
    CHECK (difference_minor = counted_minor - expected_minor),
    CHECK ((difference_minor = 0) = (reason IS NULL))
);
CREATE INDEX kk_shifts_space_day ON kk_shifts(space_id, day);

CREATE TRIGGER kk_shifts_no_update BEFORE UPDATE ON kk_shifts
BEGIN
    SELECT RAISE(ABORT, 'KK_SHIFT_IMMUTABLE');
END;

CREATE TRIGGER kk_shifts_no_delete BEFORE DELETE ON kk_shifts
BEGIN
    SELECT RAISE(ABORT, 'KK_SHIFT_IMMUTABLE');
END;
