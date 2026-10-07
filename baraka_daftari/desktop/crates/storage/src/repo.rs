//! Repository qatlami. Barcha jadvallar uchun umumiy amallar [`Record`] trait'i orqali:
//! `insert`, `get`, `list`, `update` (optimistik `version` bilan) va `soft_delete`.
//! Jadval va ustun nomlari faqat shu faylda, doimiylardan olinadi (SQL injection yo'q).

use domain::{
    date_to_string, ts_to_string, AllocationKind, AllocationRule, Asset, AssetSnapshot, AssetType,
    BillingPeriod, Category, ChapterProgress, DaftarPage, Envelope, EnvelopePeriod, Expense,
    FxRateRecord, GateBypass, HavasLimit, Household, Income, IncomeSourceType, LimitConsent,
    Member, MemberCredential, MemberRole, Meta, MoneyOwner, Necessity, NecessityChange, Obligation,
    ObligationKind, OffsetDateTime, PaymentChannel, PriceItem, PricePoint, RescueKind,
    SavingsRescue, ScheduledTreat, Setting, Subscription, TaskCompletion, VaultSource,
    VaultTransaction, VaultTxKind, VaultType, WithdrawalRequest, WithdrawalStatus,
};
use money::Money;
use rusqlite::{types::Value, Connection, OptionalExtension, Row};

use crate::{
    row::{self, META_COLS},
    StorageError,
};

pub trait Record: Sized {
    const TABLE: &'static str;
    /// Meta ustunlaridan keyingi ustunlar (tartib `values` va `from_row` bilan bir xil).
    const COLS: &'static [&'static str];
    fn meta(&self) -> &Meta;
    /// # Errors
    /// Sana yoki vaqt formatlanmasa.
    fn values(&self) -> Result<Vec<Value>, StorageError>;
    /// Qator: avval 7 ta meta ustun, so'ng `COLS` (indeks 7 dan).
    ///
    /// # Errors
    /// Qator buzilgan bo'lsa.
    fn from_row(row: &Row<'_>) -> rusqlite::Result<Self>;
}

fn t(s: &str) -> Value {
    Value::Text(s.to_owned())
}

fn ts_val(v: OffsetDateTime) -> Result<Value, StorageError> {
    ts_to_string(v)
        .map(Value::Text)
        .map_err(|e| StorageError::Corrupt(e.to_string()))
}

fn date_val(v: domain::Date) -> Result<Value, StorageError> {
    date_to_string(v)
        .map(Value::Text)
        .map_err(|e| StorageError::Corrupt(e.to_string()))
}

fn opt_text(v: Option<&str>) -> Value {
    v.map_or(Value::Null, t)
}

fn opt_bool(v: Option<bool>) -> Value {
    v.map_or(Value::Null, |b| Value::Integer(i64::from(b)))
}

fn meta_values(m: &Meta) -> Result<Vec<Value>, StorageError> {
    Ok(vec![
        t(&m.id),
        t(&m.household_id),
        ts_val(m.created_at)?,
        ts_val(m.updated_at)?,
        m.deleted_at.map(ts_val).transpose()?.unwrap_or(Value::Null),
        Value::Integer(m.version),
        t(&m.origin_device_id),
    ])
}

fn select_sql<T: Record>(filter: &str) -> String {
    format!(
        "SELECT {META_COLS}, {} FROM {} WHERE {filter}",
        T::COLS.join(", "),
        T::TABLE
    )
}

/// # Errors
/// SQL yoki format xatosi, yoki `id` takrorlansa.
pub fn insert<T: Record>(conn: &Connection, item: &T) -> Result<(), StorageError> {
    let mut vals = meta_values(item.meta())?;
    vals.extend(item.values()?);
    let n = 7 + T::COLS.len();
    let placeholders = (1..=n)
        .map(|i| format!("?{i}"))
        .collect::<Vec<_>>()
        .join(", ");
    let sql = format!(
        "INSERT INTO {} ({META_COLS}, {}) VALUES ({placeholders})",
        T::TABLE,
        T::COLS.join(", ")
    );
    conn.execute(&sql, rusqlite::params_from_iter(vals))?;
    Ok(())
}

