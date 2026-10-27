//! Shield rolining yuqori mavjudligi (ADR-0026): bitta yetakchi, zaxiralar, davriy snapshot.
//!
//! * **Yetakchilik** — `shield_leader` jadvalidagi ijara (lease). Har instansiya
//!   `renew_interval_ms` da ijarani olishga/yangilashga urinadi: o'zi egasi bo'lsa yoki muddati
//!   o'tgan bo'lsa — oladi. Ega almashganda `epoch` oshadi.
//! * **Faqat yetakchi xizmat qiladi.** Zaxira `503 SHIELD_STANDBY` qaytaradi va mijoz keyingi
//!   URL'ga o'tadi (`shield_client`). Yetakchi o'zini ijara muddatidan bir yangilash oralig'i oldin
//!   to'xtatadi: DB'ga yeta olmasa, boshqasi olishidan oldin xizmatni to'xtatadi. Ikki yetakchi
//!   bo'lmaydi, agar soatlar farqi shu zaxiradan kichik bo'lsa (NTP).
//! * **Snapshot** — yetakchi belgilar omborini `snapshot_interval_secs` da `shield_snapshots` ga yozadi.
//!   Yozuv `epoch` bilan to'silgan: ijarani yo'qotgan eski yetakchining kechikkan snapshot'i
//!   yozilmaydi. Oxirgi `snapshots_keep` tasi saqlanadi.
//! * **O'tish** — yangi `epoch` bilan yetakchi bo'lgan instansiya avval oxirgi butun snapshot'ni
//!   tiklaydi (xesh va tuzilma tekshiriladi, buzilgani o'tkazib yuboriladi), keyin xizmat qiladi.
//!   Oxirgi snapshot'dan keyingi hodisalar yo'qoladi (RPO ≤ `snapshot_interval_secs`). To'g'ri
//!   to'xtatishda (`step_down`) yakuniy snapshot yoziladi va ijara bo'shatiladi — zaxira bir
//!   yangilash oralig'ida oladi, hodisa yo'qolmaydi.

use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::Arc;
use std::time::Duration;

use mpay_common::clock::Clock;
use mpay_shield::Shield;
use mpay_vault::db::Db;
use serde::Serialize;
use sha2::{Digest, Sha256};
use sqlx::Row;
use tokio::sync::Mutex;

use crate::config::ShieldHaConfig;

/// Unix vaqti, ms.
pub fn now_ms(clock: &dyn Clock) -> i64 {
    (clock.now().unix_timestamp_nanos() / 1_000_000) as i64
}

#[derive(Debug, Default)]
struct HaState {
    /// Joriy yetakchilik davri (0 — hali yetakchi bo'lmagan).
    epoch: i64,
    last_snapshot_ms: Option<i64>,
    snapshot_bytes: usize,
}

/// Holat (healthz va metrikalar uchun).
#[derive(Debug, Clone, Serialize)]
pub struct HaStatus {
    pub instance: String,
    pub leader: bool,
    pub epoch: i64,
    /// Oxirgi snapshot'dan beri (s); yetakchi bo'lmasa yoki hali yozilmagan — `None`.
    pub snapshot_age_secs: Option<i64>,
    pub snapshot_bytes: usize,
}

/// `tick` natijasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tick {
    /// Yetakchi (davom etmoqda).
    Leader,
    /// Yetakchilikni yangi oldi (snapshot tiklandi).
    TookOver,
    /// Zaxira.
    Standby,
}

/// Yetakchilik va snapshot'lar.
pub struct ShieldHa {
    db: Db,
    shield: Arc<Shield>,
    cfg: ShieldHaConfig,
    me: String,
    state: Mutex<HaState>,
    /// Shu vaqtgacha (ms) xizmat qilish mumkin; 0 — zaxira.
    active_until: AtomicI64,
}

