//! Musofir (M6, `docs/musofir/SPEC.md` 6A): soat qiymati hisoblari (o'zgarmas, ish valyutasida), ikki
//! maqsadli bilim rejalari va «Ilm zakoti». Hammasi musofirning shaxsiy hisobi (ADR-0004).
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

// ---- Soat qiymati ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfHourRow {
    pub id: String,
    pub income_minor: i64,
    pub currency: String,
    /// `AUTO` yoki `MANUAL`.
    pub income_source: String,
    /// `AUTO` da — nechta to'liq oy o'rtachasi (1–3); `MANUAL` da 0.
    pub months: i64,
    pub minutes_per_day: i64,
    pub days: i64,
    pub hour_value_minor: i64,
    pub computed_on: String,
}

const HOUR_COLS: &str = "id, income_minor, currency, income_source, months, minutes_per_day, days,
    hour_value_minor, computed_on";

fn map_hour(r: &rusqlite::Row<'_>) -> rusqlite::Result<MfHourRow> {
    Ok(MfHourRow {
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
}

pub fn insert_hour(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    h: &MfHourRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_hour_values (id, household_id, space_id, income_minor, currency, income_source, months,
            minutes_per_day, days, hour_value_minor, computed_on, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
        params![h.id, s.household_id, s.space_id, h.income_minor, h.currency, h.income_source, h.months,
            h.minutes_per_day, h.days, h.hour_value_minor, h.computed_on, m.now, m.device_id],
    )?;
    Ok(())
}

/// Makonning hisoblari (yangisi birinchi).
pub fn hours(c: &Connection, s: &SpaceScope) -> Result<Vec<MfHourRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {HOUR_COLS} FROM mf_hour_values WHERE household_id = ?1 AND space_id = ?2
         ORDER BY created_at DESC, rowid DESC"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_hour)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Valyutadagi oxirgi hisob (bitta yozuv).
pub fn latest_hour(
    c: &Connection,
    s: &SpaceScope,
    currency: &str,
) -> Result<Option<MfHourRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {HOUR_COLS} FROM mf_hour_values
             WHERE household_id = ?1 AND space_id = ?2 AND currency = ?3
             ORDER BY created_at DESC, rowid DESC LIMIT 1"
        ),
        params![s.household_id, s.space_id, currency],
        map_hour,
    )
    .optional()?)
}

pub fn hour(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<MfHourRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {HOUR_COLS} FROM mf_hour_values
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3"
        ),
        params![s.household_id, s.space_id, id],
        map_hour,
    )
    .optional()?)
}

// ---- Bilim rejasi ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfPlanRow {
    pub id: String,
    /// `ABROAD` yoki `HOME`.
    pub goal: String,
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
    /// Faqat `HOME` maqsadida: Uy makonidagi «Hunardan ishga» g'oyasi.
    pub venture_idea_id: Option<String>,
}

const PLAN_COLS: &str = "id, goal, skill, purpose, paths, budget_minor, currency, weekly_minutes,
    start_on, review_on, status, baseline_hour_value_id, result_hour_value_id, venture_idea_id";

fn map_plan(r: &rusqlite::Row<'_>) -> rusqlite::Result<MfPlanRow> {
    Ok(MfPlanRow {
        id: r.get(0)?,
        goal: r.get(1)?,
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
        venture_idea_id: r.get(13)?,
    })
}

pub fn insert_plan(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    p: &MfPlanRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_learning_plans (id, household_id, space_id, goal, skill, purpose, paths, budget_minor,
            currency, weekly_minutes, start_on, review_on, status, baseline_hour_value_id, result_hour_value_id,
            venture_idea_id, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?17, ?18, ?18)",
        params![p.id, s.household_id, s.space_id, p.goal, p.skill, p.purpose, p.paths, p.budget_minor,
            p.currency, p.weekly_minutes, p.start_on, p.review_on, p.status, p.baseline_hour_value_id,
            p.result_hour_value_id, p.venture_idea_id, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn plan(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<MfPlanRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {PLAN_COLS} FROM mf_learning_plans
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_plan,
    )
    .optional()?)
}

/// Makonning barcha rejalari (ochilgan tartibida).
pub fn plans(c: &Connection, s: &SpaceScope) -> Result<Vec<MfPlanRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {PLAN_COLS} FROM mf_learning_plans
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL ORDER BY created_at, rowid"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_plan)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Makonning boshqa (`except` dan tashqari) faol rejalari soni — ikkala maqsad birga (musofir bitta odam).
pub fn other_active_plans(
    c: &Connection,
    s: &SpaceScope,
    except: Option<&str>,
) -> Result<usize, StorageError> {
    let n: i64 = c.query_row(
        "SELECT COUNT(*) FROM mf_learning_plans
         WHERE household_id = ?1 AND space_id = ?2 AND status = 'ACTIVE' AND deleted_at IS NULL
         AND id IS NOT coalesce(?3, '')",
        params![s.household_id, s.space_id, except],
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
            "UPDATE mf_learning_plans SET {set} = ?4, updated_at = ?5, updated_by_device_id = ?6,
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

// ---- «Ilm zakoti» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfTeachingRow {
    pub id: String,
    pub occurred_on: String,
    /// `WORK`, `LANGUAGE`, `DOCUMENTS`, `OTHER`.
    pub area: String,
    pub learner: Option<String>,
    pub topic: String,
    pub minutes: Option<i64>,
}

pub fn insert_teaching(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    t: &MfTeachingRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO mf_teaching_logs (id, household_id, space_id, occurred_on, area, learner, topic, minutes,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)",
        params![t.id, s.household_id, s.space_id, t.occurred_on, t.area, t.learner, t.topic, t.minutes,
            m.now, m.device_id],
    )?;
    Ok(())
}

/// `[from, to)` oralig'idagi o'rgatish yozuvlari (eskisi birinchi).
pub fn teaching_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<Vec<MfTeachingRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, occurred_on, area, learner, topic, minutes FROM mf_teaching_logs
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         AND occurred_on >= ?3 AND occurred_on < ?4 ORDER BY occurred_on, created_at, rowid",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, from, to], |r| {
        Ok(MfTeachingRow {
            id: r.get(0)?,
            occurred_on: r.get(1)?,
            area: r.get(2)?,
            learner: r.get(3)?,
            topic: r.get(4)?,
            minutes: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- Juma ritmi eslatmasi (bor-yo'qligi, yozuvlarsiz) ----

/// Bilim rejasi yoki soat qiymati hisobi bormi.
pub fn has_plan_or_hour(c: &Connection, s: &SpaceScope) -> Result<bool, StorageError> {
    Ok(c.query_row(
        "SELECT EXISTS(SELECT 1 FROM mf_learning_plans
             WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL)
         OR EXISTS(SELECT 1 FROM mf_hour_values WHERE household_id = ?1 AND space_id = ?2)",
        params![s.household_id, s.space_id],
        |r| r.get(0),
    )?)
}

/// `[from, to)` oralig'ida o'rgatish yozuvi bormi.
pub fn teaching_exists_between(
    c: &Connection,
    s: &SpaceScope,
    from: &str,
    to: &str,
) -> Result<bool, StorageError> {
    Ok(c.query_row(
        "SELECT EXISTS(SELECT 1 FROM mf_teaching_logs WHERE household_id = ?1 AND space_id = ?2
         AND deleted_at IS NULL AND occurred_on >= ?3 AND occurred_on < ?4)",
        params![s.household_id, s.space_id, from, to],
        |r| r.get(0),
    )?)
}
