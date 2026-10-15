//! `.baraka` almashish: JSON eksport (to'liq yoki inkremental) va birlashtirib import (DESKTOP_PROMPT 6.3, D14).
//!
//! Qoidalar:
//! * yozuvlar `id` bo'yicha moslashtiriladi; `version` kattasi yutadi, teng bo'lsa `updated_at` kechrog'i;
//!   kiruvchi yutqazsa va farq qilsa — ziddiyat ro'yxatiga;
//! * `deleted_at` (tombstone) oddiy maydon sifatida o'tadi;
//! * jurnal (`journal_entries`): zanjir `check_import` va `verify_chain` bilan tekshiriladi — fork bo'lsa import
//!   butunlay to'xtaydi; faqat davomi qo'shiladi;
//! * yopilgan davrlar (`venture_periods`) va imzolar faqat qo'shiladi; mavjud yozuv farq qilsa — ogohlantirish;
//! * imzolangan kelishuvning shu versiyasi (`answers_json`) import orqali o'zgarmaydi.
//!
//! Sxema: `spec/interchange/export-format.schema.json` (mobil bilan umumiy).

use std::collections::BTreeMap;

use domain::interchange::check_import;
use domain::journal::{JournalEntry, JournalKind, verify_chain};
use money::{Currency, Money};
use rusqlite::types::{Value as SqlValue, ValueRef};
use rusqlite::{Connection, params_from_iter};
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};
use time::Date;
use time::format_description::well_known::Iso8601;

use crate::schema::TABLES;
use crate::{Database, StorageError};

/// Almashish formati nomi.
pub const FORMAT: &str = "baraka-interchange";
/// Almashish sxemasi versiyasi.
pub const SCHEMA_VERSION: u64 = 1;

/// Faqat qo'shiladigan jadvallar (mavjud yozuv o'zgartirilmaydi).
const APPEND_ONLY: [&str; 2] = ["venture_periods", "signatures"];

/// Ziddiyat: kiruvchi yozuv qabul qilinmadi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Conflict {
    /// Jadval.
    pub table: String,
    /// Yozuv identifikatori.
    pub id: String,
    /// Sabab kodi: `LOCAL_NEWER | CLOSED_PERIOD_DIFFERS | SIGNED_VERSION_DIFFERS | SIGNATURE_DIFFERS`.
    pub reason: String,
}

/// Zanjir ayrilishi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Fork {
    /// Kelishuv.
    pub agreement_id: String,
    /// Birinchi farq qilgan yozuv (1 dan); 0 — kiruvchi zanjirning o'zi buzilgan.
    pub first_broken: usize,
}

/// Import hisoboti (dry-run yoki haqiqiy).
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct ImportReport {
    /// Fork topildi — hech narsa yozilmadi.
    pub blocked: bool,
    /// Jadval bo'yicha qo'shilgan yozuvlar.
    pub inserted: BTreeMap<String, u32>,
    /// Jadval bo'yicha yangilangan yozuvlar.
    pub updated: BTreeMap<String, u32>,
    /// Ziddiyatlar.
    pub conflicts: Vec<Conflict>,
    /// Forklar.
    pub forks: Vec<Fork>,
    /// Jurnalga qo'shilgan yozuvlar.
    pub journal_appended: u32,
    /// Eksport vaqti (fayldan).
    pub exported_at: String,
    /// Eksport qurilmasi (fayldan).
    pub device_id: String,
}

