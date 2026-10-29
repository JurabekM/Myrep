-- PostgreSQL varianti (2-faza P2.3): INTEGER → BIGINT (Rust i64), BLOB → BYTEA.
-- Emitent emulyatori sxemasi (v1). PAN saqlanmaydi — hisob karta barmoq izi (HMAC) bo'yicha topiladi.
-- Summalar minor birlikda (tiyin), valyuta ISO 4217 raqamli (860 = UZS).

CREATE TABLE issuer_accounts (
    account_id     TEXT PRIMARY KEY,
    pan_fp         BYTEA    NOT NULL UNIQUE,
    pan_masked     TEXT    NOT NULL,
    label          TEXT    NOT NULL,
    currency       BIGINT NOT NULL,
    balance_minor  BIGINT NOT NULL CHECK (balance_minor >= 0),
    created_at     BIGINT NOT NULL,
    updated_at     BIGINT NOT NULL
);

CREATE TABLE issuer_authorizations (
    auth_id        TEXT PRIMARY KEY,
    ts             BIGINT NOT NULL,
    stan           TEXT    NOT NULL,
    rrn            TEXT    NOT NULL,
    token_id       TEXT,
    account_id     TEXT,
    dpan_masked    TEXT,
    amount_minor   BIGINT NOT NULL,
    currency       BIGINT NOT NULL,
    terminal_id    TEXT    NOT NULL,
    merchant_id    TEXT    NOT NULL,
    atc            BIGINT,
    luk_seq        BIGINT,
    response_code  TEXT    NOT NULL,
    reason         TEXT    NOT NULL,
    risk_score     BIGINT,
    risk_decision  TEXT
);
CREATE INDEX issuer_auth_token ON issuer_authorizations(token_id);
