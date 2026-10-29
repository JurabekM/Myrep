//! PQ Link sessiyalar ombori (2-faza P2.4). [`MemorySessionStore`] — bitta instansiya (sandbox,
//! SQLite, testlar); ko'p instansiyada server umumiy omborni beradi (`mpay-server`: PostgreSQL,
//! sessiya kalitlari KEK bilan shifrlangan).
//!
//! Ombor `seq` hisoblagichlarining yagona manbai: [`SessionStore::advance_recv`] faqat kutilgan
//! qiymatda oshiradi (takror/poyga — rad), [`SessionStore::next_send`] atomar.

use std::collections::HashMap;
use std::sync::Mutex;

use mpay_common::ports::SecurityLevel;
use mpay_common::DeviceId;
use mpay_crypto::SecretKey32;

use crate::server::SessionId;
use crate::PqLinkError;

/// Yakunlanmagan handshake (`hello` dan keyin, `finish` gacha).
pub struct PendingSession {
    pub c2s: SecretKey32,
    pub s2c: SecretKey32,
    pub fin_c: SecretKey32,
    pub th2: [u8; 32],
    pub expires: i64,
}

/// O'rnatilgan sessiya.
#[derive(Clone)]
pub struct EstablishedSession {
    pub c2s: SecretKey32,
    pub s2c: SecretKey32,
    pub device_id: DeviceId,
    pub security_level: SecurityLevel,
    pub attested_at: Option<i64>,
    /// Keyingi qabul qilinadigan qurilma yozuvi `seq`.
    pub recv_seq: u64,
    pub expires: i64,
}

impl std::fmt::Debug for EstablishedSession {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("EstablishedSession")
            .field("device_id", &self.device_id)
            .field("recv_seq", &self.recv_seq)
            .field("expires", &self.expires)
            .finish_non_exhaustive()
    }
}

/// `take_pending` natijasi.
pub enum TakePending {
    Pending(PendingSession),
    /// Sessiya allaqachon o'rnatilgan (takroriy ClientFinished) — u buzilmaydi.
    Established,
    /// Noma'lum yoki muddati o'tgan.
    Missing,
}

/// Sessiyalar ombori. Barcha amallar atomar bo'lishi shart (bir nechta instansiya parallel).
#[async_trait::async_trait]
pub trait SessionStore: Send + Sync + std::fmt::Debug {
    /// Yangi handshake uchun joy bormi (`max_sessions` — jami, `max_pending` — yakunlanmaganlar).
    async fn has_room(
        &self,
        now: i64,
        max_sessions: usize,
        max_pending: usize,
    ) -> Result<bool, PqLinkError>;
    async fn put_pending(&self, id: SessionId, p: PendingSession) -> Result<(), PqLinkError>;
    /// Yakunlanmagan sessiyani atomar oladi va o'chiradi.
    async fn take_pending(&self, id: &SessionId, now: i64) -> Result<TakePending, PqLinkError>;
    async fn put_established(
        &self,
        id: SessionId,
        s: EstablishedSession,
    ) -> Result<(), PqLinkError>;
    /// O'rnatilgan va muddati o'tmagan sessiya (`recv_seq` — joriy qiymat).
    async fn get_established(
        &self,
        id: &SessionId,
        now: i64,
    ) -> Result<Option<EstablishedSession>, PqLinkError>;
    /// `recv_seq == expected` bo'lsa `expected + 1` ga o'tkazadi; aks holda `false` (takror/poyga).
    async fn advance_recv(&self, id: &SessionId, expected: u64) -> Result<bool, PqLinkError>;
    /// Javob uchun navbatdagi `seq` (atomar oshiriladi); sessiya yo'q bo'lsa `None`.
    async fn next_send(&self, id: &SessionId) -> Result<Option<u64>, PqLinkError>;
    async fn remove(&self, id: &SessionId) -> Result<(), PqLinkError>;
    /// Muddati o'tmagan sessiyalar soni (diagnostika).
    async fn count(&self, now: i64) -> Result<usize, PqLinkError>;
}

enum Slot {
    Pending(PendingSession),
    Established(EstablishedSession, u64),
}

impl Slot {
    fn expires(&self) -> i64 {
        match self {
            Slot::Pending(p) => p.expires,
            Slot::Established(e, _) => e.expires,
        }
    }
}