/// O'chirilmagan yozuvni qaytaradi.
///
/// # Errors
/// SQL xatosi.
pub fn get<T: Record>(conn: &Connection, id: &str) -> Result<Option<T>, StorageError> {
    let sql = select_sql::<T>("id = ?1 AND deleted_at IS NULL");
    Ok(conn.query_row(&sql, [id], T::from_row).optional()?)
}

/// Xonadonning o'chirilmagan yozuvlari (UUIDv7 bo'yicha, ya'ni yaratilish tartibida).
///
/// # Errors
/// SQL xatosi.
pub fn list<T: Record>(conn: &Connection, household_id: &str) -> Result<Vec<T>, StorageError> {
    let sql = format!(
        "{} ORDER BY id",
        select_sql::<T>("household_id = ?1 AND deleted_at IS NULL")
    );
    let mut stmt = conn.prepare(&sql)?;
    let rows = stmt
        .query_map([household_id], T::from_row)?
        .collect::<Result<_, _>>()?;
    Ok(rows)
}

/// Barcha xonadonlar bo'yicha (faqat `households` kabi xonadon bog'lanmagan jadvallar uchun).
///
/// # Errors
/// SQL xatosi.
pub fn list_all<T: Record>(conn: &Connection) -> Result<Vec<T>, StorageError> {
    let sql = format!("{} ORDER BY id", select_sql::<T>("deleted_at IS NULL"));
    let mut stmt = conn.prepare(&sql)?;
    let rows = stmt.query_map([], T::from_row)?.collect::<Result<_, _>>()?;
    Ok(rows)
}

/// Optimistik yangilash: `item.meta().version` bazadagi bilan teng bo'lishi kerak;
/// muvaffaqiyatda versiya 1 ga oshadi.
///
/// # Errors
/// Versiya mos kelmasa yoki yozuv o'chirilgan bo'lsa [`StorageError::NotFound`].
pub fn update<T: Record>(
    conn: &Connection,
    item: &T,
    now: OffsetDateTime,
) -> Result<(), StorageError> {
    let m = item.meta();
    let mut vals = item.values()?;
    let sets = T::COLS
        .iter()
        .enumerate()
        .map(|(i, c)| format!("{c} = ?{}", i + 1))
        .collect::<Vec<_>>()
        .join(", ");
    let n = T::COLS.len();
    vals.push(ts_val(now)?);
    vals.push(t(&m.id));
    vals.push(Value::Integer(m.version));
    let sql = format!(
        "UPDATE {} SET {sets}, updated_at = ?{}, version = version + 1 \
         WHERE id = ?{} AND version = ?{} AND deleted_at IS NULL",
        T::TABLE,
        n + 1,
        n + 2,
        n + 3
    );
    match conn.execute(&sql, rusqlite::params_from_iter(vals))? {
        0 => Err(StorageError::NotFound),
        _ => Ok(()),
    }
}

/// Soft delete (tombstone): `deleted_at` qo'yiladi, versiya oshadi.
///
/// # Errors
/// Yozuv yo'q yoki allaqachon o'chirilgan bo'lsa [`StorageError::NotFound`].
pub fn soft_delete<T: Record>(
    conn: &Connection,
    id: &str,
    now: OffsetDateTime,
) -> Result<(), StorageError> {
    let now = ts_val(now)?;
    let sql = format!(
        "UPDATE {} SET deleted_at = ?1, updated_at = ?1, version = version + 1 \
         WHERE id = ?2 AND deleted_at IS NULL",
        T::TABLE
    );
    match conn.execute(&sql, rusqlite::params![now, id])? {
        0 => Err(StorageError::NotFound),
        _ => Ok(()),
    }
}

fn money_vals(m: money::Money) -> [Value; 2] {
    [Value::Integer(m.minor()), t(m.currency().code())]
}

impl Record for Household {
    const TABLE: &'static str = "households";
    const COLS: &'static [&'static str] = &["name", "base_currency"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![t(&self.name), t(self.base_currency.code())])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            base_currency: row::currency(r, 8)?,
        })
    }
}

impl Record for Member {
    const TABLE: &'static str = "members";
    const COLS: &'static [&'static str] = &["display_name", "role"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![t(&self.display_name), t(self.role.as_str())])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            display_name: r.get(7)?,
            role: row::parsed(r, 8, MemberRole::parse)?,
        })
    }
}

