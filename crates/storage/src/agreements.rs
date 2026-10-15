//! D8A repo'lari: kelishuvlar (versiyali) va append-only jurnal (xesh zanjiri bilan, SPEC 2F.6).
//!
//! Jurnalga yozish bitta tranzaksiyada: oldingi xesh bazadan olinadi, yangi xesh hisoblanadi va yoziladi.
//! `UPDATE`/`DELETE` DB triggerlari bilan rad etiladi (sxema v8); bu repo ularni chaqirmaydi.

use domain::agreement::{AgreementStatus, AgreementType};
use domain::journal::{
    ChainBroken, GENESIS_HASH, JournalEntry, JournalKind, link_hash, verify_chain,
};
use money::{Currency, Money};
use rusqlite::{Connection, OptionalExtension, Row, params};
use time::OffsetDateTime;

use crate::StorageError;
use crate::finance::{format_date, parse_date};
use crate::repo::{format_ts, parse_ts};

fn money_of(minor: i64, currency: &str) -> Result<Money, StorageError> {
    let currency = Currency::from_iso(currency)
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    Ok(Money::new(minor, currency))
}

/// Kelishuv yozuvi (javoblar JSON satri sifatida saqlanadi; tuzilishi ilova qatlamida).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgreementRow {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Turi.
    pub kind: AgreementType,
    /// Sarlavha.
    pub title: String,
    /// Holati.
    pub status: AgreementStatus,
    /// Versiya (har o'zgarishda oshadi; birinchi — 1).
    pub version: i64,
    /// Javoblar (JSON).
    pub answers_json: String,
    /// Yaratilgan vaqt.
    pub created_at: OffsetDateTime,
    /// Oxirgi o'zgarish vaqti.
    pub updated_at: OffsetDateTime,
    /// Yaratgan qurilma.
    pub origin_device_id: String,
}

/// Kelishuvlar.
pub struct AgreementRepo<'a> {
    conn: &'a Connection,
}

impl<'a> AgreementRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yangi kelishuv qo'shadi.
    pub fn insert(&self, row: &AgreementRow) -> Result<(), StorageError> {
        self.conn.execute(
            "INSERT INTO agreements (id, household_id, type, title, status, version, answers_json, created_at, updated_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
            params![
                row.id,
                row.household_id,
                row.kind.code(),
                row.title,
                row.status.code(),
                row.version,
                row.answers_json,
                format_ts(row.created_at)?,
                format_ts(row.updated_at)?,
                row.origin_device_id,
            ],
        )?;
        Ok(())
    }

    /// Bitta kelishuv.
    pub fn find(&self, id: &str) -> Result<Option<AgreementRow>, StorageError> {
        self.conn
            .query_row(
                "SELECT id, household_id, type, title, status, version, answers_json, created_at, updated_at, origin_device_id \
                 FROM agreements WHERE id = ?1 AND deleted_at IS NULL",
                [id],
                read_agreement,
            )
            .optional()?
            .map(RawAgreement::into_row)
            .transpose()
    }

    /// Xonadonning kelishuvlari, yaratilish tartibida.
    pub fn list(&self, household_id: &str) -> Result<Vec<AgreementRow>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT id, household_id, type, title, status, version, answers_json, created_at, updated_at, origin_device_id \
             FROM agreements WHERE household_id = ?1 AND deleted_at IS NULL ORDER BY created_at, id",
        )?;
        let rows = statement.query_map([household_id], read_agreement)?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?.into_row()?);
        }
        Ok(out)
    }

    /// Javoblar va holatni yangilaydi; versiya bir pog'ona oshadi. `expected_version` mos kelmasa — `VersionConflict`.
    pub fn update_answers(
        &self,
        id: &str,
        expected_version: i64,
        status: AgreementStatus,
        answers_json: &str,
        now: OffsetDateTime,
    ) -> Result<i64, StorageError> {
        let changed = self.conn.execute(
            "UPDATE agreements SET status = ?3, version = version + 1, answers_json = ?4, updated_at = ?5 \
             WHERE id = ?1 AND version = ?2 AND deleted_at IS NULL",
            params![
                id,
                expected_version,
                status.code(),
                answers_json,
                format_ts(now)?,
            ],
        )?;
        if changed == 1 {
            return Ok(expected_version + 1);
        }
        Err(match self.find(id)? {
            Some(_) => StorageError::VersionConflict,
            None => StorageError::NotFound,
        })
    }
}

struct RawAgreement {
    id: String,
    household_id: String,
    kind: String,
    title: String,
    status: String,
    version: i64,
    answers_json: String,
    created_at: String,
    updated_at: String,
    origin_device_id: String,
}

fn read_agreement(row: &Row<'_>) -> rusqlite::Result<RawAgreement> {
    Ok(RawAgreement {
        id: row.get(0)?,
        household_id: row.get(1)?,
        kind: row.get(2)?,
        title: row.get(3)?,
        status: row.get(4)?,
        version: row.get(5)?,
        answers_json: row.get(6)?,
        created_at: row.get(7)?,
        updated_at: row.get(8)?,
        origin_device_id: row.get(9)?,
    })
}

