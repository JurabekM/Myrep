-- Sxema v9 (U15): onboarding javoblari va qurilmaning o'z sozlamalari.

-- Daromad ritmi bosh sahifa eslatmalarini moslaydi: kunlik naqd, buyurtma bo'yicha, oylik maosh.
ALTER TABLE households ADD COLUMN income_rhythm TEXT
    CHECK (income_rhythm IS NULL OR income_rhythm IN ('DAILY', 'ORDERS', 'MONTHLY'));
-- Onboarding'da «qarzim bor» deyilgan: qarzlar inventarga kiritilguncha taklif ko'rsatiladi.
ALTER TABLE households ADD COLUMN debts_declared INTEGER NOT NULL DEFAULT 0
    CHECK (debts_declared IN (0, 1));

-- Faqat shu qurilmaga tegishli sozlamalar (sinxronlanmaydi): masalan, buvining telefonida
-- kirill, desktopda rus tili. `locale` bo'lmasa — xonadonniki.
CREATE TABLE device_settings (
    device_id TEXT PRIMARY KEY,
    locale TEXT CHECK (locale IS NULL OR locale IN ('uz', 'uz-Cyrl', 'ru')),
    updated_at TEXT NOT NULL
);
