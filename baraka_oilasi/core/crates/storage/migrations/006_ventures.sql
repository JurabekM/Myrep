-- Sxema v6 (U12): sheriklik kassa daftari (venture ledger), chek va dalil ilovalari, yopilgan
-- davrlar va taqsimot, «Hunardan ishga» (hunarlar va g'oyalar).
-- Har bir daftar yozuvi kelishuv jurnaliga ham yoziladi (xesh-zanjir, 2F.6). Yozuvlar, ilovalar
-- va yopilgan davrlar — dalil: o'zgartirish va o'chirish DB darajasida taqiqlangan; xato faqat
-- yangi tuzatuvchi yozuv bilan to'g'rilanadi.

CREATE TABLE venture_entries (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    partnership_id TEXT NOT NULL REFERENCES partnerships(id),
    journal_entry_id TEXT NOT NULL UNIQUE REFERENCES journal_entries(id),
    kind TEXT NOT NULL CHECK (kind IN ('INCOME', 'EXPENSE', 'FORCE_MAJEURE', 'CORRECTION')),
    category TEXT,
    -- Tuzatishda ishorali (natijaga ta'siri), qolganlarida musbat.
    amount_minor INTEGER NOT NULL CHECK (amount_minor <> 0),
    currency TEXT NOT NULL,
    occurred_on TEXT NOT NULL,
    note TEXT,
    corrects_entry_id TEXT REFERENCES venture_entries(id),
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    CHECK ((kind = 'CORRECTION') = (corrects_entry_id IS NOT NULL)),
    CHECK (kind = 'CORRECTION' OR amount_minor > 0)
);

-- Chek, rasm yoki fors-major dalili. Baza SQLCipher bilan shifrlangan — fayl ham shifrlangan.
CREATE TABLE venture_attachments (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    entry_id TEXT NOT NULL REFERENCES venture_entries(id),
    file_name TEXT NOT NULL,
    mime TEXT NOT NULL CHECK (mime IN ('image/jpeg', 'image/png', 'image/webp', 'application/pdf')),
    size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
    sha256 TEXT NOT NULL,
    bytes BLOB NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);

-- Yopilgan davr: natija va taqsimot (`result_json`), shu paytdagi zanjir boshi.
CREATE TABLE venture_periods (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    partnership_id TEXT NOT NULL REFERENCES partnerships(id),
    period_no INTEGER NOT NULL CHECK (period_no >= 1),
    start_on TEXT NOT NULL,
    end_on TEXT NOT NULL CHECK (end_on >= start_on),
    currency TEXT NOT NULL,
    result_minor INTEGER NOT NULL,
    loss_policy TEXT NOT NULL CHECK (loss_policy IN ('CAPITAL_FIRST', 'PER_PERIOD')),
    signed_version INTEGER NOT NULL CHECK (signed_version >= 1),
    result_json TEXT NOT NULL,
    chain_head TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    UNIQUE (partnership_id, period_no)
);

CREATE TRIGGER venture_entries_no_update BEFORE UPDATE ON venture_entries
BEGIN
    SELECT RAISE(ABORT, 'VENTURE_IMMUTABLE');
END;

CREATE TRIGGER venture_entries_no_delete BEFORE DELETE ON venture_entries
BEGIN
    SELECT RAISE(ABORT, 'VENTURE_IMMUTABLE');
END;

CREATE TRIGGER venture_attachments_no_update BEFORE UPDATE ON venture_attachments
BEGIN
    SELECT RAISE(ABORT, 'VENTURE_IMMUTABLE');
END;

CREATE TRIGGER venture_attachments_no_delete BEFORE DELETE ON venture_attachments
BEGIN
    SELECT RAISE(ABORT, 'VENTURE_IMMUTABLE');
END;

CREATE TRIGGER venture_periods_no_update BEFORE UPDATE ON venture_periods
BEGIN
    SELECT RAISE(ABORT, 'VENTURE_IMMUTABLE');
END;

CREATE TRIGGER venture_periods_no_delete BEFORE DELETE ON venture_periods
BEGIN
    SELECT RAISE(ABORT, 'VENTURE_IMMUTABLE');
END;

-- Yopilgan davr ichidagi sanaga yozuv qo'shib bo'lmaydi (ilova tekshiruvidan tashqari, DB ham).
CREATE TRIGGER venture_entries_closed_period BEFORE INSERT ON venture_entries
WHEN EXISTS (
    SELECT 1 FROM venture_periods p
    WHERE p.partnership_id = NEW.partnership_id AND NEW.occurred_on <= p.end_on
)
BEGIN
    SELECT RAISE(ABORT, 'VENTURE_PERIOD_CLOSED');
END;

-- «Hunardan ishga»: oiladagi bekor yotgan hunarlar va mini biznes-hisoblar.
CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    member_id TEXT REFERENCES members(id),
    title TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE TABLE venture_ideas (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    skill_id TEXT REFERENCES skills(id),
    title TEXT NOT NULL,
    currency TEXT NOT NULL,
    -- [{title, amountMinor}]
    capex_json TEXT NOT NULL,
    -- [{name, incomeMinor, expenseMinor}] — PESSIMISTIC, BASE, OPTIMISTIC
    scenarios_json TEXT NOT NULL,
    worker_share_bp INTEGER CHECK (worker_share_bp BETWEEN 0 AND 10000),
    partnership_id TEXT REFERENCES partnerships(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);

CREATE INDEX idx_venture_entries ON venture_entries(partnership_id, occurred_on);
CREATE INDEX idx_venture_attachments ON venture_attachments(entry_id);
CREATE INDEX idx_venture_periods ON venture_periods(partnership_id, period_no);
CREATE INDEX idx_skills_space ON skills(household_id, space_id, deleted_at);
CREATE INDEX idx_venture_ideas_space ON venture_ideas(household_id, space_id, deleted_at);
