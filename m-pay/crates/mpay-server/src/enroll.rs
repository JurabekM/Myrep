//! Qurilmani ro'yxatdan o'tkazish (1-faza P1.7, ADR-0013): bir martalik nonce'lar va ro'yxatga
//! olingan qurilmalar reyestri (DB, `pqlink_devices`).
//!
//! Nonce **holatsiz**: `muddat(8) ‖ tasodif(8) ‖ HMAC-SHA256(k, yorliq ‖ muddat ‖ tasodif)[..16]`.
//! Server berilgan nonce'larni saqlamaydi — `/v1/pqlink/enroll` ni ko'p chaqirib xotirani yoki umumiy
//! chegarani to'ldirib bo'lmaydi (DoS). Faqat **ishlatilgan** nonce'lar muddati tugaguncha eslab
//! qolinadi (bu esa haqiqiy attestatsiya zanjiri talab qiladi).
//!
//! Ko'p instansiya (2-faza P2.4): `k` — KeyStore'dagi `mpay.enroll-nonce.v1` (HSM'da, barcha
//! instansiyalarda bir xil), ishlatilgan nonce'lar — umumiy DB'da (`pqlink_used_nonces`): bir
//! instansiya bergan nonce boshqasida iste'mol qilinadi, ikki marta — hech qayerda.

use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::Arc;

use mpay_common::clock::Clock;
use mpay_crypto::keystore::{KeyKind, KeyLabel};
use mpay_crypto::{rng, KeyStore};
use mpay_pqlink::attestation::VerifiedDevice;
use mpay_pqlink::{EnrollmentGate, PqLinkError};
use sqlx::AnyPool;

const NONCE_LABEL: &[u8] = b"MPAY-PQLINK-V1 enroll-nonce";
/// Muddati o'tgan ishlatilgan nonce'lar shuncha soniyada bir marta tozalanadi.
const CLEANUP_EVERY_SECS: i64 = 60;

/// Nonce'lar va reyestr.
pub struct Enrollment {
    ks: Arc<dyn KeyStore>,
    mac_key: KeyLabel,
    ttl_secs: i64,
    clock: Arc<dyn Clock>,
    pool: AnyPool,
    last_cleanup: AtomicI64,
}

impl std::fmt::Debug for Enrollment {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Enrollment")
            .field("ttl_secs", &self.ttl_secs)
            .finish_non_exhaustive()
    }
}

fn store_err(e: sqlx::Error) -> PqLinkError {
    tracing::error!(error = %e, "pqlink: ro'yxatdan o'tish ombori");
    PqLinkError::Crypto("ro'yxatdan o'tish ombori".into())
}

impl Enrollment {
    /// MAC kaliti KeyStore'da yo'q bo'lsa yaratiladi (`ensure_key`).
    pub fn new(
        pool: AnyPool,
        ks: Arc<dyn KeyStore>,
        clock: Arc<dyn Clock>,
        ttl_secs: i64,
    ) -> Result<Self, mpay_crypto::CryptoError> {
        let mac_key = KeyLabel::new(KeyLabel::ENROLL_NONCE);
        ks.ensure_key(&mac_key, KeyKind::HmacSha256)?;
        Ok(Self {
            ks,
            mac_key,
            ttl_secs: ttl_secs.max(1),
            clock,
            pool,
            last_cleanup: AtomicI64::new(0),
        })
    }

