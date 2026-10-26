//! PQ Link sessiyalarining umumiy ombori (2-faza P2.4): bir nechta `mpay-server` instansiyasi bitta
//! DB'ni bo'lishadi — handshake bir instansiyada boshlanib boshqasida tugashi, so'rovlar istalgan
//! instansiyaga tushishi mumkin.
//!
//! * Sessiya kalitlari (`c2s`, `s2c`, yakunlanmaganda `fin_c`, `th2`) DB'da faqat **KEK bilan
//!   shifrlangan** (AES-256-GCM, HSM'da; AAD = yorliq ‖ holat ‖ sessiya ID — boshqa sessiyaga yoki
//!   holatga ko'chirib bo'lmaydi).
//! * `recv_seq` / `send_seq` — DB'da, atomar `UPDATE` bilan: takror va poyga bir instansiyada ham,
//!   instansiyalar orasida ham rad etiladi.
//! * Shifri ochilgan kalitlar instansiya xotirasida keshlanadi (o'zgarmaydi) — har so'rovda HSM'ga
//!   murojaat yo'q.

use std::collections::HashMap;
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Arc, Mutex};

use mpay_common::clock::Clock;
use mpay_common::ports::SecurityLevel;
use mpay_common::DeviceId;
use mpay_crypto::keystore::KeyLabel;
use mpay_crypto::{KeyStore, SecretKey32};
use mpay_pqlink::store::{EstablishedSession, PendingSession, SessionStore, TakePending};
use mpay_pqlink::{PqLinkError, SessionId};
use sqlx::{AnyPool, Row};
use zeroize::Zeroizing;

const AAD_LABEL: &[u8] = b"MPAY-PQLINK-SESSION-V1";
const PENDING: &str = "PENDING";
const ESTABLISHED: &str = "ESTABLISHED";
/// Muddati o'tganlar shuncha soniyada bir marta tozalanadi (har instansiyada).
const CLEANUP_EVERY_SECS: i64 = 60;
/// Kalitlar keshi chegarasi (oshsa muddati o'tganlar, so'ng hammasi tashlanadi — DB'dan qayta o'qiladi).
const CACHE_MAX: usize = 50_000;

#[derive(Clone)]
struct CachedKeys {
    c2s: SecretKey32,
    s2c: SecretKey32,
    expires: i64,
}

/// DB'dagi sessiyalar ombori.
pub struct DbSessionStore {
    pool: AnyPool,
    ks: Arc<dyn KeyStore>,
    kek: KeyLabel,
    clock: Arc<dyn Clock>,
    cache: Mutex<HashMap<SessionId, CachedKeys>>,
    last_cleanup: AtomicI64,
}

impl std::fmt::Debug for DbSessionStore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("DbSessionStore")
    }
}

fn db_err(e: sqlx::Error) -> PqLinkError {
    tracing::error!(error = %e, "pqlink: sessiyalar ombori");
    PqLinkError::Crypto("sessiyalar ombori".into())
}

fn aad(state: &str, id: &SessionId) -> Vec<u8> {
    [AAD_LABEL, state.as_bytes(), &[0u8][..], &id[..]].concat()
}

fn key(b: &[u8]) -> Result<SecretKey32, PqLinkError> {
    SecretKey32::from_slice(b).ok_or_else(|| PqLinkError::Crypto("sessiya kaliti uzunligi".into()))
}

impl DbSessionStore {
    pub fn new(pool: AnyPool, ks: Arc<dyn KeyStore>, clock: Arc<dyn Clock>) -> Self {
        Self {
            pool,
            ks,
            kek: KeyLabel::new(KeyLabel::KEK),
            clock,
            cache: Mutex::new(HashMap::new()),
            last_cleanup: AtomicI64::new(0),
        }
    }

    fn seal(
        &self,
        state: &str,
        id: &SessionId,
        pt: &[u8],
    ) -> Result<(Vec<u8>, Vec<u8>), PqLinkError> {
        let s = self
            .ks
            .aes_gcm_seal(&self.kek, &aad(state, id), pt)
            .map_err(|e| PqLinkError::Crypto(e.to_string()))?;
        Ok((s.nonce.to_vec(), s.ciphertext))
    }

    fn open(
        &self,
        state: &str,
        id: &SessionId,
        nonce: &[u8],
        ct: &[u8],
    ) -> Result<Zeroizing<Vec<u8>>, PqLinkError> {
        let nonce: [u8; 12] = nonce
            .try_into()
            .map_err(|_| PqLinkError::Crypto("sessiya nonce".into()))?;
        self.ks
            .aes_gcm_open(&self.kek, &nonce, &aad(state, id), ct)
            .map_err(|_| PqLinkError::Crypto("sessiya yozuvini ochib bo'lmadi".into()))
    }

    fn cache_get(&self, id: &SessionId) -> Option<CachedKeys> {
        self.cache.lock().ok()?.get(id).cloned()
    }

