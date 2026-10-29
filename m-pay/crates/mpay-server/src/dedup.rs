//! Terminal so'rovlarining takroriy yuborilishi (1-faza, P1.2; ADR-0010).
//!
//! Terminal javobni ololmasa (timeout) xuddi shu so'rovni qayta yuboradi. Emitent esa o'sha ARQC'ni
//! ATC replay sifatida `Q1` bilan rad etadi — mijozdan pul yechilgan, terminal esa "rad etildi"
//! ko'rsatadi. Shuning uchun acquirer `(terminal, STAN, sana)` bo'yicha so'rovni eslab qoladi:
//!
//! * aynan bir xil so'rov → birinchi javob qayta beriladi (idempotent);
//! * bir xil STAN, boshqa mazmun → ISO `94` (takroriy uzatish), emitentga yuborilmaydi;
//! * birinchisi hali ishlanmoqda → `409 REQUEST_IN_PROGRESS`;
//! * yozuv uzoq vaqt `PENDING` (jarayon so'rov o'rtasida to'xtagan) → natija noma'lum, `96` va
//!   reversal (`crate::reversal`, ADR-0024).
//!
//! Jadval acquirer jurnali ham: yozuvda asl `0100` ning reversal va solishtirish uchun kerakli
//! maydonlari (RRN, summa, maskalangan DPAN — PAN emas) va yakuniy javob kodi saqlanadi.
//!
//! Kalit: **autentifikatsiya qilingan terminal kaliti** + so'rovdagi `terminal_id` (bir terminal
//! boshqasining STAN maydonini band qila olmasin) va **tranzaksiya sanasi kartadan** (ICC `9A`;
//! qayta urinish yarim tundan o'tsa ham kalit o'zgarmasin).

use std::sync::atomic::{AtomicI64, Ordering};

use mpay_common::api::{AuthorizationRequest, AuthorizationResponse};
use sha2::{Digest, Sha256};
use sqlx::{AnyPool, Row};
use time::OffsetDateTime;

/// Yozuvlar saqlanish muddati (STAN kun ichida noyob; 3 kun — sana chegarasidagi qayta urinishlar uchun
/// zaxira). Solishtirish (`crate::recon`) shu oynadan eskiroq davrni rad etadi.
pub const RETENTION_SECS: i64 = 3 * 24 * 3600;
const CLEANUP_EVERY_SECS: i64 = 60;
/// Shundan uzoq `PENDING` — ishlov tugamagan (jarayon to'xtagan), natija noma'lum.
pub const STALE_PENDING_SECS: i64 = 120;
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
    /// `terminal_key` — autentifikatsiya qilingan API kaliti ID'si; `txn_date` — `YYMMDD` (ICC `9A`).
    pub fn new(req: &AuthorizationRequest, terminal_key: &str, txn_date: String) -> Self {
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
            terminal_id: format!("{terminal_key}/{}", req.terminal_id),
            stan: req.stan,
            txn_date,
            hash: h.finalize().into(),
        }
    }
}

/// Asl `0100` ning jurnalga yoziladigan maydonlari (reversal va solishtirish uchun).
#[derive(Debug, Clone)]
pub struct Journal {
    /// Terminal ID (maydon 41, bo'shliqsiz).
    pub terminal_ref: String,
    pub merchant_id: String,
    pub rrn: String,
    /// Maydon 7 (`MMDDhhmmss`) — reversal'ning maydon 90 ida.
    pub transmitted: String,
    pub amount_minor: u64,
    pub currency: u16,
    pub dpan_masked: String,
}

impl Journal {
    pub fn new(req: &AuthorizationRequest, built: &crate::acquirer::Built) -> Self {
        Self {
            terminal_ref: req.terminal_id.clone(),
            merchant_id: req.merchant_id.clone(),
            rrn: built.rrn.clone(),
            transmitted: built
                .msg
                .require_str(7)
                .map(str::to_owned)
                .unwrap_or_default(),
            amount_minor: built.amount_minor,
            currency: built.currency,
            dpan_masked: built.dpan_masked.clone(),
        }
    }
}

/// Server sanasi `YYMMDD` (ICC'da `9A` bo'lmasa).
pub fn server_date(now: OffsetDateTime) -> String {
    format!(
        "{:02}{:02}{:02}",
        now.year() % 100,
        u8::from(now.month()),
        now.day()
    )
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
    /// Yozuv `STALE_PENDING_SECS` dan uzoq `PENDING` — ishlov tugamagan, natija noma'lum
    /// (emitent ishlagan bo'lishi mumkin: qayta yuborish ATC replay bo'lardi).
    Stale,
}

