//! U12: sheriklik kassa daftari (append-only), ilovalar, yopilgan davrlar; «Hunardan ishga».
//! Daftar, ilova va davr jadvallari uchun bu modulda yangilash yoki o'chirish funksiyasi **yo'q**.
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

// ---- daftar yozuvlari ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EntryRow {
    pub id: String,
    pub partnership_id: String,
    pub journal_entry_id: String,
    pub kind: String,
    pub category: Option<String>,
    pub amount_minor: i64,
    pub currency: String,
    pub occurred_on: String,
    pub note: Option<String>,
    pub corrects_entry_id: Option<String>,
    pub created_at: String,
}

const E_COLS: &str = "id, partnership_id, journal_entry_id, kind, category, amount_minor, currency,
    occurred_on, note, corrects_entry_id, created_at";

fn map_e(r: &rusqlite::Row<'_>) -> rusqlite::Result<EntryRow> {
    Ok(EntryRow {
        id: r.get(0)?,
        partnership_id: r.get(1)?,
        journal_entry_id: r.get(2)?,
        kind: r.get(3)?,
        category: r.get(4)?,
        amount_minor: r.get(5)?,
        currency: r.get(6)?,
        occurred_on: r.get(7)?,
        note: r.get(8)?,
        corrects_entry_id: r.get(9)?,
        created_at: r.get(10)?,
    })
}

pub fn insert_entry(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    e: &EntryRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO venture_entries (id, partnership_id, journal_entry_id, kind, category, amount_minor,
            currency, occurred_on, note, corrects_entry_id, created_at, household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
        params![e.id, e.partnership_id, e.journal_entry_id, e.kind, e.category, e.amount_minor,
            e.currency, e.occurred_on, e.note, e.corrects_entry_id, m.now, s.household_id,
            s.space_id, m.device_id],
    )?;
    Ok(())
}

