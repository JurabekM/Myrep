-- Sxema v24 (K9): Kasb-kor makonida 8-tamoyil «O'zingizga sarmoya qiling» (docs/kasbkor/SPEC.md 8A) —
-- egasining soat qiymati, «O'zim qilaymi yoki o'rgatib topshiraymi?» qarorlari va xodimga o'rgatish
-- («Ilm zakoti»). Uy jadvallari (023) a'zoga bog'langan; Kasb-kor makonida egasi — a'zo emas (makonning
-- o'zi), o'rganuvchi esa xodim kartochkasi (kk_agreements), shuning uchun alohida jadvallar.
-- Xarajatdagi «Sarmoya (o'qish)» belgisi — mavjud expenses.self_investment ustuni (023).

-- Egasining soat qiymati hisoblari (o'zgarmas tarix, 8A.1): AUTO — oxirgi yopilgan oylar («Hisob kuni»)
-- topgani o'rtachasi (months — nechta oy), MANUAL — egasi kiritgan (months = 0).
CREATE TABLE kk_owner_hours (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    income_minor INTEGER NOT NULL CHECK (income_minor > 0),
    currency TEXT NOT NULL,
    income_source TEXT NOT NULL CHECK (income_source IN ('AUTO', 'MANUAL')),
    months INTEGER NOT NULL CHECK (months BETWEEN 0 AND 3),
    minutes_per_day INTEGER NOT NULL CHECK (minutes_per_day BETWEEN 1 AND 1440),
    days INTEGER NOT NULL CHECK (days BETWEEN 1 AND 31),
    hour_value_minor INTEGER NOT NULL CHECK (hour_value_minor >= 0),
    computed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL,
    CHECK ((income_source = 'AUTO') = (months > 0))
);
CREATE INDEX kk_owner_hours_space ON kk_owner_hours(space_id, created_at);

CREATE TRIGGER kk_owner_hours_no_update BEFORE UPDATE ON kk_owner_hours
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_IMMUTABLE');
END;
CREATE TRIGGER kk_owner_hours_no_delete BEFORE DELETE ON kk_owner_hours
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_IMMUTABLE');
END;

-- «O'zim qilaymi yoki o'rgatib topshiraymi?» (8A.2): saqlangan kiritmalar (natija — yadroda qayta
-- hisoblanadi, vektor kk_delegate). Egasining soat qiymati — qaror paytidagi qiymat. Xodim kartochkasiga
-- bog'lanishi mumkin (faqat EMPLOYMENT).
CREATE TABLE kk_delegations (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    task TEXT NOT NULL CHECK (length(trim(task)) BETWEEN 1 AND 120),
    agreement_id TEXT REFERENCES kk_agreements(id),
    currency TEXT NOT NULL,
    owner_hour_value_minor INTEGER NOT NULL CHECK (owner_hour_value_minor > 0),
    task_minutes INTEGER NOT NULL CHECK (task_minutes BETWEEN 1 AND 44640),
    helper_hour_cost_minor INTEGER NOT NULL CHECK (helper_hour_cost_minor >= 0),
    training_money_minor INTEGER NOT NULL CHECK (training_money_minor >= 0),
    training_minutes INTEGER NOT NULL CHECK (training_minutes BETWEEN 0 AND 44640),
    decided_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX kk_delegations_space ON kk_delegations(space_id, decided_on);

-- «Ilm zakoti» — xodimga (yoki boshqa kishiga) o'rgatish yozuvi (8A.3, Uy 2G.6 bilan bir xil): kimga —
-- xodim kartochkasi yoki ixtiyoriy ism (ikkalasi birga emas), nimani, qancha vaqt. Pul hisobi yo'q.
CREATE TABLE kk_teaching_logs (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    occurred_on TEXT NOT NULL,
    agreement_id TEXT REFERENCES kk_agreements(id),
    learner TEXT,
    topic TEXT NOT NULL CHECK (length(trim(topic)) > 0),
    minutes INTEGER CHECK (minutes IS NULL OR minutes > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL,
    CHECK (agreement_id IS NULL OR learner IS NULL)
);
CREATE INDEX kk_teaching_logs_space_date ON kk_teaching_logs(space_id, occurred_on);
