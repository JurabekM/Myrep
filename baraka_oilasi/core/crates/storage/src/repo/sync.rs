//! `.baraka` sinxronlash uchun umumiy yozuv o'qish/yozish va holat jadvallari (U14).
//!
//! Jadval ro'yxati `baraka_interchange::tables` dan (sxema fayli). Jadval va ustun nomlari
//! faqat shu ro'yxat va mahalliy `PRAGMA table_info` bilan solishtirilgandan keyin SQL'ga
//! qo'yiladi; qiymatlar — doim parametr sifatida.
use std::collections::HashMap;

use baraka_interchange::canon::{blob, blob_bytes, Row};
use baraka_interchange::tables::{self, TableMode, TableSpec};
use rusqlite::types::{Value as SqlValue, ValueRef};
use rusqlite::{params, Connection, OptionalExtension, Transaction};
use serde_json::Value;

use crate::{Meta, StorageError};

/// Jadval ustunlari (mahalliy sxema bo'yicha), jadval nomi ro'yxatda bo'lishi shart.
pub fn columns(c: &Connection, table: &str) -> Result<Vec<String>, StorageError> {
    let spec = tables::table(table).ok_or(StorageError::SchemaMismatch)?;
    let mut st = c.prepare(&format!("PRAGMA table_info({})", spec.name))?;
    let cols = st
        .query_map([], |r| r.get::<_, String>(1))?
        .collect::<Result<Vec<_>, _>>()?;
    if cols.is_empty() {
        return Err(StorageError::SchemaMismatch);
    }
    Ok(cols)
}

fn to_json(v: ValueRef<'_>) -> Result<Value, StorageError> {
    Ok(match v {
        ValueRef::Null => Value::Null,
        ValueRef::Integer(i) => Value::from(i),
        ValueRef::Text(t) => Value::String(
            std::str::from_utf8(t)
                .map_err(|_| StorageError::CorruptRow)?
                .into(),
        ),
        ValueRef::Blob(b) => blob(b),
        // Pul va sanalar butun son yoki matn — kasr son bazada bo'lmasligi kerak.
        ValueRef::Real(_) => return Err(StorageError::CorruptRow),
    })
}

fn to_sql(v: &Value) -> Result<SqlValue, StorageError> {
    Ok(match v {
        Value::Null => SqlValue::Null,
        Value::Number(n) => SqlValue::Integer(n.as_i64().ok_or(StorageError::CorruptRow)?),
        Value::String(s) => SqlValue::Text(s.clone()),
        Value::Object(_) => SqlValue::Blob(blob_bytes(v).ok_or(StorageError::CorruptRow)?),
        Value::Bool(_) | Value::Array(_) => return Err(StorageError::CorruptRow),
    })
}

/// Xonadon filtri: `households` da — `id`, qolganlarida — `household_id`.
fn household_filter(spec: &TableSpec) -> &'static str {
    if spec.name == "households" {
        "id"
    } else {
        "household_id"
    }
}

fn read_rows(
    c: &Connection,
    spec: &TableSpec,
    cols: &[String],
    filter: &str,
    args: &[&dyn rusqlite::ToSql],
) -> Result<Vec<Row>, StorageError> {
    let mut st = c.prepare(&format!(
        "SELECT {} FROM {} WHERE {filter} ORDER BY rowid",
        cols.join(", "),
        spec.name
    ))?;
    let mut rows = st.query(args)?;
    let mut out = Vec::new();
    while let Some(r) = rows.next()? {
        let mut row = Row::new();
        for (i, name) in cols.iter().enumerate() {
            row.insert(name.clone(), to_json(r.get_ref(i)?)?);
        }
        out.push(row);
    }
    Ok(out)
}

/// Xonadonning barcha yozuvlari (qo'shilish tartibida).
pub fn dump(c: &Connection, household_id: &str, table: &str) -> Result<Vec<Row>, StorageError> {
    let spec = tables::table(table).ok_or(StorageError::SchemaMismatch)?;
    let cols = columns(c, table)?;
    read_rows(
        c,
        spec,
        &cols,
        &format!("{} = ?1", household_filter(spec)),
        &[&household_id],
    )
}

/// Bitta yozuv (birlamchi kalit bo'yicha, shu xonadonda).
pub fn get(
    c: &Connection,
    household_id: &str,
    table: &str,
    pk: &str,
) -> Result<Option<Row>, StorageError> {
    let spec = tables::table(table).ok_or(StorageError::SchemaMismatch)?;
    let cols = columns(c, table)?;
    let rows = read_rows(
        c,
        spec,
        &cols,
        &format!(
            "{} = ?1 AND {} = ?2",
            spec.primary_key,
            household_filter(spec)
        ),
        &[&pk, &household_id],
    )?;
    Ok(rows.into_iter().next())
}

