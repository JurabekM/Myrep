-- Sxema v11 (K2): Kasb-kor — haqiqiy foyda (docs/kasbkor/SPEC.md 3).
-- O'z mehnati bahosi, uskunalar (eskirish) va oilaviy mehnat. Hisob — `domain-kasbkor`.

-- Egasi o'z ishini yollanma odamga topshirsa, oyiga qancha to'lardi (0 — kiritilmagan; OQ-K5).
ALTER TABLE kk_settings ADD COLUMN owner_labor_minor INTEGER NOT NULL DEFAULT 0 CHECK (owner_labor_minor >= 0);

-- Uskuna (SPEC 3.3). `assets.type` ro'yxatida EQUIPMENT yo'q — alohida jadval.
-- `wallet` — qaysi hamyondan to'langan; NULL — ilovagacha bor edi (pul harakati yo'q).
-- Chiqib ketish (sotildi yoki yaroqsiz): `disposed_on` + `disposal_proceeds_minor` (0 — yaroqsiz).
CREATE TABLE kk_equipment (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
    cost_minor INTEGER NOT NULL CHECK (cost_minor > 0),
    salvage_minor INTEGER NOT NULL DEFAULT 0 CHECK (salvage_minor >= 0 AND salvage_minor <= cost_minor),
    useful_months INTEGER NOT NULL CHECK (useful_months BETWEEN 1 AND 600),
    currency TEXT NOT NULL,
    acquired_on TEXT NOT NULL,
    wallet TEXT CHECK (wallet IS NULL OR wallet IN ('CASH', 'CARD')),
    disposed_on TEXT,
    disposal_proceeds_minor INTEGER CHECK (disposal_proceeds_minor IS NULL OR disposal_proceeds_minor >= 0),
    disposal_wallet TEXT CHECK (disposal_wallet IS NULL OR disposal_wallet IN ('CASH', 'CARD')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK ((disposed_on IS NULL) = (disposal_proceeds_minor IS NULL)),
    CHECK (disposal_wallet IS NULL OR disposal_proceeds_minor > 0),
    CHECK (disposed_on IS NULL OR disposed_on >= acquired_on)
);
CREATE INDEX kk_equipment_space ON kk_equipment(space_id, acquired_on);

-- Oilaviy mehnat (SPEC 3.1): pul to'lanmasa ham tannarxga kiradi. `paid = 1` — to'langan, u chiqim
-- sifatida yozilgan, haqiqiy foydada ikki marta hisoblanmaydi. `hours100` — soat × 100.
CREATE TABLE kk_family_labor (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    person TEXT NOT NULL CHECK (length(person) BETWEEN 1 AND 100),
    member_id TEXT REFERENCES members(id),
    worked_on TEXT NOT NULL,
    hours100 INTEGER NOT NULL CHECK (hours100 > 0),
    hourly_rate_minor INTEGER NOT NULL CHECK (hourly_rate_minor >= 0),
    currency TEXT NOT NULL,
    paid INTEGER NOT NULL DEFAULT 0 CHECK (paid IN (0, 1)),
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX kk_family_labor_space_date ON kk_family_labor(space_id, worked_on);
