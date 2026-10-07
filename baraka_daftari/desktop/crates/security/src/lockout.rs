/// Xato PIN urinishlaridan keyingi kutish: dastlabki 2 ta xato bepul, so'ng 30 s dan ikki baravar
/// o'sib boradi, eng ko'pi 1 soat.
#[must_use]
pub fn lockout_delay_secs(failures: u32) -> u64 {
    const FREE: u32 = 3;
    const BASE: u64 = 30;
    const CAP: u64 = 3600;
    if failures < FREE {
        return 0;
    }
    let shift = (failures - FREE).min(7);
    (BASE << shift).min(CAP)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escalates_then_caps() {
        let d: Vec<u64> = (0..=10).map(lockout_delay_secs).collect();
        assert_eq!(d, [0, 0, 0, 30, 60, 120, 240, 480, 960, 1920, 3600]);
        assert_eq!(lockout_delay_secs(u32::MAX), 3600);
    }
}
