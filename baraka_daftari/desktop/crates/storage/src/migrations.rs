use rusqlite_migration::{Migrations, M};

/// Joriy sxema versiyasi (`PRAGMA user_version`).
pub const SCHEMA_VERSION: usize = 1;

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

/// Migratsiyalar ro'yxati. Har bir yangi versiya oxiriga qo'shiladi; mavjudlari o'zgartirilmaydi.
#[must_use]
pub fn migrations() -> Migrations<'static> {
    Migrations::new(vec![M::up(V1)])
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
        assert_eq!(tables.len(), 11);
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
}
