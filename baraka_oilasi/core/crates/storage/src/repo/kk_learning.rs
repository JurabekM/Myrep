//! Kasb-kor (K9, `docs/kasbkor/SPEC.md` 8A): egasining soat qiymati hisoblari (o'zgarmas),
//! «O'zim qilaymi yoki o'rgatib topshiraymi?» qarorlari va xodimga o'rgatish («Ilm zakoti»).
use rusqlite::{params, Connection, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

// ---- Egasining soat qiymati ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkOwnerHourRow {
    pub id: String,
    pub income_minor: i64,
    pub currency: String,
    /// `AUTO` yoki `MANUAL`.
    pub income_source: String,
    /// `AUTO` da — nechta yopilgan oy o'rtachasi (1–3); `MANUAL` da 0.
    pub months: i64,
    pub minutes_per_day: i64,
    pub days: i64,
    pub hour_value_minor: i64,
    pub computed_on: String,
}

pub fn insert_owner_hour(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    h: &KkOwnerHourRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_owner_hours (id, household_id, space_id, income_minor, currency, income_source, months,
            minutes_per_day, days, hour_value_minor, computed_on, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
        params![h.id, s.household_id, s.space_id, h.income_minor, h.currency, h.income_source, h.months,
            h.minutes_per_day, h.days, h.hour_value_minor, h.computed_on, m.now, m.device_id],
    )?;
    Ok(())
}

/// Makonning hisoblari (yangisi birinchi).
pub fn owner_hours(c: &Connection, s: &SpaceScope) -> Result<Vec<KkOwnerHourRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, income_minor, currency, income_source, months, minutes_per_day, days, hour_value_minor,
            computed_on
         FROM kk_owner_hours WHERE household_id = ?1 AND space_id = ?2
         ORDER BY created_at DESC, rowid DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkOwnerHourRow {
            id: r.get(0)?,
            income_minor: r.get(1)?,
            currency: r.get(2)?,
            income_source: r.get(3)?,
            months: r.get(4)?,
            minutes_per_day: r.get(5)?,
            days: r.get(6)?,
            hour_value_minor: r.get(7)?,
            computed_on: r.get(8)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- «O'zim qilaymi yoki o'rgatib topshiraymi?» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkDelegationRow {
    pub id: String,
    pub task: String,
    /// Xodim kartochkasi (`kk_agreements`, `EMPLOYMENT`).
    pub agreement_id: Option<String>,
    pub currency: String,
    pub owner_hour_value_minor: i64,
    pub task_minutes: i64,
    pub helper_hour_cost_minor: i64,
    pub training_money_minor: i64,
    pub training_minutes: i64,
    pub decided_on: String,
}

pub fn insert_delegation(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    d: &KkDelegationRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_delegations (id, household_id, space_id, task, agreement_id, currency,
            owner_hour_value_minor, task_minutes, helper_hour_cost_minor, training_money_minor, training_minutes,
            decided_on, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?13, ?14, ?14)",
        params![d.id, s.household_id, s.space_id, d.task, d.agreement_id, d.currency,
            d.owner_hour_value_minor, d.task_minutes, d.helper_hour_cost_minor, d.training_money_minor,
            d.training_minutes, d.decided_on, m.now, m.device_id],
    )?;
    Ok(())
}

/// Saqlangan qarorlar (yangisi birinchi).
pub fn delegations(c: &Connection, s: &SpaceScope) -> Result<Vec<KkDelegationRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, task, agreement_id, currency, owner_hour_value_minor, task_minutes, helper_hour_cost_minor,
            training_money_minor, training_minutes, decided_on
         FROM kk_delegations WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY decided_on DESC, created_at DESC, rowid DESC",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(KkDelegationRow {
            id: r.get(0)?,
            task: r.get(1)?,
            agreement_id: r.get(2)?,
            currency: r.get(3)?,
            owner_hour_value_minor: r.get(4)?,
            task_minutes: r.get(5)?,
            helper_hour_cost_minor: r.get(6)?,
            training_money_minor: r.get(7)?,
            training_minutes: r.get(8)?,
            decided_on: r.get(9)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn delete_delegation(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        "UPDATE kk_delegations SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5,
            version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

// ---- «Ilm zakoti» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkTeachingRow {
    pub id: String,
    pub occurred_on: String,
    /// Xodim kartochkasi; bo'lsa — `learner` bo'sh.
    pub agreement_id: Option<String>,
    pub learner: Option<String>,
    pub topic: String,
    pub minutes: Option<i64>,
}

pub fn insert_teaching(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    t: &KkTeachingRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO kk_teaching_logs (id, household_id, space_id, occurred_on, agreement_id, learner, topic,
            minutes, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)",
        params![t.id, s.household_id, s.space_id, t.occurred_on, t.agreement_id, t.learner, t.topic,
            t.minutes, m.now, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi o'rgatish yozuvlari (eskisi birinchi).
pub fn teaching_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<KkTeachingRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, occurred_on, agreement_id, learner, topic, minutes FROM kk_teaching_logs
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at, rowid",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], |r| {
        Ok(KkTeachingRow {
            id: r.get(0)?,
            occurred_on: r.get(1)?,
            agreement_id: r.get(2)?,
            learner: r.get(3)?,
            topic: r.get(4)?,
            minutes: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