impl std::fmt::Debug for ShieldHa {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ShieldHa")
            .field("me", &self.me)
            .finish_non_exhaustive()
    }
}

impl ShieldHa {
    pub fn new(db: Db, shield: Arc<Shield>, cfg: ShieldHaConfig) -> Self {
        let me = cfg
            .instance_id
            .clone()
            .or_else(|| std::env::var("HOSTNAME").ok().filter(|h| !h.is_empty()))
            .unwrap_or_else(|| {
                let r = mpay_crypto::rng::array::<6>().unwrap_or_default();
                format!("shield-{}", hex::encode(r))
            });
        Self {
            db,
            shield,
            cfg,
            me,
            state: Mutex::new(HaState::default()),
            active_until: AtomicI64::new(0),
        }
    }

    pub fn instance(&self) -> &str {
        &self.me
    }

    /// Hozir so'rovlarga xizmat qilish mumkinmi.
    pub fn is_active(&self, now_ms: i64) -> bool {
        now_ms < self.active_until.load(Ordering::Acquire)
    }

    /// Ijarani oladi yoki yangilaydi; olinsa — `epoch`.
    async fn try_lease(&self, now: i64) -> Result<Option<i64>, sqlx::Error> {
        let until = now + self.cfg.lease_ttl_ms as i64;
        let inserted = sqlx::query(
            "INSERT INTO shield_leader (id, holder, epoch, expires_at) VALUES (1, $1, 1, $2) \
             ON CONFLICT DO NOTHING",
        )
        .bind(&self.me)
        .bind(until)
        .execute(self.db.pool())
        .await?
        .rows_affected();
        if inserted == 1 {
            return Ok(Some(1));
        }
        // SET ichidagi `holder` — eski qiymat: ega almashsa epoch oshadi.
        sqlx::query_scalar(
            "UPDATE shield_leader SET epoch = CASE WHEN holder = $1 THEN epoch ELSE epoch + 1 END, \
             holder = $1, expires_at = $2 WHERE id = 1 AND (holder = $1 OR expires_at <= $3) \
             RETURNING epoch",
        )
        .bind(&self.me)
        .bind(until)
        .bind(now)
        .fetch_optional(self.db.pool())
        .await
    }

    /// Bitta qadam: ijara, kerak bo'lsa tiklash, vaqti kelsa snapshot.
    pub async fn tick(&self, now: i64) -> Result<Tick, sqlx::Error> {
        let mut st = self.state.lock().await;
        let lease = match self.try_lease(now).await {
            Ok(l) => l,
            Err(e) => {
                // Ijara o'z muddatida tugaydi (`active_until`) — DB'siz yetakchi o'zini to'xtatadi.
                tracing::warn!(error = %e, instance = %self.me, "shield-ha: ijarani yangilab bo'lmadi");
                return Err(e);
            }
        };
        let Some(epoch) = lease else {
            if self.active_until.swap(0, Ordering::AcqRel) > now {
                tracing::warn!(instance = %self.me, "shield-ha: yetakchilik boshqa instansiyaga o'tdi — zaxira");
            }
            return Ok(Tick::Standby);
        };
        let mut result = Tick::Leader;
        if epoch != st.epoch {
            // Yangi davr: boshqa instansiya yetakchi bo'lgan bo'lishi mumkin — avval holatni tiklash.
            let restored = self.restore_latest().await?;
            st.epoch = epoch;
            st.last_snapshot_ms = Some(now);
            crate::metrics::shield_takeover();
            tracing::warn!(
                instance = %self.me,
                epoch,
                snapshot = ?restored,
                "shield-ha: yetakchilik olindi"
            );
            result = Tick::TookOver;
        }
        let margin = self.cfg.renew_interval_ms as i64;
        self.active_until.store(
            now + self.cfg.lease_ttl_ms as i64 - margin,
            Ordering::Release,
        );
        let due = st
            .last_snapshot_ms
            .is_none_or(|t| now - t >= self.cfg.snapshot_interval_secs as i64 * 1000);
        if due {
            match self.write_snapshot(st.epoch, now).await {
                Ok(Some(size)) => {
                    st.last_snapshot_ms = Some(now);
                    st.snapshot_bytes = size;
                }
                Ok(None) => {}
                Err(e) => {
                    crate::metrics::shield_snapshot_error();
                    tracing::error!(error = %e, "shield-ha: snapshot yozilmadi");
                }
            }
        }
        Ok(result)
    }

