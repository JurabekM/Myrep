//! Repository qatlami. Barcha jadvallar uchun umumiy amallar [`Record`] trait'i orqali:
//! `insert`, `get`, `list`, `update` (optimistik `version` bilan) va `soft_delete`.
//! Jadval va ustun nomlari faqat shu faylda, doimiylardan olinadi (SQL injection yo'q).

use domain::{
    date_to_string, ts_to_string, AllocationKind, AllocationRule, Asset, AssetSnapshot, AssetType,
    Category, Expense, FxRateRecord, Household, Income, Member, MemberRole, Meta, Necessity,
    Obligation, OffsetDateTime, PaymentChannel, VaultTransaction, VaultTxKind,
};
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
    const COLS: &'static [&'static str] = &["name", "necessity"];
    fn meta(&self) -> &Meta {
        &self.meta
    }
    fn values(&self) -> Result<Vec<Value>, StorageError> {
        Ok(vec![
            t(&self.name),
            opt_text(self.necessity.map(Necessity::as_str)),
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            necessity: row::opt_parsed(r, 8, Necessity::parse)?,
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
    const COLS: &'static [&'static str] = &["name", "amount_minor", "currency", "due_day"];
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
        ])
    }
    fn from_row(r: &Row<'_>) -> rusqlite::Result<Self> {
        Ok(Self {
            meta: row::meta(r)?,
            name: r.get(7)?,
            amount: row::money(r, 8, 9)?,
            due_day: r.get(10)?,
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
