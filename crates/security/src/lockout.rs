/// Shu sondan boshlab noto'g'ri urinishlar uchun kutish qo'yiladi.
pub const LOCKOUT_THRESHOLD: u32 = 3;

/// Noto'g'ri urinishlar soniga qarab kutish (soniyalarda). Har xato bilan o'sib boradi.
///
/// 1–2 xato — kutish yo'q. 3 — 30 soniya, 4 — 1 daqiqa, 5 — 5 daqiqa, 6 — 15 daqiqa, undan keyin — 1 soat.
pub const fn lockout_delay_secs(failed_attempts: u32) -> u64 {
    match failed_attempts {
        0..=2 => 0,
        3 => 30,
        4 => 60,
        5 => 300,
        6 => 900,
        _ => 3600,
    }
}

/// Qolgan kutish vaqti (soniyalarda), yoki kutish yo'q bo'lsa `None`.
///
/// Soat orqaga surilgan bo'lsa ham kutish kattaligi [`lockout_delay_secs`] dan oshmaydi.
pub fn retry_after_secs(failed_attempts: u32, last_failed_unix: i64, now_unix: i64) -> Option<u64> {
    let delay = lockout_delay_secs(failed_attempts);
    if delay == 0 {
        return None;
    }
    let elapsed = now_unix.saturating_sub(last_failed_unix);
    let elapsed = u64::try_from(elapsed).unwrap_or(0);
    let remaining = delay.saturating_sub(elapsed);
    (remaining > 0).then_some(remaining)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn kutish_jadvali_otadi() {
        assert_eq!(lockout_delay_secs(0), 0);
        assert_eq!(lockout_delay_secs(2), 0);
        assert_eq!(lockout_delay_secs(LOCKOUT_THRESHOLD), 30);
        assert_eq!(lockout_delay_secs(4), 60);
        assert_eq!(lockout_delay_secs(5), 300);
        assert_eq!(lockout_delay_secs(6), 900);
        assert_eq!(lockout_delay_secs(50), 3600);
    }

    #[test]
    fn qolgan_vaqt_hisoblanadi() {
        assert_eq!(retry_after_secs(2, 1000, 1000), None);
        assert_eq!(retry_after_secs(3, 1000, 1000), Some(30));
        assert_eq!(retry_after_secs(3, 1000, 1010), Some(20));
        assert_eq!(retry_after_secs(3, 1000, 1030), None);
        assert_eq!(retry_after_secs(3, 1000, 2000), None);
    }

    #[test]
    fn soat_orqaga_surilsa_kutish_oshmaydi() {
        // Oxirgi xato kelajakda ko'rinyapti: kutish baribir 30 soniyadan oshmasin.
        assert_eq!(retry_after_secs(3, 5000, 1000), Some(30));
    }
}