    /// Snapshot'ni yozadi (faqat shu `epoch` ijarasi amal qilsa) va eskilarini o'chiradi.
    /// `None` — ijara endi bizniki emas (yozilmadi).
    async fn write_snapshot(&self, epoch: i64, now: i64) -> Result<Option<usize>, sqlx::Error> {
        let data = self.shield.snapshot();
        let sha = hex::encode(Sha256::digest(&data));
        let id = format!("{epoch:012}-{now:015}-{}", self.me);
        let n = sqlx::query(
            "INSERT INTO shield_snapshots (snapshot_id, epoch, holder, created_at, size, sha256, data) \
             SELECT $1, $2, $3, $4, $5, $6, $7 WHERE EXISTS (SELECT 1 FROM shield_leader \
             WHERE id = 1 AND holder = $3 AND epoch = $2 AND expires_at > $4)",
        )
        .bind(&id)
        .bind(epoch)
        .bind(&self.me)
        .bind(now)
        .bind(data.len() as i64)
        .bind(&sha)
        .bind(&data)
        .execute(self.db.pool())
        .await?
        .rows_affected();
        if n == 0 {
            tracing::warn!(instance = %self.me, epoch, "shield-ha: ijara yo'q — snapshot yozilmadi");
            return Ok(None);
        }
        sqlx::query(
            "DELETE FROM shield_snapshots WHERE snapshot_id NOT IN (SELECT snapshot_id FROM \
             shield_snapshots ORDER BY created_at DESC, snapshot_id DESC LIMIT $1)",
        )
        .bind(i64::from(self.cfg.snapshots_keep))
        .execute(self.db.pool())
        .await?;
        tracing::debug!(bytes = data.len(), epoch, "shield-ha: snapshot");
        Ok(Some(data.len()))
    }

    /// Oxirgi butun snapshot'ni tiklaydi; hech biri bo'lmasa — bo'sh ombor.
    async fn restore_latest(&self) -> Result<Option<String>, sqlx::Error> {
        let rows = sqlx::query(
            "SELECT snapshot_id, sha256, data FROM shield_snapshots \
             ORDER BY created_at DESC, snapshot_id DESC LIMIT $1",
        )
        .bind(i64::from(self.cfg.snapshots_keep.max(1)))
        .fetch_all(self.db.pool())
        .await?;
        for r in &rows {
            let id: String = r.try_get("snapshot_id")?;
            let sha: String = r.try_get("sha256")?;
            let data: Vec<u8> = r.try_get("data")?;
            if hex::encode(Sha256::digest(&data)) != sha {
                tracing::error!(snapshot = %id, "shield-ha: snapshot xeshi mos emas — o'tkazildi");
                continue;
            }
            match self.shield.restore(&data) {
                Ok(()) => return Ok(Some(id)),
                Err(e) => {
                    tracing::error!(snapshot = %id, error = %e, "shield-ha: snapshot tiklanmadi — o'tkazildi")
                }
            }
        }
        tracing::warn!("shield-ha: snapshot yo'q — belgilar ombori bo'sh");
        self.shield.reset();
        Ok(None)
    }

