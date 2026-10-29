//! Ko'p instansiyada umumiy so'rovlar chegarasi (3-faza tayyorgarligi, ADR-0019 `TODO`).
//!
//! Har instansiyadagi mahalliy token bucket amalda `N × chegara` beradi. Qimmat yo'llar uchun —
//! handshake (IP bo'yicha) va muhrlangan so'rovlar (qurilma bo'yicha) — umumiy omborda bitta chelak:
//! bitta atomar `INSERT … ON CONFLICT DO UPDATE … RETURNING` (yangilash va kamaytirish birga).
//! Mahalliy chelak oldindan filtr bo'lib qoladi (tez rad, DB'ga borilmaydi).
//!
//! * Kalit — `SHA-256(doira ‖ 0 ‖ kalit)` hex: IP manzillar DB'ga ochiq yozilmaydi.
//! * DB xatosida — **ruxsat** (fail-open, ogohlantirish va metrika): chegara mavjudlik himoyasi,
//!   ombor nosozligi to'lovlarni to'xtatmasin; mahalliy chegara baribir ishlaydi.
//! * Terminal avtorizatsiyalari (API kaliti) — mahalliy: issiq yo'lga DB murojaati qo'shilmaydi,
//!   kalitlar mTLS bilan bog'langan hamkorlarniki.

use std::sync::Arc;
use std::time::Duration;

use mpay_vault::db::{Db, Dialect};
use sha2::{Digest, Sha256};
use sqlx::Row;

use crate::ratelimit::Limited;

/// Bitta doira (masalan `ip`, `device`) uchun umumiy chelak.
#[derive(Clone)]
pub struct SharedLimiter {
    db: Db,
    scope: &'static str,
    /// Soniyasiga to'ladigan tokenlar.
    rate: f64,
    burst: f64,
}

impl std::fmt::Debug for SharedLimiter {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SharedLimiter")
            .field("scope", &self.scope)
            .field("rate", &self.rate)
            .field("burst", &self.burst)
            .finish_non_exhaustive()
    }
}

impl SharedLimiter {
    pub fn new(db: Db, scope: &'static str, rate_per_sec: f64, burst: u32) -> Self {
        Self {
            db,
            scope,
            rate: rate_per_sec.max(f64::MIN_POSITIVE),
            burst: f64::from(burst.max(1)),
        }
    }

    fn key(&self, k: &str) -> String {
        let mut h = Sha256::new();
        h.update(self.scope.as_bytes());
        h.update([0]);
        h.update(k.as_bytes());
        hex::encode(h.finalize())
    }

    /// Bitta so'rov uchun ruxsat (`now_ms` — unix millisekund).
    pub async fn check(&self, k: &str, now_ms: i64) -> Result<(), Limited> {
        let (max, min) = match self.db.dialect() {
            Dialect::Postgres => ("GREATEST", "LEAST"),
            Dialect::Sqlite => ("MAX", "MIN"),
        };
        // Yangi chelak: to'la (burst) minus shu so'rov. Mavjud: vaqt bo'yicha to'ldirish (burst gacha),
        // minus bitta; pastki chegara -1 — rad etilgan so'rovlar qarzni cheksiz oshirmaydi, lekin
        // tezlikdan oshib turgan mijoz ochilmaydi.
        let sql = format!(
            "INSERT INTO rate_buckets (k, tokens, ts) VALUES ($1, $2, $3) \
             ON CONFLICT (k) DO UPDATE SET \
               tokens = {max}(-1.0, {min}($4, rate_buckets.tokens + \
                 (excluded.ts - rate_buckets.ts) * $5) - 1.0), \
               ts = {max}(rate_buckets.ts, excluded.ts) \
             RETURNING tokens"
        );
        let r = sqlx::query(sqlx::AssertSqlSafe(sql))
            .bind(self.key(k))
            .bind(self.burst - 1.0)
            .bind(now_ms)
            .bind(self.burst)
            .bind(self.rate / 1000.0)
            .fetch_one(self.db.pool())
            .await;
        let tokens: f64 = match r.and_then(|row| row.try_get("tokens")) {
            Ok(t) => t,
            Err(e) => {
                crate::metrics::rate_limit_store_error();
                tracing::warn!(scope = self.scope, error = %e, "umumiy chegara: ombor xatosi — ruxsat (mahalliy chegara ishlaydi)");
                return Ok(());
            }
        };
        if tokens >= 0.0 {
            Ok(())
        } else {
            // Kamaytirishdan oldin `tokens + 1 < 1` edi: bitta token to'lguncha kutish.
            let wait = -tokens / self.rate;
            Err(Limited {
                retry_after: Duration::from_secs_f64(wait.clamp(0.001, 3600.0)),
            })
        }
    }
}

