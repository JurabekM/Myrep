//! Append-only jurnal. Bu modulda yangilash yoki o'chirish funksiyasi **yo'q**.
use baraka_journal::{chain_hash, EntryKind, JournalAmount, JournalEntry, GENESIS_HASH};
use rusqlite::{params, Connection, OptionalExtension, Transaction};

use super::SpaceScope;
use crate::{Meta, StorageError};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StoredEntry {
    pub seq: i64,
    pub entry: JournalEntry,
    pub prev_hash: String,
    pub hash: String,
}

const COLS: &str =
    "seq, id, agreement_id, kind, party_id, amount_minor, currency, entry_date, note,
    corrects_entry_id, refs_json, prev_hash, hash";

/// Satrni o'qiydi. Buzilgan satr (noma'lum tur, yarim summa, noto'g'ri `refs_json`) — `CorruptRow`.
fn read_row(r: &rusqlite::Row<'_>) -> rusqlite::Result<Result<StoredEntry, StorageError>> {
    let kind: String = r.get(3)?;
    let amount_minor: Option<i64> = r.get(5)?;
    let currency: Option<String> = r.get(6)?;
    let refs_json: Option<String> = r.get(10)?;
    let amount = match (amount_minor, currency) {
        (Some(minor), Some(currency)) => Some(JournalAmount { minor, currency }),
        (None, None) => None,
        _ => return Ok(Err(StorageError::CorruptRow)),
    };
    let refs: Vec<String> = match refs_json.map(|j| serde_json::from_str(&j)) {
        Some(Ok(v)) => v,
        Some(Err(_)) => return Ok(Err(StorageError::CorruptRow)),
        None => Vec::new(),
    };
    let Some(kind) = EntryKind::parse(&kind) else {
        return Ok(Err(StorageError::CorruptRow));
    };
    Ok(Ok(StoredEntry {
        seq: r.get(0)?,
        entry: JournalEntry {
            id: r.get(1)?,
            agreement_id: r.get(2)?,
            kind,
            party_id: r.get(4)?,
            amount,
            date: r.get(7)?,
            note: r.get(8)?,
            corrects_entry_id: r.get(9)?,
            refs,
        },
        prev_hash: r.get(11)?,
        hash: r.get(12)?,
    }))
}

pub fn head(
    c: &Connection,
    s: &SpaceScope,
    agreement_id: &str,
) -> Result<(i64, String), StorageError> {
    let last: Option<(i64, String)> = c
        .query_row(
            "SELECT seq, hash FROM journal_entries WHERE household_id = ?1 AND space_id = ?2 AND agreement_id = ?3
             ORDER BY seq DESC LIMIT 1",
            params![s.household_id, s.space_id, agreement_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    Ok(last.unwrap_or((0, GENESIS_HASH.to_string())))
}

/// Yozuvni zanjir oxiriga qo'shadi: `seq` va `prev_hash` bazadagi joriy boshdan olinadi.
/// Chaqiruvchi `entry.validate()` ni oldindan tekshirgan bo'lishi kerak.
pub fn append(
    tx: &Transaction<'_>,
    s: &SpaceScope,
    entry: &JournalEntry,
    m: &Meta,
) -> Result<StoredEntry, StorageError> {
    let (last_seq, prev) = head(tx, s, &entry.agreement_id)?;
    let hash = chain_hash(&prev, entry);
    let seq = last_seq + 1;
    let refs_json = if entry.refs.is_empty() {
        None
    } else {
        Some(serde_json::to_string(&entry.refs).map_err(|_| StorageError::CorruptRow)?)
    };
    tx.execute(
        &format!(
            "INSERT INTO journal_entries ({COLS}, household_id, space_id, created_at, origin_device_id)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17)"
        ),
        params![seq, entry.id, entry.agreement_id, entry.kind.as_str(), entry.party_id,
            entry.amount.as_ref().map(|a| a.minor), entry.amount.as_ref().map(|a| a.currency.clone()),
            entry.date, entry.note, entry.corrects_entry_id, refs_json, prev, hash,
            s.household_id, s.space_id, m.now, m.device_id],
    )?;
    Ok(StoredEntry {
        seq,
        entry: entry.clone(),
        prev_hash: prev,
        hash,
    })
}

pub fn list(
    c: &Connection,
    s: &SpaceScope,
    agreement_id: &str,
) -> Result<Vec<StoredEntry>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {COLS} FROM journal_entries WHERE household_id = ?1 AND space_id = ?2 AND agreement_id = ?3 ORDER BY seq"
    ))?;
    let rows = st.query_map(params![s.household_id, s.space_id, agreement_id], read_row)?;
    let mut out = Vec::new();
    for r in rows {
        out.push(r??);
    }
    Ok(out)
}
