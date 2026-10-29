-- Kliring va hisob-kitob (ADR-0025). Bir kun — bitta paket. Paket yozuvlari acquirer jurnalidan
-- nusxalanadi (jurnal 3 kun saqlanadi, kliring yozuvlari — doimiy). PAN yo'q, faqat maskalangan DPAN.
CREATE TABLE clearing_batches (
    batch_id         TEXT    PRIMARY KEY,
    business_date    TEXT    NOT NULL UNIQUE,
    state            TEXT    NOT NULL CHECK (state IN ('BUILT', 'ACKED', 'SETTLED')),
    period_from      INTEGER NOT NULL,
    period_to        INTEGER NOT NULL,
    records          INTEGER NOT NULL,
    file             TEXT    NOT NULL,
    file_sha256      TEXT    NOT NULL,
    ack              TEXT,
    accepted         INTEGER,
    rejected         INTEGER,
    merchant_fee_bps INTEGER,
    interchange_bps  INTEGER,
    created_at       INTEGER NOT NULL,
    updated_at       INTEGER NOT NULL
);

CREATE TABLE clearing_items (
    batch_id     TEXT    NOT NULL,
    seq          INTEGER NOT NULL,
    terminal_ref TEXT    NOT NULL,
    merchant_id  TEXT    NOT NULL,
    stan         INTEGER NOT NULL,
    rrn          TEXT    NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency     INTEGER NOT NULL,
    txn_at       INTEGER NOT NULL,
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
    currency    INTEGER NOT NULL,
    count       INTEGER NOT NULL,
    gross_minor INTEGER NOT NULL,
    fee_minor   INTEGER NOT NULL,
    net_minor   INTEGER NOT NULL,
    PRIMARY KEY (batch_id, party, party_id, currency)
);