    fn tag(&self, exp: i64, rnd: &[u8]) -> Result<[u8; 16], PqLinkError> {
        let msg = [NONCE_LABEL, &exp.to_be_bytes()[..], rnd].concat();
        let full = self
            .ks
            .hmac_sha256(&self.mac_key, &msg)
            .map_err(|e| PqLinkError::Crypto(e.to_string()))?;
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

    /// Nonce'ni iste'mol qiladi (bir martalik): HMAC, muddat va ishlatilmaganligi (umumiy DB'da,
    /// atomar `INSERT … ON CONFLICT DO NOTHING`) tekshiriladi.
    pub async fn consume(&self, challenge: &[u8]) -> Result<(), PqLinkError> {
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
        self.cleanup(now).await;
        let fresh = sqlx::query(
            "INSERT INTO pqlink_used_nonces (nonce, expires_at) VALUES ($1, $2) \
             ON CONFLICT DO NOTHING",
        )
        .bind(&n[..])
        .bind(exp)
        .execute(&self.pool)
        .await
        .map_err(store_err)?
        .rows_affected();
        if fresh != 1 {
            return Err(PqLinkError::Enrollment("nonce noma'lum yoki ishlatilgan"));
        }
        Ok(())
    }

    /// Muddati o'tgan ishlatilgan nonce'larni tozalash — daqiqada bir marta (har instansiyada).
    async fn cleanup(&self, now: i64) {
        let last = self.last_cleanup.load(Ordering::Relaxed);
        if now - last < CLEANUP_EVERY_SECS
            || self
                .last_cleanup
                .compare_exchange(last, now, Ordering::Relaxed, Ordering::Relaxed)
                .is_err()
        {
            return;
        }
        if let Err(e) = sqlx::query("DELETE FROM pqlink_used_nonces WHERE expires_at <= $1")
            .bind(now)
            .execute(&self.pool)
            .await
        {
            tracing::warn!(error = %e, "pqlink: ishlatilgan nonce'lar tozalanmadi");
        }
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

#[async_trait::async_trait]
impl EnrollmentGate for Enrollment {
    async fn admit(&self, d: &VerifiedDevice) -> Result<i64, PqLinkError> {
        if let Some(at) = self
            .attested_at(&d.device_id.to_hex())
            .await
            .map_err(store_err)?
        {
            return Ok(at);
        }
        self.consume(&d.attestation_challenge).await?;
        let now = self.clock.unix();
        self.register(d, now).await.map_err(store_err)?;
        tracing::info!(device = %d.device_id.to_hex()[..16], level = ?d.security_level, "pqlink: qurilma ro'yxatga olindi");
        Ok(now)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use mpay_common::clock::ManualClock;
    use mpay_crypto::keystore::MemoryKeyStore;
    use time::{Duration, OffsetDateTime};

    async fn enrollment_with(
        ks: Arc<dyn KeyStore>,
    ) -> (tempfile::TempDir, Arc<ManualClock>, Enrollment) {
        let dir = tempfile::tempdir().unwrap();
        let db = mpay_vault::db::Db::open_sqlite(&dir.path().join("e.db"))
            .await
            .unwrap();
        crate::dedup::migrate(&db).await.unwrap();
        let clock = Arc::new(ManualClock::new(OffsetDateTime::now_utc()));
        let e = Enrollment::new(db.pool().clone(), ks, clock.clone(), 300).unwrap();
        (dir, clock, e)
    }

    async fn enrollment() -> (tempfile::TempDir, Arc<ManualClock>, Enrollment) {
        enrollment_with(Arc::new(MemoryKeyStore::random())).await
    }

    #[tokio::test]
    async fn nonce_is_single_use_unforgeable_and_expires() {
        let (_d, clock, e) = enrollment().await;
        let (n, exp) = e.issue().unwrap();
        assert_eq!(exp, clock.unix() + 300);
        e.consume(&n).await.unwrap();
        assert!(e.consume(&n).await.is_err(), "ikkinchi marta");
        // Soxta: muddatni uzaytirish yoki tasodifni o'zgartirish HMAC'ni buzadi.
        let (mut f, _) = e.issue().unwrap();
        f[7] ^= 0x01;
        assert!(e.consume(&f).await.is_err());
        assert!(e.consume(&[0u8; 32]).await.is_err());
        assert!(e.consume(b"short").await.is_err());
        // Muddati o'tgan.
        let (old, _) = e.issue().unwrap();
        clock.advance(Duration::seconds(301));
        assert!(e.consume(&old).await.is_err());
        // Boshqa KeyStore (boshqa server) bergan nonce qabul qilinmaydi.
        let (_d2, _c2, other) = enrollment().await;
        let (foreign, _) = other.issue().unwrap();
        assert!(e.consume(&foreign).await.is_err());
    }

    /// Ko'p instansiya: bir xil KeyStore va bitta DB — A bergan nonce B'da qabul qilinadi, lekin
    /// bir marta (A'da ham, B'da ham qayta ishlatib bo'lmaydi).
    #[tokio::test]
    async fn nonce_from_one_instance_consumed_once_on_another() {
        let ks: Arc<dyn KeyStore> = Arc::new(MemoryKeyStore::from_seed([9; 32]));
        let (_d, clock, a) = enrollment_with(ks.clone()).await;
        let b = Enrollment::new(a.pool.clone(), ks, clock.clone(), 300).unwrap();
        let (n, _) = a.issue().unwrap();
        b.consume(&n).await.unwrap();
        assert!(a.consume(&n).await.is_err());
        assert!(b.consume(&n).await.is_err());
    }

    #[tokio::test]
    async fn issuing_keeps_no_state() {
        let (_d, _c, e) = enrollment().await;
        for _ in 0..20_000 {
            e.issue().unwrap();
        }
        let n: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM pqlink_used_nonces")
            .fetch_one(&e.pool)
            .await
            .unwrap();
        assert_eq!(n, 0);
    }
}
