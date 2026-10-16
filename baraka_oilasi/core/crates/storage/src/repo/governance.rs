//! U13: vazifa hodisalari, ko'rik bayonnomalari, «katta foyda» qayta o'qish, nizolar, hakam
//! qarori, oilaviy kelishuv tasdig'i. Hammasi append-only: bu modulda yangilash yoki o'chirish yo'q.
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

fn all<T>(
    c: &Connection,
    sql: &str,
    args: &[&dyn rusqlite::ToSql],
    f: impl FnMut(&rusqlite::Row<'_>) -> rusqlite::Result<T>,
) -> Result<Vec<T>, StorageError> {
    let mut st = c.prepare(sql)?;
    let rows = st.query_map(args, f)?;
    Ok(rows.collect::<Result<_, _>>()?)
}

// ---- vazifa hodisalari ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IncidentRow {
    pub id: String,
    pub partnership_id: String,
    pub duty_id: String,
    pub party_id: String,
    pub reason: String,
    pub occurred_on: String,
    pub proposed_solution: Option<String>,
    pub journal_entry_id: String,
    pub resolved_on: Option<String>,
    pub resolution_note: Option<String>,
}

pub fn insert_incident(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    i: &IncidentRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO duty_incidents (id, partnership_id, duty_id, party_id, reason, occurred_on,
            proposed_solution, journal_entry_id, created_at, household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)",
        params![i.id, i.partnership_id, i.duty_id, i.party_id, i.reason, i.occurred_on,
            i.proposed_solution, i.journal_entry_id, m.now, s.household_id, s.space_id, m.device_id],
    )?;
    Ok(())
}

pub fn resolve_incident(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    incident_id: &str,
    resolved_on: &str,
    note: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO incident_resolutions (incident_id, resolved_on, note, created_at, household_id,
            space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![incident_id, resolved_on, note, m.now, s.household_id, s.space_id, m.device_id],
    )?;
    Ok(())
}