/// Yozuvni aynan kelgan ko'rinishda yozadi. `MUTABLE` — qo'shish yoki to'liq almashtirish,
/// `APPEND_ONLY` — faqat qo'shish (o'zgarmas jadvallar triggerlari ham himoya qiladi).
/// Ustunlar mahalliy sxemadagi bilan aynan bir xil bo'lishi shart.
pub fn write(tx: &Transaction<'_>, table: &str, row: &Row) -> Result<(), StorageError> {
    let spec = tables::table(table).ok_or(StorageError::SchemaMismatch)?;
    let cols = columns(tx, table)?;
    if row.len() != cols.len() || !cols.iter().all(|c| row.contains_key(c)) {
        return Err(StorageError::SchemaMismatch);
    }
    let values = cols
        .iter()
        .map(|c| row.get(c).map_or(Ok(SqlValue::Null), to_sql))
        .collect::<Result<Vec<_>, _>>()?;
    let placeholders: Vec<String> = (1..=cols.len()).map(|i| format!("?{i}")).collect();
    let mut sql = format!(
        "INSERT INTO {} ({}) VALUES ({})",
        spec.name,
        cols.join(", "),
        placeholders.join(", ")
    );
    if spec.mode == TableMode::Mutable {
        let sets: Vec<String> = cols
            .iter()
            .filter(|c| **c != spec.primary_key)
            .map(|c| format!("{c} = excluded.{c}"))
            .collect();
        sql.push_str(&format!(
            " ON CONFLICT({}) DO UPDATE SET {}",
            spec.primary_key,
            sets.join(", ")
        ));
    }
    tx.execute(&sql, rusqlite::params_from_iter(values))?;
    Ok(())
}

/// Import tranzaksiyasida tashqi kalitlar tekshiruvini oxiriga qoldirish (ota-bola tartibi
/// jadvallar ichida aylana bo'lishi mumkin — masalan, tanlangan stsenariy).
pub fn defer_foreign_keys(tx: &Transaction<'_>) -> Result<(), StorageError> {
    tx.execute_batch("PRAGMA defer_foreign_keys = ON;")?;
    Ok(())
}

// ---- sinxronlash holati ----

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeerRow {
    pub peer_device_id: String,
    pub peer_name: Option<String>,
    pub last_export_at: Option<String>,
    pub last_import_at: Option<String>,
    pub last_ack_export_id: Option<String>,
}