    fn cache_put(&self, id: SessionId, k: CachedKeys) {
        if let Ok(mut c) = self.cache.lock() {
            if c.len() >= CACHE_MAX {
                let now = self.clock.unix();
                c.retain(|_, v| v.expires > now);
                if c.len() >= CACHE_MAX {
                    c.clear();
                }
            }
            c.insert(id, k);
        }
    }

    fn cache_drop(&self, id: &SessionId) {
        if let Ok(mut c) = self.cache.lock() {
            c.remove(id);
        }
    }

    /// Muddati o'tganlarni tozalash — daqiqada bir marta.
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
        if let Err(e) = sqlx::query("DELETE FROM pqlink_sessions WHERE expires_at <= $1")
            .bind(now)
            .execute(&self.pool)
            .await
        {
            tracing::warn!(error = %e, "pqlink: eski sessiyalar tozalanmadi");
        }
        if let Ok(mut c) = self.cache.lock() {
            c.retain(|_, v| v.expires > now);
        }
    }
}

#[async_trait::async_trait]
impl SessionStore for DbSessionStore {
    async fn has_room(
        &self,
        now: i64,
        max_sessions: usize,
        max_pending: usize,
    ) -> Result<bool, PqLinkError> {
        self.cleanup(now).await;
        let r = sqlx::query(
            "SELECT CAST(COUNT(*) AS BIGINT) AS total, \
             CAST(COALESCE(SUM(CASE WHEN state = 'PENDING' THEN 1 ELSE 0 END), 0) AS BIGINT) AS pending \
             FROM pqlink_sessions WHERE expires_at > $1",
        )
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(db_err)?;
        let total: i64 = r.try_get("total").map_err(db_err)?;
        let pending: i64 = r.try_get("pending").map_err(db_err)?;
        Ok((total as usize) < max_sessions && (pending as usize) < max_pending)
    }

    async fn put_pending(&self, id: SessionId, p: PendingSession) -> Result<(), PqLinkError> {
        let pt = Zeroizing::new(
            [
                &p.c2s.expose()[..],
                &p.s2c.expose()[..],
                &p.fin_c.expose()[..],
                &p.th2[..],
            ]
            .concat(),
        );
        let (nonce, sealed) = self.seal(PENDING, &id, &pt)?;
        sqlx::query(
            "INSERT INTO pqlink_sessions (session_id, state, nonce, sealed, expires_at) \
             VALUES ($1, 'PENDING', $2, $3, $4)",
        )
        .bind(&id[..])
        .bind(nonce)
        .bind(sealed)
        .bind(p.expires)
        .execute(&self.pool)
        .await
        .map_err(db_err)?;
        Ok(())
    }

    async fn take_pending(&self, id: &SessionId, now: i64) -> Result<TakePending, PqLinkError> {
        // Atomar: ikki instansiya bir xil ClientFinished'ni bir vaqtda olsa, faqat bittasi oladi.
        let row = sqlx::query(
            "DELETE FROM pqlink_sessions WHERE session_id = $1 AND state = 'PENDING' \
             RETURNING nonce, sealed, expires_at",
        )
        .bind(&id[..])
        .fetch_optional(&self.pool)
        .await
        .map_err(db_err)?;
        let Some(r) = row else {
            let est = sqlx::query(
                "SELECT 1 AS x FROM pqlink_sessions WHERE session_id = $1 AND state = 'ESTABLISHED'",
            )
            .bind(&id[..])
            .fetch_optional(&self.pool)
            .await
            .map_err(db_err)?;
            return Ok(if est.is_some() {
                TakePending::Established
            } else {
                TakePending::Missing
            });
        };
        let expires: i64 = r.try_get("expires_at").map_err(db_err)?;
        if expires <= now {
            return Ok(TakePending::Missing);
        }
        let nonce: Vec<u8> = r.try_get("nonce").map_err(db_err)?;
        let sealed: Vec<u8> = r.try_get("sealed").map_err(db_err)?;
        let pt = self.open(PENDING, id, &nonce, &sealed)?;
        if pt.len() != 128 {
            return Err(PqLinkError::Crypto("sessiya yozuvi uzunligi".into()));
        }
        let mut th2 = [0u8; 32];
        th2.copy_from_slice(&pt[96..128]);
        Ok(TakePending::Pending(PendingSession {
            c2s: key(&pt[..32])?,
            s2c: key(&pt[32..64])?,
            fin_c: key(&pt[64..96])?,
            th2,
            expires,
        }))
    }

