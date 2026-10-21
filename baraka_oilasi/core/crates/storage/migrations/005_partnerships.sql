-- Sxema v5 (U11): sheriklik (mudoraba / musharaka), shartnoma versiyalari, shu qurilmada
-- chizilgan imzolar, kapital qabul qilishda oilaviy rozilik.
-- Shartnoma matni (9 savol + sheriklik shartlari) `agreements.payload_json` da (joriy qoralama).

CREATE TABLE partnerships (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL UNIQUE REFERENCES agreements(id),
    kind TEXT NOT NULL CHECK (kind IN ('MUDARABA', 'MUSHARAKA')),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SIGNED', 'ACTIVE', 'CLOSED')),
    currency TEXT NOT NULL,
    -- Kuchdagi (to'liq imzolangan) versiya raqami.
    signed_version INTEGER CHECK (signed_version >= 1),
    -- «Bu qarz emas» tushuntirishini o'qib tasdiqlagan sana (kapital qabul qiluvchi uchun).
    not_debt_ack_on TEXT,
    -- Faollashtirish paytidagi darvoza natijasi (kapital kirituvchi uchun), JSON.
    gate_json TEXT,
    activated_on TEXT,
    closed_on TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

-- Imzolashga berilgan shartnoma matnining o'zgarmas nusxasi. Matn o'zgarsa — yangi versiya.
CREATE TABLE agreement_versions (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL REFERENCES agreements(id),
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    change_note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (agreement_id, version_no)
);

CREATE TABLE agreement_signatures (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    version_id TEXT NOT NULL REFERENCES agreement_versions(id),
    -- `party:<id>`, `witness:<n>` yoki `arbiter`.
    signer_key TEXT NOT NULL,
    signer_role TEXT NOT NULL CHECK (signer_role IN ('PARTY', 'WITNESS', 'ARBITER')),
    signer_name TEXT NOT NULL,
    strokes_json TEXT NOT NULL,
    signed_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (version_id, signer_key)
);

-- Versiyalar va imzolar — dalil: o'zgartirish va o'chirish DB darajasida taqiqlangan.
CREATE TRIGGER agreement_versions_no_update BEFORE UPDATE ON agreement_versions
BEGIN
    SELECT RAISE(ABORT, 'AGREEMENT_VERSION_IMMUTABLE');
END;

CREATE TRIGGER agreement_versions_no_delete BEFORE DELETE ON agreement_versions
BEGIN
    SELECT RAISE(ABORT, 'AGREEMENT_VERSION_IMMUTABLE');
END;

CREATE TRIGGER agreement_signatures_no_update BEFORE UPDATE ON agreement_signatures
BEGIN
    SELECT RAISE(ABORT, 'SIGNATURE_IMMUTABLE');
END;

CREATE TRIGGER agreement_signatures_no_delete BEFORE DELETE ON agreement_signatures
BEGIN
    SELECT RAISE(ABORT, 'SIGNATURE_IMMUTABLE');
END;

-- Kapital qabul qilishda kattalar roziligi (uy/SPEC 2E.6), versiyaga bog'liq.
CREATE TABLE partnership_consents (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    partnership_id TEXT NOT NULL REFERENCES partnerships(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    agreed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (partnership_id, member_id, version_no)
);

CREATE INDEX idx_partnerships_space ON partnerships(household_id, space_id, deleted_at);
CREATE INDEX idx_agreement_versions ON agreement_versions(agreement_id, version_no);
CREATE INDEX idx_agreement_signatures ON agreement_signatures(version_id);
