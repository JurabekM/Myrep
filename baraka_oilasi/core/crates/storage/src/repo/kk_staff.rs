//! Kasb-kor (K6): xodim va ta'minotchi kelishuvlari, imzolangan versiyalar, avans va haq to'lovlari,
//! yetkazish va ta'minotchiga to'lovlar.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkAgreementRow {
    pub id: String,
    pub kind: String,
    pub party_name: String,
    pub phone: Option<String>,
    pub phone_consent: bool,
    pub status: String,
    pub currency: String,
    pub terms_json: String,
    pub started_on: String,
    pub ended_on: Option<String>,
    pub opening_balance_minor: i64,
}

pub fn insert_agreement(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkAgreementRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_agreements (id, household_id, space_id, kind, party_name, phone, phone_consent, status,
            currency, terms_json, started_on, ended_on, opening_balance_minor, created_at, updated_at,
            origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?14, ?15, ?15)",
        params![r.id, s.household_id, s.space_id, r.kind, r.party_name, r.phone, r.phone_consent, r.status,
            r.currency, r.terms_json, r.started_on, r.ended_on, r.opening_balance_minor, m.now, m.device_id],
    )?;
    Ok(())
}

/// Tur va valyuta o'zgarmaydi.
pub fn update_agreement(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkAgreementRow,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_agreements SET party_name = ?4, phone = ?5, phone_consent = ?6, status = ?7, terms_json = ?8,
            started_on = ?9, ended_on = ?10, opening_balance_minor = ?11, updated_at = ?12,
            updated_by_device_id = ?13, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, r.id, r.party_name, r.phone, r.phone_consent, r.status, r.terms_json,
            r.started_on, r.ended_on, r.opening_balance_minor, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

/// Faqat imzolanmagan va hodisasiz kelishuv o'chiriladi; aks holda — `NotFound`.
pub fn delete_agreement(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_agreements SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL
           AND NOT EXISTS (SELECT 1 FROM kk_agreement_versions WHERE agreement_id = ?3)
           AND NOT EXISTS (SELECT 1 FROM kk_staff_events WHERE agreement_id = ?3)
           AND NOT EXISTS (SELECT 1 FROM kk_supply_deliveries WHERE agreement_id = ?3)
           AND NOT EXISTS (SELECT 1 FROM kk_supply_payments WHERE agreement_id = ?3)",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn agreements(c: &Connection, s: &SpaceScope) -> Result<Vec<KkAgreementRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, kind, party_name, phone, phone_consent, status, currency, terms_json, started_on, ended_on,
            opening_balance_minor
         FROM kk_agreements WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY status = 'ENDED', party_name COLLATE NOCASE, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkAgreementRow {
            id: r.get(0)?,
            kind: r.get(1)?,
            party_name: r.get(2)?,
            phone: r.get(3)?,
            phone_consent: r.get(4)?,
            status: r.get(5)?,
            currency: r.get(6)?,
            terms_json: r.get(7)?,
            started_on: r.get(8)?,
            ended_on: r.get(9)?,
            opening_balance_minor: r.get(10)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkAgreementVersionRow {
    pub id: String,
    pub agreement_id: String,
    pub seq: i64,
    pub terms_json: String,
    pub terms_hash: String,
    pub template_version: i64,
    pub template_review: String,
    pub effective_from: String,
    pub signed_on: String,
}

pub fn insert_version(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkAgreementVersionRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_agreement_versions (id, household_id, space_id, agreement_id, seq, terms_json, terms_hash,
            template_version, template_review, effective_from, signed_on, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
        params![r.id, s.household_id, s.space_id, r.agreement_id, r.seq, r.terms_json, r.terms_hash,
            r.template_version, r.template_review, r.effective_from, r.signed_on, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn versions(
    c: &Connection,
    s: &SpaceScope,
) -> Result<Vec<KkAgreementVersionRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, agreement_id, seq, terms_json, terms_hash, template_version, template_review, effective_from,
            signed_on
         FROM kk_agreement_versions WHERE household_id = ?1 AND space_id = ?2 ORDER BY agreement_id, seq",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkAgreementVersionRow {
            id: r.get(0)?,
            agreement_id: r.get(1)?,
            seq: r.get(2)?,
            terms_json: r.get(3)?,
            terms_hash: r.get(4)?,
            template_version: r.get(5)?,
            template_review: r.get(6)?,
            effective_from: r.get(7)?,
            signed_on: r.get(8)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkStaffEventRow {
    pub id: String,
    pub agreement_id: String,
    pub kind: String,
    pub occurred_on: String,
    pub amount_minor: i64,
    pub currency: String,
    pub installments: Option<i64>,
    pub start_month: Option<String>,
    pub wallet: String,
    pub expense_id: String,
    pub note: Option<String>,
}

pub fn insert_staff_event(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkStaffEventRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_staff_events (id, household_id, space_id, agreement_id, kind, occurred_on, amount_minor,
            currency, installments, start_month, wallet, expense_id, note, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)",
        params![r.id, s.household_id, s.space_id, r.agreement_id, r.kind, r.occurred_on, r.amount_minor,
            r.currency, r.installments, r.start_month, r.wallet, r.expense_id, r.note, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn staff_events(c: &Connection, s: &SpaceScope) -> Result<Vec<KkStaffEventRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, agreement_id, kind, occurred_on, amount_minor, currency, installments, start_month, wallet,
            expense_id, note
         FROM kk_staff_events WHERE household_id = ?1 AND space_id = ?2
         ORDER BY agreement_id, occurred_on, created_at, id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkStaffEventRow {
            id: r.get(0)?,
            agreement_id: r.get(1)?,
            kind: r.get(2)?,
            occurred_on: r.get(3)?,
            amount_minor: r.get(4)?,
            currency: r.get(5)?,
            installments: r.get(6)?,
            start_month: r.get(7)?,
            wallet: r.get(8)?,
            expense_id: r.get(9)?,
            note: r.get(10)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkDeliveryRow {
    pub id: String,
    pub agreement_id: String,
    pub delivered_on: String,
    pub amount_minor: i64,
    pub currency: String,
    pub due_days: i64,
    pub stock_move_id: Option<String>,
    pub note: Option<String>,
}

pub fn insert_delivery(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkDeliveryRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_supply_deliveries (id, household_id, space_id, agreement_id, delivered_on, amount_minor,
            currency, due_days, stock_move_id, note, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![r.id, s.household_id, s.space_id, r.agreement_id, r.delivered_on, r.amount_minor, r.currency,
            r.due_days, r.stock_move_id, r.note, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn deliveries(c: &Connection, s: &SpaceScope) -> Result<Vec<KkDeliveryRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, agreement_id, delivered_on, amount_minor, currency, due_days, stock_move_id, note
         FROM kk_supply_deliveries WHERE household_id = ?1 AND space_id = ?2
         ORDER BY agreement_id, delivered_on, created_at, id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkDeliveryRow {
            id: r.get(0)?,
            agreement_id: r.get(1)?,
            delivered_on: r.get(2)?,
            amount_minor: r.get(3)?,
            currency: r.get(4)?,
            due_days: r.get(5)?,
            stock_move_id: r.get(6)?,
            note: r.get(7)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkSupplyPaymentRow {
    pub id: String,
    pub agreement_id: String,
    pub paid_on: String,
    pub amount_minor: i64,
    pub currency: String,
    pub wallet: String,
    pub expense_id: Option<String>,
    pub note: Option<String>,
}

pub fn insert_supply_payment(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &KkSupplyPaymentRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_supply_payments (id, household_id, space_id, agreement_id, paid_on, amount_minor, currency,
            wallet, expense_id, note, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![r.id, s.household_id, s.space_id, r.agreement_id, r.paid_on, r.amount_minor, r.currency,
            r.wallet, r.expense_id, r.note, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn supply_payments(
    c: &Connection,
    s: &SpaceScope,
) -> Result<Vec<KkSupplyPaymentRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, agreement_id, paid_on, amount_minor, currency, wallet, expense_id, note
         FROM kk_supply_payments WHERE household_id = ?1 AND space_id = ?2
         ORDER BY agreement_id, paid_on, created_at, id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkSupplyPaymentRow {
            id: r.get(0)?,
            agreement_id: r.get(1)?,
            paid_on: r.get(2)?,
            amount_minor: r.get(3)?,
            currency: r.get(4)?,
            wallet: r.get(5)?,
            expense_id: r.get(6)?,
            note: r.get(7)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Chiqim xodim yoki ta'minotchi hisobiga bog'langanmi (bunday chiqim alohida o'chirilmaydi).
pub fn expense_linked(
    c: &Connection,
    s: &SpaceScope,
    expense_id: &str,
) -> Result<bool, StorageError> {
    let found: Option<i64> = c
        .query_row(
            "SELECT 1 FROM kk_staff_events WHERE household_id = ?1 AND space_id = ?2 AND expense_id = ?3
             UNION ALL
             SELECT 1 FROM kk_supply_payments WHERE household_id = ?1 AND space_id = ?2 AND expense_id = ?3
             LIMIT 1",
            params![s.household_id, s.space_id, expense_id],
            |r| r.get(0),
        )
        .optional()?;
    Ok(found.is_some())
}
