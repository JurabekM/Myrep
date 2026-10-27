//! 8-tamoyil «O'zingizga sarmoya qiling» (U16, `docs/uy/SPEC.md` 2G): soat qiymati hisoblari
//! (o'zgarmas), bilim rejalari, o'qish vaqti va «Ilm zakoti» yozuvlari, rejaga bog'langan xarajatlar.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

// ---- «Bir soatim qancha?» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HourValueRow {
    pub id: String,
    pub member_id: String,
    pub income_minor: i64,
    pub currency: String,
    /// `AUTO` yoki `MANUAL`.
    pub income_source: String,
    pub minutes_per_day: i64,
    pub days: i64,
    pub hour_value_minor: i64,
    pub computed_on: String,
}

const HV_COLS: &str = "id, member_id, income_minor, currency, income_source, minutes_per_day, days,
    hour_value_minor, computed_on";

fn map_hv(r: &rusqlite::Row<'_>) -> rusqlite::Result<HourValueRow> {
    Ok(HourValueRow {
        id: r.get(0)?,
        member_id: r.get(1)?,
        income_minor: r.get(2)?,
        currency: r.get(3)?,
        income_source: r.get(4)?,
        minutes_per_day: r.get(5)?,
        days: r.get(6)?,
        hour_value_minor: r.get(7)?,
        computed_on: r.get(8)?,
    })
}

pub fn insert_hour_value(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    h: &HourValueRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO learning_hour_values (id, household_id, space_id, member_id, income_minor, currency,
            income_source, minutes_per_day, days, hour_value_minor, computed_on, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
        params![h.id, s.household_id, s.space_id, h.member_id, h.income_minor, h.currency,
            h.income_source, h.minutes_per_day, h.days, h.hour_value_minor, h.computed_on, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn hour_value(
    c: &Connection,
    s: &SpaceScope,
    id: &str,
) -> Result<Option<HourValueRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {HV_COLS} FROM learning_hour_values
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3"
        ),
        params![s.household_id, s.space_id, id],
        map_hv,
    )
    .optional()?)
}

/// A'zoning eng so'nggi hisobi (saqlangan vaqti bo'yicha).
pub fn latest_hour_value(
    c: &Connection,
    s: &SpaceScope,
    member_id: &str,
) -> Result<Option<HourValueRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {HV_COLS} FROM learning_hour_values
             WHERE household_id = ?1 AND space_id = ?2 AND member_id = ?3
             ORDER BY created_at DESC, rowid DESC LIMIT 1"
        ),
        params![s.household_id, s.space_id, member_id],
        map_hv,
    )
    .optional()?)
}

/// Makonning barcha hisoblari (saqlangan tartibida: oxirgisi — eng so'nggi).
pub fn hour_values(c: &Connection, s: &SpaceScope) -> Result<Vec<HourValueRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {HV_COLS} FROM learning_hour_values WHERE household_id = ?1 AND space_id = ?2
         ORDER BY created_at, rowid"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_hv)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- Bilim rejasi ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlanRow {
    pub id: String,
    pub member_id: String,
    pub skill: String,
    pub purpose: Option<String>,
    /// Tartiblangan yo'l kodlari, vergul bilan: `BOOK,COURSE`.
    pub paths: String,
    pub budget_minor: Option<i64>,
    pub currency: String,
    pub weekly_minutes: i64,
    pub start_on: String,
    pub review_on: String,
    pub status: String,
    pub baseline_hour_value_id: Option<String>,
    pub result_hour_value_id: Option<String>,
}

const PLAN_COLS: &str =
    "id, member_id, skill, purpose, paths, budget_minor, currency, weekly_minutes,
    start_on, review_on, status, baseline_hour_value_id, result_hour_value_id";

fn map_plan(r: &rusqlite::Row<'_>) -> rusqlite::Result<PlanRow> {
    Ok(PlanRow {
        id: r.get(0)?,
        member_id: r.get(1)?,
        skill: r.get(2)?,
        purpose: r.get(3)?,
        paths: r.get(4)?,
        budget_minor: r.get(5)?,
        currency: r.get(6)?,
        weekly_minutes: r.get(7)?,
        start_on: r.get(8)?,
        review_on: r.get(9)?,
        status: r.get(10)?,
        baseline_hour_value_id: r.get(11)?,
        result_hour_value_id: r.get(12)?,
    })
}

