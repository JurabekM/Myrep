//! Kasb-kor (K1): egasi maoshi sozlamasi va egasi/hamyon harakatlari. Tushum va chiqim —
//! `incomes` / `expenses` (makon bo'yicha).
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkSettingsRow {
    pub owner_salary_minor: i64,
    pub currency: String,
}

pub fn settings(c: &Connection, s: &SpaceScope) -> Result<Option<KkSettingsRow>, StorageError> {
    Ok(c.query_row(
        "SELECT owner_salary_minor, currency FROM kk_settings
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(KkSettingsRow {
                owner_salary_minor: r.get(0)?,
                currency: r.get(1)?,
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
    row: &KkSettingsRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_settings (id, household_id, space_id, owner_salary_minor, currency, created_at,
            updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?6, ?7, ?7)
         ON CONFLICT (space_id) DO UPDATE SET owner_salary_minor = excluded.owner_salary_minor,
            currency = excluded.currency, updated_at = excluded.updated_at,
            updated_by_device_id = excluded.updated_by_device_id, version = kk_settings.version + 1",
        params![id, s.household_id, s.space_id, row.owner_salary_minor, row.currency, m.now, m.device_id],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkMoveRow {
    pub id: String,
    pub kind: String,
    pub wallet: String,
    pub to_wallet: Option<String>,
    pub amount_minor: i64,
    pub currency: String,
    pub occurred_on: String,
    pub note: Option<String>,
    pub transfer_id: Option<String>,
}

const COLS: &str =
    "id, kind, wallet, to_wallet, amount_minor, currency, occurred_on, note, transfer_id";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<KkMoveRow> {
    Ok(KkMoveRow {
        id: r.get(0)?,
        kind: r.get(1)?,
        wallet: r.get(2)?,
        to_wallet: r.get(3)?,
        amount_minor: r.get(4)?,
        currency: r.get(5)?,
        occurred_on: r.get(6)?,
        note: r.get(7)?,
        transfer_id: r.get(8)?,
    })
}

pub fn insert_move(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    row: &KkMoveRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_moves (id, household_id, space_id, kind, wallet, to_wallet, amount_minor, currency,
            occurred_on, note, transfer_id, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)",
        params![row.id, s.household_id, s.space_id, row.kind, row.wallet, row.to_wallet, row.amount_minor,
            row.currency, row.occurred_on, row.note, row.transfer_id, m.now, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi harakatlar (lokal sanalar).
pub fn moves_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<KkMoveRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM kk_moves WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}
