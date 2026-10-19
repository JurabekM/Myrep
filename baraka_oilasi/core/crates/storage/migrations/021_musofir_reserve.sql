-- Sxema v21 (M4): qorovul pul, ish boshlash summasi va qaror natijasi (docs/musofir/SPEC.md 6.4, 6.6).

-- Musofirning shaxsiy sozlamalari (oilaga yuborilmaydi, ADR-0004): qorovul pul maqsadi necha oylik
-- xarajat (1–3, bo'sh — 1); ish boshlash summasi — uy valyutasida, «Hunardan ishga» g'oyasiga bog'lanishi mumkin.
ALTER TABLE mf_settings ADD COLUMN reserve_months INTEGER CHECK (reserve_months IS NULL OR reserve_months BETWEEN 1 AND 3);
ALTER TABLE mf_settings ADD COLUMN startup_minor INTEGER CHECK (startup_minor IS NULL OR startup_minor > 0);
ALTER TABLE mf_settings ADD COLUMN startup_currency TEXT;
ALTER TABLE mf_settings ADD COLUMN startup_idea_id TEXT REFERENCES venture_ideas(id);

-- Qorovul pul harakatlari (ish valyutasida): RESERVE_IN — qorovul pulga, RESERVE_OUT — undan (sabab majburiy),
-- RESERVE_OPENING — boshlang'ich qoldiq.
CREATE TABLE mf_reserve_moves (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    kind TEXT NOT NULL CHECK (kind IN ('RESERVE_IN', 'RESERVE_OUT', 'RESERVE_OPENING')),
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL,
    occurred_on TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (kind <> 'RESERVE_OUT' OR length(trim(coalesce(note, ''))) > 0)
);
CREATE INDEX mf_reserve_moves_space_date ON mf_reserve_moves(space_id, occurred_on);

-- Qaror natijasi (bir marta, o'zgarmas; shaxsiy): DONE — qildim, DROPPED — qilmadim.
CREATE TABLE mf_decision_outcomes (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    decision_id TEXT NOT NULL UNIQUE REFERENCES mf_decisions(id),
    outcome TEXT NOT NULL CHECK (outcome IN ('DONE', 'DROPPED')),
    outcome_on TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

CREATE TRIGGER mf_decision_outcomes_no_update BEFORE UPDATE ON mf_decision_outcomes
BEGIN
    SELECT RAISE(ABORT, 'MF_DECISION_IMMUTABLE');
END;
CREATE TRIGGER mf_decision_outcomes_no_delete BEFORE DELETE ON mf_decision_outcomes
BEGIN
    SELECT RAISE(ABORT, 'MF_DECISION_IMMUTABLE');
END;
