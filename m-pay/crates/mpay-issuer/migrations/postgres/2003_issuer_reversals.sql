-- PostgreSQL varianti: INTEGER → BIGINT (Rust i64).
-- Reversal (0400/0401, ADR-0024): asl avtorizatsiya qaytarilgan vaqti va har reversal xabarining
-- qaydnomasi. Yechilgan hisob avtorizatsiya qatorida (`account_id`) — qaytarish shu hisobga.
ALTER TABLE issuer_authorizations ADD COLUMN reversed_at BIGINT;
CREATE INDEX issuer_auth_rrn ON issuer_authorizations(rrn);
CREATE INDEX issuer_auth_ts ON issuer_authorizations(ts);

CREATE TABLE issuer_reversals (
    reversal_id    TEXT PRIMARY KEY,
    ts             BIGINT NOT NULL,
    mti            TEXT    NOT NULL,
    auth_id        TEXT,
    stan           TEXT    NOT NULL,
    rrn            TEXT    NOT NULL,
    terminal_id    TEXT    NOT NULL,
    merchant_id    TEXT    NOT NULL,
    amount_minor   BIGINT NOT NULL,
    currency       BIGINT NOT NULL,
    response_code  TEXT    NOT NULL,
    reason         TEXT    NOT NULL
);
CREATE INDEX issuer_reversals_auth ON issuer_reversals(auth_id);