    async fn put_established(
        &self,
        id: SessionId,
        s: EstablishedSession,
    ) -> Result<(), PqLinkError> {
        let pt = Zeroizing::new([&s.c2s.expose()[..], &s.s2c.expose()[..]].concat());
        let (nonce, sealed) = self.seal(ESTABLISHED, &id, &pt)?;
        sqlx::query(
            "INSERT INTO pqlink_sessions (session_id, state, nonce, sealed, device_id, security_level, \
             attested_at, recv_seq, send_seq, expires_at) \
             VALUES ($1, 'ESTABLISHED', $2, $3, $4, $5, $6, $7, 1, $8)",
        )
        .bind(&id[..])
        .bind(nonce)
        .bind(sealed)
        .bind(s.device_id.to_hex())
        .bind(i64::from(s.security_level as u8))
        .bind(s.attested_at)
        .bind(s.recv_seq as i64)
        .bind(s.expires)
        .execute(&self.pool)
        .await
        .map_err(db_err)?;
        self.cache_put(
            id,
            CachedKeys {
                c2s: s.c2s,
                s2c: s.s2c,
                expires: s.expires,
            },
        );
        Ok(())
    }

    async fn get_established(
        &self,
        id: &SessionId,
        now: i64,
    ) -> Result<Option<EstablishedSession>, PqLinkError> {
        let Some(r) = sqlx::query(
            "SELECT nonce, sealed, device_id, security_level, attested_at, recv_seq, expires_at \
             FROM pqlink_sessions WHERE session_id = $1 AND state = 'ESTABLISHED'",
        )
        .bind(&id[..])
        .fetch_optional(&self.pool)
        .await
        .map_err(db_err)?
        else {
            self.cache_drop(id);
            return Ok(None);
        };
        let expires: i64 = r.try_get("expires_at").map_err(db_err)?;
        if expires <= now {
            self.remove(id).await?;
            return Ok(None);
        }
        let keys = match self.cache_get(id) {
            Some(k) => k,
            None => {
                let nonce: Vec<u8> = r.try_get("nonce").map_err(db_err)?;
                let sealed: Vec<u8> = r.try_get("sealed").map_err(db_err)?;
                let pt = self.open(ESTABLISHED, id, &nonce, &sealed)?;
                if pt.len() != 64 {
                    return Err(PqLinkError::Crypto("sessiya yozuvi uzunligi".into()));
                }
                let k = CachedKeys {
                    c2s: key(&pt[..32])?,
                    s2c: key(&pt[32..64])?,
                    expires,
                };
                self.cache_put(*id, k.clone());
                k
            }
        };
        let device_hex: String = r.try_get("device_id").map_err(db_err)?;
        let level: i64 = r.try_get("security_level").map_err(db_err)?;
        Ok(Some(EstablishedSession {
            c2s: keys.c2s,
            s2c: keys.s2c,
            device_id: DeviceId::from_hex(&device_hex)
                .ok_or_else(|| PqLinkError::Crypto("device_id".into()))?,
            security_level: u8::try_from(level)
                .ok()
                .and_then(SecurityLevel::from_raw)
                .ok_or_else(|| PqLinkError::Crypto("security_level".into()))?,
            attested_at: r.try_get("attested_at").map_err(db_err)?,
            recv_seq: r.try_get::<i64, _>("recv_seq").map_err(db_err)? as u64,
            expires,
        }))
    }

    async fn advance_recv(&self, id: &SessionId, expected: u64) -> Result<bool, PqLinkError> {
        let n = sqlx::query(
            "UPDATE pqlink_sessions SET recv_seq = recv_seq + 1 \
             WHERE session_id = $1 AND state = 'ESTABLISHED' AND recv_seq = $2",
        )
        .bind(&id[..])
        .bind(expected as i64)
        .execute(&self.pool)
        .await
        .map_err(db_err)?
        .rows_affected();
        Ok(n == 1)
    }

    async fn next_send(&self, id: &SessionId) -> Result<Option<u64>, PqLinkError> {
        let r = sqlx::query(
            "UPDATE pqlink_sessions SET send_seq = send_seq + 1 \
             WHERE session_id = $1 AND state = 'ESTABLISHED' RETURNING send_seq - 1 AS seq",
        )
        .bind(&id[..])
        .fetch_optional(&self.pool)
        .await
        .map_err(db_err)?;
        r.map(|r| r.try_get::<i64, _>("seq").map(|s| s as u64))
            .transpose()
            .map_err(db_err)
    }

    async fn remove(&self, id: &SessionId) -> Result<(), PqLinkError> {
        self.cache_drop(id);
        sqlx::query("DELETE FROM pqlink_sessions WHERE session_id = $1")
            .bind(&id[..])
            .execute(&self.pool)
            .await
            .map_err(db_err)?;
        Ok(())
    }

    async fn count(&self, now: i64) -> Result<usize, PqLinkError> {
        let n: i64 = sqlx::query_scalar(
            "SELECT CAST(COUNT(*) AS BIGINT) FROM pqlink_sessions WHERE expires_at > $1",
        )
        .bind(now)
        .fetch_one(&self.pool)
        .await
        .map_err(db_err)?;
        Ok(n as usize)
    }
}
