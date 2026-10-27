-- Sxema v23 (U16): 8-tamoyil «O'zingizga sarmoya qiling» (docs/uy/SPEC.md 2G) — soat qiymati, bilim
-- rejalari, o'qish vaqti, «Ilm zakoti» va xarajatdagi «O'zimga sarmoya» belgisi. Uy makoni, oilaga umumiy.

-- «Bir soatim qancha?» hisoblari (o'zgarmas tarix, 2G.1): daromad manbasi AUTO — oxirgi to'liq oylar
-- o'rtachasi, MANUAL — qo'lda kiritilgan; ish vaqti daqiqalarda; 1 soat qiymati tiyinda.
CREATE TABLE learning_hour_values (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    income_minor INTEGER NOT NULL CHECK (income_minor > 0),
    currency TEXT NOT NULL,
    income_source TEXT NOT NULL CHECK (income_source IN ('AUTO', 'MANUAL')),
    minutes_per_day INTEGER NOT NULL CHECK (minutes_per_day BETWEEN 1 AND 1440),
    days INTEGER NOT NULL CHECK (days BETWEEN 1 AND 31),
    hour_value_minor INTEGER NOT NULL CHECK (hour_value_minor >= 0),
    computed_on TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin_device_id TEXT NOT NULL
);
CREATE INDEX learning_hour_values_member ON learning_hour_values(space_id, member_id, created_at);

CREATE TRIGGER learning_hour_values_no_update BEFORE UPDATE ON learning_hour_values
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_IMMUTABLE');
END;
CREATE TRIGGER learning_hour_values_no_delete BEFORE DELETE ON learning_hour_values
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_IMMUTABLE');
END;

-- Bilim rejasi (2G.2): yo'llar — tartiblangan kodlar vergul bilan (`BOOK,COURSE`); byudjet ixtiyoriy;
-- boshlang'ich va natija soat qiymati — `learning_hour_values` dagi hisoblar (2G.5).
CREATE TABLE learning_plans (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    skill TEXT NOT NULL CHECK (length(trim(skill)) > 0),
    purpose TEXT,
    paths TEXT NOT NULL CHECK (length(paths) > 0),
    budget_minor INTEGER CHECK (budget_minor IS NULL OR budget_minor >= 0),
    currency TEXT NOT NULL,
    weekly_minutes INTEGER NOT NULL CHECK (weekly_minutes BETWEEN 1 AND 10080),
    start_on TEXT NOT NULL,
    review_on TEXT NOT NULL CHECK (review_on > start_on),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'PAUSED', 'DONE', 'DROPPED')),
    baseline_hour_value_id TEXT REFERENCES learning_hour_values(id),
    result_hour_value_id TEXT REFERENCES learning_hour_values(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX learning_plans_member ON learning_plans(space_id, member_id, status);

-- O'qish vaqti yozuvi (juma ritmi: «Bu hafta necha soat o'qidingiz?»), daqiqada.
CREATE TABLE learning_study_logs (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    plan_id TEXT NOT NULL REFERENCES learning_plans(id),
    occurred_on TEXT NOT NULL,
    minutes INTEGER NOT NULL CHECK (minutes > 0),
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX learning_study_logs_plan ON learning_study_logs(plan_id, occurred_on);

-- «Ilm zakoti» — o'rgatish yozuvi (2G.6): kimga (ixtiyoriy), nimani, qancha vaqt (ixtiyoriy). Pul hisobi yo'q.
CREATE TABLE teaching_logs (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    member_id TEXT NOT NULL REFERENCES members(id),
    occurred_on TEXT NOT NULL,
    learner TEXT,
    topic TEXT NOT NULL CHECK (length(trim(topic)) > 0),
    minutes INTEGER CHECK (minutes IS NULL OR minutes > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX teaching_logs_space_date ON teaching_logs(space_id, occurred_on);

-- «O'zimga sarmoya» belgisi (2G.3): xarajat toifasi o'zgarmaydi, belgili xarajat havas chegarasiga kirmaydi;
-- bilim rejasiga havola faqat belgili xarajatda.
ALTER TABLE expenses ADD COLUMN self_investment INTEGER NOT NULL DEFAULT 0 CHECK (self_investment IN (0, 1));
ALTER TABLE expenses ADD COLUMN learning_plan_id TEXT REFERENCES learning_plans(id)
    CHECK (learning_plan_id IS NULL OR self_investment = 1);