pub fn peers(c: &Connection, household_id: &str) -> Result<Vec<PeerRow>, StorageError> {
    let mut st = c.prepare(
        "SELECT peer_device_id, peer_name, last_export_at, last_import_at, last_ack_export_id
         FROM sync_peers WHERE household_id = ?1 ORDER BY created_at",
    )?;
    let rows = st.query_map([household_id], |r| {
        Ok(PeerRow {
            peer_device_id: r.get(0)?,
            peer_name: r.get(1)?,
            last_export_at: r.get(2)?,
            last_import_at: r.get(3)?,
            last_ack_export_id: r.get(4)?,
        })
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

pub fn peer(
    c: &Connection,
    household_id: &str,
    peer_device_id: &str,
) -> Result<Option<PeerRow>, StorageError> {
    Ok(peers(c, household_id)?
        .into_iter()
        .find(|p| p.peer_device_id == peer_device_id))
}

/// Import qilingandan keyin: qurilma nomi, oxirgi qabul qilingan eksport.
pub fn record_import_from(
    tx: &Transaction<'_>,
    household_id: &str,
    peer_device_id: &str,
    peer_name: &str,
    export_id: &str,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO sync_peers (peer_device_id, household_id, peer_name, last_import_at,
            last_ack_export_id, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?4, ?4)
         ON CONFLICT(peer_device_id) DO UPDATE SET peer_name = excluded.peer_name,
            last_import_at = excluded.last_import_at,
            last_ack_export_id = excluded.last_ack_export_id, updated_at = excluded.updated_at",
        params![peer_device_id, household_id, peer_name, m.now, export_id],
    )?;
    Ok(())
}

/// Eksport: `sync_exports` va (qabul qiluvchi ma'lum yoki ulash fayli bo'lsa) kutilayotgan
/// yozuvlar. `pending` — (jadval, kalit, xesh).
#[allow(clippy::too_many_arguments)]
pub fn record_export(
    tx: &Transaction<'_>,
    household_id: &str,
    export_id: &str,
    peer_device_id: Option<&str>,
    mode: &str,
    row_count: i64,
    pending: &[(String, String, String)],
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO sync_exports (export_id, household_id, peer_device_id, mode, row_count, created_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![export_id, household_id, peer_device_id, mode, row_count, m.now],
    )?;
    {
        let mut st = tx.prepare(
            "INSERT INTO sync_pending (export_id, tbl, row_id, hash) VALUES (?1, ?2, ?3, ?4)",
        )?;
        for (t, id, h) in pending {
            st.execute(params![export_id, t, id, h])?;
        }
    }
    if let Some(p) = peer_device_id {
        tx.execute(
            "INSERT INTO sync_peers (peer_device_id, household_id, last_export_at, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?3, ?3)
             ON CONFLICT(peer_device_id) DO UPDATE SET last_export_at = excluded.last_export_at,
                updated_at = excluded.updated_at",
            params![p, household_id, m.now],
        )?;
    }
    Ok(())
}

/// Kelishilgan holat: (jadval, kalit) → xesh.
pub fn bases(
    c: &Connection,
    peer_device_id: &str,
) -> Result<HashMap<(String, String), String>, StorageError> {
    let mut st = c.prepare("SELECT tbl, row_id, hash FROM sync_base WHERE peer_device_id = ?1")?;
    let rows = st.query_map([peer_device_id], |r| {
        Ok((
            (r.get::<_, String>(0)?, r.get::<_, String>(1)?),
            r.get::<_, String>(2)?,
        ))
    })?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// `ackExportId` tasdiqlagan eksportlar (shu va undan oldingi, shu qurilmaga yoki ulash
/// fayli sifatida yuborilganlar) — eskisidan yangisiga tartibda: (jadval, kalit, xesh).
pub fn acked_pending(
    c: &Connection,
    household_id: &str,
    peer_device_id: &str,
    ack_export_id: &str,
) -> Result<Vec<(String, String, String)>, StorageError> {
    let acked: Option<(Option<String>, i64)> = c
        .query_row(
            "SELECT peer_device_id, rowid FROM sync_exports WHERE export_id = ?1 AND household_id = ?2",
            params![ack_export_id, household_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    let Some((peer, rowid)) = acked else {
        return Ok(Vec::new());
    };
    if peer.as_deref().is_some_and(|p| p != peer_device_id) {
        return Ok(Vec::new());
    }
    let mut st = c.prepare(
        "SELECT p.tbl, p.row_id, p.hash FROM sync_pending p JOIN sync_exports e ON e.export_id = p.export_id
         WHERE e.household_id = ?1 AND e.rowid <= ?2
           AND (e.peer_device_id = ?3 OR e.export_id = ?4)
         ORDER BY e.rowid",
    )?;
    let rows = st.query_map(
        params![household_id, rowid, peer_device_id, ack_export_id],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
    )?;
    Ok(rows.collect::<Result<_, _>>()?)
}

/// Tasdiqlangan eksportlarni yopadi: kutilayotganlar o'chiriladi, ulash fayli qurilmaga bog'lanadi.
pub fn close_acked(
    tx: &Transaction<'_>,
    household_id: &str,
    peer_device_id: &str,
    ack_export_id: &str,
) -> Result<(), StorageError> {
    let rowid: Option<i64> = tx
        .query_row(
            "SELECT rowid FROM sync_exports WHERE export_id = ?1 AND household_id = ?2
               AND (peer_device_id IS NULL OR peer_device_id = ?3)",
            params![ack_export_id, household_id, peer_device_id],
            |r| r.get(0),
        )
        .optional()?;
    let Some(rowid) = rowid else {
        return Ok(());
    };
    tx.execute(
        "UPDATE sync_exports SET peer_device_id = ?1 WHERE export_id = ?2",
        params![peer_device_id, ack_export_id],
    )?;
    tx.execute(
        "DELETE FROM sync_pending WHERE export_id IN (SELECT export_id FROM sync_exports
            WHERE household_id = ?1 AND rowid <= ?2 AND peer_device_id = ?3)",
        params![household_id, rowid, peer_device_id],
    )?;
    Ok(())
}

pub fn set_base(
    tx: &Transaction<'_>,
    peer_device_id: &str,
    table: &str,
    row_id: &str,
    hash: &str,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO sync_base (peer_device_id, tbl, row_id, hash) VALUES (?1, ?2, ?3, ?4)
         ON CONFLICT(peer_device_id, tbl, row_id) DO UPDATE SET hash = excluded.hash",
        params![peer_device_id, table, row_id, hash],
    )?;
    Ok(())
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ImportLog {
    pub id: String,
    pub export_id: String,
    pub peer_device_id: String,
    pub mode: String,
    pub summary_json: String,
}

pub fn record_import(
    tx: &Transaction<'_>,
    household_id: &str,
    log: &ImportLog,
    m: &Meta,
) -> Result<(), StorageError> {
    tx.execute(
        "INSERT INTO sync_imports (id, household_id, export_id, peer_device_id, mode, summary_json, imported_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![log.id, household_id, log.export_id, log.peer_device_id, log.mode, log.summary_json, m.now],
    )?;
    Ok(())
}
