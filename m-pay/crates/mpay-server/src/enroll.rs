//! Qurilmani ro'yxatdan o'tkazish (1-faza P1.7, ADR-0013): bir martalik nonce'lar (xotirada, TTL)
//! va ro'yxatga olingan qurilmalar reyestri (DB, `pqlink_devices`).

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use mpay_common::clock::Clock;
use mpay_crypto::rng;
use mpay_pqlink::attestation::VerifiedDevice;
use mpay_pqlink::{EnrollmentGate, PqLinkError};
use sqlx::SqlitePool;

/// Bir vaqtda kutilayotgan nonce'lar chegarasi (xotira himoyasi; IP rate-limit bilan birga).
const MAX_PENDING: usize = 100_000;

/// Nonce do'koni va reyestr.
pub struct Enrollment {
    nonces: Mutex<HashMap<[u8; 32], i64>>,
    ttl_secs: i64,
    clock: Arc<dyn Clock>,
    pool: SqlitePool,
    rt: tokio::runtime::Handle,
}

impl std::fmt::Debug for Enrollment {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Enrollment")
            .field("ttl_secs", &self.ttl_secs)
            .finish_non_exhaustive()
    }
}

impl Enrollment {
    /// Async kontekstda yaratiladi (joriy tokio runtime saqlanadi).
    pub fn new(pool: SqlitePool, clock: Arc<dyn Clock>, ttl_secs: i64) -> Self {
        Self {
            nonces: Mutex::new(HashMap::new()),
            ttl_secs: ttl_secs.max(1),
            clock,
            pool,
            rt: tokio::runtime::Handle::current(),
        }
    }

    /// Yangi bir martalik nonce: `(nonce, muddati)`.
    pub fn issue(&self) -> Result<([u8; 32], i64), PqLinkError> {
        let now = self.clock.unix();
        let mut map = self
            .nonces
            .lock()
            .map_err(|_| PqLinkError::Crypto("nonce lock".into()))?;
        map.retain(|_, exp| *exp > now);
        if map.len() >= MAX_PENDING {
            return Err(PqLinkError::TooManySessions);
        }
        let n = rng::array::<32>().map_err(|e| PqLinkError::Crypto(e.to_string()))?;
        let exp = now + self.ttl_secs;
        map.insert(n, exp);
        Ok((n, exp))
    }

    /// Nonce'ni iste'mol qiladi (bir martalik).
    pub fn consume(&self, challenge: &[u8]) -> Result<(), PqLinkError> {
        let key: [u8; 32] = challenge
            .try_into()
            .map_err(|_| PqLinkError::Enrollment("attestatsiya challenge'i server nonce'i emas"))?;
        let now = self.clock.unix();
        let mut map = self
            .nonces
            .lock()
            .map_err(|_| PqLinkError::Crypto("nonce lock".into()))?;
        match map.remove(&key) {
            Some(exp) if exp > now => Ok(()),
            Some(_) => Err(PqLinkError::Enrollment("nonce muddati o'tgan")),
            None => Err(PqLinkError::Enrollment("nonce noma'lum yoki ishlatilgan")),
        }
    }

    async fn is_enrolled(&self, device_id: &str) -> Result<bool, sqlx::Error> {
        Ok(
            sqlx::query("SELECT 1 FROM pqlink_devices WHERE device_id = ?")
                .bind(device_id)
                .fetch_optional(&self.pool)
                .await?
                .is_some(),
        )
    }

    /// Qurilma oxirgi marta attestatsiyadan o'tgan vaqt (ro'yxatda bo'lmasa `None`).
    pub async fn attested_at(&self, device_hex: &str) -> Result<Option<i64>, sqlx::Error> {
        use sqlx::Row;
        sqlx::query("SELECT enrolled_at FROM pqlink_devices WHERE device_id = ?")
            .bind(device_hex)
            .fetch_optional(&self.pool)
            .await?
            .map(|r| r.try_get::<i64, _>("enrolled_at"))
            .transpose()
    }

    /// Kalit almashtirish: yangi qurilma ro'yxatga olinadi, eskisi o'chiriladi.
    pub async fn replace(&self, old_hex: &str, new: &VerifiedDevice) -> Result<(), sqlx::Error> {
        self.register(new, self.clock.unix()).await?;
        sqlx::query("DELETE FROM pqlink_devices WHERE device_id = ?")
            .bind(old_hex)
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    async fn register(&self, d: &VerifiedDevice, now: i64) -> Result<(), sqlx::Error> {
        sqlx::query(
            "INSERT INTO pqlink_devices (device_id, security_level, enrolled_at) VALUES (?, ?, ?) \
             ON CONFLICT DO NOTHING",
        )
        .bind(d.device_id.to_hex())
        .bind(format!("{:?}", d.security_level))
        .bind(now)
        .execute(&self.pool)
        .await?;
        Ok(())
    }
}

impl EnrollmentGate for Enrollment {
    fn admit(&self, d: &VerifiedDevice) -> Result<(), PqLinkError> {
        let db = |e: sqlx::Error| {
            tracing::error!(error = %e, "pqlink_devices");
            PqLinkError::Crypto("qurilmalar reyestri".into())
        };
        // `handle_finish` `spawn_blocking` ichida — runtime'ni bloklash xavfsiz.
        if self
            .rt
            .block_on(self.is_enrolled(&d.device_id.to_hex()))
            .map_err(db)?
        {
            return Ok(());
        }
        self.consume(&d.attestation_challenge)?;
        self.rt
            .block_on(self.register(d, self.clock.unix()))
            .map_err(db)?;
        tracing::info!(device = %d.device_id.to_hex()[..16], level = ?d.security_level, "pqlink: qurilma ro'yxatga olindi");
        Ok(())
    }
}
