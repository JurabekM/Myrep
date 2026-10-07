/// Harakatsizlikdan keyin avtomatik qulflash mantig'i (sof, vaqt tashqaridan beriladi).
/// Standart: 5 daqiqa (sozlanadi).
#[derive(Debug, Clone, Copy)]
pub struct AutoLock {
    timeout_secs: u64,
    last_activity: i64,
}

impl AutoLock {
    pub const DEFAULT_TIMEOUT_SECS: u64 = 300;

    #[must_use]
    pub const fn new(timeout_secs: u64, now: i64) -> Self {
        Self {
            timeout_secs,
            last_activity: now,
        }
    }

    pub const fn touch(&mut self, now: i64) {
        self.last_activity = now;
    }

    pub const fn set_timeout(&mut self, timeout_secs: u64) {
        self.timeout_secs = timeout_secs;
    }

    #[must_use]
    pub fn should_lock(&self, now: i64) -> bool {
        let idle = now.saturating_sub(self.last_activity);
        idle >= 0 && idle.unsigned_abs() >= self.timeout_secs
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn locks_after_timeout_and_touch_resets() {
        let mut a = AutoLock::new(300, 1000);
        assert!(!a.should_lock(1299));
        assert!(a.should_lock(1300));
        a.touch(1299);
        assert!(!a.should_lock(1500));
        a.set_timeout(60);
        assert!(a.should_lock(1359));
    }

    #[test]
    fn clock_going_backwards_does_not_lock() {
        assert!(!AutoLock::new(300, 1000).should_lock(900));
    }
}
