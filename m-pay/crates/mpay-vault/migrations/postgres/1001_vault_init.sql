-- PostgreSQL varianti (2-faza P2.3): INTEGER → BIGINT (Rust i64), BLOB → BYTEA.
-- M-Pay Vault sxemasi (v1). PAN va DPAN faqat AES-256-GCM shifrmatni sifatida saqlanadi;
-- qidiruv HMAC-SHA256 barmoq izi (pan_fp / dpan_fp) bo'yicha. Vaqtlar — unix sekund.

CREATE TABLE vault_deks (
    dek_id      TEXT PRIMARY KEY,
    kek_label   TEXT    NOT NULL,
    nonce       BYTEA    NOT NULL,
    wrapped     BYTEA    NOT NULL,
    created_at  BIGINT NOT NULL,
    active      BIGINT NOT NULL DEFAULT 1
);

CREATE TABLE vault_cards (
    card_id     TEXT PRIMARY KEY,
    pan_fp      BYTEA    NOT NULL UNIQUE,
    pan_dek     TEXT    NOT NULL REFERENCES vault_deks(dek_id),
    pan_nonce   BYTEA    NOT NULL,
    pan_ct      BYTEA    NOT NULL,
    pan_masked  TEXT    NOT NULL,
    expiry      TEXT    NOT NULL,
    created_at  BIGINT NOT NULL
);

CREATE TABLE vault_tokens (
    token_id      TEXT PRIMARY KEY,
    card_id       TEXT    NOT NULL REFERENCES vault_cards(card_id),
    device_id     TEXT    NOT NULL,
    dpan_fp       BYTEA    NOT NULL UNIQUE,
    dpan_dek      TEXT    NOT NULL REFERENCES vault_deks(dek_id),
    dpan_nonce    BYTEA    NOT NULL,
    dpan_ct       BYTEA    NOT NULL,
    dpan_masked   TEXT    NOT NULL,
    dpan_expiry   TEXT    NOT NULL,
    psn           BIGINT NOT NULL,
    state         TEXT    NOT NULL CHECK (state IN ('PENDING_IDV', 'ACTIVE', 'SUSPENDED', 'DELETED')),
    idv_decision  TEXT    NOT NULL,
    idv_score     BIGINT NOT NULL,
    last_atc      BIGINT,
    next_luk_seq  BIGINT NOT NULL DEFAULT 1,
    created_at    BIGINT NOT NULL,
    updated_at    BIGINT NOT NULL
);
CREATE INDEX vault_tokens_card ON vault_tokens(card_id);
CREATE INDEX vault_tokens_device ON vault_tokens(device_id);

-- LUK'larning o'zi saqlanmaydi (IMK'dan qayta hosil qilinadi) — faqat metama'lumot.
CREATE TABLE vault_luks (
    token_id    TEXT    NOT NULL REFERENCES vault_tokens(token_id),
    seq         BIGINT NOT NULL,
    issued_at   BIGINT NOT NULL,
    expires_at  BIGINT NOT NULL,
    max_uses    BIGINT NOT NULL,
    used        BIGINT NOT NULL DEFAULT 0,
    revoked     BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (token_id, seq)
);

-- OTP qiymati saqlanmaydi: HMAC(PAN-IDX, challenge) dan deterministik hosil qilinadi.
CREATE TABLE vault_idv_challenges (
    challenge_id  TEXT PRIMARY KEY,
    token_id      TEXT    NOT NULL REFERENCES vault_tokens(token_id),
    expires_at    BIGINT NOT NULL,
    attempts      BIGINT NOT NULL DEFAULT 0,
    consumed      BIGINT NOT NULL DEFAULT 0
);

-- Append-only, xesh-zanjirli audit log.
CREATE TABLE vault_audit (
    seq        BIGINT PRIMARY KEY,
    ts         BIGINT NOT NULL,
    actor      TEXT    NOT NULL,
    action     TEXT    NOT NULL,
    token_id   TEXT,
    details    TEXT    NOT NULL,
    prev_hash  BYTEA    NOT NULL,
    hash       BYTEA    NOT NULL
);

CREATE FUNCTION vault_audit_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'vault_audit append-only';
END;
$$;

CREATE TRIGGER vault_audit_no_update BEFORE UPDATE ON vault_audit
    FOR EACH ROW EXECUTE FUNCTION vault_audit_append_only();

CREATE TRIGGER vault_audit_no_delete BEFORE DELETE ON vault_audit
    FOR EACH ROW EXECUTE FUNCTION vault_audit_append_only();
