-- Sxema v8 (U14): `.baraka` sinxronlash holati (8.4). Har bir juft qurilma uchun oxirgi
-- kelishilgan holat (`sync_base`) — yozuv xeshi bo'yicha; soat ishlatilmaydi.
-- Eksportda yuborilgan yozuvlar `sync_pending` da turadi va qabul qiluvchining keyingi
-- faylidagi `ackExportId` bilan `sync_base` ga o'tadi.

ALTER TABLE sync_peers ADD COLUMN peer_name TEXT;
-- Shu qurilmadan oxirgi qabul qilingan eksport: unga keyingi eksportimizda «qabul qildim» deymiz.
ALTER TABLE sync_peers ADD COLUMN last_ack_export_id TEXT;

CREATE TABLE sync_exports (
    export_id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    -- NULL: yangi qurilmani ulash fayli (qabul qiluvchi hali noma'lum).
    peer_device_id TEXT,
    mode TEXT NOT NULL CHECK (mode IN ('FULL', 'INCREMENTAL', 'PAIRING')),
    row_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE sync_pending (
    export_id TEXT NOT NULL REFERENCES sync_exports(export_id),
    tbl TEXT NOT NULL,
    row_id TEXT NOT NULL,
    hash TEXT NOT NULL,
    PRIMARY KEY (export_id, tbl, row_id)
);

CREATE TABLE sync_base (
    peer_device_id TEXT NOT NULL,
    tbl TEXT NOT NULL,
    row_id TEXT NOT NULL,
    hash TEXT NOT NULL,
    PRIMARY KEY (peer_device_id, tbl, row_id)
);

-- Import tarixi (bir fayl ikki marta import qilinsa ham zarar yo'q — natija bir xil).
CREATE TABLE sync_imports (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    export_id TEXT NOT NULL,
    peer_device_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    imported_at TEXT NOT NULL
);

CREATE INDEX sync_imports_peer ON sync_imports (peer_device_id, imported_at);