pub fn incidents(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<IncidentRow>, StorageError> {
    all(
        c,
        "SELECT i.id, i.partnership_id, i.duty_id, i.party_id, i.reason, i.occurred_on,
            i.proposed_solution, i.journal_entry_id, r.resolved_on, r.note
         FROM duty_incidents i LEFT JOIN incident_resolutions r ON r.incident_id = i.id
         WHERE i.household_id = ?1 AND i.space_id = ?2 AND i.partnership_id = ?3
         ORDER BY i.occurred_on, i.rowid",
        &[&s.household_id, &s.space_id, &partnership_id],
        |r| {
            Ok(IncidentRow {
                id: r.get(0)?,
                partnership_id: r.get(1)?,
                duty_id: r.get(2)?,
                party_id: r.get(3)?,
                reason: r.get(4)?,
                occurred_on: r.get(5)?,
                proposed_solution: r.get(6)?,
                journal_entry_id: r.get(7)?,
                resolved_on: r.get(8)?,
                resolution_note: r.get(9)?,
            })
        },
    )
}

// ---- ko'rik bayonnomalari ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReviewRow {
    pub id: String,
    pub partnership_id: String,
    pub review_no: i64,
    pub from_on: String,
    pub to_on: String,
    pub reason: String,
    pub chain_seq: i64,
    pub chain_head: String,
    pub summary_json: String,
    pub held_on: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AckRow {
    pub id: String,
    pub review_id: String,
    pub party_id: String,
    pub verdict: String,
    pub note: Option<String>,
    pub journal_entry_id: String,
}

pub fn insert_review(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &ReviewRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO account_reviews (id, partnership_id, review_no, from_on, to_on, reason, chain_seq,
            chain_head, summary_json, held_on, created_at, household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
        params![r.id, r.partnership_id, r.review_no, r.from_on, r.to_on, r.reason, r.chain_seq,
            r.chain_head, r.summary_json, r.held_on, m.now, s.household_id, s.space_id, m.device_id],
    )?;
    Ok(())
}

pub fn insert_ack(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    a: &AckRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO review_acks (id, review_id, party_id, verdict, note, journal_entry_id, created_at,
            household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![a.id, a.review_id, a.party_id, a.verdict, a.note, a.journal_entry_id, m.now,
            s.household_id, s.space_id, m.device_id],
    )?;
    Ok(())
}

pub fn reviews(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<ReviewRow>, StorageError> {
    all(
        c,
        "SELECT id, partnership_id, review_no, from_on, to_on, reason, chain_seq, chain_head,
            summary_json, held_on
         FROM account_reviews WHERE household_id = ?1 AND space_id = ?2 AND partnership_id = ?3
         ORDER BY review_no",
        &[&s.household_id, &s.space_id, &partnership_id],
        |r| {
            Ok(ReviewRow {
                id: r.get(0)?,
                partnership_id: r.get(1)?,
                review_no: r.get(2)?,
                from_on: r.get(3)?,
                to_on: r.get(4)?,
                reason: r.get(5)?,
                chain_seq: r.get(6)?,
                chain_head: r.get(7)?,
                summary_json: r.get(8)?,
                held_on: r.get(9)?,
            })
        },
    )
}

pub fn acks(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<AckRow>, StorageError> {
    all(
        c,
        "SELECT a.id, a.review_id, a.party_id, a.verdict, a.note, a.journal_entry_id
         FROM review_acks a JOIN account_reviews r ON r.id = a.review_id
         WHERE a.household_id = ?1 AND a.space_id = ?2 AND r.partnership_id = ?3 ORDER BY a.rowid",
        &[&s.household_id, &s.space_id, &partnership_id],
        |r| {
            Ok(AckRow {
                id: r.get(0)?,
                review_id: r.get(1)?,
                party_id: r.get(2)?,
                verdict: r.get(3)?,
                note: r.get(4)?,
                journal_entry_id: r.get(5)?,
            })
        },
    )
}

// ---- «katta foyda» ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RereadRow {
    pub id: String,
    pub partnership_id: String,
    pub period_no: i64,
    pub party_id: String,
    pub acked_on: String,
}

pub fn insert_reread(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    r: &RereadRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO spike_rereads (id, partnership_id, period_no, party_id, acked_on, created_at,
            household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![
            r.id,
            r.partnership_id,
            r.period_no,
            r.party_id,
            r.acked_on,
            m.now,
            s.household_id,
            s.space_id,
            m.device_id
        ],
    )?;
    Ok(())
}

/// Shu davr uchun 4–5-bandlarni qayta o'qigan tomonlar.
pub fn rereads(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
    period_no: i64,
) -> Result<Vec<String>, StorageError> {
    all(
        c,
        "SELECT party_id FROM spike_rereads WHERE household_id = ?1 AND space_id = ?2
         AND partnership_id = ?3 AND period_no = ?4 ORDER BY rowid",
        &[&s.household_id, &s.space_id, &partnership_id, &period_no],
        |r| r.get(0),
    )
}

// ---- nizolar ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DisputeRow {
    pub id: String,
    pub partnership_id: String,
    pub opened_on: String,
    pub opened_by_party: String,
    pub subject: String,
    pub clauses_json: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ClaimRow {
    pub dispute_id: String,
    pub party_id: String,
    pub claim: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DecisionRow {
    pub dispute_id: String,
    pub decided_on: String,
    pub arbiter_name: String,
    pub decision: String,
    pub outcome: String,
}

pub fn insert_dispute(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    d: &DisputeRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO disputes (id, partnership_id, opened_on, opened_by_party, subject, clauses_json,
            created_at, household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        params![d.id, d.partnership_id, d.opened_on, d.opened_by_party, d.subject, d.clauses_json,
            m.now, s.household_id, s.space_id, m.device_id],
    )?;
    Ok(())
}

pub fn insert_claim(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    c: &ClaimRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO dispute_claims (id, dispute_id, party_id, claim, created_at, household_id,
            space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        params![
            id,
            c.dispute_id,
            c.party_id,
            c.claim,
            m.now,
            s.household_id,
            s.space_id,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn insert_decision(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    d: &DecisionRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO arbiter_decisions (dispute_id, decided_on, arbiter_name, decision, outcome,
            created_at, household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![
            d.dispute_id,
            d.decided_on,
            d.arbiter_name,
            d.decision,
            d.outcome,
            m.now,
            s.household_id,
            s.space_id,
            m.device_id
        ],
    )?;
    Ok(())
}

pub fn disputes(
    c: &Connection,
    s: &SpaceScope,
    partnership_id: &str,
) -> Result<Vec<DisputeRow>, StorageError> {
    all(
        c,
        "SELECT id, partnership_id, opened_on, opened_by_party, subject, clauses_json FROM disputes
         WHERE household_id = ?1 AND space_id = ?2 AND partnership_id = ?3 ORDER BY rowid",
        &[&s.household_id, &s.space_id, &partnership_id],
        |r| {
            Ok(DisputeRow {
                id: r.get(0)?,
                partnership_id: r.get(1)?,
                opened_on: r.get(2)?,
                opened_by_party: r.get(3)?,
                subject: r.get(4)?,
                clauses_json: r.get(5)?,
            })
        },
    )
}

pub fn claims(
    c: &Connection,
    s: &SpaceScope,
    dispute_id: &str,
) -> Result<Vec<ClaimRow>, StorageError> {
    all(
        c,
        "SELECT dispute_id, party_id, claim FROM dispute_claims WHERE household_id = ?1
         AND space_id = ?2 AND dispute_id = ?3 ORDER BY rowid",
        &[&s.household_id, &s.space_id, &dispute_id],
        |r| {
            Ok(ClaimRow {
                dispute_id: r.get(0)?,
                party_id: r.get(1)?,
                claim: r.get(2)?,
            })
        },
    )
}

pub fn decision(
    c: &Connection,
    s: &SpaceScope,
    dispute_id: &str,
) -> Result<Option<DecisionRow>, StorageError> {
    Ok(c.query_row(
        "SELECT dispute_id, decided_on, arbiter_name, decision, outcome FROM arbiter_decisions
         WHERE household_id = ?1 AND space_id = ?2 AND dispute_id = ?3",
        params![s.household_id, s.space_id, dispute_id],
        |r| {
            Ok(DecisionRow {
                dispute_id: r.get(0)?,
                decided_on: r.get(1)?,
                arbiter_name: r.get(2)?,
                decision: r.get(3)?,
                outcome: r.get(4)?,
            })
        },
    )
    .optional()?)
}

// ---- oilaviy kelishuvlar ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FamilySignoffRow {
    pub member_id: String,
    pub payload_hash: String,
    pub agreed_on: String,
}

pub fn insert_family_signoff(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    id: &str,
    agreement_id: &str,
    f: &FamilySignoffRow,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO family_signoffs (id, agreement_id, member_id, payload_hash, agreed_on, created_at,
            household_id, space_id, origin_device_id)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        params![id, agreement_id, f.member_id, f.payload_hash, f.agreed_on, m.now, s.household_id,
            s.space_id, m.device_id],
    )?;
    Ok(())
}

pub fn family_signoffs(
    c: &Connection,
    s: &SpaceScope,
    agreement_id: &str,
) -> Result<Vec<FamilySignoffRow>, StorageError> {
    all(
        c,
        "SELECT member_id, payload_hash, agreed_on FROM family_signoffs WHERE household_id = ?1
         AND space_id = ?2 AND agreement_id = ?3 ORDER BY rowid",
        &[&s.household_id, &s.space_id, &agreement_id],
        |r| {
            Ok(FamilySignoffRow {
                member_id: r.get(0)?,
                payload_hash: r.get(1)?,
                agreed_on: r.get(2)?,
            })
        },
    )
}