impl Record for Category {
    const TABLE: &'static str = "categories";
    const COLS: &'static [&'static str] = &["name", "necessity", "owner", "is_charity", "is_habit"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.name),
            opt_text(self.necessity.map(Necessity::as_str)),
            opt_text(self.owner.map(MoneyOwner::as_str)),
            Value::Integer(i64::from(self.is_charity)),
            Value::Integer(i64::from(self.is_habit)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            necessity: row::opt_parsed(r, 8, Necessity::parse)?,
            owner: row::opt_parsed(r, 9, MoneyOwner::parse)?,
            is_charity: r.get(10)?,
            is_habit: r.get(11)?,
        })
    }
}

impl Record for Income {
    const TABLE: &'static str = "incomes";
    const COLS: &'static [&'static str] = &[
        "member_id",
        "source",
        "channel",
        "amount_minor",
        "currency",
        "received_on",
        "source_type",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(&self.member_id),
            t(&self.source),
            t(self.channel.as_str()),
            minor,
            cur,
            date_val(self.received_on)?,
            opt_text(self.source_type.map(IncomeSourceType::as_str)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            member_id: r.get(7)?,
            source: r.get(8)?,
            channel: row::parsed(r, 9, PaymentChannel::parse)?,
            amount: row::money(r, 10, 11)?,
            received_on: row::date(r, 12)?,
            source_type: row::opt_parsed(r, 13, IncomeSourceType::parse)?,
        })
    }
}

impl Record for Expense {
    const TABLE: &'static str = "expenses";
    const COLS: &'static [&'static str] = &[
        "member_id",
        "category_id",
        "amount_minor",
        "currency",
        "spent_on",
        "payment_channel",
        "necessity",
        "envelope_id",
        "is_gift",
        "is_ostentation",
        "funded_by_debt",
        "audit_month",
        "note",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(&self.member_id),
            t(&self.category_id),
            minor,
            cur,
            date_val(self.spent_on)?,
            t(self.payment_channel.as_str()),
            opt_text(self.necessity.map(Necessity::as_str)),
            opt_text(self.envelope_id.as_deref()),
            opt_bool(self.is_gift),
            opt_bool(self.is_ostentation),
            opt_bool(self.funded_by_debt),
            opt_text(self.audit_month.as_deref()),
            opt_text(self.note.as_deref()),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            member_id: r.get(7)?,
            category_id: r.get(8)?,
            amount: row::money(r, 9, 10)?,
            spent_on: row::date(r, 11)?,
            payment_channel: row::parsed(r, 12, PaymentChannel::parse)?,
            necessity: row::opt_parsed(r, 13, Necessity::parse)?,
            envelope_id: r.get(14)?,
            is_gift: r.get(15)?,
            is_ostentation: r.get(16)?,
            funded_by_debt: r.get(17)?,
            audit_month: r.get(18)?,
            note: r.get(19)?,
        })
    }
}

impl Record for Asset {
    const TABLE: &'static str = "assets";
    const COLS: &'static [&'static str] = &[
        "asset_type",
        "name",
        "quantity",
        "unit",
        "currency",
        "acquired_at",
        "vault_type",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(self.asset_type.as_str()),
            t(&self.name),
            Value::Integer(self.quantity),
            t(&self.unit),
            opt_text(self.currency.map(money::Currency::code)),
            ts_val(self.acquired_at)?,
            opt_text(self.vault_type.map(VaultType::as_str)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            asset_type: row::parsed(r, 7, AssetType::parse)?,
            name: r.get(8)?,
            quantity: r.get(9)?,
            unit: r.get(10)?,
            currency: row::opt_currency(r, 11)?,
            acquired_at: row::ts(r, 12)?,
            vault_type: row::opt_parsed(r, 13, VaultType::parse)?,
        })
    }
}

impl Record for AssetSnapshot {
    const TABLE: &'static str = "asset_snapshots";
    const COLS: &'static [&'static str] = &["asset_id", "quantity", "taken_at"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.asset_id),
            Value::Integer(self.quantity),
            ts_val(self.taken_at)?,
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            asset_id: r.get(7)?,
            quantity: r.get(8)?,
            taken_at: row::ts(r, 9)?,
        })
    }
}

