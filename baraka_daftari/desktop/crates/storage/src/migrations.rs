use rusqlite_migration::{Migrations, M};

/// Joriy sxema versiyasi (`PRAGMA user_version`).
pub const SCHEMA_VERSION: usize = 9;

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
        assert_eq!(tables.len(), 38);
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
}