fn columns(conn: &Connection, table: &str) -> Result<Vec<String>, StorageError> {
    let mut statement = conn.prepare(&format!("PRAGMA table_info({table})"))?;
    let rows = statement.query_map([], |row| row.get::<_, String>(1))?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

fn to_json(value: ValueRef<'_>) -> Value {
    match value {
        ValueRef::Null => Value::Null,
        ValueRef::Integer(i) => json!(i),
        ValueRef::Real(f) => serde_json::Number::from_f64(f).map_or(Value::Null, Value::Number),
        ValueRef::Text(t) => Value::String(String::from_utf8_lossy(t).into_owned()),
        ValueRef::Blob(b) => Value::String(format!(
            "$hex:{}",
            b.iter().map(|byte| format!("{byte:02x}")).collect::<String>()
        )),
    }
}

fn from_json(value: &Value) -> Result<SqlValue, StorageError> {
    Ok(match value {
        Value::Null => SqlValue::Null,
        Value::Bool(b) => SqlValue::Integer(i64::from(*b)),
        Value::Number(n) => n
            .as_i64()
            .map(SqlValue::Integer)
            .or_else(|| n.as_f64().map(SqlValue::Real))
            .ok_or_else(|| StorageError::InvalidData("son".to_owned()))?,
        Value::String(s) => match s.strip_prefix("$hex:") {
            Some(hex) => SqlValue::Blob(decode_hex(hex)?),
            None => SqlValue::Text(s.clone()),
        },
        Value::Array(_) | Value::Object(_) => {
            return Err(StorageError::InvalidData("ichki JSON qiymati".to_owned()));
        }
    })
}

fn decode_hex(hex: &str) -> Result<Vec<u8>, StorageError> {
    if !hex.len().is_multiple_of(2) {
        return Err(StorageError::InvalidData("hex".to_owned()));
    }
    (0..hex.len())
        .step_by(2)
        .map(|i| {
            u8::from_str_radix(&hex[i..i + 2], 16)
                .map_err(|_| StorageError::InvalidData("hex".to_owned()))
        })
        .collect()
}

/// Bazani JSON ko'rinishga eksport qiladi. `since` berilsa — faqat `updated_at` (yo'q bo'lsa `created_at`)
/// undan keyingi yozuvlar; ikkalasi ham bo'lmagan jadvallar to'liq chiqadi.
pub fn export_json(
    db: &Database,
    household_id: &str,
    device_id: &str,
    exported_at: &str,
    since: Option<&str>,
) -> Result<Value, StorageError> {
    let conn = db.connection();
    let mut tables = Map::new();
    for table in TABLES {
        let cols = columns(conn, table)?;
        let mut sql = format!("SELECT {} FROM {table}", cols.join(", "));
        let filter = since.and_then(|_| {
            if cols.iter().any(|c| c == "updated_at") {
                Some("updated_at")
            } else if cols.iter().any(|c| c == "created_at") {
                Some("created_at")
            } else {
                None
            }
        });
        if let Some(column) = filter {
            sql.push_str(&format!(" WHERE {column} > ?1"));
        }
        let mut statement = conn.prepare(&sql)?;
        let mut rows = match (filter, since) {
            (Some(_), Some(since)) => statement.query([since])?,
            _ => statement.query([])?,
        };
        let mut out = Vec::new();
        while let Some(row) = rows.next()? {
            let mut object = Map::new();
            for (index, name) in cols.iter().enumerate() {
                object.insert(name.clone(), to_json(row.get_ref(index)?));
            }
            out.push(Value::Object(object));
        }
        tables.insert((*table).to_owned(), Value::Array(out));
    }
    Ok(json!({
        "format": FORMAT,
        "schemaVersion": SCHEMA_VERSION,
        "exportedAt": exported_at,
        "deviceId": device_id,
        "householdId": household_id,
        "since": since,
        "tables": tables,
    }))
}

fn str_of<'a>(row: &'a Map<String, Value>, key: &str) -> Option<&'a str> {
    row.get(key).and_then(Value::as_str)
}

fn envelope(payload: &Value) -> Result<(&Map<String, Value>, String, String), StorageError> {
    let object = payload
        .as_object()
        .ok_or_else(|| StorageError::InvalidData("konteyner JSON emas".to_owned()))?;
    if object.get("format").and_then(Value::as_str) != Some(FORMAT)
        || object.get("schemaVersion").and_then(Value::as_u64) != Some(SCHEMA_VERSION)
    {
        return Err(StorageError::InvalidData("almashish formati".to_owned()));
    }
    let tables = object
        .get("tables")
        .and_then(Value::as_object)
        .ok_or_else(|| StorageError::InvalidData("tables".to_owned()))?;
    Ok((
        tables,
        object
            .get("exportedAt")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned(),
        object
            .get("deviceId")
            .and_then(Value::as_str)
            .unwrap_or_default()
            .to_owned(),
    ))
}

fn journal_entry(row: &Map<String, Value>) -> Result<JournalEntry, StorageError> {
    let kind = JournalKind::from_code(str_of(row, "kind").unwrap_or_default())
        .ok_or_else(|| StorageError::InvalidData("jurnal turi".to_owned()))?;
    let currency = Currency::from_iso(str_of(row, "currency").unwrap_or_default())
        .map_err(|_| StorageError::InvalidData("valyuta".to_owned()))?;
    let minor = row
        .get("amount_minor")
        .and_then(Value::as_i64)
        .ok_or_else(|| StorageError::InvalidData("summa".to_owned()))?;
    let date = Date::parse(str_of(row, "entry_date").unwrap_or_default(), &Iso8601::DATE)
        .map_err(|_| StorageError::InvalidData("sana".to_owned()))?;
    Ok(JournalEntry {
        id: str_of(row, "id").unwrap_or_default().to_owned(),
        agreement_id: str_of(row, "agreement_id").unwrap_or_default().to_owned(),
        kind,
        party_id: str_of(row, "party_id").unwrap_or_default().to_owned(),
        amount: Money::new(minor, currency),
        date,
        note: str_of(row, "note").map(str::to_owned),
    })
}

