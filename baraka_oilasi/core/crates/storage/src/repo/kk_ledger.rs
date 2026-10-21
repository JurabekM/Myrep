//! Kasb-kor (K4): kunlik kassa yopish, mijozlar va nasiya daftari.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

/// Yopilgan kassa kuni (o'zgarmas).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkCashDayRow {
    pub id: String,
    pub day: String,
    pub currency: String,
    pub opening_minor: i64,
    pub expected_minor: i64,
    pub counted_minor: i64,
    pub difference_minor: i64,
    pub reason: Option<String>,
    pub note: Option<String>,
    pub result_json: String,
    pub closed_at: String,
}

pub fn insert_cash_day(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkCashDayRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_cash_days (id, household_id, space_id, day, currency, opening_minor, expected_minor,
            counted_minor, difference_minor, reason, note, result_json, closed_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
        params![r.id, s.household_id, s.space_id, r.day, r.currency, r.opening_minor, r.expected_minor,
            r.counted_minor, r.difference_minor, r.reason, r.note, r.result_json, r.closed_at, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi yopilgan kunlar, sana bo'yicha.
pub fn cash_days_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<KkCashDayRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, day, currency, opening_minor, expected_minor, counted_minor, difference_minor, reason, note,
            result_json, closed_at
         FROM kk_cash_days WHERE household_id = ?1 AND space_id = ?2 AND day >= ?3 AND day < ?4 ORDER BY day",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], |r| {
        Ok(KkCashDayRow {
            id: r.get(0)?,
            day: r.get(1)?,
            currency: r.get(2)?,
            opening_minor: r.get(3)?,
            expected_minor: r.get(4)?,
            counted_minor: r.get(5)?,
            difference_minor: r.get(6)?,
            reason: r.get(7)?,
            note: r.get(8)?,
            result_json: r.get(9)?,
            closed_at: r.get(10)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Oxirgi yopilgan kassa kuni.
pub fn cash_closed_until(c: &Connection, s: &SpaceScope) -> Result<Option<String>, StorageError> {
    Ok(c.query_row(
        "SELECT MAX(day) FROM kk_cash_days WHERE household_id = ?1 AND space_id = ?2",
        params![s.household_id, s.space_id],
        |r| r.get(0),
    )?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkCustomerRow {
    pub id: String,
    pub name: String,
    pub phone: Option<String>,
    pub phone_consent: bool,
    pub note: Option<String>,
}

pub fn insert_customer(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkCustomerRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_customers (id, household_id, space_id, name, phone, phone_consent, note, created_at, updated_at,
            origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?8, ?9, ?9)",
        params![r.id, s.household_id, s.space_id, r.name, r.phone, r.phone_consent, r.note, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn customers(c: &Connection, s: &SpaceScope) -> Result<Vec<KkCustomerRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, name, phone, phone_consent, note FROM kk_customers
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL ORDER BY name COLLATE NOCASE, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkCustomerRow {
            id: r.get(0)?,
            name: r.get(1)?,
            phone: r.get(2)?,
            phone_consent: r.get(3)?,
            note: r.get(4)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkCreditSaleRow {
    pub id: String,
    pub customer_id: String,
    pub item: String,
    pub currency: String,
    pub cash_price_minor: Option<i64>,
    pub credit_price_minor: i64,
    pub installments: i64,
    pub sold_on: String,
    pub first_due: String,
    pub witness: Option<String>,
    pub note: Option<String>,
    pub review_week: Option<String>,
}

pub fn insert_credit_sale(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkCreditSaleRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_credit_sales (id, household_id, space_id, customer_id, item, currency, cash_price_minor,
            credit_price_minor, installments, sold_on, first_due, witness, note, review_week, created_at, updated_at,
            origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?15, ?16, ?16)",
        params![r.id, s.household_id, s.space_id, r.customer_id, r.item, r.currency, r.cash_price_minor,
            r.credit_price_minor, r.installments, r.sold_on, r.first_due, r.witness, r.note, r.review_week, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn credit_sales(c: &Connection, s: &SpaceScope) -> Result<Vec<KkCreditSaleRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, customer_id, item, currency, cash_price_minor, credit_price_minor, installments, sold_on, first_due,
            witness, note, review_week
         FROM kk_credit_sales WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL ORDER BY sold_on, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkCreditSaleRow {
            id: r.get(0)?,
            customer_id: r.get(1)?,
            item: r.get(2)?,
            currency: r.get(3)?,
            cash_price_minor: r.get(4)?,
            credit_price_minor: r.get(5)?,
            installments: r.get(6)?,
            sold_on: r.get(7)?,
            first_due: r.get(8)?,
            witness: r.get(9)?,
            note: r.get(10)?,
            review_week: r.get(11)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// «Bu hafta kim bilan gaplashaman» belgisi (narx va jadvalga tegmaydi).
pub fn set_review_week(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    week: Option<&str>,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_credit_sales SET review_week = ?4, updated_at = ?5, updated_by_device_id = ?6, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, week, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

/// Hodisasi yo'q nasiyani o'chirish (xato kiritilgan bo'lsa).
pub fn delete_credit_sale(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_credit_sales SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL
           AND NOT EXISTS (SELECT 1 FROM kk_credit_events e WHERE e.sale_id = ?3)",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkCreditEventRow {
    pub id: String,
    pub sale_id: String,
    pub kind: String,
    pub occurred_on: String,
    pub amount_minor: Option<i64>,
    pub months: Option<i64>,
    pub wallet: Option<String>,
    pub income_id: Option<String>,
    pub note: Option<String>,
}

pub fn insert_credit_event(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkCreditEventRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_credit_events (id, household_id, space_id, sale_id, kind, occurred_on, amount_minor, months,
            wallet, income_id, note, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
        params![r.id, s.household_id, s.space_id, r.sale_id, r.kind, r.occurred_on, r.amount_minor, r.months,
            r.wallet, r.income_id, r.note, m.now, m.device_id],
    )?;
    Ok(())
}

/// Makondagi barcha nasiya hodisalari (sana, yozilish tartibida).
pub fn credit_events(
    c: &Connection,
    s: &SpaceScope,
) -> Result<Vec<KkCreditEventRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, sale_id, kind, occurred_on, amount_minor, months, wallet, income_id, note
         FROM kk_credit_events WHERE household_id = ?1 AND space_id = ?2 ORDER BY occurred_on, created_at, id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkCreditEventRow {
            id: r.get(0)?,
            sale_id: r.get(1)?,
            kind: r.get(2)?,
            occurred_on: r.get(3)?,
            amount_minor: r.get(4)?,
            months: r.get(5)?,
            wallet: r.get(6)?,
            income_id: r.get(7)?,
            note: r.get(8)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Mijoz nomi (o'chirilmagan bo'lsa).
pub fn customer_name(
    c: &Connection,
    s: &SpaceScope,
    id: &str,
) -> Result<Option<String>, StorageError> {
    Ok(c.query_row(
        "SELECT name FROM kk_customers WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id],
        |r| r.get(0),
    )
    .optional()?)
}
