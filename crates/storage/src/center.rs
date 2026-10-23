//! D13A repo: kelishuvlar markazi — vazifa hodisalari, ochiq hisob ko'riklari va belgilar, nizolar,
//! oilaviy tasdiqlar, versiya izohlari (sxema v15). Hammasi kelishuvga bog'langan; yozuvlar o'chirilmaydi.

use rusqlite::{Connection, OptionalExtension, Row, params};
use time::{Date, OffsetDateTime};

use crate::StorageError;
use crate::finance::{format_date, parse_date};
use crate::repo::{format_ts, parse_ts};

/// Vazifa hodisasi («bajara olmayapman»).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IncidentRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Kelishuv.
    pub agreement_id: String,
    /// Vazifa (`duties[].id`).
    pub duty_id: String,
    /// Xabar bergan tomon.
    pub party_id: String,
    /// Sabab.
    pub reason: String,
    /// Taklif qilingan yechim.
    pub proposed_fix: Option<String>,
    /// Sana.
    pub occurred_on: Date,
    /// Yopilgan vaqt.
    pub resolved_at: Option<OffsetDateTime>,
    /// Yozilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Ochiq hisob ko'rigi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReviewRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Kelishuv.
    pub agreement_id: String,
    /// Davr boshi.
    pub period_start: Date,
    /// Davr oxiri.
    pub period_end: Date,
    /// O'sha paytdagi zanjir boshi.
    pub chain_head: String,
    /// Zanjir tekshiruvi natijasi.
    pub chain_ok: bool,
    /// Yaratilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Tomon belgisi: `AGREE` yoki `OBJECT` (izoh bilan).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MarkRow {
    /// Tomon.
    pub party_id: String,
    /// Qaror.
    pub decision: String,
    /// Izoh.
    pub comment: Option<String>,
}

/// Nizo.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DisputeRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon.
    pub household_id: String,
    /// Kelishuv.
    pub agreement_id: String,
    /// Ochgan tomon.
    pub opened_by_party_id: String,
    /// Mavzu.
    pub subject: String,
    /// Tegishli bandlar.
    pub clauses: String,
    /// Talab.
    pub claim: String,
    /// Ochilgan sana.
    pub opened_on: Date,
    /// Hakam qarori.
    pub decision: Option<String>,
    /// Qaror sanasi.
    pub decided_on: Option<Date>,
    /// Yozilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Qurilma.
    pub origin_device_id: String,
}

/// Markaz repo'si.
pub struct CenterRepo<'a> {
    conn: &'a Connection,
}

