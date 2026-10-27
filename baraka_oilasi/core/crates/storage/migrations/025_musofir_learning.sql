-- Sxema v25 (M6): Musofir makonida 8-tamoyil «O'zingizga sarmoya qiling» (docs/musofir/SPEC.md 6A) —
-- soat qiymati ish valyutasida, ikki maqsadli bilim rejasi va «Ilm zakoti» (hamyurtlarga yordam).
-- Uy jadvallari (023) a'zoga bog'langan (member_id NOT NULL); Musofir makonida musofirning o'zi — makon
-- (daromad yozuvlarida a'zo yo'q), shuning uchun Kasb-kor (024) kabi alohida jadvallar. Hammasi
-- space_id = Musofir makoni — uydagi oila qurilmasiga (HOME roli, ADR-0004) umuman yuborilmaydi.
-- Xarajatdagi «Sarmoya» belgisi — mavjud expenses.self_investment ustuni (023); Musofir xarajati Uy
-- bilim rejasiga bog'lanmaydi (learning_plan_id bo'sh).

-- Soat qiymati hisoblari (o'zgarmas tarix): AUTO — oxirgi to'liq oylar (daromad yozuvi borlari)
-- maosh + boshqa daromad o'rtachasi (months — nechta oy), MANUAL — musofir kiritgan (months = 0).
-- Summalar ish valyutasida; uy valyutasidagi ko'rinish saqlanmaydi — har safar amaldagi kurs bilan.
CREATE TABLE mf_hour_values (
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
CREATE INDEX mf_hour_values_space ON mf_hour_values(space_id, created_at);

CREATE TRIGGER mf_hour_values_no_update BEFORE UPDATE ON mf_hour_values
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_IMMUTABLE');
END;
CREATE TRIGGER mf_hour_values_no_delete BEFORE DELETE ON mf_hour_values
BEGIN
    SELECT RAISE(ABORT, 'LEARNING_IMMUTABLE');
END;

-- Bilim rejasi (Uy 2G.2 bilan bir xil maydonlar) + maqsad: ABROAD — chet eldagi soatni qimmatlashtirish
-- (til, malaka toifasi, guvohnoma), HOME — qaytgandan keyin uyda daromad beradigan hunar; HOME reja Uy
-- makonidagi «Hunardan ishga» g'oyasiga (U12) bog'lanishi mumkin. Byudjet — ish valyutasida.
CREATE TABLE mf_learning_plans (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    goal TEXT NOT NULL CHECK (goal IN ('ABROAD', 'HOME')),
    skill TEXT NOT NULL CHECK (length(trim(skill)) > 0),
    purpose TEXT,
    paths TEXT NOT NULL CHECK (length(paths) > 0),
    budget_minor INTEGER CHECK (budget_minor IS NULL OR budget_minor >= 0),
    currency TEXT NOT NULL,
    weekly_minutes INTEGER NOT NULL CHECK (weekly_minutes BETWEEN 1 AND 10080),
    start_on TEXT NOT NULL,
    review_on TEXT NOT NULL CHECK (review_on > start_on),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'PAUSED', 'DONE', 'DROPPED')),
    baseline_hour_value_id TEXT REFERENCES mf_hour_values(id),
    result_hour_value_id TEXT REFERENCES mf_hour_values(id),
    venture_idea_id TEXT REFERENCES venture_ideas(id) CHECK (venture_idea_id IS NULL OR goal = 'HOME'),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    origin_device_id TEXT NOT NULL,
    updated_by_device_id TEXT NOT NULL
);
CREATE INDEX mf_learning_plans_space ON mf_learning_plans(space_id, status);

-- «Ilm zakoti» (Uy 2G.6): yangi kelgan hamyurtlarga ish, til yoki hujjat bo'yicha yordam ham o'rgatish.
-- Kimga (ixtiyoriy), qaysi soha, nimani, qancha vaqt (ixtiyoriy). Pul hisobi yo'q.
CREATE TABLE mf_teaching_logs (
    id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL REFERENCES households(id),
    space_id TEXT NOT NULL REFERENCES spaces(id),
    occurred_on TEXT NOT NULL,
    area TEXT NOT NULL CHECK (area IN ('WORK', 'LANGUAGE', 'DOCUMENTS', 'OTHER')),
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
CREATE INDEX mf_teaching_logs_space_date ON mf_teaching_logs(space_id, occurred_on);