/// Server bo'yicha umumiy chegaralar (IP — handshake, qurilma — muhrlangan so'rovlar).
#[derive(Debug)]
pub struct SharedLimits {
    pub ip: SharedLimiter,
    pub device: SharedLimiter,
    cleanup: tokio::task::AbortHandle,
}

impl Drop for SharedLimits {
    fn drop(&mut self) {
        self.cleanup.abort();
    }
}

/// Unix vaqti, millisekund (instansiyalar orasida umumiy o'lchov).
pub fn now_ms() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

impl SharedLimits {
    pub fn new(db: Db, cfg: &crate::ratelimit::RateLimitConfig) -> Arc<Self> {
        // Eski (to'lib bo'lgan) chelaklar tozalanadi: 1 soatdan beri tegilmagan.
        let pool = db.pool().clone();
        let cleanup = tokio::spawn(async move {
            let mut t = tokio::time::interval(Duration::from_secs(60));
            loop {
                t.tick().await;
                if let Err(e) = sqlx::query("DELETE FROM rate_buckets WHERE ts < $1")
                    .bind(now_ms() - 3_600_000)
                    .execute(&pool)
                    .await
                {
                    tracing::warn!(error = %e, "umumiy chegara: tozalash xatosi");
                }
            }
        })
        .abort_handle();
        Arc::new(Self {
            ip: SharedLimiter::new(
                db.clone(),
                "ip",
                f64::from(cfg.ip_handshake_per_minute) / 60.0,
                cfg.ip_handshake_burst,
            ),
            device: SharedLimiter::new(
                db.clone(),
                "device",
                f64::from(cfg.device_per_minute) / 60.0,
                cfg.device_burst,
            ),
            cleanup,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    async fn db() -> (tempfile::TempDir, Db) {
        let dir = tempfile::tempdir().unwrap();
        let db = Db::open_sqlite(&dir.path().join("r.db")).await.unwrap();
        crate::dedup::migrate(&db).await.unwrap();
        (dir, db)
    }

    #[tokio::test]
    async fn bucket_burst_refill_and_hashed_keys() {
        let (_d, db) = db().await;
        // Soniyasiga 2 token, burst 3.
        let l = SharedLimiter::new(db.clone(), "ip", 2.0, 3);
        let t0 = 1_800_000_000_000;
        for _ in 0..3 {
            l.check("10.0.0.1", t0).await.unwrap();
        }
        let e = l.check("10.0.0.1", t0).await.unwrap_err();
        assert!(e.retry_after <= Duration::from_millis(1000), "{e:?}");
        // Boshqa kalit — o'z chelagi.
        l.check("10.0.0.2", t0).await.unwrap();
        // Rad etilganlar qarzni -1 dan pastga tushirmaydi: 1 s da bitta token tiklanadi.
        for _ in 0..10 {
            assert!(l.check("10.0.0.1", t0).await.is_err());
        }
        l.check("10.0.0.1", t0 + 1000).await.unwrap();
        assert!(l.check("10.0.0.1", t0 + 1000).await.is_err());
        // Uzoq kutishda burst'dan oshmaydi.
        for _ in 0..3 {
            l.check("10.0.0.1", t0 + 60_000).await.unwrap();
        }
        assert!(l.check("10.0.0.1", t0 + 60_000).await.is_err());
        // IP ochiq saqlanmaydi.
        let keys: Vec<String> = sqlx::query_scalar("SELECT k FROM rate_buckets")
            .fetch_all(db.pool())
            .await
            .unwrap();
        assert_eq!(keys.len(), 2);
        assert!(keys.iter().all(|k| k.len() == 64 && !k.contains("10.0")));
    }

    #[tokio::test]
    async fn store_error_fails_open() {
        let (_d, db) = db().await;
        let l = SharedLimiter::new(db.clone(), "device", 0.001, 1);
        l.check("d", 1).await.unwrap();
        assert!(l.check("d", 1).await.is_err());
        sqlx::query("DROP TABLE rate_buckets")
            .execute(db.pool())
            .await
            .unwrap();
        // Ombor ishlamasa — o'tkaziladi (mahalliy chegara baribir ishlaydi).
        l.check("d", 1).await.unwrap();
    }
}