impl Record for VaultTransaction {
    const TABLE: &'static str = "vault_transactions";
    const COLS: &'static [&'static str] = &[
        "asset_id",
        "kind",
        "amount_minor",
        "currency",
        "occurred_at",
        "note",
        "source",
        "income_id",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(&self.asset_id),
            t(self.kind.as_str()),
            minor,
            cur,
            ts_val(self.occurred_at)?,
            opt_text(self.note.as_deref()),
            opt_text(self.source.map(VaultSource::as_str)),
            opt_text(self.income_id.as_deref()),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            asset_id: r.get(7)?,
            kind: row::parsed(r, 8, VaultTxKind::parse)?,
            amount: row::money(r, 9, 10)?,
            occurred_at: row::ts(r, 11)?,
            note: r.get(12)?,
            source: row::opt_parsed(r, 13, VaultSource::parse)?,
            income_id: r.get(14)?,
        })
    }
}

impl Record for AllocationRule {
    const TABLE: &'static str = "allocation_rules";
    const COLS: &'static [&'static str] = &["kind", "value", "currency"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(self.kind.as_str()),
            Value::Integer(self.value),
            opt_text(self.currency.map(money::Currency::code)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            kind: row::parsed(r, 7, AllocationKind::parse)?,
            value: r.get(8)?,
            currency: row::opt_currency(r, 9)?,
        })
    }
}

impl Record for Obligation {
    const TABLE: &'static str = "obligations";
    const COLS: &'static [&'static str] = &[
        "name",
        "amount_minor",
        "currency",
        "due_day",
        "kind",
        "owner",
        "creditor",
        "remaining_minor",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(&self.name),
            minor,
            cur,
            Value::Integer(i64::from(self.due_day)),
            t(self.kind.as_str()),
            t(self.owner.as_str()),
            opt_text(self.creditor.as_deref()),
            self.remaining
                .map_or(Value::Null, |m| Value::Integer(m.minor())),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        let amount = row::money(r, 8, 9)?;
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            amount,
            due_day: r.get(10)?,
            kind: row::parsed(r, 11, ObligationKind::parse)?,
            owner: row::parsed(r, 12, MoneyOwner::parse)?,
            creditor: r.get(13)?,
            remaining: r
                .get::<_, Option<i64>>(14)?
                .map(|v| Money::new(v, amount.currency())),
        })
    }
}

impl Record for FxRateRecord {
    const TABLE: &'static str = "fx_rates";
    const COLS: &'static [&'static str] = &[
        "from_currency",
        "to_currency",
        "rate_num",
        "rate_den",
        "date",
        "source",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(self.from.code()),
            t(self.to.code()),
            Value::Integer(self.rate_num),
            Value::Integer(self.rate_den),
            date_val(self.date)?,
            t(&self.source),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            from: row::currency(r, 7)?,
            to: row::currency(r, 8)?,
            rate_num: r.get(9)?,
            rate_den: r.get(10)?,
            date: row::date(r, 11)?,
            source: r.get(12)?,
        })
    }
}

impl Record for WithdrawalRequest {
    const TABLE: &'static str = "withdrawal_requests";
    const COLS: &'static [&'static str] = &[
        "asset_id",
        "amount_minor",
        "currency",
        "reason",
        "available_at",
        "status",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(&self.asset_id),
            minor,
            cur,
            t(&self.reason),
            ts_val(self.available_at)?,
            t(self.status.as_str()),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            asset_id: r.get(7)?,
            amount: row::money(r, 8, 9)?,
            reason: r.get(10)?,
            available_at: row::ts(r, 11)?,
            status: row::parsed(r, 12, WithdrawalStatus::parse)?,
        })
    }
}

impl Record for TaskCompletion {
    const TABLE: &'static str = "task_completions";
    const COLS: &'static [&'static str] = &["chapter_id", "task_id", "week_start", "completed_at"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.chapter_id),
            t(&self.task_id),
            date_val(self.week_start)?,
            ts_val(self.completed_at)?,
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            chapter_id: r.get(7)?,
            task_id: r.get(8)?,
            week_start: row::date(r, 9)?,
            completed_at: row::ts(r, 10)?,
        })
    }
}

