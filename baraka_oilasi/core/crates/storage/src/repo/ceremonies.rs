//! U10: marosim rejalari, stsenariylar, byudjet qatorlari, oilaviy muhokama, maqsad hissalari.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

fn changed(n: usize) -> Result<(), StorageError> {
    if n == 0 {
        Err(StorageError::NotFound)
    } else {
        Ok(())
    }
}

/// Bu moduldagi jadvallar uchun soft delete (jadval nomi ichki — foydalanuvchidan kelmaydi).
fn soft_delete(
    tx: &Transaction<'_>,
    table: &str,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    changed(tx.execute(
        &format!(
            "UPDATE {table} SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CeremonyRow {
    pub id: String,
    pub kind: String,
    pub title: String,
    pub planned_on: Option<String>,
    pub status: String,
    pub selected_scenario_id: Option<String>,
    pub currency: String,
    pub monthly_capacity_minor: Option<i64>,
    pub discussion_json: Option<String>,
}

const CER_COLS: &str = "id, kind, title, planned_on, status, selected_scenario_id, currency,
    monthly_capacity_minor, discussion_json";

fn map_cer(r: &rusqlite::Row<'_>) -> rusqlite::Result<CeremonyRow> {
    Ok(CeremonyRow {
        id: r.get(0)?,
        kind: r.get(1)?,
        title: r.get(2)?,
        planned_on: r.get(3)?,
        status: r.get(4)?,
        selected_scenario_id: r.get(5)?,
        currency: r.get(6)?,
        monthly_capacity_minor: r.get(7)?,
        discussion_json: r.get(8)?,
    })
}

pub fn insert_ceremony(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    c: &CeremonyRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        &format!(
            "INSERT INTO ceremonies ({CER_COLS}, household_id, space_id, created_at, updated_at,
                origin_device_id, updated_by_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?12, ?13, ?13)"
        ),
        params![
            c.id,
            c.kind,
            c.title,
            c.planned_on,
            c.status,
            c.selected_scenario_id,
            c.currency,
            c.monthly_capacity_minor,
            c.discussion_json,
            s.household_id,
            s.space_id,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

/// O'zgaruvchan maydonlarni yangilaydi (holat, tanlangan stsenariy, ajratma, muhokama, nom, sana).
pub fn update_ceremony(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    c: &CeremonyRow,
    m: &Meta,
) -> Result<(), StorageError> {
    changed(tx.execute(
        "UPDATE ceremonies SET title = ?4, planned_on = ?5, status = ?6, selected_scenario_id = ?7,
            monthly_capacity_minor = ?8, discussion_json = ?9, updated_at = ?10, updated_by_device_id = ?11,
            version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, c.id, c.title, c.planned_on, c.status, c.selected_scenario_id,
            c.monthly_capacity_minor, c.discussion_json, m.now, m.device_id],
    )?)
}

pub fn list_ceremonies(c: &Connection, s: &SpaceScope) -> Result<Vec<CeremonyRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {CER_COLS} FROM ceremonies WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY created_at"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_cer)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn get_ceremony(
    c: &Connection,
    s: &SpaceScope,
    id: &str,
) -> Result<Option<CeremonyRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {CER_COLS} FROM ceremonies
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_cer,
    )
    .optional()?)
}

