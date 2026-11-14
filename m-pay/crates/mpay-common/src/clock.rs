//! Vaqt manbai. Testlarda LUK TTL va sessiya muddatlarini boshqarish uchun `ManualClock`.

use std::sync::Mutex;

use time::{Duration, OffsetDateTime};

/// Vaqt manbai.
pub trait Clock: Send + Sync + std::fmt::Debug {
    fn now(&self) -> OffsetDateTime;

    /// Unix sekundlari.
    fn unix(&self) -> i64 {
        self.now().unix_timestamp()
    }
}

/// Tizim soati (UTC).
#[derive(Debug, Default, Clone, Copy)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now(&self) -> OffsetDateTime {
        OffsetDateTime::now_utc()
    }
}

/// Qo'lda boshqariladigan soat (testlar uchun).
#[derive(Debug)]
pub struct ManualClock(Mutex<OffsetDateTime>);

impl ManualClock {
    pub fn new(start: OffsetDateTime) -> Self {
        Self(Mutex::new(start))
    }

    /// Vaqtni oldinga suradi.
    pub fn advance(&self, d: Duration) {
        let mut g = self
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        *g += d;
    }

    pub fn set(&self, t: OffsetDateTime) {
        *self
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = t;
    }
}

impl Clock for ManualClock {
    fn now(&self) -> OffsetDateTime {
        *self
            .0
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manual_clock_advances() {
        let c = ManualClock::new(OffsetDateTime::UNIX_EPOCH);
        c.advance(Duration::hours(25));
        assert_eq!(c.unix(), 25 * 3600);
    }
}
