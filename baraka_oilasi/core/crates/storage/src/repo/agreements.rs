use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AgreementRow {
    pub id: String,
    pub agreement_type: String,
    pub status: String,
    pub title: String,
    pub keeper_device_id: String,
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    a: &AgreementRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO agreements (id, household_id, space_id, type, status, title, keeper_device_id,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?8, ?9, ?9)",
        params![
            a.id,
            s.household_id,
            s.space_id,
            a.agreement_type,
            a.status,
            a.title,
            a.keeper_device_id,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn get(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<AgreementRow>, StorageError> {
    Ok(c.query_row(
        "SELECT id, type, status, title, keeper_device_id FROM agreements
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id],
        |r| {
            Ok(AgreementRow {
                id: r.get(0)?,
                agreement_type: r.get(1)?,
                status: r.get(2)?,
                title: r.get(3)?,
                keeper_device_id: r.get(4)?,
            })
        },
    )
    .optional()?)
}
