use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AssetRow {
    pub id: String,
    pub asset_type: String,
    pub name: String,
    pub unit: String,
    pub currency: Option<String>,
    pub vault_type: Option<String>,
    pub owner_member_id: Option<String>,
    pub visibility: String,
}

const COLS: &str = "id, type, name, unit, currency, vault_type, owner_member_id, visibility";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<AssetRow> {
    Ok(AssetRow {
        id: r.get(0)?,
        asset_type: r.get(1)?,
        name: r.get(2)?,
        unit: r.get(3)?,
        currency: r.get(4)?,
        vault_type: r.get(5)?,
        owner_member_id: r.get(6)?,
        visibility: r.get(7)?,
    })
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    a: &AssetRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO assets (id, household_id, space_id, type, name, unit, currency, vault_type, owner_member_id,
            visibility, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?11, ?12, ?12)",
        params![a.id, s.household_id, s.space_id, a.asset_type, a.name, a.unit, a.currency, a.vault_type,
            a.owner_member_id, a.visibility, m.now, m.device_id],
    )?;
    Ok(())
}

/// Makonning umumiy (SHARED) jamg'armasi: `vault_type` bo'yicha.
pub fn shared_vault(
    c: &Connection,
    s: &SpaceScope,
    vault_type: &str,
) -> Result<Option<AssetRow>, StorageError> {
    Ok(c.query_row(
        &format!("SELECT {COLS} FROM assets WHERE household_id = ?1 AND space_id = ?2 AND type = 'VAULT'
                  AND vault_type = ?3 AND visibility = 'SHARED' AND deleted_at IS NULL ORDER BY created_at LIMIT 1"),
        params![s.household_id, s.space_id, vault_type],
        map,
    )
    .optional()?)
}

pub fn list(c: &Connection, s: &SpaceScope) -> Result<Vec<AssetRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM assets WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL ORDER BY created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}
