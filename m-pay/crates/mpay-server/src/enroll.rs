//! Qurilmani ro'yxatdan o'tkazish (1-faza P1.7, ADR-0013): bir martalik nonce'lar va ro'yxatga
//! olingan qurilmalar reyestri (DB, `pqlink_devices`).
//!
//! Nonce **holatsiz**: `muddat(8) ‖ tasodif(8) ‖ HMAC-SHA256(k, yorliq ‖ muddat ‖ tasodif)[..16]`.
//! Server berilgan nonce'larni saqlamaydi — `/v1/pqlink/enroll` ni ko'p chaqirib xotirani yoki umumiy
//! chegarani to'ldirib bo'lmaydi (DoS). Faqat **ishlatilgan** nonce'lar muddati tugaguncha eslab
//! qolinadi (bu esa haqiqiy attestatsiya zanjiri talab qiladi). `TODO(spec):` ko'p instansiyada (P2.4)
//! `k` umumiy (KeyStore'dan) va ishlatilganlar ro'yxati umumiy omborda.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use mpay_common::clock::Clock;
use mpay_crypto::rng;
use mpay_pqlink::attestation::VerifiedDevice;
use mpay_pqlink::{EnrollmentGate, PqLinkError};
use sqlx::AnyPool;

const NONCE_LABEL: &[u8] = b"MPAY-PQLINK-V1 enroll-nonce";
/// Ishlatilganlar ro'yxati shundan oshsa — muddati o'tganlari tozalanadi.
const USED_PRUNE_AT: usize = 10_000;

/// Nonce do'koni va reyestr.
pub struct Enrollment {
    mac_key: zeroize::Zeroizing<[u8; 32]>,
    /// Ishlatilgan nonce → muddati (takroriy ishlatishni rad etish uchun).
    used: Mutex<HashMap<[u8; 32], i64>>,
    ttl_secs: i64,
    clock: Arc<dyn Clock>,
    pool: AnyPool,
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
    pub fn new(
        pool: AnyPool,
        clock: Arc<dyn Clock>,
        ttl_secs: i64,
    ) -> Result<Self, mpay_crypto::CryptoError> {
        Ok(Self {
            mac_key: rng::secret_array::<32>()?,
            used: Mutex::new(HashMap::new()),
            ttl_secs: ttl_secs.max(1),
            clock,
            pool,
            rt: tokio::runtime::Handle::current(),
        })
    }

    fn tag(&self, exp: i64, rnd: &[u8]) -> Result<[u8; 16], PqLinkError> {
        use hmac::{Hmac, KeyInit, Mac};
        let mut mac = <Hmac<sha2::Sha256> as KeyInit>::new_from_slice(&self.mac_key[..])
            .map_err(|_| PqLinkError::Crypto("nonce kaliti".into()))?;
        mac.update(NONCE_LABEL);
        mac.update(&exp.to_be_bytes());
        mac.update(rnd);
        let full: [u8; 32] = mac.finalize().into_bytes().into();
        let mut out = [0u8; 16];
        out.copy_from_slice(&full[..16]);
        Ok(out)
    }

    /// Yangi bir martalik nonce: `(nonce, muddati)`. Holat saqlanmaydi.
    pub fn issue(&self) -> Result<([u8; 32], i64), PqLinkError> {
        let exp = self.clock.unix() + self.ttl_secs;
        let rnd = rng::array::<8>().map_err(|e| PqLinkError::Crypto(e.to_string()))?;
        let mut n = [0u8; 32];
        n[..8].copy_from_slice(&exp.to_be_bytes());
        n[8..16].copy_from_slice(&rnd);
        n[16..].copy_from_slice(&self.tag(exp, &rnd)?);
        Ok((n, exp))
    }

    /// Nonce'ni iste'mol qiladi (bir martalik): HMAC, muddat va ishlatilmaganligi tekshiriladi.
    pub fn consume(&self, challenge: &[u8]) -> Result<(), PqLinkError> {
        let n: [u8; 32] = challenge
            .try_into()
            .map_err(|_| PqLinkError::Enrollment("attestatsiya challenge'i server nonce'i emas"))?;
        let mut exp_b = [0u8; 8];
        exp_b.copy_from_slice(&n[..8]);
        let exp = i64::from_be_bytes(exp_b);
        if !mpay_crypto::ct_eq(&self.tag(exp, &n[8..16])?, &n[16..]) {
            return Err(PqLinkError::Enrollment("nonce noma'lum yoki ishlatilgan"));
        }
        let now = self.clock.unix();
        if exp <= now {
            return Err(PqLinkError::Enrollment("nonce muddati o'tgan"));
        }
        let mut used = self
            .used
            .lock()
            .map_err(|_| PqLinkError::Crypto("nonce lock".into()))?;
        if used.len() >= USED_PRUNE_AT {
            used.retain(|_, e| *e > now);
        }
        if used.insert(n, exp).is_some() {
            return Err(PqLinkError::Enrollment("nonce noma'lum yoki ishlatilgan"));
        }
        Ok(())
    }

