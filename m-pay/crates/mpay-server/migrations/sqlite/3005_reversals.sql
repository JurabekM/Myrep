-- Reversal va solishtirish (ADR-0024). Takroriy so'rovlar jadvali acquirer jurnali ham bo'ladi:
-- reversal (`0400`) va solishtirish uchun asl xabar maydonlari (PAN yo'q — faqat maskalangan DPAN).
ALTER TABLE acquirer_requests ADD COLUMN terminal_ref TEXT;
ALTER TABLE acquirer_requests ADD COLUMN merchant_id TEXT;
ALTER TABLE acquirer_requests ADD COLUMN rrn TEXT;
ALTER TABLE acquirer_requests ADD COLUMN transmitted TEXT;
ALTER TABLE acquirer_requests ADD COLUMN amount_minor INTEGER;
ALTER TABLE acquirer_requests ADD COLUMN currency INTEGER;
ALTER TABLE acquirer_requests ADD COLUMN dpan_masked TEXT;
ALTER TABLE acquirer_requests ADD COLUMN response_code TEXT;

-- Reversal navbati: natijasi noma'lum (`96`) avtorizatsiyalar. Kalit — takroriy so'rov kaliti
-- (bitta avtorizatsiya — bitta reversal). `PENDING` → `DONE` (emitent `00`/`25`) yoki `FAILED`
-- (boshqa kod — qo'lda ko'rib chiqish).
CREATE TABLE acquirer_reversals (
    terminal_id     TEXT    NOT NULL,
    stan            INTEGER NOT NULL,
    txn_date        TEXT    NOT NULL,
    terminal_ref    TEXT    NOT NULL,
    merchant_id     TEXT    NOT NULL,
    rrn             TEXT    NOT NULL,
    transmitted     TEXT    NOT NULL,
    amount_minor    INTEGER NOT NULL,
    currency        INTEGER NOT NULL,
    dpan_masked     TEXT    NOT NULL,
    cause           TEXT    NOT NULL,
    state           TEXT    NOT NULL CHECK (state IN ('PENDING', 'DONE', 'FAILED')),
    attempts        INTEGER NOT NULL,
    next_attempt_at INTEGER NOT NULL,
    response_code   TEXT,
    result          TEXT,
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER NOT NULL,
    PRIMARY KEY (terminal_id, stan, txn_date)
);

CREATE INDEX acquirer_reversals_due ON acquirer_reversals (state, next_attempt_at);
CREATE INDEX acquirer_reversals_created ON acquirer_reversals (created_at);