impl<'a> CenterRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Hodisa yozadi.
    pub fn insert_incident(&self, row: &IncidentRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO duty_incidents (id, household_id, agreement_id, duty_id, party_id, reason, proposed_fix, \
             occurred_on, resolved_at, created_at, origin_device_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, NULL, ?9, ?10)",
            params![
                row.id,
                row.household_id,
                row.agreement_id,
                row.duty_id,
                row.party_id,
                row.reason,
                row.proposed_fix,
                format_date(row.occurred_on)?,
                format_ts(row.created_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Hodisani yopadi; kelishuv identifikatorini qaytaradi.
    pub fn resolve_incident(&self, id: &str, now: OffsetDateTime) -> Result<String, StorageError> {
        let agreement_id: Option<String> = self
            .conn
            .query_row(
                "SELECT agreement_id FROM duty_incidents WHERE id = ?1",
                [id],
                |row| row.get(0),
            )
            .optional()?;
        let agreement_id = agreement_id.ok_or(StorageError::NotFound)?;
        self.conn.execute(
            "UPDATE duty_incidents SET resolved_at = ?2 WHERE id = ?1 AND resolved_at IS NULL",
            params![id, format_ts(now)?],
        )?;
        Ok(agreement_id)
    }

    /// Kelishuv hodisalari (yangidan eskiga).
    pub fn incidents(&self, agreement_id: &str) -> Result<Vec<IncidentRow>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, agreement_id, duty_id, party_id, reason, proposed_fix, occurred_on, resolved_at, \
             created_at, origin_device_id FROM duty_incidents WHERE agreement_id = ?1 ORDER BY created_at DESC, id",
        )?;
        let rows = statement.query_map([agreement_id], read_incident)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }

    /// Ochiq hodisalar soni.
    pub fn open_incident_count(&self, agreement_id: &str) -> Result<u32, StorageError> {
        let count: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM duty_incidents WHERE agreement_id = ?1 AND resolved_at IS NULL",
            [agreement_id],
            |row| row.get(0),
        )?;
        Ok(u32::try_from(count).unwrap_or(u32::MAX))
    }

    /// Ko'rik yozadi.
    pub fn insert_review(&self, row: &ReviewRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO reviews (id, household_id, agreement_id, period_start, period_end, chain_head, chain_ok, \
             created_at, origin_device_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
            params![
                row.id,
                row.household_id,
                row.agreement_id,
                format_date(row.period_start)?,
                format_date(row.period_end)?,
                row.chain_head,
                i32::from(row.chain_ok),
                format_ts(row.created_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Bitta ko'rik.
    pub fn find_review(&self, id: &str) -> Result<Option<ReviewRow>, StorageError> {
        self.conn
            .query_row(&format!("{REVIEW_SELECT} WHERE id = ?1"), [id], read_review)
            .optional()?
            .transpose()
    }

    /// Kelishuv ko'riklari (eskidan yangiga).
    pub fn reviews(&self, agreement_id: &str) -> Result<Vec<ReviewRow>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{REVIEW_SELECT} WHERE agreement_id = ?1 ORDER BY created_at, id"
        ))?;
        let rows = statement.query_map([agreement_id], read_review)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row??);
        }
        Ok(out)
    }

    /// Tomon belgisini yozadi (qayta yozish mumkin — oxirgi fikr qoladi).
    pub fn upsert_mark(
        &self,
        review_id: &str,
        mark: &MarkRow,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO review_marks (review_id, party_id, decision, comment, created_at) VALUES (?1, ?2, ?3, ?4, ?5) \
             ON CONFLICT (review_id, party_id) DO UPDATE SET decision = excluded.decision, comment = excluded.comment, \
             created_at = excluded.created_at",
            params![
                review_id,
                mark.party_id,
                mark.decision,
                mark.comment,
                format_ts(now)?
            ],
        )?;
        Ok(())
    }

    /// Ko'rik belgilari.
    pub fn marks(&self, review_id: &str) -> Result<Vec<MarkRow>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT party_id, decision, comment FROM review_marks WHERE review_id = ?1 ORDER BY party_id",
        )?;
        let rows = statement.query_map([review_id], |row| {
            Ok(MarkRow {
                party_id: row.get(0)?,
                decision: row.get(1)?,
                comment: row.get(2)?,
            })
        })?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }

    /// Nizo yozadi.
    pub fn insert_dispute(&self, row: &DisputeRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO disputes (id, household_id, agreement_id, opened_by_party_id, subject, clauses, claim, opened_on, \
             decision, decided_on, created_at, origin_device_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, NULL, NULL, ?9, ?10)",
            params![
                row.id,
                row.household_id,
                row.agreement_id,
                row.opened_by_party_id,
                row.subject,
                row.clauses,
                row.claim,
                format_date(row.opened_on)?,
                format_ts(row.created_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Hakam qarorini yozadi.
    pub fn decide_dispute(
        &self,
        id: &str,
        decision: &str,
        decided_on: Date,
    ) -> Result<(), StorageError> {
        let changed = self.conn.execute(
            "UPDATE disputes SET decision = ?2, decided_on = ?3 WHERE id = ?1 AND decision IS NULL",
            params![id, decision, format_date(decided_on)?],
        )?;
        if changed == 0 {
            return Err(StorageError::NotFound);
        }
        Ok(())
    }

    /// Bitta nizo.
    pub fn find_dispute(&self, id: &str) -> Result<Option<DisputeRow>, StorageError> {
        self.conn
            .query_row(
                &format!("{DISPUTE_SELECT} WHERE id = ?1"),
                [id],
                read_dispute,
            )
            .optional()?
            .transpose()
    }

    /// Kelishuv nizolari (eskidan yangiga).
    pub fn disputes(&self, agreement_id: &str) -> Result<Vec<DisputeRow>, StorageError> {
        let mut statement = self.conn.prepare(&format!(
            "{DISPUTE_SELECT} WHERE agreement_id = ?1 ORDER BY created_at, id"
        ))?;
        let rows = statement.query_map([agreement_id], read_dispute)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row??);
        }
        Ok(out)
    }

    /// Ochiq nizolar soni.
    pub fn open_dispute_count(&self, agreement_id: &str) -> Result<u32, StorageError> {
        let count: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM disputes WHERE agreement_id = ?1 AND decision IS NULL",
            [agreement_id],
            |row| row.get(0),
        )?;
        Ok(u32::try_from(count).unwrap_or(u32::MAX))
    }

    /// Oilaviy tasdiq (a'zo, versiya).
    pub fn insert_family_consent(
        &self,
        agreement_id: &str,
        member_id: &str,
        version: i64,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT OR IGNORE INTO family_consents (agreement_id, member_id, version, created_at) VALUES (?1, ?2, ?3, ?4)",
            params![agreement_id, member_id, version, format_ts(now)?],
        )?;
        Ok(())
    }

    /// Versiya uchun tasdiqlagan a'zolar.
    pub fn family_consents(
        &self,
        agreement_id: &str,
        version: i64,
    ) -> Result<Vec<String>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT member_id FROM family_consents WHERE agreement_id = ?1 AND version = ?2 ORDER BY created_at",
        )?;
        let rows = statement.query_map(params![agreement_id, version], |row| {
            row.get::<_, String>(0)
        })?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }

    /// Versiya izohi (masalan, «o'zgarishsiz tasdiqlandi» yoki hakam qarori).
    pub fn insert_version_note(
        &self,
        agreement_id: &str,
        version: i64,
        note: &str,
        now: OffsetDateTime,
    ) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT OR REPLACE INTO version_notes (agreement_id, version, note, created_at) VALUES (?1, ?2, ?3, ?4)",
            params![agreement_id, version, note, format_ts(now)?],
        )?;
        Ok(())
    }

    /// Versiya izohlari (versiya tartibida): (versiya, izoh, vaqt).
    pub fn version_notes(
        &self,
        agreement_id: &str,
    ) -> Result<Vec<(i64, String, OffsetDateTime)>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT version, note, created_at FROM version_notes WHERE agreement_id = ?1 ORDER BY version",
        )?;
        let rows = statement.query_map([agreement_id], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (version, note, created) = row?;
            out.push((version, note, parse_ts(&created)?));
        }
        Ok(out)
    }
}