/// So'rovni qayd etadi yoki avvalgisini topadi.
pub async fn begin(
    pool: &AnyPool,
    k: &RequestKey,
    j: &Journal,
    now_unix: i64,
) -> Result<Begin, sqlx::Error> {
    // Eski yozuvlarni tozalash — har so'rovda emas (har commit — fsync), daqiqada bir marta.
    let last = LAST_CLEANUP.load(Ordering::Relaxed);
    if now_unix - last >= CLEANUP_EVERY_SECS
        && LAST_CLEANUP
            .compare_exchange(last, now_unix, Ordering::Relaxed, Ordering::Relaxed)
            .is_ok()
    {
        sqlx::query("DELETE FROM acquirer_requests WHERE created_at < $1")
            .bind(now_unix - RETENTION_SECS)
            .execute(pool)
            .await?;
    }
    let inserted = sqlx::query(
        "INSERT INTO acquirer_requests (terminal_id, stan, txn_date, request_hash, state, created_at, \
         terminal_ref, merchant_id, rrn, transmitted, amount_minor, currency, dpan_masked) \
         VALUES ($1, $2, $3, $4, 'PENDING', $5, $6, $7, $8, $9, $10, $11, $12) ON CONFLICT DO NOTHING",
    )
    .bind(&k.terminal_id)
    .bind(i64::from(k.stan))
    .bind(&k.txn_date)
    .bind(&k.hash[..])
    .bind(now_unix)
    .bind(&j.terminal_ref)
    .bind(&j.merchant_id)
    .bind(&j.rrn)
    .bind(&j.transmitted)
    .bind(j.amount_minor as i64)
    .bind(i64::from(j.currency))
    .bind(&j.dpan_masked)
    .execute(pool)
    .await?
    .rows_affected();
    if inserted == 1 {
        return Ok(Begin::New);
    }
    let row = sqlx::query(
        "SELECT request_hash, state, response, created_at FROM acquirer_requests \
         WHERE terminal_id = $1 AND stan = $2 AND txn_date = $3",
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
    let created_at: i64 = row.try_get("created_at")?;
    match (state.as_str(), response) {
        ("DONE", Some(json)) => serde_json::from_str(&json)
            .map(Begin::Replay)
            .map_err(|e| sqlx::Error::Decode(Box::new(e))),
        _ if now_unix - created_at > STALE_PENDING_SECS => Ok(Begin::Stale),
        _ => Ok(Begin::InProgress),
    }
}

/// Emitent javobini saqlaydi.
pub async fn finish(
    pool: &AnyPool,
    k: &RequestKey,
    resp: &AuthorizationResponse,
) -> Result<(), sqlx::Error> {
    let json = serde_json::to_string(resp).map_err(|e| sqlx::Error::Encode(Box::new(e)))?;
    sqlx::query(
        "UPDATE acquirer_requests SET state = 'DONE', response = $1, response_code = $2 \
         WHERE terminal_id = $3 AND stan = $4 AND txn_date = $5",
    )
    .bind(json)
    .bind(&resp.response_code)
    .bind(&k.terminal_id)
    .bind(i64::from(k.stan))
    .bind(&k.txn_date)
    .execute(pool)
    .await?;
    Ok(())
}

/// Emitentga yetib bo'lmadi — yozuv o'chiriladi, terminal qayta urinishi mumkin.
pub async fn abort(pool: &AnyPool, k: &RequestKey) -> Result<(), sqlx::Error> {
    sqlx::query(
        "DELETE FROM acquirer_requests \
         WHERE terminal_id = $1 AND stan = $2 AND txn_date = $3 AND state = 'PENDING'",
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
pub async fn migrate(db: &mpay_vault::db::Db) -> Result<(), sqlx::migrate::MigrateError> {
    db.migrate_with(
        sqlx::migrate!("./migrations/sqlite"),
        sqlx::migrate!("./migrations/postgres"),
    )
    .await
}

#[cfg(test)]
mod tests {
    use super::*;

    fn req(tid: &str, stan: u32) -> AuthorizationRequest {
        AuthorizationRequest {
            terminal_id: tid.into(),
            merchant_id: "SHOP0000000001".into(),
            stan,
            icc_data: "9F2608AABBCCDDEEFF0011".into(),
        }
    }

    fn journal() -> Journal {
        Journal {
            terminal_ref: "TERM0001".into(),
            merchant_id: "SHOP0000000001".into(),
            rrn: "629812000009".into(),
            transmitted: "1025120000".into(),
            amount_minor: 100,
            currency: 860,
            dpan_masked: "990077******0001".into(),
        }
    }

    async fn db() -> (tempfile::TempDir, mpay_vault::db::Db) {
        let dir = tempfile::tempdir().unwrap();
        let db = mpay_vault::db::Db::open_sqlite(&dir.path().join("d.db"))
            .await
            .unwrap();
        migrate(&db).await.unwrap();
        (dir, db)
    }

    async fn pool() -> (tempfile::TempDir, AnyPool) {
        let (dir, db) = db().await;
        (dir, db.pool().clone())
    }

    #[tokio::test]
    async fn key_is_bound_to_terminal_key_and_card_date() {
        let (_d, p) = pool().await;
        let r = req("TERM0002", 7);
        // Boshqa terminal kaliti o'sha terminal_id/STAN bilan — begona maydon band qilinmaydi.
        let a = RequestKey::new(&r, "terminal-1", "261025".into());
        let b = RequestKey::new(&r, "terminal-2", "261025".into());
        assert!(matches!(
            begin(&p, &a, &journal(), 1000).await.unwrap(),
            Begin::New
        ));
        assert!(matches!(
            begin(&p, &b, &journal(), 1000).await.unwrap(),
            Begin::New
        ));
        // Qayta urinish ertasi kuni (server soati) — kalit kartadagi sanadan, shuning uchun o'sha yozuv.
        let again = RequestKey::new(&r, "terminal-1", "261025".into());
        assert!(matches!(
            begin(&p, &again, &journal(), 1000 + 30).await.unwrap(),
            Begin::InProgress
        ));
    }

    #[tokio::test]
    async fn stale_pending_is_settled_with_96_and_one_reversal() {
        use crate::reversal::{settle_unknown, CAUSE_TIMEOUT, CAUSE_UNKNOWN};
        let (_d, db) = db().await;
        let p = db.pool().clone();
        let k = RequestKey::new(&req("TERM0001", 9), "terminal-1", "261025".into());
        assert!(matches!(
            begin(&p, &k, &journal(), 1000).await.unwrap(),
            Begin::New
        ));
        assert!(matches!(
            begin(&p, &k, &journal(), 1000 + 5).await.unwrap(),
            Begin::InProgress
        ));
        assert!(matches!(
            begin(&p, &k, &journal(), 1000 + STALE_PENDING_SECS + 1)
                .await
                .unwrap(),
            Begin::Stale
        ));
        // `96` saqlanadi va reversal navbatga qo'yiladi (emitent yechgan bo'lishi mumkin).
        let cfg = crate::config::AcquirerConfig::default();
        let now = 1000 + STALE_PENDING_SECS + 1;
        let r = settle_unknown(&db, &(&k).into(), CAUSE_UNKNOWN, &cfg, now)
            .await
            .unwrap();
        assert_eq!(
            (r.response_code.as_str(), r.reason.as_str()),
            ("96", "OUTCOME_UNKNOWN")
        );
        assert_eq!(
            (r.amount_minor, r.dpan_masked.as_str()),
            (100, "990077******0001")
        );
        // Ikkinchi marta (parallel ishchi yoki timeout yo'li) — o'sha javob, ikkinchi reversal yo'q.
        let again = settle_unknown(&db, &(&k).into(), CAUSE_TIMEOUT, &cfg, now + 1)
            .await
            .unwrap();
        assert_eq!(again, r);
        let (n, next, cause): (i64, i64, String) = sqlx::query_as(
            "SELECT COUNT(*), MAX(next_attempt_at), MAX(cause) FROM acquirer_reversals",
        )
        .fetch_one(&p)
        .await
        .unwrap();
        assert_eq!(
            (n, next, cause.as_str()),
            (1, now + cfg.reversal_delay_secs, "OUTCOME_UNKNOWN")
        );
        // Keyingi urinishlar o'sha javobni oladi (emitentga qayta yuborilmaydi).
        match begin(&p, &k, &journal(), now + 2).await.unwrap() {
            Begin::Replay(x) => assert_eq!(x.response_code, "96"),
            other => panic!("{other:?}"),
        }
    }
}