pub fn insert_plan(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    p: &PlanRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO learning_plans (id, household_id, space_id, member_id, skill, purpose, paths, budget_minor,
            currency, weekly_minutes, start_on, review_on, status, baseline_hour_value_id, result_hour_value_id,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?16, ?17, ?17)",
        params![p.id, s.household_id, s.space_id, p.member_id, p.skill, p.purpose, p.paths, p.budget_minor,
            p.currency, p.weekly_minutes, p.start_on, p.review_on, p.status, p.baseline_hour_value_id,
            p.result_hour_value_id, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn plan(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<PlanRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {PLAN_COLS} FROM learning_plans
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_plan,
    )
    .optional()?)
}

/// Makonning barcha rejalari (ochilgan tartibida).
pub fn plans(c: &Connection, s: &SpaceScope) -> Result<Vec<PlanRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {PLAN_COLS} FROM learning_plans
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL ORDER BY created_at, rowid"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_plan)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// A'zoning boshqa (`except` dan tashqari) faol rejalari soni.
pub fn other_active_plans(
    c: &Connection,
    s: &SpaceScope,
    member_id: &str,
    except: Option<&str>,
) -> Result<usize, StorageError> {
    let n: i64 = c.query_row(
        "SELECT COUNT(*) FROM learning_plans
         WHERE household_id = ?1 AND space_id = ?2 AND member_id = ?3 AND status = 'ACTIVE'
         AND deleted_at IS NULL AND id IS NOT coalesce(?4, '')",
        params![s.household_id, s.space_id, member_id, except],
        |r| r.get(0),
    )?;
    usize::try_from(n).map_err(|_| StorageError::CorruptRow)
}

fn touch_plan(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    set: &str,
    value: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    let n = tx.execute(
        &format!(
            "UPDATE learning_plans SET {set} = ?4, updated_at = ?5, updated_by_device_id = ?6,
                version = version + 1
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id, value, m.now, m.device_id],
    )?;
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

pub fn set_plan_status(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    status: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    touch_plan(tx, s, id, "status", status, m)
}

pub fn set_plan_result(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    hour_value_id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    touch_plan(tx, s, id, "result_hour_value_id", hour_value_id, m)
}

// ---- O'qish vaqti ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StudyLogRow {
    pub id: String,
    pub plan_id: String,
    pub occurred_on: String,
    pub minutes: i64,
    pub note: Option<String>,
}

pub fn insert_study_log(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    l: &StudyLogRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO learning_study_logs (id, household_id, space_id, plan_id, occurred_on, minutes, note,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?8, ?9, ?9)",
        params![l.id, s.household_id, s.space_id, l.plan_id, l.occurred_on, l.minutes, l.note, m.now,
            m.device_id],
    )?;
    Ok(())
}

/// Rejalar bo'yicha jami o'qish daqiqalari: (reja, daqiqa). `plan_id` — faqat shu reja.
pub fn study_minutes(
    c: &Connection,
    s: &SpaceScope,
    plan_id: Option<&str>,
) -> Result<Vec<(String, i64)>, StorageError> {
    let mut st = c.prepare(
        "SELECT plan_id, SUM(minutes) FROM learning_study_logs
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND (?3 IS NULL OR plan_id = ?3) GROUP BY plan_id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, plan_id], |r| {
        Ok((r.get(0)?, r.get(1)?))
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Rejalarga bog'langan «O'zimga sarmoya» xarajatlari: (reja, valyuta, summa). `plan_id` — faqat
/// shu reja.
pub fn plan_spending(
    c: &Connection,
    s: &SpaceScope,
    plan_id: Option<&str>,
) -> Result<Vec<(String, String, i64)>, StorageError> {
    let mut st = c.prepare(
        "SELECT learning_plan_id, currency, SUM(amount_minor) FROM expenses
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL AND self_investment = 1
         AND learning_plan_id IS NOT NULL AND (?3 IS NULL OR learning_plan_id = ?3)
         GROUP BY learning_plan_id, currency",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, plan_id], |r| {
        Ok((r.get(0)?, r.get(1)?, r.get(2)?))
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- «Ilm zakoti» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TeachingRow {
    pub id: String,
    pub member_id: String,
    pub occurred_on: String,
    pub learner: Option<String>,
    pub topic: String,
    pub minutes: Option<i64>,
}

pub fn insert_teaching(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    t: &TeachingRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO teaching_logs (id, household_id, space_id, member_id, occurred_on, learner, topic, minutes,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)",
        params![t.id, s.household_id, s.space_id, t.member_id, t.occurred_on, t.learner, t.topic,
            t.minutes, m.now, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi o'rgatish yozuvlari.
pub fn teaching_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<TeachingRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, member_id, occurred_on, learner, topic, minutes FROM teaching_logs
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at, rowid",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], |r| {
        Ok(TeachingRow {
            id: r.get(0)?,
            member_id: r.get(1)?,
            occurred_on: r.get(2)?,
            learner: r.get(3)?,
            topic: r.get(4)?,
            minutes: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
