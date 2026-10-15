//! Qarzlar (U8): olingan qarzlar, bergan qarzlar, to'lov rejasi qatorlari, to'lovlar, maqsadlar.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::{opt_bool, SpaceScope};
use crate::{Meta, StorageError};

/// Reja va to'lovlar kimga tegishli.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Owner {
    Debt,
    Receivable,
}

impl Owner {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Debt => "DEBT",
            Self::Receivable => "RECEIVABLE",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DebtRow {
    pub id: String,
    pub creditor_type: String,
    pub creditor: String,
    pub reason: Option<String>,
    pub currency: String,
    pub principal_minor: i64,
    pub original_principal_minor: i64,
    pub paid_before_minor: i64,
    pub plan_kind: String,
    pub annual_bp: i64,
    pub markup_minor: i64,
    pub months: u32,
    pub started_on: String,
    pub early_repayment_terms: Option<String>,
    pub priority: Option<i64>,
    pub borrow_check_json: Option<String>,
    pub agreement_id: Option<String>,
    pub status: String,
}

const DEBT_COLS: &str = "id, creditor_type, creditor, reason, currency, principal_minor,
    original_principal_minor, paid_before_minor, plan_kind, annual_bp, markup_minor, months,
    started_on, early_repayment_terms, priority, borrow_check_json, agreement_id, status";

fn map_debt(r: &rusqlite::Row<'_>) -> rusqlite::Result<DebtRow> {
    Ok(DebtRow {
        id: r.get(0)?,
        creditor_type: r.get(1)?,
        creditor: r.get(2)?,
        reason: r.get(3)?,
        currency: r.get(4)?,
        principal_minor: r.get(5)?,
        original_principal_minor: r.get(6)?,
        paid_before_minor: r.get(7)?,
        plan_kind: r.get(8)?,
        annual_bp: r.get(9)?,
        markup_minor: r.get(10)?,
        months: r.get(11)?,
        started_on: r.get(12)?,
        early_repayment_terms: r.get(13)?,
        priority: r.get(14)?,
        borrow_check_json: r.get(15)?,
        agreement_id: r.get(16)?,
        status: r.get(17)?,
    })
}

pub fn insert_debt(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    d: &DebtRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        &format!(
            "INSERT INTO debts ({DEBT_COLS}, household_id, space_id, created_at, updated_at,
                origin_device_id, updated_by_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18,
                ?19, ?20, ?21, ?21, ?22, ?22)"
        ),
        params![d.id, d.creditor_type, d.creditor, d.reason, d.currency, d.principal_minor,
            d.original_principal_minor, d.paid_before_minor, d.plan_kind, d.annual_bp, d.markup_minor,
            d.months, d.started_on, d.early_repayment_terms, d.priority, d.borrow_check_json,
            d.agreement_id, d.status, s.household_id, s.space_id, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn list_debts(c: &Connection, s: &SpaceScope) -> Result<Vec<DebtRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {DEBT_COLS} FROM debts WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY status, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_debt)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn get_debt(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<DebtRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {DEBT_COLS} FROM debts
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_debt,
    )
    .optional()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReceivableRow {
    pub id: String,
    pub debtor: String,
    pub currency: String,
    pub amount_minor: i64,
    pub lent_on: String,
    pub note: Option<String>,
    pub agreement_id: Option<String>,
    pub status: String,
}

const REC_COLS: &str = "id, debtor, currency, amount_minor, lent_on, note, agreement_id, status";

fn map_rec(r: &rusqlite::Row<'_>) -> rusqlite::Result<ReceivableRow> {
    Ok(ReceivableRow {
        id: r.get(0)?,
        debtor: r.get(1)?,
        currency: r.get(2)?,
        amount_minor: r.get(3)?,
        lent_on: r.get(4)?,
        note: r.get(5)?,
        agreement_id: r.get(6)?,
        status: r.get(7)?,
    })
}

pub fn insert_receivable(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    v: &ReceivableRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        &format!(
            "INSERT INTO receivables ({REC_COLS}, household_id, space_id, created_at, updated_at,
                origin_device_id, updated_by_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?11, ?12, ?12)"
        ),
        params![
            v.id,
            v.debtor,
            v.currency,
            v.amount_minor,
            v.lent_on,
            v.note,
            v.agreement_id,
            v.status,
            s.household_id,
            s.space_id,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn list_receivables(
    c: &Connection,
    s: &SpaceScope,
) -> Result<Vec<ReceivableRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {REC_COLS} FROM receivables WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY status, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_rec)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn get_receivable(
    c: &Connection,
    s: &SpaceScope,
    id: &str,
) -> Result<Option<ReceivableRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {REC_COLS} FROM receivables
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_rec,
    )
    .optional()?)
}

