//! U9: byudjet rejimi, qarz to'lovchilari, sotiladigan buyumlar.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BudgetRow {
    pub mode: String,
    pub household_bp: i64,
    pub extra_debt_bp: i64,
    pub savings_bp: i64,
    pub changed_on: String,
}

pub fn budget(c: &Connection, s: &SpaceScope) -> Result<Option<BudgetRow>, StorageError> {
    Ok(c.query_row(
        "SELECT mode, household_bp, extra_debt_bp, savings_bp, changed_on FROM budget_settings
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL",
        params![s.household_id, s.space_id],
        |r| {
            Ok(BudgetRow {
                mode: r.get(0)?,
                household_bp: r.get(1)?,
                extra_debt_bp: r.get(2)?,
                savings_bp: r.get(3)?,
                changed_on: r.get(4)?,
            })
        },
    )
    .optional()?)
}

/// Makonning yagona yozuvini yaratadi yoki yangilaydi.
pub fn upsert_budget(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    b: &BudgetRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO budget_settings (id, household_id, space_id, mode, household_bp, extra_debt_bp, savings_bp,
            changed_on, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)
         ON CONFLICT(space_id) DO UPDATE SET mode = excluded.mode, household_bp = excluded.household_bp,
            extra_debt_bp = excluded.extra_debt_bp, savings_bp = excluded.savings_bp,
            changed_on = excluded.changed_on, updated_at = excluded.updated_at,
            updated_by_device_id = excluded.updated_by_device_id, version = budget_settings.version + 1",
        params![id, s.household_id, s.space_id, b.mode, b.household_bp, b.extra_debt_bp, b.savings_bp,
            b.changed_on, m.now, m.device_id],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ContributorRow {
    pub id: String,
    pub debt_id: String,
    pub name: String,
    pub monthly_share_minor: Option<i64>,
    pub currency: String,
}

pub fn insert_contributor(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    c: &ContributorRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO debt_contributors (id, household_id, space_id, debt_id, name, monthly_share_minor, currency,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?8, ?9, ?9)",
        params![c.id, s.household_id, s.space_id, c.debt_id, c.name, c.monthly_share_minor, c.currency,
            m.now, m.device_id],
    )?;
    Ok(())
}

pub fn contributors(
    c: &Connection,
    s: &SpaceScope,
    debt_id: &str,
) -> Result<Vec<ContributorRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, debt_id, name, monthly_share_minor, currency FROM debt_contributors
         WHERE household_id = ?1 AND space_id = ?2 AND debt_id = ?3 AND deleted_at IS NULL ORDER BY created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, debt_id], |r| {
        Ok(ContributorRow {
            id: r.get(0)?,
            debt_id: r.get(1)?,
            name: r.get(2)?,
            monthly_share_minor: r.get(3)?,
            currency: r.get(4)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ItemRow {
    pub id: String,
    pub title: String,
    pub estimated_minor: i64,
    pub currency: String,
    pub status: String,
    pub sold_minor: Option<i64>,
    pub sold_on: Option<String>,
    pub debt_id: Option<String>,
    pub repayment_id: Option<String>,
}

const ITEM_COLS: &str =
    "id, title, estimated_minor, currency, status, sold_minor, sold_on, debt_id, repayment_id";

fn map_item(r: &rusqlite::Row<'_>) -> rusqlite::Result<ItemRow> {
    Ok(ItemRow {
        id: r.get(0)?,
        title: r.get(1)?,
        estimated_minor: r.get(2)?,
        currency: r.get(3)?,
        status: r.get(4)?,
        sold_minor: r.get(5)?,
        sold_on: r.get(6)?,
        debt_id: r.get(7)?,
        repayment_id: r.get(8)?,
    })
}

pub fn insert_item(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    i: &ItemRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        &format!(
            "INSERT INTO sellable_items ({ITEM_COLS}, household_id, space_id, created_at, updated_at,
                origin_device_id, updated_by_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)"
        ),
        params![i.id, i.title, i.estimated_minor, i.currency, i.status, i.sold_minor, i.sold_on, i.debt_id,
            i.repayment_id, s.household_id, s.space_id, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn items(c: &Connection, s: &SpaceScope) -> Result<Vec<ItemRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {ITEM_COLS} FROM sellable_items WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY status, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_item)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn get_item(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<ItemRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {ITEM_COLS} FROM sellable_items
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_item,
    )
    .optional()?)
}

/// Buyum sotildi: narx, sana va (bo'lsa) qaysi qarzga yo'naltirilgani.
pub fn mark_sold(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    sold: (i64, &str),
    debt: (Option<&str>, Option<&str>),
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE sellable_items SET status = 'SOLD', sold_minor = ?4, sold_on = ?5, debt_id = ?6, repayment_id = ?7,
            updated_at = ?8, updated_by_device_id = ?9, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND status = 'LISTED' AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, sold.0, sold.1, debt.0, debt.1, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}
