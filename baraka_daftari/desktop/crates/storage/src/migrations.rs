use rusqlite_migration::{Migrations, M};

/// Joriy sxema versiyasi (`PRAGMA user_version`).
pub const SCHEMA_VERSION: usize = 13;

/// Har bir jadvalda: UUIDv7 `id`, `household_id`, UTC vaqtlar, soft delete, `version`, `origin_device_id`.
/// Keyingi vazifalar maydonlari (`necessity`, `envelope_id`, ...) hozirdan nullable.
const V1: &str = "
CREATE TABLE households (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1), origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, base_currency TEXT NOT NULL
);
CREATE TABLE members (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  display_name TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('ADULT','CHILD','VIEWER'))
);
CREATE TABLE categories (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, necessity TEXT CHECK (necessity IN ('ZARUR','KERAK','HAVAS'))
);
CREATE TABLE incomes (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  member_id TEXT NOT NULL REFERENCES members(id), source TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('CASH','CARD')),
  amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, received_on TEXT NOT NULL
);
CREATE INDEX idx_incomes_household_date ON incomes (household_id, received_on);
CREATE TABLE expenses (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  member_id TEXT NOT NULL REFERENCES members(id), category_id TEXT NOT NULL REFERENCES categories(id),
  amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, spent_on TEXT NOT NULL,
  payment_channel TEXT NOT NULL CHECK (payment_channel IN ('CASH','CARD')),
  necessity TEXT CHECK (necessity IN ('ZARUR','KERAK','HAVAS')),
  envelope_id TEXT, is_gift INTEGER, is_ostentation INTEGER, funded_by_debt INTEGER
);
CREATE INDEX idx_expenses_household_date ON expenses (household_id, spent_on);
CREATE TABLE assets (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  asset_type TEXT NOT NULL CHECK (asset_type IN ('CASH','BANK_CARD','VAULT','GOLD','SILVER',
    'FOREIGN_CURRENCY','RECEIVABLE','TRADE_GOODS','BUSINESS_SHARE')),
  name TEXT NOT NULL, quantity INTEGER NOT NULL, unit TEXT NOT NULL, currency TEXT,
  acquired_at TEXT NOT NULL
);
CREATE TABLE asset_snapshots (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  asset_id TEXT NOT NULL REFERENCES assets(id), quantity INTEGER NOT NULL, taken_at TEXT NOT NULL
);
CREATE INDEX idx_asset_snapshots_asset ON asset_snapshots (asset_id, taken_at);
CREATE TABLE vault_transactions (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  asset_id TEXT NOT NULL REFERENCES assets(id), kind TEXT NOT NULL CHECK (kind IN ('DEPOSIT','WITHDRAW')),
  amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, occurred_at TEXT NOT NULL, note TEXT
);
CREATE TABLE allocation_rules (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('PERCENT','FIXED_AMOUNT')), value INTEGER NOT NULL, currency TEXT
);
CREATE TABLE obligations (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, amount_minor INTEGER NOT NULL, currency TEXT NOT NULL,
  due_day INTEGER NOT NULL CHECK (due_day BETWEEN 1 AND 31)
);
CREATE TABLE fx_rates (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  from_currency TEXT NOT NULL, to_currency TEXT NOT NULL,
  rate_num INTEGER NOT NULL CHECK (rate_num > 0), rate_den INTEGER NOT NULL CHECK (rate_den > 0),
  date TEXT NOT NULL, source TEXT NOT NULL
);
";

/// D4: Kelajagim manbasi va daromadga bog'lanish, majburiyat turlari/egalari, nasiya, audit,
/// pul olish so'rovlari. Faqat `ADD COLUMN` va yangi jadvallar: v1 ma'lumotlari saqlanadi.
const V2: &str = "
ALTER TABLE vault_transactions ADD COLUMN source TEXT CHECK (source IN ('ALLOCATION','OPENING','MANUAL'));
ALTER TABLE vault_transactions ADD COLUMN income_id TEXT REFERENCES incomes(id);
CREATE INDEX idx_vault_tx_asset_time ON vault_transactions (asset_id, occurred_at);
ALTER TABLE obligations ADD COLUMN kind TEXT NOT NULL DEFAULT 'RECURRING' CHECK (kind IN ('RECURRING','NASIYA'));
ALTER TABLE obligations ADD COLUMN owner TEXT NOT NULL DEFAULT 'OTHER'
  CHECK (owner IN ('LANDLORD','BANK','SHOP','STATE','FUEL','OTHER'));
ALTER TABLE obligations ADD COLUMN creditor TEXT;
ALTER TABLE obligations ADD COLUMN remaining_minor INTEGER;
ALTER TABLE categories ADD COLUMN owner TEXT CHECK (owner IN ('LANDLORD','BANK','SHOP','STATE','FUEL','OTHER'));
ALTER TABLE expenses ADD COLUMN audit_month TEXT;
CREATE INDEX idx_expenses_audit ON expenses (household_id, audit_month);
CREATE TABLE withdrawal_requests (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  asset_id TEXT NOT NULL REFERENCES assets(id), amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
  currency TEXT NOT NULL, reason TEXT NOT NULL, available_at TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PENDING','CONFIRMED','CANCELLED'))
);
";

