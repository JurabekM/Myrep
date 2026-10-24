//! Terminal so'rovlarining takroriy yuborilishi (1-faza, P1.2; ADR-0010).
//!
//! Terminal javobni ololmasa (timeout) xuddi shu so'rovni qayta yuboradi. Emitent esa o'sha ARQC'ni
//! ATC replay sifatida `Q1` bilan rad etadi — mijozdan pul yechilgan, terminal esa "rad etildi"
//! ko'rsatadi. Shuning uchun acquirer `(terminal, STAN, sana)` bo'yicha so'rovni eslab qoladi:
//!
//! * aynan bir xil so'rov → birinchi javob qayta beriladi (idempotent);
//! * bir xil STAN, boshqa mazmun → ISO `94` (takroriy uzatish), emitentga yuborilmaydi;
//! * birinchisi hali ishlanmoqda → `409 REQUEST_IN_PROGRESS`.

use std::sync::atomic::{AtomicI64, Ordering};

use mpay_common::api::{AuthorizationRequest, AuthorizationResponse};
use sha2::{Digest, Sha256};
use sqlx::{Row, SqlitePool};
use time::OffsetDateTime;

/// Yozuvlar saqlanish muddati (STAN kun ichida noyob; 3 kun — sana chegarasidagi qayta urinishlar uchun zaxira).
const RETENTION_SECS: i64 = 3 * 24 * 3600;
const CLEANUP_EVERY_SECS: i64 = 60;
static LAST_CLEANUP: AtomicI64 = AtomicI64::new(0);

/// So'rov kaliti va mazmun xeshi.
#[derive(Debug, Clone)]
pub struct RequestKey {
    pub terminal_id: String,
    pub stan: u32,
    pub txn_date: String,
    hash: [u8; 32],
}

impl RequestKey {
    pub fn new(req: &AuthorizationRequest, now: OffsetDateTime) -> Self {
        let mut h = Sha256::new();
        for part in [
            req.terminal_id.as_bytes(),
            req.merchant_id.as_bytes(),
            req.stan.to_string().as_bytes(),
            req.icc_data.to_ascii_uppercase().as_bytes(),
        ] {
            h.update((part.len() as u32).to_be_bytes());
            h.update(part);
        }
        Self {
            terminal_id: req.terminal_id.clone(),
            stan: req.stan,
            txn_date: format!(
                "{:04}{:02}{:02}",
                now.year(),
                u8::from(now.month()),
                now.day()
            ),
            hash: h.finalize().into(),
        }
    }
}

/// `begin` natijasi.
#[derive(Debug)]
pub enum Begin {
    /// Yangi so'rov — emitentga yuboriladi, so'ng `finish` yoki `abort`.
    New,
    /// Aynan shu so'rov avval ishlangan — saqlangan javob.
    Replay(AuthorizationResponse),
    /// Shu STAN boshqa mazmun bilan ishlatilgan.
    Duplicate,
    /// Shu so'rov hali ishlanmoqda.
    InProgress,
}

/// So'rovni qayd etadi yoki avvalgisini topadi.
pub async fn begin(pool: &SqlitePool, k: &RequestKey, now_unix: i64) -> Result<Begin, sqlx::Error> {
    // Eski yozuvlarni tozalash — har so'rovda emas (har commit — fsync), daqiqada bir marta.
    let last = LAST_CLEANUP.load(Ordering::Relaxed);
    if now_unix - last >= CLEANUP_EVERY_SECS
        && LAST_CLEANUP
            .compare_exchange(last, now_unix, Ordering::Relaxed, Ordering::Relaxed)
            .is_ok()
    {
        sqlx::query("DELETE FROM acquirer_requests WHERE created_at < ?")
            .bind(now_unix - RETENTION_SECS)
            .execute(pool)
            .await?;
    }
    let inserted = sqlx::query(
        "INSERT INTO acquirer_requests (terminal_id, stan, txn_date, request_hash, state, created_at) \
         VALUES (?, ?, ?, ?, 'PENDING', ?) ON CONFLICT DO NOTHING",
    )
    .bind(&k.terminal_id)
    .bind(i64::from(k.stan))
    .bind(&k.txn_date)
    .bind(&k.hash[..])
    .bind(now_unix)
    .execute(pool)
    .await?
    .rows_affected();
    if inserted == 1 {
        return Ok(Begin::New);
    }
    let row = sqlx::query(
        "SELECT request_hash, state, response FROM acquirer_requests \
         WHERE terminal_id = ? AND stan = ? AND txn_date = ?",
    )
    .bind(&k.terminal_id)
    .bind(i64::from(k.stan))
    .bind(&k.txn_date)
    .fetch_one(pool)
    .await?;
    let hash: Vec<u8> = row.try_get("request_hash")?;
    if hash != k.hash {
        return Ok(Begin::Duplicate);
    }
    let state: String = row.try_get("state")?;
    let response: Option<String> = row.try_get("response")?;
    match (state.as_str(), response) {
        ("DONE", Some(json)) => serde_json::from_str(&json)
            .map(Begin::Replay)
            .map_err(|e| sqlx::Error::Decode(Box::new(e))),
        _ => Ok(Begin::InProgress),
    }
}

/// Emitent javobini saqlaydi.
pub async fn finish(
    pool: &SqlitePool,
    k: &RequestKey,
    resp: &AuthorizationResponse,
) -> Result<(), sqlx::Error> {
    let json = serde_json::to_string(resp).map_err(|e| sqlx::Error::Encode(Box::new(e)))?;
    sqlx::query(
        "UPDATE acquirer_requests SET state = 'DONE', response = ? \
         WHERE terminal_id = ? AND stan = ? AND txn_date = ?",
    )
    .bind(json)
    .bind(&k.terminal_id)
    .bind(i64::from(k.stan))
    .bind(&k.txn_date)
    .execute(pool)
    .await?;
    Ok(())
}

/// Emitentga yetib bo'lmadi — yozuv o'chiriladi, terminal qayta urinishi mumkin.
pub async fn abort(pool: &SqlitePool, k: &RequestKey) -> Result<(), sqlx::Error> {
    sqlx::query(
        "DELETE FROM acquirer_requests \
         WHERE terminal_id = ? AND stan = ? AND txn_date = ? AND state = 'PENDING'",
    )
    .bind(&k.terminal_id)
    .bind(i64::from(k.stan))
    .bind(&k.txn_date)
    .execute(pool)
    .await?;
    Ok(())
}

/// `94` javobi: emitentga yuborilmagan, RRN yo'q.
pub fn duplicate_response(
    req: &AuthorizationRequest,
    dpan_masked: String,
    amount_minor: u64,
    currency: u16,
) -> AuthorizationResponse {
    AuthorizationResponse {
        approved: false,
        response_code: "94".into(),
        reason: "DUPLICATE_TRANSMISSION".into(),
        stan: req.stan,
        rrn: String::new(),
        dpan_masked,
        amount_minor,
        currency,
        issuer_auth_data: None,
        risk_score: None,
    }
}

/// Server migratsiyalari (`migrations/3xxx`).
pub async fn migrate(pool: &SqlitePool) -> Result<(), sqlx::migrate::MigrateError> {
    let mut m = sqlx::migrate!("./migrations");
    m.set_ignore_missing(true);
    m.run(pool).await
}