/// Qarz yoki bergan qarz holatini o'zgartiradi (`ACTIVE` → `CLOSED`).
pub fn set_status(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    owner: Owner,
    id: &str,
    status: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let table = match owner {
        Owner::Debt => "debts",
        Owner::Receivable => "receivables",
    };
    let n = tx.execute(
        &format!(
            "UPDATE {table} SET status = ?4, updated_at = ?5, updated_by_device_id = ?6, version = version + 1
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id, status, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlanLineRow {
    pub id: String,
    pub due_on: String,
    pub amount_minor: i64,
    pub currency: String,
}

pub fn insert_plan(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    owner: Owner,
    owner_id: &str,
    lines: &[PlanLineRow],
    m: &Meta,
) -> Result<(), StorageError> {
    for (seq, l) in (1i64..).zip(lines) {
        tx.execute(
            "INSERT INTO repayment_plan_lines (id, household_id, space_id, owner_type, owner_id, seq, due_on,
                amount_minor, currency, created_at, updated_at, origin_device_id, updated_by_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?10, ?11, ?11)",
            params![l.id, s.household_id, s.space_id, owner.as_str(), owner_id, seq, l.due_on,
                l.amount_minor, l.currency, m.now, m.device_id],
        )?;
    }
    Ok(())
}

pub fn plan(
    c: &Connection,
    s: &SpaceScope,
    owner: Owner,
    owner_id: &str,
) -> Result<Vec<PlanLineRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, due_on, amount_minor, currency FROM repayment_plan_lines
         WHERE household_id = ?1 AND space_id = ?2 AND owner_type = ?3 AND owner_id = ?4 AND deleted_at IS NULL
         ORDER BY seq",
    )?;
    let rows = st.query_map(
        params![s.household_id, s.space_id, owner.as_str(), owner_id],
        |r| {
            Ok(PlanLineRow {
                id: r.get(0)?,
                due_on: r.get(1)?,
                amount_minor: r.get(2)?,
                currency: r.get(3)?,
            })
        },
    )?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RepaymentRow {
    pub id: String,
    pub amount_minor: i64,
    pub currency: String,
    pub paid_on: String,
    pub is_prepayment: bool,
    pub note: Option<String>,
    pub journal_entry_id: Option<String>,
}

pub fn insert_repayment(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    owner: Owner,
    owner_id: &str,
    p: &RepaymentRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO repayments (id, household_id, space_id, owner_type, owner_id, amount_minor, currency,
            paid_on, is_prepayment, note, journal_entry_id, created_at, updated_at, origin_device_id,
            updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)",
        params![p.id, s.household_id, s.space_id, owner.as_str(), owner_id, p.amount_minor, p.currency,
            p.paid_on, i64::from(p.is_prepayment), p.note, p.journal_entry_id, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn repayments(
    c: &Connection,
    s: &SpaceScope,
    owner: Owner,
    owner_id: &str,
) -> Result<Vec<RepaymentRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, amount_minor, currency, paid_on, is_prepayment, note, journal_entry_id FROM repayments
         WHERE household_id = ?1 AND space_id = ?2 AND owner_type = ?3 AND owner_id = ?4 AND deleted_at IS NULL
         ORDER BY paid_on, created_at",
    )?;
    let rows = st.query_map(
        params![s.household_id, s.space_id, owner.as_str(), owner_id],
        |r| {
            Ok(RepaymentRow {
                id: r.get(0)?,
                amount_minor: r.get(1)?,
                currency: r.get(2)?,
                paid_on: r.get(3)?,
                is_prepayment: opt_bool(r.get(4)?),
                note: r.get(5)?,
                journal_entry_id: r.get(6)?,
            })
        },
    )?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GoalRow {
    pub id: String,
    pub title: String,
    pub target_minor: i64,
    pub currency: String,
}

pub fn insert_goal(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    g: &GoalRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO goals (id, household_id, space_id, title, target_minor, currency, created_at, updated_at,
            origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?7, ?8, ?8)",
        params![g.id, s.household_id, s.space_id, g.title, g.target_minor, g.currency, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn list_goals(c: &Connection, s: &SpaceScope) -> Result<Vec<GoalRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, title, target_minor, currency FROM goals
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL ORDER BY created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(GoalRow {
            id: r.get(0)?,
            title: r.get(1)?,
            target_minor: r.get(2)?,
            currency: r.get(3)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn delete_goal(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE goals SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}