impl RawAgreement {
    fn into_row(self) -> Result<AgreementRow, StorageError> {
        Ok(AgreementRow {
            id: self.id,
            household_id: self.household_id,
            kind: AgreementType::from_code(&self.kind)
                .ok_or_else(|| StorageError::InvalidData("kelishuv turi".to_owned()))?,
            title: self.title,
            status: AgreementStatus::from_code(&self.status)
                .ok_or_else(|| StorageError::InvalidData("kelishuv holati".to_owned()))?,
            version: self.version,
            answers_json: self.answers_json,
            created_at: parse_ts(&self.created_at)?,
            updated_at: parse_ts(&self.updated_at)?,
            origin_device_id: self.origin_device_id,
        })
    }
}

/// Saqlangan jurnal yozuvi: domen yozuvi, uning xeshi va oldingi xeshi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoredEntry {
    /// Tartib raqami (1 dan).
    pub seq: i64,
    /// Yozuv.
    pub entry: JournalEntry,
    /// Oldingi xesh (birinchisi — genesis).
    pub prev_hash: String,
    /// Shu yozuvning xeshi.
    pub hash: String,
}

/// Append-only jurnal.
pub struct JournalRepo<'a> {
    conn: &'a Connection,
}

impl<'a> JournalRepo<'a> {
    /// Ulanish ustida repo.
    pub fn new(conn: &'a Connection) -> Self {
        Self { conn }
    }

    /// Yozuvni zanjirga qo'shadi. Yangi xesh qaytariladi.
    pub fn append(
        &self,
        household_id: &str,
        entry: &JournalEntry,
        created_at: OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<String, StorageError> {
        let agreement = entry.agreement_id.as_str();
        let tx = self.conn.unchecked_transaction()?;
        let last_seq: i64 = tx.query_row(
            "SELECT COALESCE(MAX(seq), 0) FROM journal_entries WHERE agreement_id = ?1",
            [agreement],
            |row| row.get(0),
        )?;
        let prev_hash = if last_seq == 0 {
            GENESIS_HASH.to_owned()
        } else {
            tx.query_row(
                "SELECT hash FROM journal_entries WHERE agreement_id = ?1 AND seq = ?2",
                params![agreement, last_seq],
                |row| row.get(0),
            )?
        };
        let hash = link_hash(&prev_hash, entry);
        tx.execute(
            "INSERT INTO journal_entries (id, household_id, agreement_id, seq, kind, party_id, amount_minor, currency, entry_date, note, prev_hash, hash, created_at, origin_device_id) \
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
            params![
                entry.id,
                household_id,
                agreement,
                last_seq + 1,
                entry.kind.code(),
                entry.party_id,
                entry.amount.minor(),
                entry.amount.currency().iso_code(),
                format_date(entry.date)?,
                entry.note,
                prev_hash,
                hash,
                format_ts(created_at)?,
                origin_device_id,
            ],
        )?;
        tx.commit()?;
        Ok(hash)
    }

    /// Kelishuv jurnali, tartib bo'yicha.
    pub fn list(&self, agreement_id: &str) -> Result<Vec<StoredEntry>, StorageError> {
        let mut statement = self.conn.prepare(
            "SELECT seq, id, agreement_id, kind, party_id, amount_minor, currency, entry_date, note, prev_hash, hash \
             FROM journal_entries WHERE agreement_id = ?1 ORDER BY seq",
        )?;
        let rows = statement.query_map([agreement_id], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
                row.get::<_, String>(4)?,
                row.get::<_, i64>(5)?,
                row.get::<_, String>(6)?,
                row.get::<_, String>(7)?,
                row.get::<_, Option<String>>(8)?,
                row.get::<_, String>(9)?,
                row.get::<_, String>(10)?,
            ))
        })?;
        let mut out = Vec::new();
        for row in rows {
            let (seq, id, agreement, kind, party, minor, currency, date, note, prev_hash, hash) =
                row?;
            let kind = JournalKind::from_code(&kind)
                .ok_or_else(|| StorageError::InvalidData("jurnal turi".to_owned()))?;
            out.push(StoredEntry {
                seq,
                entry: JournalEntry {
                    id,
                    agreement_id: agreement,
                    kind,
                    party_id: party,
                    amount: money_of(minor, &currency)?,
                    date: parse_date(&date)?,
                    note,
                },
                prev_hash,
                hash,
            });
        }
        Ok(out)
    }

    /// Zanjirni tekshiradi. Ichki `Ok(Err(..))` — zanjir buzilgan (birinchi buzilgan yozuv, 1 dan).
    /// Tashqi `Err` — baza xatosi: u zanjir buzilishi deb talqin qilinmaydi.
    pub fn verify(&self, agreement_id: &str) -> Result<Result<(), ChainBroken>, StorageError> {
        let stored = self.list(agreement_id)?;
        let entries: Vec<JournalEntry> = stored.iter().map(|item| item.entry.clone()).collect();
        let hashes: Vec<String> = stored.iter().map(|item| item.hash.clone()).collect();
        Ok(verify_chain(&entries, &hashes))
    }
}