impl Record for ChapterProgress {
    const TABLE: &'static str = "chapter_progress";
    const COLS: &'static [&'static str] = &["chapter_id", "opened_on"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![t(&self.chapter_id), date_val(self.opened_on)?])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            chapter_id: r.get(7)?,
            opened_on: row::date(r, 8)?,
        })
    }
}

impl Record for DaftarPage {
    const TABLE: &'static str = "daftar_pages";
    const COLS: &'static [&'static str] = &["chapter_id", "body"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![t(&self.chapter_id), t(&self.body)])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            chapter_id: r.get(7)?,
            body: r.get(8)?,
        })
    }
}

impl Record for Setting {
    const TABLE: &'static str = "settings";
    const COLS: &'static [&'static str] = &["key", "value"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![t(&self.key), t(&self.value)])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            key: r.get(7)?,
            value: r.get(8)?,
        })
    }
}

impl Record for MemberCredential {
    const TABLE: &'static str = "member_credentials";
    const COLS: &'static [&'static str] = &["member_id", "pin_hash", "failures", "locked_until"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.member_id),
            t(&self.pin_hash),
            Value::Integer(i64::from(self.failures)),
            Value::Integer(self.locked_until),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            member_id: r.get(7)?,
            pin_hash: r.get(8)?,
            failures: r.get(9)?,
            locked_until: r.get(10)?,
        })
    }
}

impl Record for NecessityChange {
    const TABLE: &'static str = "necessity_changes";
    const COLS: &'static [&'static str] = &[
        "category_id",
        "from_necessity",
        "to_necessity",
        "changed_by",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.category_id),
            opt_text(self.from.map(Necessity::as_str)),
            t(self.to.as_str()),
            t(&self.changed_by),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            category_id: r.get(7)?,
            from: row::opt_parsed(r, 8, Necessity::parse)?,
            to: row::parsed(r, 9, Necessity::parse)?,
            changed_by: r.get(10)?,
        })
    }
}

impl Record for HavasLimit {
    const TABLE: &'static str = "havas_limits";
    const COLS: &'static [&'static str] = &["amount_minor", "currency", "proposed_by"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![minor, cur, t(&self.proposed_by)])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            amount: row::money(r, 7, 8)?,
            proposed_by: r.get(9)?,
        })
    }
}

impl Record for LimitConsent {
    const TABLE: &'static str = "limit_consents";
    const COLS: &'static [&'static str] = &["limit_id", "member_id", "consented_at"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.limit_id),
            t(&self.member_id),
            ts_val(self.consented_at)?,
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            limit_id: r.get(7)?,
            member_id: r.get(8)?,
            consented_at: row::ts(r, 9)?,
        })
    }
}

impl Record for ScheduledTreat {
    const TABLE: &'static str = "scheduled_treats";
    const COLS: &'static [&'static str] =
        &["name", "amount_minor", "currency", "weekday", "active"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(&self.name),
            minor,
            cur,
            Value::Integer(i64::from(self.weekday)),
            Value::Integer(i64::from(self.active)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            amount: row::money(r, 8, 9)?,
            weekday: r.get(10)?,
            active: r.get(11)?,
        })
    }
}

fn opt_date(v: Option<domain::Date>) -> Result<Value, StorageError> {
    v.map_or(Ok(Value::Null), date_val)
}

fn opt_row_date(r: &Row<'_>, idx: usize) -> rusqlite::Result<Option<domain::Date>> {
    r.get::<_, Option<String>>(idx)?
        .map(|s| {
            domain::date_from_str(&s).map_err(|e| {
                rusqlite::Error::FromSqlConversionFailure(
                    idx,
                    rusqlite::types::Type::Text,
                    Box::new(e),
                )
            })
        })
        .transpose()
}

impl Record for Subscription {
    const TABLE: &'static str = "subscriptions";
    const COLS: &'static [&'static str] = &[
        "name",
        "amount_minor",
        "currency",
        "period",
        "started_on",
        "last_used_on",
        "cancelled_on",
        "needed",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(&self.name),
            minor,
            cur,
            t(self.period.as_str()),
            date_val(self.started_on)?,
            opt_date(self.last_used_on)?,
            opt_date(self.cancelled_on)?,
            opt_bool(self.needed),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            amount: row::money(r, 8, 9)?,
            period: row::parsed(r, 10, BillingPeriod::parse)?,
            started_on: row::date(r, 11)?,
            last_used_on: opt_row_date(r, 12)?,
            cancelled_on: opt_row_date(r, 13)?,
            needed: r.get(14)?,
        })
    }
}