/// Importni bajaradi. `dry_run` — hamma narsa tranzaksiyada hisoblanadi, so'ng bekor qilinadi.
/// Fork topilsa — hech narsa yozilmaydi (`blocked`).
pub fn import_json(db: &Database, payload: &Value, dry_run: bool) -> Result<ImportReport, StorageError> {
    let (tables, exported_at, device_id) = envelope(payload)?;
    let conn = db.connection();
    let mut report = ImportReport {
        exported_at,
        device_id,
        ..ImportReport::default()
    };

    // 1. Jurnal: zanjirlar tekshiruvi (fork → to'xtash).
    let mut journal_rows: BTreeMap<String, Vec<&Map<String, Value>>> = BTreeMap::new();
    if let Some(rows) = tables.get("journal_entries").and_then(Value::as_array) {
        for row in rows.iter().filter_map(Value::as_object) {
            let agreement = str_of(row, "agreement_id").unwrap_or_default().to_owned();
            journal_rows.entry(agreement).or_default().push(row);
        }
    }
    let mut journal_append: Vec<(String, Vec<&Map<String, Value>>)> = Vec::new();
    for (agreement_id, mut rows) in journal_rows {
        rows.sort_by_key(|r| r.get("seq").and_then(Value::as_i64).unwrap_or(0));
        let incoming_hashes: Vec<String> = rows
            .iter()
            .map(|r| str_of(r, "hash").unwrap_or_default().to_owned())
            .collect();
        let entries = rows
            .iter()
            .map(|r| journal_entry(r))
            .collect::<Result<Vec<_>, _>>()?;
        if verify_chain(&entries, &incoming_hashes).is_err() {
            report.forks.push(Fork {
                agreement_id: agreement_id.clone(),
                first_broken: 0,
            });
            continue;
        }
        let mut statement = conn.prepare(
            "SELECT hash FROM journal_entries WHERE agreement_id = ?1 ORDER BY seq",
        )?;
        let local: Vec<String> = statement
            .query_map([agreement_id.as_str()], |row| row.get(0))?
            .collect::<Result<_, _>>()?;
        match check_import(&local, &incoming_hashes) {
            Err(first_broken) => report.forks.push(Fork {
                agreement_id: agreement_id.clone(),
                first_broken,
            }),
            Ok(()) => {
                if incoming_hashes.len() > local.len() {
                    journal_append.push((agreement_id, rows[local.len()..].to_vec()));
                }
            }
        }
    }
    if !report.forks.is_empty() {
        report.blocked = true;
        return Ok(report);
    }

    let tx = conn.unchecked_transaction()?;
    for table in TABLES {
        if *table == "journal_entries" {
            continue;
        }
        let Some(rows) = tables.get(*table).and_then(Value::as_array) else {
            continue;
        };
        let cols = columns(&tx, table)?;
        let has_id = cols.iter().any(|c| c == "id");
        for row in rows.iter().filter_map(Value::as_object) {
            let present: Vec<&String> = cols.iter().filter(|c| row.contains_key(*c)).collect();
            if present.is_empty() {
                continue;
            }
            let values = present
                .iter()
                .map(|c| from_json(row.get(*c).unwrap_or(&Value::Null)))
                .collect::<Result<Vec<_>, _>>()?;
            if !has_id {
                let placeholders = (1..=present.len())
                    .map(|i| format!("?{i}"))
                    .collect::<Vec<_>>()
                    .join(", ");
                let names = present.iter().map(|c| c.as_str()).collect::<Vec<_>>().join(", ");
                let changed = tx.execute(
                    &format!("INSERT OR IGNORE INTO {table} ({names}) VALUES ({placeholders})"),
                    params_from_iter(values.iter()),
                )?;
                if changed > 0 {
                    *report.inserted.entry((*table).to_owned()).or_default() += 1;
                }
                continue;
            }
            let id = str_of(row, "id").unwrap_or_default().to_owned();
            let local = local_row(&tx, table, &cols, &id)?;
            match local {
                None => {
                    let placeholders = (1..=present.len())
                        .map(|i| format!("?{i}"))
                        .collect::<Vec<_>>()
                        .join(", ");
                    let names = present.iter().map(|c| c.as_str()).collect::<Vec<_>>().join(", ");
                    tx.execute(
                        &format!("INSERT INTO {table} ({names}) VALUES ({placeholders})"),
                        params_from_iter(values.iter()),
                    )?;
                    *report.inserted.entry((*table).to_owned()).or_default() += 1;
                }
                Some(existing) => {
                    let differs = present
                        .iter()
                        .any(|c| existing.get(*c) != row.get(*c));
                    if !differs {
                        continue;
                    }
                    if APPEND_ONLY.contains(table) {
                        report.conflicts.push(Conflict {
                            table: (*table).to_owned(),
                            id,
                            reason: if *table == "venture_periods" {
                                "CLOSED_PERIOD_DIFFERS".to_owned()
                            } else {
                                "SIGNATURE_DIFFERS".to_owned()
                            },
                        });
                        continue;
                    }
                    if !incoming_wins(&existing, row) {
                        report.conflicts.push(Conflict {
                            table: (*table).to_owned(),
                            id,
                            reason: "LOCAL_NEWER".to_owned(),
                        });
                        continue;
                    }
                    if *table == "agreements"
                        && existing.get("status").and_then(Value::as_str) == Some("SIGNED")
                        && existing.get("version") == row.get("version")
                        && existing.get("answers_json") != row.get("answers_json")
                    {
                        report.conflicts.push(Conflict {
                            table: (*table).to_owned(),
                            id,
                            reason: "SIGNED_VERSION_DIFFERS".to_owned(),
                        });
                        continue;
                    }
                    let assignments = present
                        .iter()
                        .enumerate()
                        .filter(|(_, c)| c.as_str() != "id")
                        .map(|(i, c)| format!("{c} = ?{}", i + 1))
                        .collect::<Vec<_>>()
                        .join(", ");
                    let mut bound = values.clone();
                    bound.push(SqlValue::Text(id.clone()));
                    tx.execute(
                        &format!(
                            "UPDATE {table} SET {assignments} WHERE id = ?{}",
                            present.len() + 1
                        ),
                        params_from_iter(bound.iter()),
                    )?;
                    *report.updated.entry((*table).to_owned()).or_default() += 1;
                }
            }
        }
    }
    // 2. Jurnal davomi (zanjir tekshirilgan).
    let journal_cols = columns(&tx, "journal_entries")?;
    for (_, rows) in journal_append {
        for row in rows {
            let present: Vec<&String> = journal_cols
                .iter()
                .filter(|c| row.contains_key(*c))
                .collect();
            let values = present
                .iter()
                .map(|c| from_json(row.get(*c).unwrap_or(&Value::Null)))
                .collect::<Result<Vec<_>, _>>()?;
            let placeholders = (1..=present.len())
                .map(|i| format!("?{i}"))
                .collect::<Vec<_>>()
                .join(", ");
            let names = present.iter().map(|c| c.as_str()).collect::<Vec<_>>().join(", ");
            tx.execute(
                &format!("INSERT INTO journal_entries ({names}) VALUES ({placeholders})"),
                params_from_iter(values.iter()),
            )?;
            report.journal_appended += 1;
        }
    }
    if dry_run {
        tx.rollback()?;
    } else {
        tx.commit()?;
    }
    Ok(report)
}