/// D5: kontent jarayoni. Partial UNIQUE indekslar faqat faol (o'chirilmagan) yozuvlarni cheklaydi,
/// shuning uchun tombstone'lar (kelajakdagi sinxronlash) to'qnashmaydi.
const V3: &str = "
CREATE TABLE task_completions (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL, task_id TEXT NOT NULL, week_start TEXT NOT NULL, completed_at TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_task_completion ON task_completions (household_id, task_id, week_start)
  WHERE deleted_at IS NULL;
CREATE TABLE chapter_progress (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL, opened_on TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_chapter_progress ON chapter_progress (household_id, chapter_id) WHERE deleted_at IS NULL;
CREATE TABLE daftar_pages (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  chapter_id TEXT NOT NULL, body TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_daftar_page ON daftar_pages (household_id, chapter_id) WHERE deleted_at IS NULL;
CREATE TABLE settings (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  key TEXT NOT NULL, value TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_setting ON settings (household_id, key) WHERE deleted_at IS NULL;
";

/// D6: toifalar tarixi, havas chegarasi va rozilik, shaxsiy PIN, «Juma shirinligi», sadaqa/odat belgilari.
const V4: &str = "
ALTER TABLE categories ADD COLUMN is_charity INTEGER NOT NULL DEFAULT 0 CHECK (is_charity IN (0,1));
ALTER TABLE categories ADD COLUMN is_habit INTEGER NOT NULL DEFAULT 0 CHECK (is_habit IN (0,1));
ALTER TABLE expenses ADD COLUMN note TEXT;
CREATE TABLE member_credentials (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  member_id TEXT NOT NULL REFERENCES members(id), pin_hash TEXT NOT NULL,
  failures INTEGER NOT NULL DEFAULT 0, locked_until INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX uq_member_credential ON member_credentials (member_id) WHERE deleted_at IS NULL;
CREATE TABLE necessity_changes (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  category_id TEXT NOT NULL REFERENCES categories(id),
  from_necessity TEXT CHECK (from_necessity IN ('ZARUR','KERAK','HAVAS')),
  to_necessity TEXT NOT NULL CHECK (to_necessity IN ('ZARUR','KERAK','HAVAS')),
  changed_by TEXT NOT NULL REFERENCES members(id)
);
CREATE INDEX idx_necessity_changes_cat ON necessity_changes (category_id, created_at);
CREATE TABLE havas_limits (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL,
  proposed_by TEXT NOT NULL REFERENCES members(id)
);
CREATE TABLE limit_consents (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  limit_id TEXT NOT NULL REFERENCES havas_limits(id), member_id TEXT NOT NULL REFERENCES members(id),
  consented_at TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_limit_consent ON limit_consents (limit_id, member_id) WHERE deleted_at IS NULL;
CREATE TABLE scheduled_treats (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL,
  weekday INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 7), active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);
";

/// D13 (5-qonun): venture ledger (davrlar, yozuvlar, dalillar, taqsimot) va «Hunardan ishga».
/// **Yopilgan davr o'zgarmasligi bazada triggerlar bilan ham ta'minlanadi.**
const V11: &str = "
CREATE TABLE venture_periods (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  partnership_id TEXT NOT NULL REFERENCES partnerships(id), period_no INTEGER NOT NULL CHECK (period_no >= 1),
  start_date TEXT NOT NULL, end_date TEXT, status TEXT NOT NULL CHECK (status IN ('OPEN','CLOSED')),
  net_minor INTEGER, currency TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_venture_period_no ON venture_periods (partnership_id, period_no) WHERE deleted_at IS NULL;
CREATE TABLE venture_entries (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  partnership_id TEXT NOT NULL REFERENCES partnerships(id), period_id TEXT NOT NULL REFERENCES venture_periods(id),
  kind TEXT NOT NULL CHECK (kind IN ('INCOME','EXPENSE')), description TEXT NOT NULL,
  amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL, occurred_on TEXT NOT NULL,
  note TEXT, force_majeure INTEGER NOT NULL DEFAULT 0 CHECK (force_majeure IN (0,1))
);
CREATE INDEX idx_venture_entries_period ON venture_entries (period_id);
CREATE TABLE venture_attachments (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  entry_id TEXT NOT NULL REFERENCES venture_entries(id), filename TEXT NOT NULL, mime TEXT NOT NULL, data BLOB NOT NULL
);
CREATE TABLE venture_distributions (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  period_id TEXT NOT NULL REFERENCES venture_periods(id), party_id TEXT NOT NULL REFERENCES partnership_parties(id),
  amount_minor INTEGER NOT NULL, buyout_minor INTEGER NOT NULL, currency TEXT NOT NULL
);
CREATE TABLE craft_ideas (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, note TEXT, currency TEXT NOT NULL,
  income_pess INTEGER NOT NULL, income_avg INTEGER NOT NULL, income_opt INTEGER NOT NULL,
  expense_pess INTEGER NOT NULL, expense_avg INTEGER NOT NULL, expense_opt INTEGER NOT NULL,
  share_bp INTEGER CHECK (share_bp BETWEEN 0 AND 10000)
);
CREATE TABLE craft_capex (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  idea_id TEXT NOT NULL REFERENCES craft_ideas(id), item TEXT NOT NULL,
  price_minor INTEGER NOT NULL CHECK (price_minor >= 0), currency TEXT NOT NULL
);
CREATE TRIGGER trg_entries_closed_ins BEFORE INSERT ON venture_entries
WHEN (SELECT status FROM venture_periods WHERE id = NEW.period_id) = 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_entries_closed_upd BEFORE UPDATE ON venture_entries
WHEN (SELECT status FROM venture_periods WHERE id = OLD.period_id) = 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_entries_closed_del BEFORE DELETE ON venture_entries
WHEN (SELECT status FROM venture_periods WHERE id = OLD.period_id) = 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_attach_closed_ins BEFORE INSERT ON venture_attachments
WHEN (SELECT p.status FROM venture_entries e JOIN venture_periods p ON p.id = e.period_id WHERE e.id = NEW.entry_id) = 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_attach_closed_upd BEFORE UPDATE ON venture_attachments
WHEN (SELECT p.status FROM venture_entries e JOIN venture_periods p ON p.id = e.period_id WHERE e.id = OLD.entry_id) = 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_period_closed_upd BEFORE UPDATE ON venture_periods
WHEN OLD.status = 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_period_closed_del BEFORE DELETE ON venture_periods
WHEN OLD.status = 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_dist_upd BEFORE UPDATE ON venture_distributions
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
CREATE TRIGGER trg_dist_del BEFORE DELETE ON venture_distributions
BEGIN SELECT RAISE(ABORT, 'closed_period'); END;
";

/// D12 (5-qonun): sheriklik shartnomasi, tomonlar, kapital, tasdiqlar, versiyalar va buyout.
const V10: &str = "
CREATE TABLE partnerships (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('MUDARABA','MUSHARAKA')),
  term_months INTEGER NOT NULL CHECK (term_months BETWEEN 1 AND 120),
  report_period TEXT NOT NULL CHECK (report_period IN ('MONTHLY','QUARTERLY','YEARLY')),
  end_clause TEXT NOT NULL, dispute_clause TEXT NOT NULL, witnesses TEXT NOT NULL DEFAULT '',
  contract_version INTEGER NOT NULL CHECK (contract_version >= 1),
  status TEXT NOT NULL CHECK (status IN ('DRAFT','ACTIVE','ENDED'))
);
CREATE TABLE partnership_parties (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  partnership_id TEXT NOT NULL REFERENCES partnerships(id), name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('CAPITAL_PROVIDER','WORKER','PARTNER')),
  share_bp INTEGER NOT NULL CHECK (share_bp BETWEEN 0 AND 10000),
  member_id TEXT REFERENCES members(id)
);
CREATE TABLE partnership_capital (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  partnership_id TEXT NOT NULL REFERENCES partnerships(id), party_id TEXT NOT NULL REFERENCES partnership_parties(id),
  description TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('CASH','EQUIPMENT')),
  value_minor INTEGER NOT NULL CHECK (value_minor >= 0), currency TEXT NOT NULL
);
CREATE TABLE partnership_signatures (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  partnership_id TEXT NOT NULL REFERENCES partnerships(id), contract_version INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('PARTY','WITNESS','FAMILY_CONSENT')),
  signer TEXT NOT NULL, signer_name TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_partnership_signature ON partnership_signatures (partnership_id, contract_version, kind, signer)
  WHERE deleted_at IS NULL;
CREATE TABLE partnership_versions (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  partnership_id TEXT NOT NULL REFERENCES partnerships(id), contract_version INTEGER NOT NULL, snapshot TEXT NOT NULL
);
CREATE TABLE buyout_plans (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  partnership_id TEXT NOT NULL REFERENCES partnerships(id), provider_party_id TEXT NOT NULL REFERENCES partnership_parties(id),
  periods INTEGER NOT NULL CHECK (periods BETWEEN 1 AND 240), start_date TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_buyout_partnership ON buyout_plans (partnership_id) WHERE deleted_at IS NULL;
CREATE TABLE buyout_payments (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  plan_id TEXT NOT NULL REFERENCES buyout_plans(id), paid_on TEXT NOT NULL,
  amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL
);
";

/// D11 (4-qonun): marosim rejalari va byudjet qatorlari.
const V9: &str = "
CREATE TABLE ceremony_plans (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('WEDDING','BESHIK','SUNNAT','MARAKA','OTHER')),
  ceremony_date TEXT, status TEXT NOT NULL CHECK (status IN ('DRAFT','CONFIRMED')),
  discussed INTEGER NOT NULL DEFAULT 0 CHECK (discussed IN (0,1)), discussion_note TEXT
);
CREATE TABLE ceremony_lines (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  plan_id TEXT NOT NULL REFERENCES ceremony_plans(id), name TEXT NOT NULL,
  qty INTEGER NOT NULL CHECK (qty >= 1), unit_price_minor INTEGER NOT NULL CHECK (unit_price_minor >= 0),
  currency TEXT NOT NULL,
  funding TEXT NOT NULL CHECK (funding IN ('SAVINGS','FAMILY','EXPECTED_GIFTS','DEBT'))
);
CREATE INDEX idx_ceremony_lines_plan ON ceremony_lines (plan_id);
";

/// D10 (4-qonun): qarz bo'yicha qo'shimcha to'lovchilar va sotiladigan buyumlar.
const V8: &str = "
CREATE TABLE debt_contributors (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  debt_id TEXT NOT NULL REFERENCES debts(id), member_id TEXT NOT NULL REFERENCES members(id),
  monthly_share_minor INTEGER NOT NULL CHECK (monthly_share_minor >= 0), currency TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_debt_contributor ON debt_contributors (debt_id, member_id) WHERE deleted_at IS NULL;
CREATE TABLE sellable_items (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, price_minor INTEGER NOT NULL CHECK (price_minor > 0), currency TEXT NOT NULL,
  unused_since TEXT, status TEXT NOT NULL CHECK (status IN ('LISTED','SOLD')),
  sold_minor INTEGER, sold_on TEXT, debt_id TEXT REFERENCES debts(id)
);
";

/// D9 (4-qonun): qarz inventari, to'lov jadvali, to'lovlar, berilgan qarzlar (foizsiz), maqsadlar, tilxat.
const V7: &str = "
CREATE TABLE debts (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  creditor TEXT NOT NULL,
  creditor_type TEXT NOT NULL CHECK (creditor_type IN ('BANK','SHOP','RELATIVE','FRIEND','OTHER')),
  reason TEXT, principal_minor INTEGER NOT NULL CHECK (principal_minor > 0), currency TEXT NOT NULL,
  schedule_kind TEXT NOT NULL CHECK (schedule_kind IN ('ANNUITY','DIFFERENTIATED','FIXED_MARKUP','MANUAL')),
  monthly_minor INTEGER NOT NULL CHECK (monthly_minor > 0), due_date TEXT NOT NULL, borrowed_on TEXT NOT NULL,
  early_terms TEXT, priority INTEGER, closed_on TEXT,
  check_need TEXT CHECK (check_need IN ('NEED','LUXURY')),
  check_alternative TEXT CHECK (check_alternative IN ('NONE','GUARD','RELATIVE','SELL_ITEM')),
  check_burden_bp INTEGER
);
CREATE TABLE debt_instalments (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  debt_id TEXT NOT NULL REFERENCES debts(id), due_on TEXT NOT NULL,
  amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL
);
CREATE INDEX idx_instalments_debt ON debt_instalments (debt_id, due_on);
CREATE TABLE debt_payments (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  debt_id TEXT NOT NULL REFERENCES debts(id), member_id TEXT NOT NULL REFERENCES members(id),
  paid_on TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL,
  expense_id TEXT REFERENCES expenses(id)
);
CREATE INDEX idx_debt_payments_debt ON debt_payments (debt_id, paid_on);
CREATE TABLE receivables (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  debtor TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL,
  given_on TEXT NOT NULL, due_on TEXT, note TEXT, returned_minor INTEGER NOT NULL DEFAULT 0 CHECK (returned_minor >= 0)
);
CREATE TABLE goals (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, target_minor INTEGER NOT NULL CHECK (target_minor > 0), currency TEXT NOT NULL,
  saved_minor INTEGER NOT NULL DEFAULT 0 CHECK (saved_minor >= 0), due_on TEXT
);
CREATE TABLE loan_receipts (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  ref_kind TEXT NOT NULL CHECK (ref_kind IN ('DEBT','RECEIVABLE')), ref_id TEXT NOT NULL,
  witnesses TEXT NOT NULL DEFAULT '', confirmed INTEGER NOT NULL DEFAULT 0 CHECK (confirmed IN (0,1))
);
CREATE UNIQUE INDEX uq_receipt_ref ON loan_receipts (ref_kind, ref_id) WHERE deleted_at IS NULL;
";

/// D8 (3-qonun): mavjud «Kelajagim» → QOROVUL (balans o'zgarmaydi), daromad manbasi turi,
/// narx daftari, darvozani chetlab o'tish qaydi.
const V6: &str = "
ALTER TABLE assets ADD COLUMN vault_type TEXT CHECK (vault_type IN ('QOROVUL','OSADIGAN'));
UPDATE assets SET vault_type = 'QOROVUL' WHERE asset_type = 'VAULT';
ALTER TABLE incomes ADD COLUMN source_type TEXT CHECK (source_type IN ('TER','MOL','TAVAKKAL','RIBO'));
CREATE TABLE price_items (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, unit TEXT NOT NULL, weight_bp INTEGER NOT NULL CHECK (weight_bp BETWEEN 0 AND 10000),
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);
CREATE UNIQUE INDEX uq_price_item_name ON price_items (household_id, name) WHERE deleted_at IS NULL;
CREATE TABLE price_points (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  item_id TEXT NOT NULL REFERENCES price_items(id), price_minor INTEGER NOT NULL CHECK (price_minor > 0),
  currency TEXT NOT NULL, observed_on TEXT NOT NULL, place TEXT
);
CREATE INDEX idx_price_points_item ON price_points (item_id, observed_on);
CREATE TABLE gate_bypasses (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  guard_months_x100 INTEGER NOT NULL CHECK (guard_months_x100 >= 0)
);
";

/// D7: obunalar, konvertlar (+ yopilgan haftalar), qutqarilgan pul.
const V5: &str = "
CREATE TABLE subscriptions (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0), currency TEXT NOT NULL,
  period TEXT NOT NULL CHECK (period IN ('WEEKLY','MONTHLY','QUARTERLY','YEARLY')),
  started_on TEXT NOT NULL, last_used_on TEXT, cancelled_on TEXT,
  needed INTEGER CHECK (needed IN (0,1))
);
CREATE TABLE envelopes (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  name TEXT NOT NULL, weekly_limit_minor INTEGER NOT NULL CHECK (weekly_limit_minor > 0), currency TEXT NOT NULL,
  category_id TEXT REFERENCES categories(id),
  necessity TEXT CHECK (necessity IN ('ZARUR','KERAK','HAVAS')),
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);
CREATE TABLE envelope_periods (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  envelope_id TEXT NOT NULL REFERENCES envelopes(id), week_start TEXT NOT NULL,
  limit_minor INTEGER NOT NULL, spent_minor INTEGER NOT NULL, leftover_minor INTEGER NOT NULL,
  difference_minor INTEGER NOT NULL, currency TEXT NOT NULL
);
CREATE UNIQUE INDEX uq_envelope_period ON envelope_periods (envelope_id, week_start) WHERE deleted_at IS NULL;
CREATE TABLE savings_rescues (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('HAVAS_DROP','SUBSCRIPTION')),
  amount_minor INTEGER NOT NULL CHECK (amount_minor > 0), currency TEXT NOT NULL,
  week_start TEXT, note TEXT, transferred_at TEXT
);
CREATE UNIQUE INDEX uq_rescue_week ON savings_rescues (household_id, week_start)
  WHERE kind = 'HAVAS_DROP' AND deleted_at IS NULL;
";

/// D8A (6-qonun): kelishuv dvigateli — kelishuvlar, o'zgarmas versiyalar, tasdiqlar va append-only jurnal (SPEC 2F).
/// Jurnal va versiyalar UPDATE/DELETE bilan o'zgartirilmaydi: triggerlar `RAISE(ABORT)` qiladi.
const V12: &str = "
CREATE TABLE agreements (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  agreement_type TEXT NOT NULL CHECK (agreement_type IN ('PARTNERSHIP','LOAN','RENT','SERVICE','FAMILY','OTHER')),
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('DRAFT','SIGNED','ACTIVE','IN_DISPUTE','CLOSED')),
  subject_kind TEXT NOT NULL CHECK (subject_kind IN ('PARTNERSHIP','DEBT','RECEIVABLE','NONE')),
  subject_id TEXT,
  current_version INTEGER NOT NULL CHECK (current_version >= 1),
  effective_from TEXT NOT NULL,
  keeper_device_id TEXT,
  legacy INTEGER NOT NULL DEFAULT 0 CHECK (legacy IN (0,1))
);
CREATE UNIQUE INDEX uq_agreement_subject ON agreements (subject_kind, subject_id)
  WHERE subject_id IS NOT NULL AND deleted_at IS NULL;
CREATE TABLE agreement_versions (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  agreement_id TEXT NOT NULL REFERENCES agreements(id), version_no INTEGER NOT NULL CHECK (version_no >= 1),
  content TEXT NOT NULL, content_hash TEXT NOT NULL CHECK (length(content_hash) = 64), change_note TEXT
);
CREATE UNIQUE INDEX uq_agreement_version ON agreement_versions (agreement_id, version_no);
CREATE TRIGGER trg_agv_upd BEFORE UPDATE ON agreement_versions
BEGIN SELECT RAISE(ABORT, 'agreement_version_immutable'); END;
CREATE TRIGGER trg_agv_del BEFORE DELETE ON agreement_versions
BEGIN SELECT RAISE(ABORT, 'agreement_version_immutable'); END;
CREATE TABLE agreement_signatures (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  agreement_id TEXT NOT NULL REFERENCES agreements(id), version_no INTEGER NOT NULL CHECK (version_no >= 1),
  kind TEXT NOT NULL CHECK (kind IN ('PARTY','WITNESS','ARBITER','FAMILY_CONSENT')),
  signer_key TEXT NOT NULL, signer_name TEXT NOT NULL,
  method TEXT NOT NULL CHECK (method IN ('IN_APP','FAMILY_PIN','PRINTED_SCAN'))
);
CREATE UNIQUE INDEX uq_agreement_signature ON agreement_signatures (agreement_id, version_no, kind, signer_key);
CREATE TRIGGER trg_ags_upd BEFORE UPDATE ON agreement_signatures
BEGIN SELECT RAISE(ABORT, 'agreement_signature_immutable'); END;
CREATE TRIGGER trg_ags_del BEFORE DELETE ON agreement_signatures
BEGIN SELECT RAISE(ABORT, 'agreement_signature_immutable'); END;
CREATE TABLE journal_entries (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  agreement_id TEXT NOT NULL REFERENCES agreements(id), seq INTEGER NOT NULL CHECK (seq >= 1),
  kind TEXT NOT NULL CHECK (kind IN ('OPENING_BALANCE','CONTRIBUTION','VENTURE_INCOME','VENTURE_EXPENSE',
    'PROFIT_DISTRIBUTION','LOSS_SHARE','BUYOUT_PAYMENT','PAYMENT','PERIOD_CLOSED','CORRECTION')),
  party_id TEXT,
  amount_minor INTEGER, amount_currency TEXT CHECK (amount_currency IN ('UZS','USD','EUR','RUB')),
  entry_date TEXT NOT NULL, note TEXT NOT NULL CHECK (length(trim(note)) > 0),
  reference TEXT, corrects TEXT REFERENCES journal_entries(id),
  prev_hash TEXT NOT NULL CHECK (length(prev_hash) = 64), hash TEXT NOT NULL CHECK (length(hash) = 64),
  CHECK ((amount_minor IS NULL) = (amount_currency IS NULL))
);
CREATE UNIQUE INDEX uq_journal_seq ON journal_entries (agreement_id, seq);
CREATE TRIGGER trg_journal_upd BEFORE UPDATE ON journal_entries
BEGIN SELECT RAISE(ABORT, 'journal_append_only'); END;
CREATE TRIGGER trg_journal_del BEFORE DELETE ON journal_entries
BEGIN SELECT RAISE(ABORT, 'journal_append_only'); END;
";

/// v12 → v13: jurnalga yangi voqea turlari (vazifa hodisasi, nizo, katta foyda tasdig'i, ko'rik) (D13A).
/// SQLite'da CHECK o'zgartirilmaydi, shuning uchun jadval qayta yaratiladi: barcha yozuvlar, xeshlar va
/// tuzatish havolalari ko'chiriladi; append-only triggerlar qayta o'rnatiladi. Havolalar tranzaksiya
/// oxirida tekshiriladi (`defer_foreign_keys`).
const V13: &str = "
PRAGMA defer_foreign_keys = ON;
DROP TRIGGER trg_journal_upd;
DROP TRIGGER trg_journal_del;
ALTER TABLE journal_entries RENAME TO journal_entries_v12;
CREATE TABLE journal_entries (
  id TEXT PRIMARY KEY, household_id TEXT NOT NULL REFERENCES households(id), created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, deleted_at TEXT, version INTEGER NOT NULL CHECK (version >= 1),
  origin_device_id TEXT NOT NULL,
  agreement_id TEXT NOT NULL REFERENCES agreements(id), seq INTEGER NOT NULL CHECK (seq >= 1),
  kind TEXT NOT NULL CHECK (kind IN ('OPENING_BALANCE','CONTRIBUTION','VENTURE_INCOME','VENTURE_EXPENSE',
    'PROFIT_DISTRIBUTION','LOSS_SHARE','BUYOUT_PAYMENT','PAYMENT','PERIOD_CLOSED','CORRECTION',
    'DUTY_INCIDENT','DISPUTE_OPENED','DISPUTE_RESOLVED','PROFIT_ALERT_ACK','REVIEW_ACK','REVIEW_CLOSED')),
  party_id TEXT,
  amount_minor INTEGER, amount_currency TEXT CHECK (amount_currency IN ('UZS','USD','EUR','RUB')),
  entry_date TEXT NOT NULL, note TEXT NOT NULL CHECK (length(trim(note)) > 0),
  reference TEXT, corrects TEXT REFERENCES journal_entries(id),
  prev_hash TEXT NOT NULL CHECK (length(prev_hash) = 64), hash TEXT NOT NULL CHECK (length(hash) = 64),
  CHECK ((amount_minor IS NULL) = (amount_currency IS NULL))
);
INSERT INTO journal_entries SELECT * FROM journal_entries_v12;
DROP TABLE journal_entries_v12;
CREATE UNIQUE INDEX uq_journal_seq ON journal_entries (agreement_id, seq);
CREATE TRIGGER trg_journal_upd BEFORE UPDATE ON journal_entries
BEGIN SELECT RAISE(ABORT, 'journal_append_only'); END;
CREATE TRIGGER trg_journal_del BEFORE DELETE ON journal_entries
BEGIN SELECT RAISE(ABORT, 'journal_append_only'); END;
";

/// Migratsiyalar ro'yxati. Har bir yangi versiya oxiriga qo'shiladi; mavjudlari o'zgartirilmaydi.
#[must_use]
pub fn migrations() -> Migrations<'static> {
    Migrations::new(vec![
        M::up(V1),
        M::up(V2),
        M::up(V3),
        M::up(V4),
        M::up(V5),
        M::up(V6),
        M::up(V7),
        M::up(V8),
        M::up(V9),
        M::up(V10),
        M::up(V11),
        M::up(V12),
        M::up(V13),
    ])
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    #[test]
    fn migrations_are_valid() {
        migrations().validate().unwrap();
    }

    #[test]
    fn latest_version_matches_constant() {
        let mut conn = Connection::open_in_memory().unwrap();
        migrations().to_latest(&mut conn).unwrap();
        let v: i64 = conn
            .pragma_query_value(None, "user_version", |r| r.get(0))
            .unwrap();
        assert_eq!(usize::try_from(v).unwrap(), SCHEMA_VERSION);
    }

    #[test]
    fn every_table_has_sync_columns() {
        let mut conn = Connection::open_in_memory().unwrap();
        migrations().to_latest(&mut conn).unwrap();
        let tables: Vec<String> = conn
            .prepare(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            )
            .unwrap()
            .query_map([], |r| r.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        assert_eq!(tables.len(), 55);
        for t in tables {
            let cols: Vec<String> = conn
                .prepare(&format!("PRAGMA table_info({t})"))
                .unwrap()
                .query_map([], |r| r.get(1))
                .unwrap()
                .collect::<Result<_, _>>()
                .unwrap();
            for c in [
                "id",
                "household_id",
                "created_at",
                "updated_at",
                "deleted_at",
                "version",
                "origin_device_id",
            ] {
                assert!(cols.iter().any(|x| x == c), "{t} da {c} yo'q");
            }
        }
    }

    /// v1 bazasi (ma'lumot bilan) v2 ga yangilanganda hech narsa yo'qolmaydi, yangi ustunlar standart qiymat oladi.
    #[test]
    fn v1_data_survives_upgrade_to_v2() {
        let mut conn = Connection::open_in_memory().unwrap();
        migrations().to_version(&mut conn, 1).unwrap();
        conn.execute_batch(
            "INSERT INTO households VALUES ('h','h','t','t',NULL,1,'d','Oila','UZS');
             INSERT INTO obligations VALUES ('o','h','t','t',NULL,1,'d','Ijara',300000000,'UZS',5);
             INSERT INTO categories VALUES ('c','h','t','t',NULL,1,'d','Non',NULL);",
        )
        .unwrap();
        migrations().to_latest(&mut conn).unwrap();
        let (name, kind, owner, remaining): (String, String, String, Option<i64>) = conn
            .query_row(
                "SELECT name, kind, owner, remaining_minor FROM obligations WHERE id='o'",
                [],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
            )
            .unwrap();
        assert_eq!(
            (name.as_str(), kind.as_str(), owner.as_str(), remaining),
            ("Ijara", "RECURRING", "OTHER", None)
        );
        let cat_owner: Option<String> = conn
            .query_row("SELECT owner FROM categories WHERE id='c'", [], |r| {
                r.get(0)
            })
            .unwrap();
        assert_eq!(cat_owner, None);
    }

    /// v5 → v6: mavjud «Kelajagim» QOROVUL bo'ladi, balans va tranzaksiyalar o'zgarmaydi.
    #[test]
    fn v6_migrates_vault_to_qorovul_without_losing_balance() {
        let mut conn = Connection::open_in_memory().unwrap();
        migrations().to_version(&mut conn, 5).unwrap();
        conn.execute_batch(
            "INSERT INTO households VALUES ('h','h','t','t',NULL,1,'d','Oila','UZS');
             INSERT INTO assets VALUES ('a','h','t','t',NULL,1,'d','VAULT','Kelajagim',777000,'tiyin','UZS','t');
             INSERT INTO assets VALUES ('c','h','t','t',NULL,1,'d','CASH','Naqd',5,'tiyin','UZS','t');
             INSERT INTO vault_transactions (id,household_id,created_at,updated_at,version,origin_device_id,asset_id,kind,amount_minor,currency,occurred_at)
               VALUES ('v','h','t','t',1,'d','a','DEPOSIT',777000,'UZS','t');",
        )
        .unwrap();
        migrations().to_latest(&mut conn).unwrap();
        let (qty, vt): (i64, Option<String>) = conn
            .query_row(
                "SELECT quantity, vault_type FROM assets WHERE id='a'",
                [],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!((qty, vt.as_deref()), (777_000, Some("QOROVUL")));
        let other: Option<String> = conn
            .query_row("SELECT vault_type FROM assets WHERE id='c'", [], |r| {
                r.get(0)
            })
            .unwrap();
        assert_eq!(other, None);
        let n: i64 = conn
            .query_row("SELECT COUNT(*) FROM vault_transactions", [], |r| r.get(0))
            .unwrap();
        assert_eq!(n, 1);
    }
    /// v12 → v13: jurnal yozuvlari, xeshlar va tuzatish havolasi saqlanadi; yangi turlar qabul qilinadi;
    /// o'zgartirish va o'chirish hamon rad etiladi (D13A).
    #[test]
    fn v12_to_v13_keeps_the_journal_chain_and_accepts_new_kinds() {
        let mut conn = Connection::open_in_memory().unwrap();
        conn.pragma_update(None, "foreign_keys", true).unwrap();
        migrations().to_version(&mut conn, 12).unwrap();
        let zeros = "0".repeat(64);
        let h1 = "1".repeat(64);
        let h2 = "2".repeat(64);
        conn.execute_batch(&format!(
            "INSERT INTO households VALUES ('h','h','t','t',NULL,1,'d','Oila','UZS');
             INSERT INTO agreements (id, household_id, created_at, updated_at, deleted_at, version,
               origin_device_id, agreement_type, title, status, subject_kind, subject_id,
               current_version, effective_from, keeper_device_id, legacy)
             VALUES ('a','h','t','t',NULL,1,'d','PARTNERSHIP','Test','ACTIVE','NONE',NULL,1,
               '2026-10-01','d',0);
             INSERT INTO journal_entries (id, household_id, created_at, updated_at, deleted_at, version,
               origin_device_id, agreement_id, seq, kind, party_id, amount_minor, amount_currency,
               entry_date, note, reference, corrects, prev_hash, hash)
             VALUES ('j1','h','t','t',NULL,1,'d','a',1,'OPENING_BALANCE',NULL,NULL,NULL,
               '2026-10-01','Boshlang''ich holat',NULL,NULL,'{zeros}','{h1}'),
               ('j2','h','t','t',NULL,1,'d','a',2,'CORRECTION',NULL,NULL,NULL,
               '2026-10-02','Tuzatish',NULL,'j1','{h1}','{h2}');"
        ))
        .unwrap();
        migrations().to_latest(&mut conn).unwrap();
        let (corrects, hash): (String, String) = conn
            .query_row(
                "SELECT corrects, hash FROM journal_entries WHERE id='j2'",
                [],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!((corrects.as_str(), hash.as_str()), ("j1", h2.as_str()));
        conn.execute(
            "INSERT INTO journal_entries (id, household_id, created_at, updated_at, deleted_at, version,
               origin_device_id, agreement_id, seq, kind, party_id, amount_minor, amount_currency,
               entry_date, note, reference, corrects, prev_hash, hash)
             VALUES ('j3','h','t','t',NULL,1,'d','a',3,'DUTY_INCIDENT','p',NULL,NULL,
               '2026-10-03','Bajara olmayapman',NULL,NULL,?1,?2)",
            [h2.as_str(), zeros.as_str()],
        )
        .unwrap();
        let upd = conn.execute("UPDATE journal_entries SET note='x' WHERE id='j1'", []);
        assert!(upd.unwrap_err().to_string().contains("journal_append_only"));
        let del = conn.execute("DELETE FROM journal_entries WHERE id='j1'", []);
        assert!(del.unwrap_err().to_string().contains("journal_append_only"));
    }

    /// v11 → v12: kelishuv jadvallari qo'shiladi, mavjud sheriklik ma'lumoti o'zgarmaydi (D8A).
    /// Eski sheriklik keyinroq `agreements` ga ko'chiriladi (services qatlamida, idempotent).
    #[test]
    fn v11_to_v12_keeps_partnership_data_and_adds_agreement_tables() {
        let mut conn = Connection::open_in_memory().unwrap();
        migrations().to_version(&mut conn, 11).unwrap();
        conn.execute_batch(
            "INSERT INTO households VALUES ('h','h','t','t',NULL,1,'d','Oila','UZS');
             INSERT INTO partnerships (id, household_id, created_at, updated_at, deleted_at, version,
               origin_device_id, name, kind, term_months, report_period, end_clause, dispute_clause,
               witnesses, contract_version, status)
             VALUES ('p','h','t','t',NULL,1,'d','Yetkazib berish','MUSHARAKA',12,'MONTHLY','tugash',
               'nizo','',1,'ACTIVE');",
        )
        .unwrap();
        migrations().to_latest(&mut conn).unwrap();
        let name: String = conn
            .query_row("SELECT name FROM partnerships WHERE id='p'", [], |r| {
                r.get(0)
            })
            .unwrap();
        assert_eq!(name, "Yetkazib berish");
        let agreements: i64 = conn
            .query_row("SELECT COUNT(*) FROM agreements", [], |r| r.get(0))
            .unwrap();
        assert_eq!(agreements, 0);
        let journal: i64 = conn
            .query_row("SELECT COUNT(*) FROM journal_entries", [], |r| r.get(0))
            .unwrap();
        assert_eq!(journal, 0);
    }
}