    /// To'g'ri to'xtatish: yakuniy snapshot va ijarani bo'shatish (zaxira darhol oladi).
    pub async fn step_down(&self, now: i64) {
        let st = self.state.lock().await;
        if !self.is_active(now) {
            return;
        }
        self.active_until.store(0, Ordering::Release);
        if let Err(e) = self.write_snapshot(st.epoch, now).await {
            tracing::error!(error = %e, "shield-ha: yakuniy snapshot yozilmadi");
        }
        if let Err(e) = sqlx::query(
            "UPDATE shield_leader SET expires_at = 0 WHERE id = 1 AND holder = $1 AND epoch = $2",
        )
        .bind(&self.me)
        .bind(st.epoch)
        .execute(self.db.pool())
        .await
        {
            tracing::error!(error = %e, "shield-ha: ijara bo'shatilmadi");
        }
        tracing::info!(instance = %self.me, "shield-ha: yetakchilik topshirildi");
    }

    pub async fn status(&self, now: i64) -> HaStatus {
        let st = self.state.lock().await;
        let leader = self.is_active(now);
        HaStatus {
            instance: self.me.clone(),
            leader,
            epoch: st.epoch,
            snapshot_age_secs: if leader {
                st.last_snapshot_ms.map(|t| (now - t).max(0) / 1000)
            } else {
                None
            },
            snapshot_bytes: st.snapshot_bytes,
        }
    }