fn local_row(
    conn: &Connection,
    table: &str,
    cols: &[String],
    id: &str,
) -> Result<Option<Map<String, Value>>, StorageError> {
    let mut statement = conn.prepare(&format!(
        "SELECT {} FROM {table} WHERE id = ?1",
        cols.join(", ")
    ))?;
    let mut rows = statement.query([id])?;
    let Some(row) = rows.next()? else {
        return Ok(None);
    };
    let mut object = Map::new();
    for (index, name) in cols.iter().enumerate() {
        object.insert(name.clone(), to_json(row.get_ref(index)?));
    }
    Ok(Some(object))
}

/// `version` kattasi yutadi; teng bo'lsa `updated_at` kechrog'i; ikkalasi ham yo'q bo'lsa — kiruvchi yutadi.
fn incoming_wins(local: &Map<String, Value>, incoming: &Map<String, Value>) -> bool {
    let version = |row: &Map<String, Value>| row.get("version").and_then(Value::as_i64);
    match (version(local), version(incoming)) {
        (Some(l), Some(i)) if l != i => return i > l,
        _ => {}
    }
    let updated = |row: &Map<String, Value>| {
        row.get("updated_at")
            .and_then(Value::as_str)
            .map(str::to_owned)
    };
    match (updated(local), updated(incoming)) {
        (Some(l), Some(i)) => i >= l,
        _ => true,
    }
}