fn read_incident(row: &Row<'_>) -> rusqlite::Result<IncidentRow> {
    let occurred: String = row.get(7)?;
    let resolved: Option<String> = row.get(8)?;
    let created: String = row.get(9)?;
    Ok(IncidentRow {
        id: row.get(0)?,
        household_id: row.get(1)?,
        agreement_id: row.get(2)?,
        duty_id: row.get(3)?,
        party_id: row.get(4)?,
        reason: row.get(5)?,
        proposed_fix: row.get(6)?,
        occurred_on: parse_date(&occurred).map_err(to_sql_error)?,
        resolved_at: resolved
            .as_deref()
            .map(parse_ts)
            .transpose()
            .map_err(to_sql_error)?,
        created_at: parse_ts(&created).map_err(to_sql_error)?,
        origin_device_id: row.get(10)?,
    })
}

const REVIEW_SELECT: &str = "SELECT id, household_id, agreement_id, period_start, period_end, chain_head, chain_ok, created_at, \
    origin_device_id FROM reviews";

fn read_review(row: &Row<'_>) -> rusqlite::Result<Result<ReviewRow, StorageError>> {
    let start: String = row.get(3)?;
    let end: String = row.get(4)?;
    let chain_ok: i64 = row.get(6)?;
    let created: String = row.get(7)?;
    let id: String = row.get(0)?;
    let household_id: String = row.get(1)?;
    let agreement_id: String = row.get(2)?;
    let chain_head: String = row.get(5)?;
    let origin_device_id: String = row.get(8)?;
    Ok((|| {
        Ok(ReviewRow {
            id,
            household_id,
            agreement_id,
            period_start: parse_date(&start)?,
            period_end: parse_date(&end)?,
            chain_head,
            chain_ok: chain_ok != 0,
            created_at: parse_ts(&created)?,
            origin_device_id,
        })
    })())
}

const DISPUTE_SELECT: &str = "SELECT id, household_id, agreement_id, opened_by_party_id, subject, clauses, claim, opened_on, \
    decision, decided_on, created_at, origin_device_id FROM disputes";

fn read_dispute(row: &Row<'_>) -> rusqlite::Result<Result<DisputeRow, StorageError>> {
    let opened: String = row.get(7)?;
    let decided: Option<String> = row.get(9)?;
    let created: String = row.get(10)?;
    let id: String = row.get(0)?;
    let household_id: String = row.get(1)?;
    let agreement_id: String = row.get(2)?;
    let opened_by_party_id: String = row.get(3)?;
    let subject: String = row.get(4)?;
    let clauses: String = row.get(5)?;
    let claim: String = row.get(6)?;
    let decision: Option<String> = row.get(8)?;
    let origin_device_id: String = row.get(11)?;
    Ok((|| {
        Ok(DisputeRow {
            id,
            household_id,
            agreement_id,
            opened_by_party_id,
            subject,
            clauses,
            claim,
            opened_on: parse_date(&opened)?,
            decision,
            decided_on: decided.as_deref().map(parse_date).transpose()?,
            created_at: parse_ts(&created)?,
            origin_device_id,
        })
    })())
}

fn to_sql_error(error: StorageError) -> rusqlite::Error {
    rusqlite::Error::FromSqlConversionFailure(0, rusqlite::types::Type::Text, Box::new(error))
}
