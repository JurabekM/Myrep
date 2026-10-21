-- Sxema v22 (M5): olib kelingan summa chet el valyutasida — kurs bilan (docs/musofir/SPEC.md 6.8).
-- 1 `brought_home_currency` = brought_rate_num / brought_rate_den uy valyutasi; uy valyutasida bo'lsa — bo'sh.
ALTER TABLE mf_settings ADD COLUMN brought_rate_num INTEGER CHECK (brought_rate_num IS NULL OR brought_rate_num > 0);
ALTER TABLE mf_settings ADD COLUMN brought_rate_den INTEGER CHECK (brought_rate_den IS NULL OR brought_rate_den > 0);