#[derive(Default)]
struct Table {
    map: HashMap<SessionId, Slot>,
    pending: usize,
}

impl Table {
    fn purge(&mut self, now: i64) {
        self.map.retain(|_, s| s.expires() > now);
        self.pending = self
            .map
            .values()
            .filter(|s| matches!(s, Slot::Pending(_)))
            .count();
    }

    fn remove(&mut self, id: &SessionId) -> Option<Slot> {
        let s = self.map.remove(id)?;
        if matches!(s, Slot::Pending(_)) {
            self.pending -= 1;
        }
        Some(s)
    }
}

/// Xotiradagi ombor (bitta instansiya).
#[derive(Default)]
pub struct MemorySessionStore {
    t: Mutex<Table>,
}

impl std::fmt::Debug for MemorySessionStore {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("MemorySessionStore")
    }
}

impl MemorySessionStore {
    pub fn new() -> Self {
        Self::default()
    }

    fn lock(&self) -> Result<std::sync::MutexGuard<'_, Table>, PqLinkError> {
        self.t
            .lock()
            .map_err(|_| PqLinkError::Crypto("sessiya lock".into()))
    }
}

#[async_trait::async_trait]
impl SessionStore for MemorySessionStore {
    async fn has_room(
        &self,
        now: i64,
        max_sessions: usize,
        max_pending: usize,
    ) -> Result<bool, PqLinkError> {
        let mut t = self.lock()?;
        let full = |t: &Table| t.map.len() >= max_sessions || t.pending >= max_pending;
        // Har `hello` da emas (O(n)), faqat chegaraga yetganda tozalanadi.
        if full(&t) {
            t.purge(now);
        }
        Ok(!full(&t))
    }

    async fn put_pending(&self, id: SessionId, p: PendingSession) -> Result<(), PqLinkError> {
        let mut t = self.lock()?;
        if let Some(old) = t.map.insert(id, Slot::Pending(p)) {
            if matches!(old, Slot::Pending(_)) {
                t.pending -= 1;
            }
        }
        t.pending += 1;
        Ok(())
    }

    async fn take_pending(&self, id: &SessionId, now: i64) -> Result<TakePending, PqLinkError> {
        let mut t = self.lock()?;
        match t.map.get(id) {
            Some(Slot::Established(..)) => Ok(TakePending::Established),
            Some(Slot::Pending(_)) => match t.remove(id) {
                Some(Slot::Pending(p)) if p.expires > now => Ok(TakePending::Pending(p)),
                _ => Ok(TakePending::Missing),
            },
            None => Ok(TakePending::Missing),
        }
    }

    async fn put_established(
        &self,
        id: SessionId,
        s: EstablishedSession,
    ) -> Result<(), PqLinkError> {
        let mut t = self.lock()?;
        t.remove(&id);
        t.map.insert(id, Slot::Established(s, 1));
        Ok(())
    }

    async fn get_established(
        &self,
        id: &SessionId,
        now: i64,
    ) -> Result<Option<EstablishedSession>, PqLinkError> {
        let mut t = self.lock()?;
        match t.map.get(id) {
            Some(Slot::Established(s, _)) if s.expires > now => Ok(Some(s.clone())),
            Some(Slot::Established(..)) => {
                t.remove(id);
                Ok(None)
            }
            _ => Ok(None),
        }
    }

    async fn advance_recv(&self, id: &SessionId, expected: u64) -> Result<bool, PqLinkError> {
        let mut t = self.lock()?;
        match t.map.get_mut(id) {
            Some(Slot::Established(s, _)) if s.recv_seq == expected => {
                s.recv_seq += 1;
                Ok(true)
            }
            _ => Ok(false),
        }
    }

    async fn next_send(&self, id: &SessionId) -> Result<Option<u64>, PqLinkError> {
        let mut t = self.lock()?;
        match t.map.get_mut(id) {
            Some(Slot::Established(_, send)) => {
                let seq = *send;
                *send += 1;
                Ok(Some(seq))
            }
            _ => Ok(None),
        }
    }

    async fn remove(&self, id: &SessionId) -> Result<(), PqLinkError> {
        self.lock()?.remove(id);
        Ok(())
    }

    async fn count(&self, now: i64) -> Result<usize, PqLinkError> {
        Ok(self
            .lock()?
            .map
            .values()
            .filter(|s| s.expires() > now)
            .count())
    }
}
