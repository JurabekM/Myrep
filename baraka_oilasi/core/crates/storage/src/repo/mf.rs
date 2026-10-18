//! Musofir (M1): makon sozlamalari (ish valyutasi, o'z ulushi, qaytish maqsadi), kurslar va pul
//! harakatlari. Maosh va xarajat — `incomes` / `expenses` (makon bo'yicha).
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfSettingsRow {
    pub country: Option<String>,
    pub work_currency: String,
    pub share_bp: i64,
    pub target_minor: Option<i64>,
    pub target_currency: Option<String>,
    pub return_on: Option<String>,
}

pub fn settings(c: &Connection, s: &SpaceScope) -> Result<Option<MfSettingsRow>, StorageError> {
    Ok(c.query_row(
        "SELECT country, work_currency, share_bp, target_minor, target_currency, return_on FROM mf_settings
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(MfSettingsRow {
                country: r.get(0)?,
                work_currency: r.get(1)?,
                share_bp: r.get(2)?,
                target_minor: r.get(3)?,
                target_currency: r.get(4)?,
                return_on: r.get(5)?,
            })
        },
    )
    .optional()?)
}

/// Yangi makon uchun `id` bilan yaratadi, mavjud bo'lsa yangilaydi.
pub fn upsert_settings(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    row: &MfSettingsRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_settings (id, household_id, space_id, country, work_currency, share_bp, target_minor,
            target_currency, return_on, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?10, ?11, ?11)
         ON CONFLICT (space_id) DO UPDATE SET country = excluded.country,
            work_currency = excluded.work_currency, share_bp = excluded.share_bp,
            target_minor = excluded.target_minor, target_currency = excluded.target_currency,
            return_on = excluded.return_on, updated_at = excluded.updated_at,
            updated_by_device_id = excluded.updated_by_device_id, version = mf_settings.version + 1",
        params![id, s.household_id, s.space_id, row.country, row.work_currency, row.share_bp,
            row.target_minor, row.target_currency, row.return_on, m.now, m.device_id],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfRateRow {
    pub id: String,
    pub rate_on: String,
    pub from_currency: String,
    pub to_currency: String,
    pub rate_num: i64,
    pub rate_den: i64,
    pub source: Option<String>,
}

pub fn insert_rate(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &MfRateRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_rates (id, household_id, space_id, rate_on, from_currency, to_currency, rate_num,
            rate_den, source, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        params![row.id, s.household_id, s.space_id, row.rate_on, row.from_currency, row.to_currency,
            row.rate_num, row.rate_den, row.source, m.now, m.device_id],
    )?;
    Ok(())
}

/// `on` sanasigacha (shu kun ham) amaldagi kurs: eng so'nggi sana, bir sanada — oxirgi kiritilgani.
pub fn rate_on(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
    on: &str,
) -> Result<Option<MfRateRow>, StorageError> {
    Ok(c.query_row(
        "SELECT id, rate_on, from_currency, to_currency, rate_num, rate_den, source FROM mf_rates
         WHERE household_id = ?1 AND space_id = ?2 AND from_currency = ?3 AND to_currency = ?4
            AND rate_on <= ?5
         ORDER BY rate_on DESC, created_at DESC, id DESC LIMIT 1",
        params![s.household_id, s.space_id, from, to, on],
        |r| {
            Ok(MfRateRow {
                id: r.get(0)?,
                rate_on: r.get(1)?,
                from_currency: r.get(2)?,
                to_currency: r.get(3)?,
                rate_num: r.get(4)?,
                rate_den: r.get(5)?,
                source: r.get(6)?,
            })
        },
    )
    .optional()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfMoveRow {
    pub id: String,
    pub kind: String,
    pub amount_minor: i64,
    pub currency: String,
    pub fee_minor: i64,
    pub received_minor: Option<i64>,
    pub received_currency: Option<String>,
    pub occurred_on: String,
    pub note: Option<String>,
}

const COLS: &str = "id, kind, amount_minor, currency, fee_minor, received_minor, received_currency,
    occurred_on, note";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<MfMoveRow> {
    Ok(MfMoveRow {
        id: r.get(0)?,
        kind: r.get(1)?,
        amount_minor: r.get(2)?,
        currency: r.get(3)?,
        fee_minor: r.get(4)?,
        received_minor: r.get(5)?,
        received_currency: r.get(6)?,
        occurred_on: r.get(7)?,
        note: r.get(8)?,
    })
}

pub fn insert_move(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &MfMoveRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_moves (id, household_id, space_id, kind, amount_minor, currency, fee_minor,
            received_minor, received_currency, occurred_on, note, created_at, updated_at, origin_device_id,
            updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)",
        params![row.id, s.household_id, s.space_id, row.kind, row.amount_minor, row.currency,
            row.fee_minor, row.received_minor, row.received_currency, row.occurred_on, row.note, m.now,
            m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi harakatlar (lokal sanalar).
pub fn moves_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<MfMoveRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM mf_moves WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Makonda istalgan yozuv bormi (maosh, xarajat yoki harakat).
pub fn has_records(c: &Connection, s: &SpaceScope) -> Result<bool, StorageError> {
    has_records_other_than(c, s, "")
}

/// Makonda boshqa valyutadagi yozuv bormi (ish valyutasini o'zgartirish taqiqi uchun).
pub fn has_records_other_than(
    c: &Connection,
    s: &SpaceScope,
    currency: &str,
) -> Result<bool, StorageError> {
    let n: i64 = c.query_row(
        "SELECT (SELECT COUNT(*) FROM incomes WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
                    AND currency <> ?3)
              + (SELECT COUNT(*) FROM expenses WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
                    AND currency <> ?3)
              + (SELECT COUNT(*) FROM mf_moves WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
                    AND currency <> ?3)",
        params![s.household_id, s.space_id, currency],
        |r| r.get(0),
    )?;
    Ok(n > 0)
}