impl Record for Envelope {
    const TABLE: &'static str = "envelopes";
    const COLS: &'static [&'static str] = &[
        "name",
        "weekly_limit_minor",
        "currency",
        "category_id",
        "necessity",
        "active",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.weekly_limit);
        Ok(vec![
            t(&self.name),
            minor,
            cur,
            opt_text(self.category_id.as_deref()),
            opt_text(self.necessity.map(Necessity::as_str)),
            Value::Integer(i64::from(self.active)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            weekly_limit: row::money(r, 8, 9)?,
            category_id: r.get(10)?,
            necessity: row::opt_parsed(r, 11, Necessity::parse)?,
            active: r.get(12)?,
        })
    }
}

impl Record for EnvelopePeriod {
    const TABLE: &'static str = "envelope_periods";
    const COLS: &'static [&'static str] = &[
        "envelope_id",
        "week_start",
        "limit_minor",
        "spent_minor",
        "leftover_minor",
        "difference_minor",
        "currency",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.envelope_id),
            date_val(self.week_start)?,
            Value::Integer(self.limit.minor()),
            Value::Integer(self.spent.minor()),
            Value::Integer(self.leftover_cash.minor()),
            Value::Integer(self.difference.minor()),
            t(self.limit.currency().code()),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        let cur = row::currency(r, 13)?;
        Ok(Self {
            meta: row::meta(r)?,
            envelope_id: r.get(7)?,
            week_start: row::date(r, 8)?,
            limit: Money::new(r.get(9)?, cur),
            spent: Money::new(r.get(10)?, cur),
            leftover_cash: Money::new(r.get(11)?, cur),
            difference: Money::new(r.get(12)?, cur),
        })
    }
}

impl Record for SavingsRescue {
    const TABLE: &'static str = "savings_rescues";
    const COLS: &'static [&'static str] = &[
        "kind",
        "amount_minor",
        "currency",
        "week_start",
        "note",
        "transferred_at",
    ];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.amount);
        Ok(vec![
            t(self.kind.as_str()),
            minor,
            cur,
            opt_date(self.week_start)?,
            opt_text(self.note.as_deref()),
            self.transferred_at
                .map(ts_val)
                .transpose()?
                .unwrap_or(Value::Null),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            kind: row::parsed(r, 7, RescueKind::parse)?,
            amount: row::money(r, 8, 9)?,
            week_start: opt_row_date(r, 10)?,
            note: r.get(11)?,
            transferred_at: row::opt_ts(r, 12)?,
        })
    }
}

impl Record for PriceItem {
    const TABLE: &'static str = "price_items";
    const COLS: &'static [&'static str] = &["name", "unit", "weight_bp", "active"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.name),
            t(&self.unit),
            Value::Integer(i64::from(self.weight_bp)),
            Value::Integer(i64::from(self.active)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            unit: r.get(8)?,
            weight_bp: r.get(9)?,
            active: r.get::<_, i64>(10)? != 0,
        })
    }
}

impl Record for PricePoint {
    const TABLE: &'static str = "price_points";
    const COLS: &'static [&'static str] =
        &["item_id", "price_minor", "currency", "observed_on", "place"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        let [minor, cur] = money_vals(self.price);
        Ok(vec![
            t(&self.item_id),
            minor,
            cur,
            date_val(self.observed_on)?,
            opt_text(self.place.as_deref()),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            item_id: r.get(7)?,
            price: row::money(r, 8, 9)?,
            observed_on: row::date(r, 10)?,
            place: r.get(11)?,
        })
    }
}

impl Record for GateBypass {
    const TABLE: &'static str = "gate_bypasses";
    const COLS: &'static [&'static str] = &["guard_months_x100"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![Value::Integer(i64::from(self.guard_months_x100))])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            guard_months_x100: r.get(7)?,
        })
    }
}
