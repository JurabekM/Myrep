//! Kasb-kor (K5): tovarlar va tovar harakatlari.
use rusqlite::{params, Connection, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkItemRow {
    pub id: String,
    pub name: String,
    pub unit: String,
    pub method: String,
    pub currency: String,
    pub sale_price_minor: Option<i64>,
    pub replacement_price_minor: Option<i64>,
    pub min_qty: Option<i64>,
    pub frozen_days: i64,
    pub note: Option<String>,
}

pub fn insert_item(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkItemRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_items (id, household_id, space_id, name, unit, method, currency, sale_price_minor,
            replacement_price_minor, min_qty, frozen_days, note, created_at, updated_at, origin_device_id,
            updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?13, ?14, ?14)",
        params![r.id, s.household_id, s.space_id, r.name, r.unit, r.method, r.currency, r.sale_price_minor,
            r.replacement_price_minor, r.min_qty, r.frozen_days, r.note, m.now, m.device_id],
    )?;
    Ok(())
}

/// Birlik va valyuta o'zgarmaydi (harakatlar shularda yozilgan).
pub fn update_item(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkItemRow,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_items SET name = ?4, method = ?5, sale_price_minor = ?6, replacement_price_minor = ?7,
            min_qty = ?8, frozen_days = ?9, note = ?10, updated_at = ?11, updated_by_device_id = ?12,
            version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, r.id, r.name, r.method, r.sale_price_minor, r.replacement_price_minor,
            r.min_qty, r.frozen_days, r.note, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn items(c: &Connection, s: &SpaceScope) -> Result<Vec<KkItemRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, name, unit, method, currency, sale_price_minor, replacement_price_minor, min_qty, frozen_days, note
         FROM kk_items WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY name COLLATE NOCASE, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkItemRow {
            id: r.get(0)?,
            name: r.get(1)?,
            unit: r.get(2)?,
            method: r.get(3)?,
            currency: r.get(4)?,
            sale_price_minor: r.get(5)?,
            replacement_price_minor: r.get(6)?,
            min_qty: r.get(7)?,
            frozen_days: r.get(8)?,
            note: r.get(9)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkStockMoveRow {
    pub id: String,
    pub item_id: String,
    pub kind: String,
    pub occurred_on: String,
    pub qty: i64,
    pub amount_minor: Option<i64>,
    pub wallet: Option<String>,
    pub income_id: Option<String>,
    pub reason: Option<String>,
}

pub fn insert_move(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkStockMoveRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_stock_moves (id, household_id, space_id, item_id, kind, occurred_on, qty, amount_minor,
            wallet, income_id, reason, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
        params![r.id, s.household_id, s.space_id, r.item_id, r.kind, r.occurred_on, r.qty, r.amount_minor,
            r.wallet, r.income_id, r.reason, m.now, m.device_id],
    )?;
    Ok(())
}

/// Makondagi barcha tovar harakatlari: tovar, sana va yozilish tartibida (tannarx shu tartibda hisoblanadi).
pub fn moves(c: &Connection, s: &SpaceScope) -> Result<Vec<KkStockMoveRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, item_id, kind, occurred_on, qty, amount_minor, wallet, income_id, reason
         FROM kk_stock_moves WHERE household_id = ?1 AND space_id = ?2 ORDER BY item_id, occurred_on, created_at, id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkStockMoveRow {
            id: r.get(0)?,
            item_id: r.get(1)?,
            kind: r.get(2)?,
            occurred_on: r.get(3)?,
            qty: r.get(4)?,
            amount_minor: r.get(5)?,
            wallet: r.get(6)?,
            income_id: r.get(7)?,
            reason: r.get(8)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Faqat harakatsiz tovar o'chiriladi; harakati bor yoki topilmasa — `NotFound`.
pub fn delete_item(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_items SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL
           AND NOT EXISTS (SELECT 1 FROM kk_stock_moves WHERE item_id = ?3)",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}
