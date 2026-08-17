//! Replay himoyasi — spec 4.2-bo'lim, band 2: counter monotonik o'sishi + bitmap oyna.

/// Qabul qilish oynasi hajmi (spec tavsiyasi: 64 ta counter qiymati).
pub const WINDOW_SIZE: u32 = 64;

/// Har bir `session_id` uchun saqlanadigan replay-himoya holati.
#[derive(Debug, Default)]
pub struct ReplayWindow {
    highest: u32,
    bitmap: u64,
    initialized: bool,
}

impl ReplayWindow {
    pub fn new() -> Self {
        Self::default()
    }

    /// `counter` qabul qilinishi mumkinmi tekshiradi va, agar mumkin bo'lsa, holatni
    /// yangilaydi. `false` qaytsa — chaqiruvchi frame'ni rad etishi (Implicit Rejection
    /// yo'lini ishga tushirishi) SHART.
    pub fn check_and_update(&mut self, counter: u32) -> bool {
        if !self.initialized {
            self.initialized = true;
            self.highest = counter;
            self.bitmap = 1;
            return true;
        }

        if counter > self.highest {
            let shift = counter - self.highest;
            self.bitmap = if shift >= WINDOW_SIZE { 0 } else { self.bitmap << shift };
            self.bitmap |= 1;
            self.highest = counter;
            true
        } else {
            let diff = self.highest - counter;
            if diff >= WINDOW_SIZE {
                false
            } else {
                let bit = 1u64 << diff;
                if self.bitmap & bit != 0 {
                    false
                } else {
                    self.bitmap |= bit;
                    true
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_strictly_increasing_counters() {
        let mut w = ReplayWindow::new();
        assert!(w.check_and_update(1));
        assert!(w.check_and_update(2));
        assert!(w.check_and_update(3));
    }

    #[test]
    fn rejects_exact_replay() {
        let mut w = ReplayWindow::new();
        assert!(w.check_and_update(5));
        assert!(!w.check_and_update(5));
    }

    #[test]
    fn rejects_stale_below_window() {
        let mut w = ReplayWindow::new();
        assert!(w.check_and_update(1000));
        assert!(!w.check_and_update(1000 - WINDOW_SIZE));
    }

    #[test]
    fn accepts_reordered_within_window() {
        let mut w = ReplayWindow::new();
        assert!(w.check_and_update(10));
        assert!(w.check_and_update(12));
        assert!(w.check_and_update(11));
        assert!(!w.check_and_update(11));
    }
}
