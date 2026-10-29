-- PostgreSQL varianti: INTEGER → BIGINT (Rust i64).
-- Kliring va hisob-kitob (ADR-0025). Bir kun — bitta paket. Paket yozuvlari acquirer jurnalidan
-- nusxalanadi (jurnal 3 kun saqlanadi, kliring yozuvlari — doimiy). PAN yo'q, faqat maskalangan DPAN.
CREATE TABLE clearing_batches (
    batch_id         TEXT    PRIMARY KEY,
    business_date    TEXT    NOT NULL UNIQUE,
    state            TEXT    NOT NULL CHECK (state IN ('BUILT', 'ACKED', 'SETTLED')),
    period_from      BIGINT NOT NULL,
    period_to        BIGINT NOT NULL,
    records          BIGINT NOT NULL,
    file             TEXT    NOT NULL,
    file_sha256      TEXT    NOT NULL,
    ack              TEXT,
    accepted         BIGINT,
    rejected         BIGINT,
    merchant_fee_bps BIGINT,
    interchange_bps  BIGINT,
    created_at       BIGINT NOT NULL,
    updated_at       BIGINT NOT NULL
);

CREATE TABLE clearing_items (
    batch_id     TEXT    NOT NULL,
    seq          BIGINT NOT NULL,
    terminal_ref TEXT    NOT NULL,
    merchant_id  TEXT    NOT NULL,
    stan         BIGINT NOT NULL,
    rrn          TEXT    NOT NULL,
    amount_minor BIGINT NOT NULL,
    currency     BIGINT NOT NULL,
    txn_at       BIGINT NOT NULL,
    dpan_masked  TEXT    NOT NULL,
    status       TEXT    NOT NULL CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED')),
    code         TEXT,
    reason       TEXT,
    PRIMARY KEY (batch_id, seq)
);
CREATE INDEX clearing_items_key ON clearing_items (terminal_ref, stan, rrn);
CREATE INDEX clearing_items_txn ON clearing_items (txn_at);

-- Hisob-kitob pozitsiyalari: ISSUER (emitent acquirer'ga to'laydi), MERCHANT (acquirer savdo
-- nuqtasiga to'laydi), ACQUIRER (M-Pay daromadi). Ishora acquirer nuqtai nazaridan.
CREATE TABLE settlement_positions (
    batch_id    TEXT    NOT NULL,
    party       TEXT    NOT NULL CHECK (party IN ('ISSUER', 'MERCHANT', 'ACQUIRER')),
    party_id    TEXT    NOT NULL,
    currency    BIGINT NOT NULL,
    count       BIGINT NOT NULL,
    gross_minor BIGINT NOT NULL,
    fee_minor   BIGINT NOT NULL,
    net_minor   BIGINT NOT NULL,
    PRIMARY KEY (batch_id, party, party_id, currency)
);
