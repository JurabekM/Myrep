-- Sxema v12 (K3): Kasb-kor «Hisob kuni» (docs/kasbkor/SPEC.md 4.5).
-- Soliq zaxirasi va taqsimot qoidasi — `kk_settings` da; yopilgan oy bayonnomasi o'zgarmas.

-- Soliq zaxirasi qoidasi (OQ-K3): NONE, REVENUE yoki PROFIT (foiz, bp), FIXED (qat'iy summa).
ALTER TABLE kk_settings ADD COLUMN tax_base TEXT NOT NULL DEFAULT 'NONE' CHECK (tax_base IN ('NONE', 'REVENUE', 'PROFIT', 'FIXED'));
ALTER TABLE kk_settings ADD COLUMN tax_bp INTEGER NOT NULL DEFAULT 0 CHECK (tax_bp BETWEEN 0 AND 10000);
ALTER TABLE kk_settings ADD COLUMN tax_fixed_minor INTEGER NOT NULL DEFAULT 0 CHECK (tax_fixed_minor >= 0);
-- Qolgan pul taqsimoti (bp, jami 10 000 — ilovada tekshiriladi): zaxira, aylanma, kengayish, sadaqa.
ALTER TABLE kk_settings ADD COLUMN reserve_bp INTEGER NOT NULL DEFAULT 3000 CHECK (reserve_bp BETWEEN 0 AND 10000);
ALTER TABLE kk_settings ADD COLUMN working_bp INTEGER NOT NULL DEFAULT 5000 CHECK (working_bp BETWEEN 0 AND 10000);
ALTER TABLE kk_settings ADD COLUMN expansion_bp INTEGER NOT NULL DEFAULT 2000 CHECK (expansion_bp BETWEEN 0 AND 10000);
ALTER TABLE kk_settings ADD COLUMN sadaqa_bp INTEGER NOT NULL DEFAULT 0 CHECK (sadaqa_bp BETWEEN 0 AND 10000);

-- «Hisob kuni» bayonnomasi. `result_json` — barcha raqamlar (minor) va qoida; `content_hash` =
-- sha256(oldingi bayonnoma xeshi + "\n" + result_json) — yopilgan oylar zanjiri.
CREATE TABLE kk_month_closes (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL CHECK (period_end >= period_start),
    currency TEXT NOT NULL,
    remaining_minor INTEGER NOT NULL,
    -- Keyingi oy maoshidan ushlanadigan summa (maoshdan ortiq olingan).
    carry_minor INTEGER NOT NULL DEFAULT 0 CHECK (carry_minor >= 0),
    reserve_minor INTEGER NOT NULL DEFAULT 0 CHECK (reserve_minor >= 0),
    explanation TEXT,
    result_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (space_id, period_start),
    CHECK (remaining_minor >= 0 OR explanation IS NOT NULL)
);

CREATE TRIGGER kk_month_closes_no_update BEFORE UPDATE ON kk_month_closes
BEGIN
    SELECT RAISE(ABORT, 'KK_CLOSE_IMMUTABLE');
END;

CREATE TRIGGER kk_month_closes_no_delete BEFORE DELETE ON kk_month_closes
BEGIN
    SELECT RAISE(ABORT, 'KK_CLOSE_IMMUTABLE');
END;
