use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::{opt_bool, SpaceScope};
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CategoryRow {
    pub id: String,
    pub name_key: String,
    pub custom_name: Option<String>,
    pub default_necessity: Option<String>,
    pub is_system: bool,
    pub sort_order: i64,
    pub version: i64,
}

const COLS: &str = "id, name_key, custom_name, default_necessity, is_system, sort_order, version";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<CategoryRow> {
    Ok(CategoryRow {
        id: r.get(0)?,
        name_key: r.get(1)?,
        custom_name: r.get(2)?,
        default_necessity: r.get(3)?,
        is_system: opt_bool(r.get(4)?),
        sort_order: r.get(5)?,
        version: r.get(6)?,
    })
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    c: &CategoryRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO categories (id, household_id, space_id, name_key, custom_name, default_necessity, is_system,
            sort_order, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)",
        params![c.id, s.household_id, s.space_id, c.name_key, c.custom_name, c.default_necessity,
            i64::from(c.is_system), c.sort_order, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn list(c: &Connection, s: &SpaceScope) -> Result<Vec<CategoryRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM categories WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY sort_order, name_key"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn get(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<CategoryRow>, StorageError> {
    Ok(c.query_row(
        &format!("SELECT {COLS} FROM categories WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"),
        params![s.household_id, s.space_id, id],
        map,
    )
    .optional()?)
}

pub fn rename(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    custom_name: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE categories SET custom_name = ?4, updated_at = ?5, updated_by_device_id = ?6, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, custom_name, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn set_default_necessity(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    necessity: Option<&str>,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE categories SET default_necessity = ?4, updated_at = ?5, updated_by_device_id = ?6, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, necessity, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn soft_delete(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE categories SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}
