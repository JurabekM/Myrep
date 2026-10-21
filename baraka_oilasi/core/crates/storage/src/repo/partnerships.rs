//! U11: sheriklik, shartnoma versiyalari (o'zgarmas), imzolar (o'zgarmas), oilaviy rozilik.
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

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PartnershipRow {
    pub id: String,
    pub agreement_id: String,
    pub kind: String,
    pub title: String,
    pub status: String,
    pub currency: String,
    pub signed_version: Option<i64>,
    pub not_debt_ack_on: Option<String>,
    pub gate_json: Option<String>,
    pub activated_on: Option<String>,
    pub closed_on: Option<String>,
}

const P_COLS: &str = "id, agreement_id, kind, title, status, currency, signed_version,
    not_debt_ack_on, gate_json, activated_on, closed_on";

fn map_p(r: &rusqlite::Row<'_>) -> rusqlite::Result<PartnershipRow> {
    Ok(PartnershipRow {
        id: r.get(0)?,
        agreement_id: r.get(1)?,
        kind: r.get(2)?,
        title: r.get(3)?,
        status: r.get(4)?,
        currency: r.get(5)?,
        signed_version: r.get(6)?,
        not_debt_ack_on: r.get(7)?,
        gate_json: r.get(8)?,
        activated_on: r.get(9)?,
        closed_on: r.get(10)?,
    })
}

pub fn insert(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    p: &PartnershipRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        &format!(
            "INSERT INTO partnerships ({P_COLS}, household_id, space_id, created_at, updated_at,
                origin_device_id, updated_by_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?14, ?15, ?15)"
        ),
        params![
            p.id,
            p.agreement_id,
            p.kind,
            p.title,
            p.status,
            p.currency,
            p.signed_version,
            p.not_debt_ack_on,
            p.gate_json,
            p.activated_on,
            p.closed_on,
            s.household_id,
            s.space_id,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

/// Holat, versiya va sanalarni yangilaydi (id va kelishuv o'zgarmaydi).
pub fn update(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    p: &PartnershipRow,
    m: &Meta,
) -> Result<(), StorageError> {
    changed(tx.execute(
        "UPDATE partnerships SET kind = ?4, title = ?5, status = ?6, signed_version = ?7,
            not_debt_ack_on = ?8, gate_json = ?9, activated_on = ?10, closed_on = ?11,
            updated_at = ?12, updated_by_device_id = ?13, version = version + 1
         WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL",
        params![
            s.household_id,
            s.space_id,
            p.id,
            p.kind,
            p.title,
            p.status,
            p.signed_version,
            p.not_debt_ack_on,
            p.gate_json,
            p.activated_on,
            p.closed_on,
            m.now,
            m.device_id
        ],
    )?)
}

/// Faqat imzolanmagan qoralama o'chiriladi (soft delete, kelishuv bilan birga).
pub fn delete(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    p: &PartnershipRow,
    m: &Meta,
) -> Result<(), StorageError> {
    for table in ["partnerships", "agreements"] {
        let id = if table == "partnerships" {
            &p.id
        } else {
            &p.agreement_id
        };
        changed(tx.execute(
            &format!(
                "UPDATE {table} SET deleted_at = ?4, updated_at = ?4, updated_by_device_id = ?5,
                    version = version + 1
                 WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
            ),
            params![s.household_id, s.space_id, id, m.now, m.device_id],
        )?)?;
    }
    Ok(())
}

pub fn get(
    c: &Connection,
    s: &SpaceScope,
    id: &str,
) -> Result<Option<PartnershipRow>, StorageError> {
    Ok(c.query_row(
        &format!(
            "SELECT {P_COLS} FROM partnerships
             WHERE household_id = ?1 AND space_id = ?2 AND id = ?3 AND deleted_at IS NULL"
        ),
        params![s.household_id, s.space_id, id],
        map_p,
    )
    .optional()?)
}

pub fn list(c: &Connection, s: &SpaceScope) -> Result<Vec<PartnershipRow>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {P_COLS} FROM partnerships
         WHERE household_id = ?1 AND space_id = ?2 AND deleted_at IS NULL
         ORDER BY created_at DESC, id"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id], map_p)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VersionRow {
    pub id: String,
    pub version_no: i64,
    pub payload_json: String,
    pub payload_hash: String,
    pub change_note: Option<String>,
    pub created_at: String,
}

pub fn insert_version(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    agreement_id: &str,
    v: &VersionRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO agreement_versions (id, household_id, space_id, agreement_id, version_no,
            payload_json, payload_hash, change_note, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![
            v.id,
            s.household_id,
            s.space_id,
            agreement_id,
            v.version_no,
            v.payload_json,
            v.payload_hash,
            v.change_note,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn versions(
    c: &Connection,
    s: &SpaceScope,
    agreement_id: &str,
) -> Result<Vec<VersionRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, version_no, payload_json, payload_hash, change_note, created_at
         FROM agreement_versions
         WHERE household_id = ?1 AND space_id = ?2 AND agreement_id = ?3
         ORDER BY version_no",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, agreement_id], |r| {
        Ok(VersionRow {
            id: r.get(0)?,
            version_no: r.get(1)?,
            payload_json: r.get(2)?,
            payload_hash: r.get(3)?,
            change_note: r.get(4)?,
            created_at: r.get(5)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SignatureRow {
    pub id: String,
    pub version_id: String,
    pub signer_key: String,
    pub signer_role: String,
    pub signer_name: String,
    pub strokes_json: String,
    pub signed_at: String,
}

pub fn insert_signature(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    g: &SignatureRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO agreement_signatures (id, household_id, space_id, version_id, signer_key,
            signer_role, signer_name, strokes_json, signed_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![
            g.id,
            s.household_id,
            s.space_id,
            g.version_id,
            g.signer_key,
            g.signer_role,
            g.signer_name,
            g.strokes_json,
            g.signed_at,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn signatures(
    c: &Connection,
    s: &SpaceScope,
    version_id: &str,
) -> Result<Vec<SignatureRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT id, version_id, signer_key, signer_role, signer_name, strokes_json, signed_at
         FROM agreement_signatures
         WHERE household_id = ?1 AND space_id = ?2 AND version_id = ?3
         ORDER BY signed_at, id",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, version_id], |r| {
        Ok(SignatureRow {
            id: r.get(0)?,
            version_id: r.get(1)?,
            signer_key: r.get(2)?,
            signer_role: r.get(3)?,
            signer_name: r.get(4)?,
            strokes_json: r.get(5)?,
            signed_at: r.get(6)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ConsentRow {
    pub member_id: String,
    pub version_no: i64,
    pub agreed_on: String,
}

pub fn insert_consent(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    partnership_id: &str,
    c: &ConsentRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO partnership_consents (id, household_id, space_id, partnership_id, member_id,
            version_no, agreed_on, created_at, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![
            id,
            s.household_id,
            s.space_id,
            partnership_id,
            c.member_id,
            c.version_no,
            c.agreed_on,
            m.now,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn consents(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<ConsentRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT member_id, version_no, agreed_on FROM partnership_consents
         WHERE household_id = ?1 AND space_id = ?2 AND partnership_id = ?3
         ORDER BY version_no, agreed_on",
    )?;
    let rows = st.query_map(params![s.household_id, s.space_id, partnership_id], |r| {
        Ok(ConsentRow {
            member_id: r.get(0)?,
            version_no: r.get(1)?,
            agreed_on: r.get(2)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}