pub fn delete_ceremony(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    soft_delete(tx, "ceremonies", s, id, m)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ScenarioRow {
    pub id: String,
    pub ceremony_id: String,
    pub name: String,
    pub guests: i64,
    pub sort_order: i64,
}

pub fn insert_scenario(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &ScenarioRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO ceremony_scenarios (id, household_id, space_id, ceremony_id, name, guests, sort_order,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?8, ?9, ?9)",
        params![r.id, s.household_id, s.space_id, r.ceremony_id, r.name, r.guests, r.sort_order, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn update_scenario(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &ScenarioRow,
    m: &Meta,
) -> Result<(), StorageError> {
    changed(tx.execute(
        "UPDATE ceremony_scenarios SET name = ?4, guests = ?5, updated_at = ?6, updated_by_device_id = ?7,
            version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, r.id, r.name, r.guests, m.now, m.device_id],
    )?)
}

pub fn delete_scenario(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    soft_delete(tx, "ceremony_scenarios", s, id, m)
}

pub fn scenarios(
    c: &Connection,
    s: &SpaceScope,
    ceremony_id: &str,
) -> Result<Vec<ScenarioRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, ceremony_id, name, guests, sort_order FROM ceremony_scenarios
         WHERE household_id = ?1 AND space_id = ?2 AND ceremony_id = ?3 AND deleted_at IS NULL
         ORDER BY sort_order, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, ceremony_id], |r| {
        Ok(ScenarioRow {
            id: r.get(0)?,
            ceremony_id: r.get(1)?,
            name: r.get(2)?,
            guests: r.get(3)?,
            sort_order: r.get(4)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LineRow {
    pub id: String,
    pub scenario_id: String,
    pub title: String,
    pub line_kind: String,
    pub amount_minor: i64,
    pub currency: String,
    pub source: String,
}

pub fn insert_line(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    l: &LineRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO ceremony_lines (id, household_id, space_id, scenario_id, title, line_kind, amount_minor,
            currency, source, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?10, ?11, ?11)",
        params![l.id, s.household_id, s.space_id, l.scenario_id, l.title, l.line_kind, l.amount_minor,
            l.currency, l.source, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn delete_line(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    soft_delete(tx, "ceremony_lines", s, id, m)
}

pub fn lines(
    c: &Connection,
    s: &SpaceScope,
    scenario_id: &str,
) -> Result<Vec<LineRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, scenario_id, title, line_kind, amount_minor, currency, source FROM ceremony_lines
         WHERE household_id = ?1 AND space_id = ?2 AND scenario_id = ?3 AND deleted_at IS NULL
         ORDER BY created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, scenario_id], |r| {
        Ok(LineRow {
            id: r.get(0)?,
            scenario_id: r.get(1)?,
            title: r.get(2)?,
            line_kind: r.get(3)?,
            amount_minor: r.get(4)?,
            currency: r.get(5)?,
            source: r.get(6)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Qator qaysi marosimga tegishli (qulflanganini tekshirish uchun).
pub fn line_ceremony(
    c: &Connection,
    s: &SpaceScope,
    line_id: &str,
) -> Result<Option<String>, StorageError> {
    Ok(c.query_row(
        "SELECT sc.ceremony_id FROM ceremony_lines l JOIN ceremony_scenarios sc ON sc.id = l.scenario_id
         WHERE l.household_id = ?1 AND l.space_id = ?2 AND l.id = ?3 AND l.deleted_at IS NULL",
        params![s.household_id, s.space_id, line_id],
        |r| r.get(0),
    )
    .optional()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SignoffRow {
    pub id: String,
    pub member_id: String,
    pub agreed_on: String,
}

pub fn insert_signoff(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    ceremony_id: &str,
    r: &SignoffRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO ceremony_signoffs (id, household_id, space_id, ceremony_id, member_id, agreed_on,
            created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?7, ?8, ?8)",
        params![r.id, s.household_id, s.space_id, ceremony_id, r.member_id, r.agreed_on, m.now,
            m.device_id],
    )?;
    Ok(())
}

pub fn signoffs(
    c: &Connection,
    s: &SpaceScope,
    ceremony_id: &str,
) -> Result<Vec<SignoffRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, member_id, agreed_on FROM ceremony_signoffs
         WHERE household_id = ?1 AND space_id = ?2 AND ceremony_id = ?3 AND deleted_at IS NULL
         ORDER BY created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, ceremony_id], |r| {
        Ok(SignoffRow {
            id: r.get(0)?,
            member_id: r.get(1)?,
            agreed_on: r.get(2)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Reja o'zgarganda barcha roziliklar bekor qilinadi.
pub fn clear_signoffs(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    ceremony_id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "UPDATE ceremony_signoffs SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5,
            version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND ceremony_id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, ceremony_id, m.now, m.device_id],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ContributionRow {
    pub id: String,
    pub goal_id: String,
    pub contributor: String,
    pub amount_minor: i64,
    pub currency: String,
    pub given_on: String,
}

pub fn insert_contribution(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &ContributionRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO goal_contributions (id, household_id, space_id, goal_id, contributor, amount_minor,
            currency, given_on, created_at, updated_at, origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?9, ?10, ?10)",
        params![r.id, s.household_id, s.space_id, r.goal_id, r.contributor, r.amount_minor, r.currency,
            r.given_on, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn contributions(
    c: &Connection,
    s: &SpaceScope,
    goal_id: &str,
) -> Result<Vec<ContributionRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, goal_id, contributor, amount_minor, currency, given_on FROM goal_contributions
         WHERE household_id = ?1 AND space_id = ?2 AND goal_id = ?3 AND deleted_at IS NULL
         ORDER BY given_on, created_at",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, goal_id], |r| {
        Ok(ContributionRow {
            id: r.get(0)?,
            goal_id: r.get(1)?,
            contributor: r.get(2)?,
            amount_minor: r.get(3)?,
            currency: r.get(4)?,
            given_on: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
