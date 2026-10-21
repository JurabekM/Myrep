-- Sxema v7 (U13): 6-qonun ijrosi — vazifa hodisalari, ochiq hisob ko'rigi va bayonnomalar,
-- «katta foyda»da shartnomani qayta o'qish, nizo va hakam qarori, oilaviy kelishuvlar tasdig'i.
-- Barchasi dalil: o'zgartirish va o'chirish DB darajasida taqiqlangan (holat yangi yozuv bilan
-- o'zgaradi: hodisa yechimi, hakam qarori).

CREATE TABLE duty_incidents (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    partnership_id TEXT NOT NULL REFERENCES partnerships(id),
    duty_id TEXT NOT NULL,
    party_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    occurred_on TEXT NOT NULL,
    proposed_solution TEXT,
    journal_entry_id TEXT NOT NULL UNIQUE REFERENCES journal_entries(id),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

CREATE TABLE incident_resolutions (
    incident_id TEXT PRIMARY KEY REFERENCES duty_incidents(id),
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    resolved_on TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

-- Bayonnoma: shu paytdagi zanjir boshi (`chain_seq`, `chain_head`) va yakun (`summary_json`).
CREATE TABLE account_reviews (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    partnership_id TEXT NOT NULL REFERENCES partnerships(id),
    review_no INTEGER NOT NULL CHECK (review_no >= 1),
    from_on TEXT NOT NULL,
    to_on TEXT NOT NULL CHECK (to_on >= from_on),
    reason TEXT NOT NULL CHECK (reason IN ('SCHEDULED', 'PROFIT_SPIKE', 'EXTRA')),
    chain_seq INTEGER NOT NULL CHECK (chain_seq >= 0),
    chain_head TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    held_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (partnership_id, review_no)
);

CREATE TABLE review_acks (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    review_id TEXT NOT NULL REFERENCES account_reviews(id),
    party_id TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('AGREE', 'OBJECT')),
    note TEXT,
    journal_entry_id TEXT NOT NULL UNIQUE REFERENCES journal_entries(id),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (review_id, party_id),
    CHECK (verdict = 'AGREE' OR note IS NOT NULL)
);

-- «Katta foyda»: taqsimotdan oldin 4–5-bandlarni qayta o'qiganlik (davr raqami bo'yicha).
CREATE TABLE spike_rereads (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    partnership_id TEXT NOT NULL REFERENCES partnerships(id),
    period_no INTEGER NOT NULL CHECK (period_no >= 1),
    party_id TEXT NOT NULL,
    acked_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (partnership_id, period_no, party_id)
);

CREATE TABLE disputes (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    partnership_id TEXT NOT NULL REFERENCES partnerships(id),
    opened_on TEXT NOT NULL,
    opened_by_party TEXT NOT NULL,
    subject TEXT NOT NULL,
    -- Tegishli bandlar (1..9), JSON massiv.
    clauses_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

CREATE TABLE dispute_claims (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    dispute_id TEXT NOT NULL REFERENCES disputes(id),
    party_id TEXT NOT NULL,
    claim TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (dispute_id, party_id)
);

CREATE TABLE arbiter_decisions (
    dispute_id TEXT PRIMARY KEY REFERENCES disputes(id),
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    decided_on TEXT NOT NULL,
    arbiter_name TEXT NOT NULL,
    decision TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('RESUME', 'AMEND')),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

-- Oilaviy kelishuv: kattalar tasdig'i matn xeshiga bog'liq (matn o'zgarsa — qayta tasdiqlanadi).
CREATE TABLE family_signoffs (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    agreement_id TEXT NOT NULL REFERENCES agreements(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    payload_hash TEXT NOT NULL,
    agreed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (agreement_id, member_id, payload_hash)
);

CREATE TRIGGER duty_incidents_no_update BEFORE UPDATE ON duty_incidents
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER duty_incidents_no_delete BEFORE DELETE ON duty_incidents
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER incident_resolutions_no_update BEFORE UPDATE ON incident_resolutions
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER incident_resolutions_no_delete BEFORE DELETE ON incident_resolutions
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER account_reviews_no_update BEFORE UPDATE ON account_reviews
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER account_reviews_no_delete BEFORE DELETE ON account_reviews
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER review_acks_no_update BEFORE UPDATE ON review_acks
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER review_acks_no_delete BEFORE DELETE ON review_acks
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER spike_rereads_no_update BEFORE UPDATE ON spike_rereads
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER spike_rereads_no_delete BEFORE DELETE ON spike_rereads
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER disputes_no_update BEFORE UPDATE ON disputes
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER disputes_no_delete BEFORE DELETE ON disputes
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER dispute_claims_no_update BEFORE UPDATE ON dispute_claims
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER dispute_claims_no_delete BEFORE DELETE ON dispute_claims
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER arbiter_decisions_no_update BEFORE UPDATE ON arbiter_decisions
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER arbiter_decisions_no_delete BEFORE DELETE ON arbiter_decisions
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER family_signoffs_no_update BEFORE UPDATE ON family_signoffs
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE TRIGGER family_signoffs_no_delete BEFORE DELETE ON family_signoffs
BEGIN
    SELECT RAISE(ABORT, 'GOVERNANCE_IMMUTABLE');
END;

CREATE INDEX idx_duty_incidents ON duty_incidents(partnership_id, occurred_on);
CREATE INDEX idx_account_reviews ON account_reviews(partnership_id, review_no);
CREATE INDEX idx_review_acks ON review_acks(review_id);
CREATE INDEX idx_disputes ON disputes(partnership_id);
CREATE INDEX idx_dispute_claims ON dispute_claims(dispute_id);
CREATE INDEX idx_family_signoffs ON family_signoffs(agreement_id);
