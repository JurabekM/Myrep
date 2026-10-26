-- Emitent emulyatori sxemasi (v1). PAN saqlanmaydi — hisob karta barmoq izi (HMAC) bo'yicha topiladi.
-- Summalar minor birlikda (tiyin), valyuta ISO 4217 raqamli (860 = UZS).

CREATE TABLE issuer_accounts (
    account_id     TEXT PRIMARY KEY,
    pan_fp         BLOB    NOT NULL UNIQUE,
    pan_masked     TEXT    NOT NULL,
    label          TEXT    NOT NULL,
    currency       INTEGER NOT NULL,
    balance_minor  INTEGER NOT NULL CHECK (balance_minor >= 0),
    created_at     INTEGER NOT NULL,
    updated_at     INTEGER NOT NULL
);

CREATE TABLE issuer_authorizations (
    auth_id        TEXT PRIMARY KEY,
    ts             INTEGER NOT NULL,
    stan           TEXT    NOT NULL,
    rrn            TEXT    NOT NULL,
    token_id       TEXT,
    account_id     TEXT,
    dpan_masked    TEXT,
    amount_minor   INTEGER NOT NULL,
    currency       INTEGER NOT NULL,
    terminal_id    TEXT    NOT NULL,
    merchant_id    TEXT    NOT NULL,
    atc            INTEGER,
    luk_seq        INTEGER,
    response_code  TEXT    NOT NULL,
    reason         TEXT    NOT NULL,
    risk_score     INTEGER,
    risk_decision  TEXT
);
CREATE INDEX issuer_auth_token ON issuer_authorizations(token_id);
