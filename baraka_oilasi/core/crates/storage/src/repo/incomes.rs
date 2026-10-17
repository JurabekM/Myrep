use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IncomeRow {
    pub id: String,
    pub member_id: Option<String>,
    pub amount_minor: i64,
    pub currency: String,
    pub source: String,
    pub channel: String,
    pub source_type: Option<String>,
    pub occurred_on: String,
    pub note: Option<String>,
}

const COLS: &str =
    "id, member_id, amount_minor, currency, source, channel, source_type, occurred_on, note";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<IncomeRow> {
    Ok(IncomeRow {
        id: r.get(0)?,
        member_id: r.get(1)?,
        amount_minor: r.get(2)?,
        currency: r.get(3)?,
        source: r.get(4)?,
        channel: r.get(5)?,
        source_type: r.get(6)?,
        occurred_on: r.get(7)?,
        note: r.get(8)?,
    })
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    i: &IncomeRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO incomes (id, household_id, space_id, member_id, amount_minor, currency, source, channel,
            source_type, occurred_on, note, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)",
        params![i.id, s.household_id, s.space_id, i.member_id, i.amount_minor, i.currency, i.source, i.channel,
            i.source_type, i.occurred_on, i.note, m.now, m.device_id],
    )?;
    Ok(())
}

/// Makonlararo o'tkazmaning qabul qiluvchi tomoni (`BARAKA_OILASI.md` 4.6): umumiy `transfer_id`.
pub fn insert_with_transfer(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    i: &IncomeRow,
    transfer_id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    insert(tx, s, i, m)?;
    tx.execute(
        "UPDATE incomes SET transfer_id = ?3 WHERE household_id = ?1 AND id = ?2",
        params![s.household_id, i.id, transfer_id],
    )?;
    Ok(())
}

pub fn get(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<IncomeRow>, StorageError> {
    Ok(c.query_row(
        &format!("SELECT {COLS} FROM incomes WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"),
        params![s.household_id, s.space_id, id],
        map,
    )
    .optional()?)
}

/// `[from, to)` oralig'idagi daromadlar (lokal sanalar).
pub fn list_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<IncomeRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM incomes WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Oxirgi kiritilgan daromad (manba va kanalni eslab qolish uchun).
pub fn last(c: &Connection, s: &SpaceScope) -> Result<Option<IncomeRow>, StorageError> {
    Ok(c.query_row(
        &format!("SELECT {COLS} FROM incomes WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
                  ORDER BY created_at DESC, id DESC LIMIT 1"),
        params![s.household_id, s.space_id],
        map,
    )
    .optional()?)
}

/// Eng so'nggi daromad sanasi (kiritilgan vaqti emas, `occurred_on`).
pub fn last_occurred_on(c: &Connection, s: &SpaceScope) -> Result<Option<String>, StorageError> {
    Ok(c.query_row(
        "SELECT MAX(occurred_on) FROM incomes WHERE household_id = ?1 AND space_id = ?2
            AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| r.get::<_, Option<String>>(0),
    )?)
}
