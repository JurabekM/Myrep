-- Kliring (ADR-0025): avtorizatsiya qaysi kliring paketida tasdiqlangani va qabul qilingan paketlar
-- (bir paket ID — bitta natija: qayta yuborilsa saqlangan tasdiq qaytadi).
ALTER TABLE issuer_authorizations ADD COLUMN cleared_batch TEXT;

CREATE TABLE issuer_clearing_batches (
    batch_id      TEXT PRIMARY KEY,
    business_date TEXT    NOT NULL,
    file_sha256   TEXT    NOT NULL,
    received_at   INTEGER NOT NULL,
    records       INTEGER NOT NULL,
    accepted      INTEGER NOT NULL,
    ack           TEXT    NOT NULL
);
