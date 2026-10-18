//! Qurilma rollari (K8, ADR-0003): `device_access` (sinxronlanadi, faqat egasi yozadi),
//! `local_device_role` (shu qurilma rolli ulash faylidan qo'shilgan bo'lsa), ulash taklifidagi rol
//! (`sync_exports.role`) va sotuvchi smenalari.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DeviceAccessRow {
    pub device_id: String,
    pub role: String,
    pub space_id: String,
    pub revoked_at: Option<String>,
}

pub fn device_access(
    c: &Connection,
    household_id: &str,
) -> Result<Vec<DeviceAccessRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT device_id, role, space_id, revoked_at FROM device_access
         WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at",
    )?;
    let rows = st.query_map([household_id], |r| {
        Ok(DeviceAccessRow {
            device_id: r.get(0)?,
            role: r.get(1)?,
            space_id: r.get(2)?,
            revoked_at: r.get(3)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn access_of(
    c: &Connection,
    household_id: &str,
    device_id: &str,
) -> Result<Option<DeviceAccessRow>, StorageError> {
    Ok(device_access(c, household_id)?
        .into_iter()
        .find(|a| a.device_id == device_id))
}

/// Egasi qurilmani rolga bog'laydi (qurilma ulash faylini tasdiqlaganda).
pub fn insert_access(
    tx: &Transaction<'_>,
    household_id: &str,
    a: &DeviceAccessRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO device_access (id, household_id, device_id, role, space_id, revoked_at, created_at,
            updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?1, ?3, ?4, ?5, ?6, ?6, ?7, ?7)",
        params![a.device_id, household_id, a.role, a.space_id, a.revoked_at, m.now, m.device_id],
    )?;
    Ok(())
}

/// Rolni bekor qilish: qurilmaga eksport ham, undan import ham to'xtaydi.
pub fn revoke_access(
    tx: &Transaction<'_>,
    household_id: &str,
    device_id: &str,
    m: &Meta,
) -> Result<bool, StorageError> {
    let n = tx.execute(
        "UPDATE device_access SET revoked_at = ?3, updated_at = ?3, updated_by_device_id = ?4,
            version = version + 1
         WHERE household_id = ?1 AND device_id = ?2 AND revoked_at IS NULL",
        params![household_id, device_id, m.now, m.device_id],
    )?;
    Ok(n == 1)
}

/// Shu qurilmaning ulash faylidagi roli: (rol, makon).
pub fn local_role(
    c: &Connection,
    household_id: &str,
) -> Result<Option<(String, String)>, StorageError> {
    Ok(c.query_row(
        "SELECT role, space_id FROM local_device_role WHERE household_id = ?1",
        [household_id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )
    .optional()?)
}

pub fn set_local_role(
    tx: &Transaction<'_>,
    household_id: &str,
    role: &str,
    space_id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO local_device_role (household_id, role, space_id, created_at) VALUES (?1, ?2, ?3, ?4)",
        params![household_id, role, space_id, m.now],
    )?;
    Ok(())
}

/// Ulash taklifiga rol yozish (eksport yozilgan tranzaksiyada).
pub fn set_export_role(
    tx: &Transaction<'_>,
    export_id: &str,
    role: &str,
    space_id: &str,
) -> Result<(), StorageError> {
    tx.execute(
        "UPDATE sync_exports SET role = ?2, role_space_id = ?3 WHERE export_id = ?1 AND mode = 'PAIRING'",
        params![export_id, role, space_id],
    )?;
    Ok(())
}

/// Rolli ulash taklifi: (rol, makon). Taklif boshqa qurilmaga bog'langan bo'lsa — `None`.
pub fn pairing_role(
    c: &Connection,
    household_id: &str,
    export_id: &str,
    peer_device_id: &str,
) -> Result<Option<(String, String)>, StorageError> {
    Ok(c.query_row(
        "SELECT role, role_space_id FROM sync_exports
         WHERE household_id = ?1 AND export_id = ?2 AND mode = 'PAIRING' AND role IS NOT NULL
           AND (peer_device_id IS NULL OR peer_device_id = ?3)",
        params![household_id, export_id, peer_device_id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )
    .optional()?)
}

// ---- sotuvchi smenasi ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkShiftRow {
    pub id: String,
    pub device_id: String,
    pub day: String,
    pub currency: String,
    pub opening_minor: i64,
    pub cash_sales_minor: i64,
    pub credit_payments_minor: i64,
    pub card_in_minor: i64,
    pub expected_minor: i64,
    pub counted_minor: i64,
    pub difference_minor: i64,
    pub reason: Option<String>,
    pub handed_over_minor: i64,
    pub note: Option<String>,
    pub closed_at: String,
}

pub fn insert_shift(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkShiftRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_shifts (id, household_id, space_id, device_id, day, currency, opening_minor,
            cash_sales_minor, credit_payments_minor, card_in_minor, expected_minor, counted_minor,
            difference_minor, reason, handed_over_minor, note, closed_at, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19)",
        params![r.id, s.household_id, s.space_id, r.device_id, r.day, r.currency, r.opening_minor,
            r.cash_sales_minor, r.credit_payments_minor, r.card_in_minor, r.expected_minor, r.counted_minor,
            r.difference_minor, r.reason, r.handed_over_minor, r.note, r.closed_at, m.now, m.device_id],
    )?;
    Ok(())
}

/// Smenalar, yangisi birinchi; `device` berilsa — faqat shu qurilmaniki.
pub fn shifts(
    c: &Connection,
    s: &SpaceScope,
    device: Option<&str>,
) -> Result<Vec<KkShiftRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, device_id, day, currency, opening_minor, cash_sales_minor, credit_payments_minor,
            card_in_minor, expected_minor, counted_minor, difference_minor, reason, handed_over_minor, note,
            closed_at
         FROM kk_shifts WHERE household_id = ?1 AND space_id = ?2 AND (?3 IS NULL OR device_id = ?3)
         ORDER BY day DESC, closed_at DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, device], |r| {
        Ok(KkShiftRow {
            id: r.get(0)?,
            device_id: r.get(1)?,
            day: r.get(2)?,
            currency: r.get(3)?,
            opening_minor: r.get(4)?,
            cash_sales_minor: r.get(5)?,
            credit_payments_minor: r.get(6)?,
            card_in_minor: r.get(7)?,
            expected_minor: r.get(8)?,
            counted_minor: r.get(9)?,
            difference_minor: r.get(10)?,
            reason: r.get(11)?,
            handed_over_minor: r.get(12)?,
            note: r.get(13)?,
            closed_at: r.get(14)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Shu qurilma shu kuni yozgan tushumlar: savdo yoki nasiya to'lovi, tovar sotilgan bo'lsa — miqdor.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OwnIncomeRow {
    pub id: String,
    pub amount_minor: i64,
    pub channel: String,
    pub source: String,
    pub is_payment: bool,
    pub qty: Option<i64>,
    pub unit: Option<String>,
}

pub fn own_day_incomes(
    c: &Connection,
    s: &SpaceScope,
    device_id: &str,
    day: &str,
) -> Result<Vec<OwnIncomeRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT i.id, i.amount_minor, i.channel, i.source,
            EXISTS (SELECT 1 FROM kk_credit_events e WHERE e.income_id = i.id),
            m.qty, it.unit
         FROM incomes i
         LEFT JOIN kk_stock_moves m ON m.income_id = i.id
         LEFT JOIN kk_items it ON it.id = m.item_id
         WHERE i.household_id = ?1 AND i.space_id = ?2 AND i.origin_device_id = ?3 AND i.occurred_on = ?4
           AND i.deleted_at IS NULL
         ORDER BY i.created_at, i.rowid",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, device_id, day], |r| {
        Ok(OwnIncomeRow {
            id: r.get(0)?,
            amount_minor: r.get(1)?,
            channel: r.get(2)?,
            source: r.get(3)?,
            is_payment: r.get(4)?,
            qty: r.get(5)?,
            unit: r.get(6)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
