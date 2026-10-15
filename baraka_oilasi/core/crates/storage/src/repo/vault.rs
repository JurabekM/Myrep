use rusqlite::{params, Connection, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VaultTxRow {
    pub id: String,
    pub asset_id: String,
    pub amount_minor: i64,
    pub currency: String,
    pub reason: String,
    pub income_id: Option<String>,
    pub note: Option<String>,
    pub occurred_on: String,
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    v: &VaultTxRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO vault_transactions (id, household_id, space_id, asset_id, amount_minor, currency, reason,
            income_id, note, occurred_on, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?11, ?12, ?12)",
        params![v.id, s.household_id, s.space_id, v.asset_id, v.amount_minor, v.currency, v.reason,
            v.income_id, v.note, v.occurred_on, m.now, m.device_id],
    )?;
    Ok(())
}

/// Jamg'arma qoldig'i (minor birlikda). Yig'indi i64 dan oshsa — xato.
pub fn balance(c: &Connection, s: &SpaceScope, asset_id: &str) -> Result<i64, StorageError> {
    let mut st = c.prepare(
        "SELECT amount_minor FROM vault_transactions
         WHERE household_id = ?1 AND space_id = ?2 AND asset_id = ?3 AND deleted_at IS NULL",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, asset_id], |r| {
        r.get::<_, i64>(0)
    })?;
    let mut total: i64 = 0;
    for v in rows {
        total = total.checked_add(v?).ok_or(StorageError::CorruptRow)?;
    }
    Ok(total)
}

/// Odat ko'rsatkichi uchun: jamg'armaga qo'shilgan (musbat) yozuvlar sanalari.
pub fn deposit_dates(
    c: &Connection,
    s: &SpaceScope,
    asset_id: &str,
) -> Result<Vec<String>, StorageError> {
    let mut st = c.prepare(
        "SELECT DISTINCT occurred_on FROM vault_transactions
         WHERE household_id = ?1 AND space_id = ?2 AND asset_id = ?3 AND deleted_at IS NULL
         AND amount_minor > 0 AND reason <> 'INITIAL' ORDER BY occurred_on",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, asset_id], |r| {
        r.get::<_, String>(0)
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn list(
    c: &Connection,
    s: &SpaceScope,
    asset_id: &str,
) -> Result<Vec<VaultTxRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, asset_id, amount_minor, currency, reason, income_id, note, occurred_on FROM vault_transactions
         WHERE household_id = ?1 AND space_id = ?2 AND asset_id = ?3 AND deleted_at IS NULL
         ORDER BY occurred_on DESC, created_at DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, asset_id], |r| {
        Ok(VaultTxRow {
            id: r.get(0)?,
            asset_id: r.get(1)?,
            amount_minor: r.get(2)?,
            currency: r.get(3)?,
            reason: r.get(4)?,
            income_id: r.get(5)?,
            note: r.get(6)?,
            occurred_on: r.get(7)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
