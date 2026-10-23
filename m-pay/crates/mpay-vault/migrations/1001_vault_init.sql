-- M-Pay Vault sxemasi (v1). PAN va DPAN faqat AES-256-GCM shifrmatni sifatida saqlanadi;
-- qidiruv HMAC-SHA256 barmoq izi (pan_fp / dpan_fp) bo'yicha. Vaqtlar — unix sekund.

CREATE TABLE vault_deks (
    dek_id      TEXT PRIMARY KEY,
    kek_label   TEXT    NOT NULL,
    nonce       BLOB    NOT NULL,
    wrapped     BLOB    NOT NULL,
    created_at  INTEGER NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE vault_cards (
    card_id     TEXT PRIMARY KEY,
    pan_fp      BLOB    NOT NULL UNIQUE,
    pan_dek     TEXT    NOT NULL REFERENCES vault_deks(dek_id),
    pan_nonce   BLOB    NOT NULL,
    pan_ct      BLOB    NOT NULL,
    pan_masked  TEXT    NOT NULL,
    expiry      TEXT    NOT NULL,
    created_at  INTEGER NOT NULL
);

CREATE TABLE vault_tokens (
    token_id      TEXT PRIMARY KEY,
    card_id       TEXT    NOT NULL REFERENCES vault_cards(card_id),
    device_id     TEXT    NOT NULL,
    dpan_fp       BLOB    NOT NULL UNIQUE,
    dpan_dek      TEXT    NOT NULL REFERENCES vault_deks(dek_id),
    dpan_nonce    BLOB    NOT NULL,
    dpan_ct       BLOB    NOT NULL,
    dpan_masked   TEXT    NOT NULL,
    dpan_expiry   TEXT    NOT NULL,
    psn           INTEGER NOT NULL,
    state         TEXT    NOT NULL CHECK (state IN ('PENDING_IDV', 'ACTIVE', 'SUSPENDED', 'DELETED')),
    idv_decision  TEXT    NOT NULL,
    idv_score     INTEGER NOT NULL,
    last_atc      INTEGER,
    next_luk_seq  INTEGER NOT NULL DEFAULT 1,
    created_at    INTEGER NOT NULL,
    updated_at    INTEGER NOT NULL
);
CREATE INDEX vault_tokens_card ON vault_tokens(card_id);
CREATE INDEX vault_tokens_device ON vault_tokens(device_id);

-- LUK'larning o'zi saqlanmaydi (IMK'dan qayta hosil qilinadi) — faqat metama'lumot.
CREATE TABLE vault_luks (
    token_id    TEXT    NOT NULL REFERENCES vault_tokens(token_id),
    seq         INTEGER NOT NULL,
    issued_at   INTEGER NOT NULL,
    expires_at  INTEGER NOT NULL,
    max_uses    INTEGER NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0,
    revoked     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (token_id, seq)
);

-- OTP qiymati saqlanmaydi: HMAC(PAN-IDX, challenge) dan deterministik hosil qilinadi.
CREATE TABLE vault_idv_challenges (
    challenge_id  TEXT PRIMARY KEY,
    token_id      TEXT    NOT NULL REFERENCES vault_tokens(token_id),
    expires_at    INTEGER NOT NULL,
    attempts      INTEGER NOT NULL DEFAULT 0,
    consumed      INTEGER NOT NULL DEFAULT 0
);

-- Append-only, xesh-zanjirli audit log.
CREATE TABLE vault_audit (
    seq        INTEGER PRIMARY KEY,
    ts         INTEGER NOT NULL,
    actor      TEXT    NOT NULL,
    action     TEXT    NOT NULL,
    token_id   TEXT,
    details    TEXT    NOT NULL,
    prev_hash  BLOB    NOT NULL,
    hash       BLOB    NOT NULL
);

CREATE TRIGGER vault_audit_no_update BEFORE UPDATE ON vault_audit
BEGIN
    SELECT RAISE(ABORT, 'vault_audit append-only');
END;

CREATE TRIGGER vault_audit_no_delete BEFORE DELETE ON vault_audit
BEGIN
    SELECT RAISE(ABORT, 'vault_audit append-only');
END;
