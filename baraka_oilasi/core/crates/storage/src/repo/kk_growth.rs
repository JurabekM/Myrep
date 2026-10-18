//! Kasb-kor (K7): darvoza va zakot sozlamalari, konvertdan foydalanish, tarozi tekshiruvi, zakot hisobi va
//! yillik inventarizatsiya snapshot'lari.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkGrowthSettingsRow {
    pub reserve_months: i64,
    pub max_bad_bp: i64,
    pub zakat_month: Option<i64>,
    pub zakat_day: Option<i64>,
    pub gold_price_minor: Option<i64>,
    pub nisab_grams: i64,
    pub stock_valuation: String,
    pub scale_reminder: bool,
    pub currency: String,
}

pub fn growth_settings(
    c: &Connection,
    s: &SpaceScope,
) -> Result<Option<KkGrowthSettingsRow>, StorageError> {
    Ok(c.query_row(
        "SELECT reserve_months, max_bad_bp, zakat_month, zakat_day, gold_price_minor, nisab_grams, stock_valuation,
            scale_reminder, currency
         FROM kk_growth_settings WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(KkGrowthSettingsRow {
                reserve_months: r.get(0)?,
                max_bad_bp: r.get(1)?,
                zakat_month: r.get(2)?,
                zakat_day: r.get(3)?,
                gold_price_minor: r.get(4)?,
                nisab_grams: r.get(5)?,
                stock_valuation: r.get(6)?,
                scale_reminder: r.get(7)?,
                currency: r.get(8)?,
            })
        },
    )
    .optional()?)
}

