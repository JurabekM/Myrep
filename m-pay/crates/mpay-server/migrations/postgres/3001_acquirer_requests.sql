-- PostgreSQL varianti (2-faza P2.3): INTEGER → BIGINT (Rust i64), BLOB → BYTEA.
-- Acquirer: terminal so'rovlarining takroriy yuborilishini aniqlash (1-faza, P1.2).
-- Kalit: terminal + STAN + sana (UTC, YYYYMMDD). Bir xil mazmun — birinchi javob qaytariladi
-- (idempotent), boshqa mazmun — ISO 94. Javobda faqat maskalangan DPAN bor.
CREATE TABLE acquirer_requests (
    terminal_id  TEXT    NOT NULL,
    stan         BIGINT NOT NULL,
    txn_date     TEXT    NOT NULL,
    request_hash BYTEA    NOT NULL,
    state        TEXT    NOT NULL CHECK (state IN ('PENDING', 'DONE')),
    response     TEXT,
    created_at   BIGINT NOT NULL,
    PRIMARY KEY (terminal_id, stan, txn_date)
);

CREATE INDEX acquirer_requests_created ON acquirer_requests (created_at);