    /// Qurilma oxirgi marta attestatsiyadan o'tgan vaqt (ro'yxatda bo'lmasa `None`).
    pub async fn attested_at(&self, device_hex: &str) -> Result<Option<i64>, sqlx::Error> {
        use sqlx::Row;
        sqlx::query("SELECT enrolled_at FROM pqlink_devices WHERE device_id = $1")
            .bind(device_hex)
            .fetch_optional(&self.pool)
            .await?
            .map(|r| r.try_get::<i64, _>("enrolled_at"))
            .transpose()
    }

    /// Kalit almashtirish, 1-qadam: yangi qurilma ro'yxatga olinadi (attestatsiya vaqti — hozir).
    pub async fn register_new(&self, new: &VerifiedDevice) -> Result<(), sqlx::Error> {
        self.register(new, self.clock.unix()).await
    }

    /// Qurilmani reyestrdan o'chiradi (rekey oxirida eskisi yoki xatoda yangisi).
    pub async fn remove(&self, device_hex: &str) -> Result<(), sqlx::Error> {
        sqlx::query("DELETE FROM pqlink_devices WHERE device_id = $1")
            .bind(device_hex)
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    async fn register(&self, d: &VerifiedDevice, now: i64) -> Result<(), sqlx::Error> {
        sqlx::query(
            "INSERT INTO pqlink_devices (device_id, security_level, enrolled_at) VALUES ($1, $2, $3) \
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
    fn admit(&self, d: &VerifiedDevice) -> Result<i64, PqLinkError> {
        let db = |e: sqlx::Error| {
            tracing::error!(error = %e, "pqlink_devices");
            PqLinkError::Crypto("qurilmalar reyestri".into())
        };
        // `handle_finish` `spawn_blocking` ichida — runtime'ni bloklash xavfsiz.
        if let Some(at) = self
            .rt
            .block_on(self.attested_at(&d.device_id.to_hex()))
            .map_err(db)?
        {
            return Ok(at);
        }
        self.consume(&d.attestation_challenge)?;
        let now = self.clock.unix();
        self.rt.block_on(self.register(d, now)).map_err(db)?;
        tracing::info!(device = %d.device_id.to_hex()[..16], level = ?d.security_level, "pqlink: qurilma ro'yxatga olindi");
        Ok(now)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use mpay_common::clock::ManualClock;
    use time::{Duration, OffsetDateTime};

    async fn enrollment() -> (tempfile::TempDir, Arc<ManualClock>, Enrollment) {
        let dir = tempfile::tempdir().unwrap();
        let pool = mpay_vault::db::Db::open_sqlite(&dir.path().join("e.db"))
            .await
            .unwrap()
            .pool()
            .clone();
        let clock = Arc::new(ManualClock::new(OffsetDateTime::now_utc()));
        let e = Enrollment::new(pool, clock.clone(), 300).unwrap();
        (dir, clock, e)
    }

    #[tokio::test]
    async fn nonce_is_single_use_unforgeable_and_expires() {
        let (_d, clock, e) = enrollment().await;
        let (n, exp) = e.issue().unwrap();
        assert_eq!(exp, clock.unix() + 300);
        e.consume(&n).unwrap();
        assert!(e.consume(&n).is_err(), "ikkinchi marta");
        // Soxta: muddatni uzaytirish yoki tasodifni o'zgartirish HMAC'ni buzadi.
        let (mut f, _) = e.issue().unwrap();
        f[7] ^= 0x01;
        assert!(e.consume(&f).is_err());
        assert!(e.consume(&[0u8; 32]).is_err());
        assert!(e.consume(b"short").is_err());
        // Muddati o'tgan.
        let (old, _) = e.issue().unwrap();
        clock.advance(Duration::seconds(301));
        assert!(e.consume(&old).is_err());
        // Boshqa server kaliti bilan berilgan nonce qabul qilinmaydi.
        let (_d2, _c2, other) = enrollment().await;
        let (foreign, _) = other.issue().unwrap();
        assert!(e.consume(&foreign).is_err());
    }

    #[tokio::test]
    async fn issuing_keeps_no_state() {
        let (_d, _c, e) = enrollment().await;
        for _ in 0..200_000 {
            e.issue().unwrap();
        }
        assert_eq!(e.used.lock().unwrap().len(), 0);
    }
}
