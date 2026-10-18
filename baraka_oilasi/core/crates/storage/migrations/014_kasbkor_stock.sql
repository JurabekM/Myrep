-- Sxema v14 (K5): Kasb-kor — tovar qoldig'i, tannarx, qayta tiklash narxi (docs/kasbkor/SPEC.md 4.1–4.4).
-- Miqdorlar butun sonda, asosiy birlikda (G — gramm, ML, PCS — dona, MM). Narxlar «ko'rsatish
-- birligi»ga: kg, l, m (1000 asosiy birlik) yoki dona.

CREATE TABLE kk_items (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    unit TEXT NOT NULL CHECK (unit IN ('G', 'ML', 'PCS', 'MM')),
    -- Tannarx usuli (OQ-K1): standart — o'rtacha tortilgan; FIFO — tovar bo'yicha.
    method TEXT NOT NULL DEFAULT 'AVERAGE' CHECK (method IN ('AVERAGE', 'FIFO')),
    currency TEXT NOT NULL,
    sale_price_minor INTEGER CHECK (sale_price_minor IS NULL OR sale_price_minor > 0),
    -- Qo'lda kiritilgan joriy xarid narxi; bo'lmasa — oxirgi xarid narxi.
    replacement_price_minor INTEGER CHECK (replacement_price_minor IS NULL OR replacement_price_minor > 0),
    min_qty INTEGER CHECK (min_qty IS NULL OR min_qty >= 0),
    -- «Muzlagan tovar» chegarasi (OQ-K4), kun.
    frozen_days INTEGER NOT NULL DEFAULT 90 CHECK (frozen_days BETWEEN 1 AND 3650),
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

-- Tovar harakatlari (o'zgarmas): xarid (+), sotuv (−, Kasb-kor tushumi bilan), hisobdan chiqarish (−, sabab
-- majburiy), inventarizatsiya tuzatishi (±, sabab majburiy; ortiqchada `amount_minor` — topilgan tovar qiymati).
CREATE TABLE kk_stock_moves (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    item_id TEXT NOT NULL REFERENCES kk_items(id),
    kind TEXT NOT NULL CHECK (kind IN ('PURCHASE', 'SALE', 'WRITE_OFF', 'ADJUST')),
    occurred_on TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty <> 0),
    amount_minor INTEGER CHECK (amount_minor IS NULL OR amount_minor >= 0),
    -- Xaridda: qaysi hamyondan (NULL — ilovagacha bor edi); sotuvda: qaysi hamyonga.
    wallet TEXT CHECK (wallet IS NULL OR wallet IN ('CASH', 'CARD')),
    income_id TEXT REFERENCES incomes(id),
    reason TEXT,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    CHECK (kind = 'ADJUST' OR qty > 0),
    CHECK (kind <> 'PURCHASE' OR coalesce(amount_minor, 0) > 0),
    CHECK ((kind = 'SALE') = (income_id IS NOT NULL)),
    CHECK (kind <> 'SALE' OR wallet IS NOT NULL),
    CHECK (kind NOT IN ('WRITE_OFF', 'ADJUST') OR reason IS NOT NULL),
    CHECK (kind <> 'ADJUST' OR qty < 0 OR amount_minor IS NOT NULL)
);
CREATE INDEX kk_stock_moves_item ON kk_stock_moves(item_id, occurred_on);

CREATE TRIGGER kk_stock_moves_no_update BEFORE UPDATE ON kk_stock_moves
BEGIN
    SELECT RAISE(ABORT, 'KK_STOCK_MOVE_IMMUTABLE');
END;

CREATE TRIGGER kk_stock_moves_no_delete BEFORE DELETE ON kk_stock_moves
BEGIN
    SELECT RAISE(ABORT, 'KK_STOCK_MOVE_IMMUTABLE');
END;