pub fn upsert_growth_settings(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    r: &KkGrowthSettingsRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_growth_settings (id, household_id, space_id, reserve_months, max_bad_bp, zakat_month,
            zakat_day, gold_price_minor, nisab_grams, stock_valuation, scale_reminder, currency, created_at,
            updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?13, ?14, ?14)
         ON CONFLICT (space_id) DO UPDATE SET reserve_months = excluded.reserve_months,
            max_bad_bp = excluded.max_bad_bp, zakat_month = excluded.zakat_month, zakat_day = excluded.zakat_day,
            gold_price_minor = excluded.gold_price_minor, nisab_grams = excluded.nisab_grams,
            stock_valuation = excluded.stock_valuation, scale_reminder = excluded.scale_reminder,
            currency = excluded.currency, updated_at = excluded.updated_at,
            updated_by_device_id = excluded.updated_by_device_id, version = kk_growth_settings.version + 1",
        params![id, s.household_id, s.space_id, r.reserve_months, r.max_bad_bp, r.zakat_month, r.zakat_day,
            r.gold_price_minor, r.nisab_grams, r.stock_valuation, r.scale_reminder, r.currency, m.now, m.device_id],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkFundUseRow {
    pub id: String,
    pub fund: String,
    pub used_on: String,
    pub amount_minor: i64,
    pub currency: String,
    pub note: Option<String>,
}

pub fn insert_fund_use(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkFundUseRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_fund_uses (id, household_id, space_id, fund, used_on, amount_minor, currency, note,
            created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![r.id, s.household_id, s.space_id, r.fund, r.used_on, r.amount_minor, r.currency, r.note, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn fund_uses(c: &Connection, s: &SpaceScope) -> Result<Vec<KkFundUseRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, fund, used_on, amount_minor, currency, note FROM kk_fund_uses
         WHERE household_id = ?1 AND space_id = ?2 ORDER BY used_on, created_at, id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkFundUseRow {
            id: r.get(0)?,
            fund: r.get(1)?,
            used_on: r.get(2)?,
            amount_minor: r.get(3)?,
            currency: r.get(4)?,
            note: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkScaleCheckRow {
    pub id: String,
    pub checked_on: String,
    pub result: String,
    pub note: Option<String>,
}

pub fn insert_scale_check(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkScaleCheckRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_scale_checks (id, household_id, space_id, checked_on, result, note, created_at,
            origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![r.id, s.household_id, s.space_id, r.checked_on, r.result, r.note, m.now, m.device_id],
    )?;
    Ok(())
}

/// Yangisi birinchi.
pub fn scale_checks(c: &Connection, s: &SpaceScope) -> Result<Vec<KkScaleCheckRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, checked_on, result, note FROM kk_scale_checks WHERE household_id = ?1 AND space_id = ?2
         ORDER BY checked_on DESC, created_at DESC, id DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkScaleCheckRow {
            id: r.get(0)?,
            checked_on: r.get(1)?,
            result: r.get(2)?,
            note: r.get(3)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkZakatCalcRow {
    pub id: String,
    pub calculated_on: String,
    pub hijri_date: String,
    pub currency: String,
    pub inputs_json: String,
    pub base_minor: i64,
    pub nisab_minor: i64,
    pub zakat_minor: i64,
    pub reason: Option<String>,
}

pub fn insert_zakat_calc(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkZakatCalcRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_zakat_calcs (id, household_id, space_id, calculated_on, hijri_date, currency, inputs_json,
            base_minor, nisab_minor, zakat_minor, reason, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
        params![r.id, s.household_id, s.space_id, r.calculated_on, r.hijri_date, r.currency, r.inputs_json,
            r.base_minor, r.nisab_minor, r.zakat_minor, r.reason, m.now, m.device_id],
    )?;
    Ok(())
}

/// Yangisi birinchi.
pub fn zakat_calcs(c: &Connection, s: &SpaceScope) -> Result<Vec<KkZakatCalcRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, calculated_on, hijri_date, currency, inputs_json, base_minor, nisab_minor, zakat_minor, reason
         FROM kk_zakat_calcs WHERE household_id = ?1 AND space_id = ?2
         ORDER BY calculated_on DESC, created_at DESC, id DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkZakatCalcRow {
            id: r.get(0)?,
            calculated_on: r.get(1)?,
            hijri_date: r.get(2)?,
            currency: r.get(3)?,
            inputs_json: r.get(4)?,
            base_minor: r.get(5)?,
            nisab_minor: r.get(6)?,
            zakat_minor: r.get(7)?,
            reason: r.get(8)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkStockCountRow {
    pub id: String,
    pub counted_on: String,
    pub currency: String,
    pub lines_json: String,
    pub value_before_minor: i64,
    pub value_after_minor: i64,
}

pub fn insert_stock_count(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkStockCountRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_stock_counts (id, household_id, space_id, counted_on, currency, lines_json,
            value_before_minor, value_after_minor, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![
            r.id,
            s.household_id,
            s.space_id,
            r.counted_on,
            r.currency,
            r.lines_json,
            r.value_before_minor,
            r.value_after_minor,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

/// Yangisi birinchi.
pub fn stock_counts(c: &Connection, s: &SpaceScope) -> Result<Vec<KkStockCountRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, counted_on, currency, lines_json, value_before_minor, value_after_minor FROM kk_stock_counts
         WHERE household_id = ?1 AND space_id = ?2 ORDER BY counted_on DESC, created_at DESC, id DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkStockCountRow {
            id: r.get(0)?,
            counted_on: r.get(1)?,
            currency: r.get(2)?,
            lines_json: r.get(3)?,
            value_before_minor: r.get(4)?,
            value_after_minor: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Makondagi eng birinchi yozuv sanasi (tushum, chiqim, harakat, tovar) — hawl taklifi uchun.
pub fn first_activity(c: &Connection, s: &SpaceScope) -> Result<Option<String>, StorageError> {
    Ok(c.query_row(
        "SELECT min(d) FROM (
            SELECT min(occurred_on) AS d FROM incomes WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
            UNION ALL SELECT min(occurred_on) FROM expenses WHERE household_id = ?1 AND space_id = ?2
                AND deleted_at IS NULL
            UNION ALL SELECT min(occurred_on) FROM kk_moves WHERE household_id = ?1 AND space_id = ?2
                AND deleted_at IS NULL
            UNION ALL SELECT min(occurred_on) FROM kk_stock_moves WHERE household_id = ?1 AND space_id = ?2)",
        params![s.household_id, s.space_id],
        |r| r.get(0),
    )?)
}
