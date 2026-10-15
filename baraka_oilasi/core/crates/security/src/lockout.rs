use serde::{Deserialize, Serialize};

/// Kutishsiz ruxsat etilgan xato urinishlar soni.
pub const FREE_ATTEMPTS: u32 = 5;

/// O'sib boruvchi kutish (7.4): 5 xatodan keyin 30 s, keyin 1, 5, 15, 60 daqiqa.
pub const fn lockout_seconds(failures: u32) -> i64 {
    match failures {
        0..FREE_ATTEMPTS => 0,
        5 => 30,
        6 => 60,
        7 => 300,
        8 => 900,
        _ => 3_600,
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LockoutState {
    pub failures: u32,
    /// Unix soniya; shu vaqtgacha urinish qabul qilinmaydi.
    pub locked_until: i64,
}

impl LockoutState {
    pub fn check(&self, now: i64) -> Result<(), i64> {
        if now < self.locked_until {
            Err(self.locked_until)
        } else {
            Ok(())
        }
    }

    pub fn record_failure(&mut self, now: i64) {
        self.failures = self.failures.saturating_add(1);
        let wait = lockout_seconds(self.failures);
        self.locked_until = if wait > 0 { now + wait } else { 0 };
    }

    pub fn reset(&mut self) {
        *self = Self::default();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn schedule() {
        let mut s = LockoutState::default();
        for _ in 0..4 {
            s.record_failure(1_000);
        }
        assert_eq!(s.check(1_000), Ok(()));
        s.record_failure(1_000);
        assert_eq!(s.check(1_000), Err(1_030));
        assert_eq!(s.check(1_030), Ok(()));
        s.record_failure(1_030);
        assert_eq!(s.locked_until, 1_090);
        for _ in 0..10 {
            s.record_failure(2_000);
        }
        assert_eq!(s.locked_until, 5_600);
        s.reset();
        assert_eq!(s, LockoutState::default());
    }
}
