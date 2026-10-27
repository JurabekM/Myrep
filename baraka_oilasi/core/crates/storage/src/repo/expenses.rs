use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::{opt_bool, SpaceScope};
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExpenseRow {
    pub id: String,
    pub category_id: String,
    pub member_id: Option<String>,
    pub amount_minor: i64,
    pub currency: String,
    pub channel: String,
    pub occurred_on: String,
    pub necessity: Option<String>,
    pub obligation_id: Option<String>,
    pub is_gift: bool,
    pub is_ostentation: bool,
    pub funded_by_debt: bool,
    pub note: Option<String>,
    /// «O'zimga sarmoya» belgisi (uy/SPEC 2G.3): toifa o'zgarmaydi, havas chegarasiga kirmaydi.
    pub self_investment: bool,
    /// Bilim rejasiga havola (faqat belgili xarajatda).
    pub learning_plan_id: Option<String>,
}

const COLS: &str =
    "id, category_id, member_id, amount_minor, currency, channel, occurred_on, necessity,
    obligation_id, is_gift, is_ostentation, funded_by_debt, note, self_investment, learning_plan_id";

fn map(r: &rusqlite::Row<'_>) -> rusqlite::Result<ExpenseRow> {
    Ok(ExpenseRow {
        id: r.get(0)?,
        category_id: r.get(1)?,
        member_id: r.get(2)?,
        amount_minor: r.get(3)?,
        currency: r.get(4)?,
        channel: r.get(5)?,
        occurred_on: r.get(6)?,
        necessity: r.get(7)?,
        obligation_id: r.get(8)?,
        is_gift: opt_bool(r.get(9)?),
        is_ostentation: opt_bool(r.get(10)?),
        funded_by_debt: opt_bool(r.get(11)?),
        note: r.get(12)?,
        self_investment: opt_bool(r.get(13)?),
        learning_plan_id: r.get(14)?,
    })
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    e: &ExpenseRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO expenses (id, household_id, space_id, category_id, member_id, amount_minor, currency, channel,
            occurred_on, necessity, obligation_id, is_gift, is_ostentation, funded_by_debt, note,
            self_investment, learning_plan_id, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?18, ?19, ?19)",
        params![e.id, s.household_id, s.space_id, e.category_id, e.member_id, e.amount_minor, e.currency,
            e.channel, e.occurred_on, e.necessity, e.obligation_id, i64::from(e.is_gift),
            i64::from(e.is_ostentation), i64::from(e.funded_by_debt), e.note, i64::from(e.self_investment),
            e.learning_plan_id, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn list_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<ExpenseRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM expenses WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], map)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn soft_delete(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE expenses SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

/// Chiqim sanasi va kanali (o'chirilmagan bo'lsa).
pub fn date_channel(
    c: &Connection,
    s: &SpaceScope,
    id: &str,
) -> Result<Option<(String, String)>, StorageError> {
    Ok(c.query_row(
        "SELECT occurred_on, channel FROM expenses WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )
    .optional()?)
}

/// «Sarmoya» belgili xarajatlar `[from, last]` oralig'ida (ikkala chet ham kiradi): (sana, valyuta,
/// summa). Bir nechta davr jami bitta so'rov bilan yig'iladi (K9 «Hisob kuni» qatori).
pub fn self_investment_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    last: &str,
) -> Result<Vec<(String, String, i64)>, StorageError> {
    let mut st = c.prepare(
        "SELECT occurred_on, currency, amount_minor FROM expenses
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL AND self_investment = 1
         AND occurred_on >= ?3 AND occurred_on <= ?4",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, last], |r| {
        Ok((r.get(0)?, r.get(1)?, r.get(2)?))
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
