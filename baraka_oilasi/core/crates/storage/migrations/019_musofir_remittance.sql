-- Sxema v19 (M2, ADR-0004): «Ikki qirg'oq» — yuborish maqsadlari, uyda qabul va maqsad bo'yicha xarajat;
-- uydagi oila qurilmasi roli `HOME`.

-- Rol CHECK'lariga `HOME` (SQLite CHECK'ni o'zgartira olmaydi — jadvallar yangi nusxa orqali
-- almashtiriladi). `sync_pending` → `sync_exports` tashqi kaliti buzilmasligi uchun kutilayotgan
-- yozuvlar vaqtincha chetga olinadi va qaytariladi.
CREATE TABLE device_access_v19 (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    device_id TEXT NOT NULL UNIQUE REFERENCES devices(id),
    role TEXT NOT NULL CHECK (role IN ('SELLER', 'ACCOUNTANT', 'HOME')),
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
INSERT INTO device_access_v19 SELECT * FROM device_access;
DROP TABLE device_access;
ALTER TABLE device_access_v19 RENAME TO device_access;

CREATE TABLE local_device_role_v19 (
    household_id TEXT PRIMARY KEY REFERENCES households(id),
    role TEXT NOT NULL CHECK (role IN ('SELLER', 'ACCOUNTANT', 'HOME')),
    space_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
INSERT INTO local_device_role_v19 SELECT * FROM local_device_role;
DROP TABLE local_device_role;
ALTER TABLE local_device_role_v19 RENAME TO local_device_role;

CREATE TEMP TABLE sync_pending_v18 AS SELECT * FROM sync_pending;
DELETE FROM sync_pending;
CREATE TABLE sync_exports_v19 (
    export_id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    -- NULL: yangi qurilmani ulash fayli (qabul qiluvchi hali noma'lum).
    peer_device_id TEXT,
    mode TEXT NOT NULL CHECK (mode IN ('FULL', 'INCREMENTAL', 'PAIRING')),
    row_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    role TEXT CHECK (role IS NULL OR role IN ('SELLER', 'ACCOUNTANT', 'HOME')),
    role_space_id TEXT
);
INSERT INTO sync_exports_v19 (export_id, household_id, peer_device_id, mode, row_count, created_at, role, role_space_id)
    SELECT export_id, household_id, peer_device_id, mode, row_count, created_at, role, role_space_id FROM sync_exports;
DROP TABLE sync_exports;
ALTER TABLE sync_exports_v19 RENAME TO sync_exports;
INSERT INTO sync_pending SELECT * FROM temp.sync_pending_v18;
DROP TABLE temp.sync_pending_v18;

-- «Ikki qirg'oq» shartlari (musofirning shaxsiy yozuvi): standart maqsad ulushlari (JSON:
-- [{"purpose": "HOUSEHOLD", "bp": 5000}, …]), kim qabul qiladi, Uy makonidagi oilaviy kelishuv.
CREATE TABLE mf_remittance_terms (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL UNIQUE REFERENCES spaces(id),
    shares_json TEXT NOT NULL,
    receiver_member_id TEXT REFERENCES members(id),
    agreement_id TEXT REFERENCES agreements(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

-- Yuborishning maqsadlarga bo'linishi (o'zgarmas): ulushlar yig'indisi 100 % (ilova tekshiradi).
CREATE TABLE mf_remittance_parts (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    move_id TEXT NOT NULL REFERENCES mf_moves(id),
    purpose TEXT NOT NULL CHECK (purpose IN ('HOUSEHOLD', 'DEBT', 'BUILD', 'EDUCATION', 'CEREMONY', 'SAVINGS', 'OTHER')),
    share_bp INTEGER NOT NULL CHECK (share_bp BETWEEN 1 AND 10000),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (move_id, purpose)
);

-- Uyda qabul (o'zgarmas): haqiqatda olingan summa uy valyutasida; Uy makonidagi daromad bilan bog'liq.
CREATE TABLE mf_receipts (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    move_id TEXT NOT NULL UNIQUE REFERENCES mf_moves(id),
    income_id TEXT NOT NULL UNIQUE REFERENCES incomes(id),
    member_id TEXT REFERENCES members(id),
    received_minor INTEGER NOT NULL CHECK (received_minor > 0),
    currency TEXT NOT NULL,
    received_on TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

-- Uy makonidagi xarajatning maqsadi (o'zgarmas).
CREATE TABLE mf_spends (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    expense_id TEXT NOT NULL UNIQUE REFERENCES expenses(id),
    purpose TEXT NOT NULL CHECK (purpose IN ('HOUSEHOLD', 'DEBT', 'BUILD', 'EDUCATION', 'CEREMONY', 'SAVINGS', 'OTHER')),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

CREATE TRIGGER mf_remittance_parts_no_update BEFORE UPDATE ON mf_remittance_parts
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
CREATE TRIGGER mf_remittance_parts_no_delete BEFORE DELETE ON mf_remittance_parts
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
CREATE TRIGGER mf_receipts_no_update BEFORE UPDATE ON mf_receipts
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
CREATE TRIGGER mf_receipts_no_delete BEFORE DELETE ON mf_receipts
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
CREATE TRIGGER mf_spends_no_update BEFORE UPDATE ON mf_spends
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
CREATE TRIGGER mf_spends_no_delete BEFORE DELETE ON mf_spends
BEGIN
    SELECT RAISE(ABORT, 'MF_REMITTANCE_IMMUTABLE');
END;
