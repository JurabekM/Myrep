//! Append-only, xesh-zanjirli audit log.
//!
//! ```text
//! hash_n = SHA-256("MPAY-AUDIT-V1" ‖ prev_hash ‖ seq ‖ ts ‖ L(actor) ‖ L(action) ‖ L(token_id) ‖ L(details))
//! ```
//! `L(x)` = `u32` uzunlik ‖ baytlar; `prev_hash` birinchi yozuv uchun 32 nol bayt.
//! O'zgartirish va o'chirishni SQLite trigger'lari taqiqlaydi; zanjir [`verify`] bilan tekshiriladi.
//! `details` — faqat maxfiy bo'lmagan JSON (maskalangan PAN, ID'lar, sabab kodlari).

use serde::Serialize;
use sha2::{Digest, Sha256};
use sqlx::{Row, Sqlite, Transaction};

use crate::VaultError;

/// Audit yozuvi (yangi).
#[derive(Debug, Clone)]
pub struct AuditEntry<'a> {
    pub actor: &'a str,
    pub action: &'a str,
    pub token_id: Option<&'a str>,
    pub details: serde_json::Value,
}

fn hash_record(
    prev: &[u8],
    seq: i64,
    ts: i64,
    actor: &str,
    action: &str,
    token_id: Option<&str>,
    details: &str,
) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(b"MPAY-AUDIT-V1");
    h.update(prev);
    h.update(seq.to_be_bytes());
    h.update(ts.to_be_bytes());
    for part in [actor, action, token_id.unwrap_or(""), details] {
        h.update((part.len() as u32).to_be_bytes());
        h.update(part.as_bytes());
    }
    h.finalize().into()
}

/// Tranzaksiya ichida yozuv qo'shadi. Chaqiruvchi yozish qulfini ushlab turadi.
pub async fn append(
    tx: &mut Transaction<'_, Sqlite>,
    ts: i64,
    e: &AuditEntry<'_>,
) -> Result<i64, VaultError> {
    let last = sqlx::query("SELECT seq, hash FROM vault_audit ORDER BY seq DESC LIMIT 1")
        .fetch_optional(&mut **tx)
        .await?;
    let (seq, prev): (i64, Vec<u8>) = match last {
        Some(r) => (r.try_get::<i64, _>("seq")? + 1, r.try_get("hash")?),
        None => (1, vec![0u8; 32]),
    };
    let details = e.details.to_string();
    let hash = hash_record(&prev, seq, ts, e.actor, e.action, e.token_id, &details);
    sqlx::query(
        "INSERT INTO vault_audit (seq, ts, actor, action, token_id, details, prev_hash, hash) \
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    )
    .bind(seq)
    .bind(ts)
    .bind(e.actor)
    .bind(e.action)
    .bind(e.token_id)
    .bind(&details)
    .bind(&prev)
    .bind(hash.as_slice())
    .execute(&mut **tx)
    .await?;
    Ok(seq)
}

/// Zanjirni tekshirish natijasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AuditReport {
    pub entries: i64,
    pub head_hash: String,
}

/// Butun zanjirni boshidan tekshiradi.
pub async fn verify(pool: &sqlx::SqlitePool) -> Result<AuditReport, VaultError> {
    let rows = sqlx::query("SELECT seq, ts, actor, action, token_id, details, prev_hash, hash FROM vault_audit ORDER BY seq")
        .fetch_all(pool)
        .await?;
    let mut prev = vec![0u8; 32];
    for (expected_seq, r) in (1i64..).zip(rows.iter()) {
        let seq: i64 = r.try_get("seq")?;
        let stored_prev: Vec<u8> = r.try_get("prev_hash")?;
        let stored: Vec<u8> = r.try_get("hash")?;
        let token_id: Option<String> = r.try_get("token_id")?;
        let calc = hash_record(
            &prev,
            seq,
            r.try_get("ts")?,
            &r.try_get::<String, _>("actor")?,
            &r.try_get::<String, _>("action")?,
            token_id.as_deref(),
            &r.try_get::<String, _>("details")?,
        );
        if seq != expected_seq || stored_prev != prev || stored != calc {
            return Err(VaultError::AuditBroken(seq));
        }
        prev = stored;
    }
    Ok(AuditReport {
        entries: rows.len() as i64,
        head_hash: hex::encode(&prev),
    })
}