/// Sana bo'yicha, bir kunda — kiritilish tartibida.
pub fn entries(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<EntryRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {E_COLS} FROM venture_entries WHERE household_id = ?1 AND space_id = ?2
         AND partnership_id = ?3 ORDER BY occurred_on, created_at, rowid"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, partnership_id], map_e)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- ilovalar ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AttachmentMeta {
    pub id: String,
    pub entry_id: String,
    pub file_name: String,
    pub mime: String,
    pub size_bytes: i64,
    pub sha256: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AttachmentRow {
    pub meta: AttachmentMeta,
    pub bytes: Vec<u8>,
}

pub fn insert_attachment(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    a: &AttachmentRow,
    m: &Meta,
) -> Result<(), StorageError> {
    let x = &a.meta;
    tx.execute(
        "INSERT INTO venture_attachments (id, entry_id, file_name, mime, size_bytes, sha256, bytes,
            created_at, household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        params![
            x.id,
            x.entry_id,
            x.file_name,
            x.mime,
            x.size_bytes,
            x.sha256,
            a.bytes,
            m.now,
            s.household_id,
            s.space_id,
            m.device_id
        ],
    )?;
    Ok(())
}

/// Sherikning barcha ilovalari (baytlarsiz).
pub fn attachments(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<AttachmentMeta>, StorageError> {
    let mut st = c.prepare(
        "SELECT a.id, a.entry_id, a.file_name, a.mime, a.size_bytes, a.sha256
         FROM venture_attachments a JOIN venture_entries e ON e.id = a.entry_id
         WHERE a.household_id = ?1 AND a.space_id = ?2 AND e.partnership_id = ?3
         ORDER BY a.created_at, a.rowid",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, partnership_id], |r| {
        Ok(AttachmentMeta {
            id: r.get(0)?,
            entry_id: r.get(1)?,
            file_name: r.get(2)?,
            mime: r.get(3)?,
            size_bytes: r.get(4)?,
            sha256: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn attachment(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
    id: &str,
) -> Result<Option<AttachmentRow>, StorageError> {
    Ok(c.query_row(
        "SELECT a.id, a.entry_id, a.file_name, a.mime, a.size_bytes, a.sha256, a.bytes
         FROM venture_attachments a JOIN venture_entries e ON e.id = a.entry_id
         WHERE a.household_id = ?1 AND a.space_id = ?2 AND e.partnership_id = ?3 AND a.id = ?4",
        params![s.household_id, s.space_id, partnership_id, id],
        |r| {
            Ok(AttachmentRow {
                meta: AttachmentMeta {
                    id: r.get(0)?,
                    entry_id: r.get(1)?,
                    file_name: r.get(2)?,
                    mime: r.get(3)?,
                    size_bytes: r.get(4)?,
                    sha256: r.get(5)?,
                },
                bytes: r.get(6)?,
            })
        },
    )
    .optional()?)
}

// ---- yopilgan davrlar ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodRow {
    pub id: String,
    pub partnership_id: String,
    pub period_no: i64,
    pub start_on: String,
    pub end_on: String,
    pub currency: String,
    pub result_minor: i64,
    pub loss_policy: String,
    pub signed_version: i64,
    pub result_json: String,
    pub chain_head: String,
    pub closed_at: String,
}

const P_COLS: &str = "id, partnership_id, period_no, start_on, end_on, currency, result_minor,
    loss_policy, signed_version, result_json, chain_head, closed_at";

fn map_p(r: &rusqlite::Row<'_>) -> rusqlite::Result<PeriodRow> {
    Ok(PeriodRow {
        id: r.get(0)?,
        partnership_id: r.get(1)?,
        period_no: r.get(2)?,
        start_on: r.get(3)?,
        end_on: r.get(4)?,
        currency: r.get(5)?,
        result_minor: r.get(6)?,
        loss_policy: r.get(7)?,
        signed_version: r.get(8)?,
        result_json: r.get(9)?,
        chain_head: r.get(10)?,
        closed_at: r.get(11)?,
    })
}

pub fn insert_period(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    p: &PeriodRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        &format!(
            "INSERT INTO venture_periods ({P_COLS}, household_id, space_id, origin_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15)"
        ),
        params![
            p.id,
            p.partnership_id,
            p.period_no,
            p.start_on,
            p.end_on,
            p.currency,
            p.result_minor,
            p.loss_policy,
            p.signed_version,
            p.result_json,
            p.chain_head,
            p.closed_at,
            s.household_id,
            s.space_id,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn periods(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<PeriodRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {P_COLS} FROM venture_periods WHERE household_id = ?1 AND space_id = ?2
         AND partnership_id = ?3 ORDER BY period_no"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, partnership_id], map_p)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- «Hunardan ishga» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SkillRow {
    pub id: String,
    pub member_id: Option<String>,
    pub title: String,
    pub note: Option<String>,
}

pub fn insert_skill(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    k: &SkillRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO skills (id, member_id, title, note, household_id, space_id, created_at, updated_at,
            origin_device_id, updated_by_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?7, ?8, ?8)",
        params![k.id, k.member_id, k.title, k.note, s.household_id, s.space_id, m.now, m.device_id],
    )?;
    Ok(())
}

pub fn skills(c: &Connection, s: &SpaceScope) -> Result<Vec<SkillRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, member_id, title, note FROM skills WHERE household_id = ?1 AND space_id = ?2
         AND deleted_at IS NULL ORDER BY created_at, rowid",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id], |r| {
        Ok(SkillRow {
            id: r.get(0)?,
            member_id: r.get(1)?,
            title: r.get(2)?,
            note: r.get(3)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn delete_skill(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    changed(tx.execute(
        "UPDATE skills SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IdeaRow {
    pub id: String,
    pub skill_id: Option<String>,
    pub title: String,
    pub currency: String,
    pub capex_json: String,
    pub scenarios_json: String,
    pub worker_share_bp: Option<i64>,
    pub partnership_id: Option<String>,
}

const I_COLS: &str =
    "id, skill_id, title, currency, capex_json, scenarios_json, worker_share_bp, partnership_id";

fn map_i(r: &rusqlite::Row<'_>) -> rusqlite::Result<IdeaRow> {
    Ok(IdeaRow {
        id: r.get(0)?,
        skill_id: r.get(1)?,
        title: r.get(2)?,
        currency: r.get(3)?,
        capex_json: r.get(4)?,
        scenarios_json: r.get(5)?,
        worker_share_bp: r.get(6)?,
        partnership_id: r.get(7)?,
    })
}

pub fn insert_idea(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    i: &IdeaRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        &format!(
            "INSERT INTO venture_ideas ({I_COLS}, household_id, space_id, created_at, updated_at,
                origin_device_id, updated_by_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?11, ?12, ?12)"
        ),
        params![
            i.id,
            i.skill_id,
            i.title,
            i.currency,
            i.capex_json,
            i.scenarios_json,
            i.worker_share_bp,
            i.partnership_id,
            s.household_id,
            s.space_id,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn update_idea(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    i: &IdeaRow,
    m: &Meta,
) -> Result<(), StorageError> {
    changed(tx.execute(
        "UPDATE venture_ideas SET skill_id = ?4, title = ?5, capex_json = ?6, scenarios_json = ?7,
            worker_share_bp = ?8, partnership_id = ?9, updated_at = ?10, updated_by_device_id = ?11,
            version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![
            s.household_id,
            s.space_id,
            i.id,
            i.skill_id,
            i.title,
            i.capex_json,
            i.scenarios_json,
            i.worker_share_bp,
            i.partnership_id,
            m.now,
            m.device_id
        ],
    )?)
}

pub fn get_idea(c: &Connection, s: &SpaceScope, id: &str) -> Result<Option<IdeaRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {I_COLS} FROM venture_ideas WHERE household_id = ?1 AND space_id = ?2 AND id = ?3
             AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_i,
    )
    .optional()?)
}

pub fn ideas(c: &Connection, s: &SpaceScope) -> Result<Vec<IdeaRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {I_COLS} FROM venture_ideas WHERE household_id = ?1 AND space_id = ?2
         AND deleted_at IS NULL ORDER BY created_at, rowid"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_i)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn delete_idea(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    changed(tx.execute(
        "UPDATE venture_ideas SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5,
            version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![s.household_id, s.space_id, id, m.now, m.device_id],
    )?)
}
