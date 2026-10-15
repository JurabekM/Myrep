use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::{opt_bool, SpaceScope};
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AllocationRuleRow {
    pub id: String,
    pub kind: String,
    pub bp: Option<i64>,
    pub amount_minor: Option<i64>,
    pub currency: Option<String>,
    pub progressive: bool,
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &AllocationRuleRow,
    m: &Meta,
) -> Result<(), StorageError> {
    // Bitta faol qoida: eskisi o'chiriladi.
    tx.execute(
        "UPDATE allocation_rules SET active = 0, updated_at = ?3, updated_by_device_id = ?4, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND active = 1 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, m.now, m.device_id],
    )?;
    tx.execute(
        "INSERT INTO allocation_rules (id, household_id, space_id, kind, bp, amount_minor, currency, progressive,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)",
        params![r.id, s.household_id, s.space_id, r.kind, r.bp, r.amount_minor, r.currency,
            i64::from(r.progressive), m.now, m.device_id],
    )?;
    Ok(())
}

pub fn active(c: &Connection, s: &SpaceScope) -> Result<Option<AllocationRuleRow>, StorageError> {
    Ok(c.query_row(
        "SELECT id, kind, bp, amount_minor, currency, progressive FROM allocation_rules
         WHERE household_id = ?1 AND space_id = ?2 AND active = 1 AND deleted_at IS NULL
         ORDER BY created_at DESC LIMIT 1",
        params![s.household_id, s.space_id],
        |r| {
            Ok(AllocationRuleRow {
                id: r.get(0)?,
                kind: r.get(1)?,
                bp: r.get(2)?,
                amount_minor: r.get(3)?,
                currency: r.get(4)?,
                progressive: opt_bool(r.get(5)?),
            })
        },
    )
    .optional()?)
}
