use std::time::Duration;

/// Ilova fonga o'tgandan keyin avtomatik qulflash vaqti (DESKTOP_PROMPT.md 6.2: 5 daqiqa).
pub const AUTO_LOCK_TIMEOUT: Duration = Duration::from_secs(5 * 60);

/// Avto-qulflash siyosati: oyna fokusdan tushgandan keyin `timeout` o'tsa, qulflash kerak.
///
/// Vaqt monoton soat bo'yicha beriladi (ilova ishga tushgandan beri o'tgan `Duration`),
/// shuning uchun devor soati o'zgarishi siyosatga ta'sir qilmaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AutoLockPolicy {
    timeout: Duration,
    unfocused_since: Option<Duration>,
}

impl AutoLockPolicy {
    /// Berilgan vaqt bilan siyosat. Boshida oyna fokusda deb hisoblanadi.
    pub fn new(timeout: Duration) -> Self {
        Self {
            timeout,
            unfocused_since: None,
        }
    }

    /// Oyna fokusdan tushdi. Takroriy chaqiriq birinchi vaqtni o'zgartirmaydi.
    pub fn on_focus_lost(&mut self, now: Duration) {
        if self.unfocused_since.is_none() {
            self.unfocused_since = Some(now);
        }
    }

    /// Oyna yana fokusga keldi: taymer bekor qilinadi.
    pub fn on_focus_gained(&mut self) {
        self.unfocused_since = None;
    }

    /// Hozir qulflash kerakmi.
    pub fn should_lock(&self, now: Duration) -> bool {
        match self.unfocused_since {
            Some(since) => now.saturating_sub(since) >= self.timeout,
            None => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn secs(value: u64) -> Duration {
        Duration::from_secs(value)
    }

    #[test]
    fn fokusda_qulflanmaydi() {
        let policy = AutoLockPolicy::new(AUTO_LOCK_TIMEOUT);
        assert!(!policy.should_lock(secs(10_000)));
    }

    #[test]
    fn fokusdan_tushib_vaqt_otsa_qulflaydi() {
        let mut policy = AutoLockPolicy::new(secs(300));
        policy.on_focus_lost(secs(100));
        assert!(!policy.should_lock(secs(399)));
        assert!(policy.should_lock(secs(400)));
    }

    #[test]
    fn qaytib_kelsa_taymer_bekor_boladi() {
        let mut policy = AutoLockPolicy::new(secs(300));
        policy.on_focus_lost(secs(100));
        policy.on_focus_gained();
        assert!(!policy.should_lock(secs(10_000)));
    }

    #[test]
    fn takroriy_fokus_yoqotish_birinchi_vaqtni_saqlaydi() {
        let mut policy = AutoLockPolicy::new(secs(300));
        policy.on_focus_lost(secs(100));
        policy.on_focus_lost(secs(250));
        assert!(policy.should_lock(secs(400)));
    }
}