    /// Fon tsikli.
    pub fn spawn(self: Arc<Self>, clock: Arc<dyn Clock>) -> tokio::task::AbortHandle {
        tokio::spawn(async move {
            let mut t = tokio::time::interval(Duration::from_millis(self.cfg.renew_interval_ms));
            t.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
            loop {
                t.tick().await;
                let _ = self.tick(now_ms(clock.as_ref())).await;
            }
        })
        .abort_handle()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use mpay_shield::features::TxnEvent;
    use mpay_shield::rules::RuleSet;

    fn engine() -> Arc<Shield> {
        Arc::new(Shield::new(RuleSet::default_rules().unwrap(), None))
    }

    fn cfg(id: &str) -> ShieldHaConfig {
        ShieldHaConfig {
            enabled: true,
            instance_id: Some(id.into()),
            lease_ttl_ms: 3_000,
            renew_interval_ms: 1_000,
            snapshot_interval_secs: 10,
            snapshots_keep: 2,
        }
    }

    fn txn(card: u8, at: i64) -> TxnEvent {
        TxnEvent {
            at,
            device: [card; 32],
            card: [card; 32],
            merchant: "SHOP".into(),
            country: 860,
            amount_minor: 10_000,
            cdcvm: false,
            is_p2p: false,
        }
    }

    async fn db() -> (tempfile::TempDir, Db) {
        let dir = tempfile::tempdir().unwrap();
        let db = Db::open_sqlite(&dir.path().join("h.db")).await.unwrap();
        crate::dedup::migrate(&db).await.unwrap();
        (dir, db)
    }

    #[tokio::test]
    async fn crashed_leader_is_replaced_from_last_snapshot() {
        let (_d, db) = db().await;
        let (ea, eb) = (engine(), engine());
        let a = ShieldHa::new(db.clone(), ea.clone(), cfg("a"));
        let b = ShieldHa::new(db.clone(), eb.clone(), cfg("b"));
        let t0 = 1_000_000;
        assert_eq!(a.tick(t0).await.unwrap(), Tick::TookOver);
        assert_eq!(b.tick(t0 + 10).await.unwrap(), Tick::Standby);
        assert!(a.is_active(t0 + 100) && !b.is_active(t0 + 100));

        // A ishlaydi: 3 karta, 10 s dan keyin snapshot (3 karta), keyin yana 2 karta (yo'qoladi).
        for c in 1..=3 {
            ea.assess_txn(&txn(c, 1_800_000_000));
        }
        assert_eq!(a.tick(t0 + 10_000).await.unwrap(), Tick::Leader);
        for c in 4..=5 {
            ea.assess_txn(&txn(c, 1_800_000_001));
        }
        assert_eq!(ea.stats().0, 5);

        // A "yiqildi" (tick yo'q). Ijara muddati tugaguncha B olmaydi.
        assert_eq!(b.tick(t0 + 11_000).await.unwrap(), Tick::Standby);
        // A o'zini ijaradan oldin to'xtatadi (DB'ga yetmasa ham ikki yetakchi bo'lmaydi).
        assert!(!a.is_active(t0 + 10_000 + 2_000));
        assert_eq!(b.tick(t0 + 13_001).await.unwrap(), Tick::TookOver);
        assert!(b.is_active(t0 + 13_002));
        assert_eq!(eb.stats().0, 3, "oxirgi snapshot tiklandi");
        assert_eq!(b.status(t0 + 13_002).await.epoch, 2);

        // A qaytdi: ijara B'da — zaxira; eski davr bilan snapshot yoza olmaydi.
        assert_eq!(a.tick(t0 + 14_000).await.unwrap(), Tick::Standby);
        assert!(!a.is_active(t0 + 14_001));
        assert_eq!(a.write_snapshot(1, t0 + 14_002).await.unwrap(), None);
        let epochs: Vec<i64> =
            sqlx::query_scalar("SELECT epoch FROM shield_snapshots ORDER BY created_at")
                .fetch_all(db.pool())
                .await
                .unwrap();
        assert!(epochs.iter().all(|e| *e <= 2), "{epochs:?}");
    }

    #[tokio::test]
    async fn graceful_step_down_hands_over_without_loss() {
        let (_d, db) = db().await;
        let (ea, eb) = (engine(), engine());
        let a = ShieldHa::new(db.clone(), ea.clone(), cfg("a"));
        let b = ShieldHa::new(db.clone(), eb.clone(), cfg("b"));
        let t0 = 2_000_000;
        a.tick(t0).await.unwrap();
        for c in 1..=4 {
            ea.assess_txn(&txn(c, 1_800_000_000));
        }
        a.step_down(t0 + 500).await;
        assert!(!a.is_active(t0 + 501));
        // Ijara bo'shatilgan — B darhol oladi va yakuniy snapshot'dagi 4 kartani ko'radi.
        assert_eq!(b.tick(t0 + 600).await.unwrap(), Tick::TookOver);
        assert_eq!(eb.stats().0, 4);
        // Faqat oxirgi `snapshots_keep` (2) tasi saqlanadi.
        b.tick(t0 + 20_000).await.unwrap();
        b.tick(t0 + 40_000).await.unwrap();
        let n: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM shield_snapshots")
            .fetch_one(db.pool())
            .await
            .unwrap();
        assert_eq!(n, 2);
    }

    #[tokio::test]
    async fn corrupted_latest_snapshot_falls_back_to_previous() {
        let (_d, db) = db().await;
        let (ea, eb) = (engine(), engine());
        let a = ShieldHa::new(db.clone(), ea.clone(), cfg("a"));
        let b = ShieldHa::new(db.clone(), eb.clone(), cfg("b"));
        let t0 = 3_000_000;
        a.tick(t0).await.unwrap(); // yetakchi (birinchi snapshot interval o'tgach)
        ea.assess_txn(&txn(1, 1_800_000_000));
        a.tick(t0 + 10_000).await.unwrap(); // 1 karta
        ea.assess_txn(&txn(2, 1_800_000_000));
        a.step_down(t0 + 11_000).await; // 2 karta — eng oxirgisi
        sqlx::query(
            "UPDATE shield_snapshots SET sha256 = 'buzilgan' WHERE created_at = (SELECT MAX(created_at) FROM shield_snapshots)",
        )
        .execute(db.pool())
        .await
        .unwrap();
        assert_eq!(b.tick(t0 + 12_000).await.unwrap(), Tick::TookOver);
        assert_eq!(eb.stats().0, 1, "buzilgani o'tkazildi, oldingisi tiklandi");
    }
}
