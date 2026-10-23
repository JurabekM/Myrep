//! «Kelajagim» odati (SPEC 2.2): ketma-ket ajratilgan haftalar (streak).
//!
//! Haftalar jumadan boshlanadi ([`week_of`]). Joriy hafta hali tugamagan bo'lsa va unda ajratish
//! bo'lmasa, streak uzilmaydi — o'tgan haftadan sanaladi. Sanalar Toshkent kalendar sanasi.
//! Qoida `spec/test-vectors/streak.json` bilan bir xil.

use std::collections::BTreeSet;

use time::Date;

use crate::calendar::{DateRange, shift_days, week_of};

/// «Kelajagim» odati ko'rsatkichlari.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HabitStats {
    /// Ketma-ket ajratilgan haftalar (joriy yoki o'tgan haftadan sanaladi).
    pub current_streak_weeks: u32,
    /// Jami ajratilgan haftalar soni (uzilishlardan qat'i nazar).
    pub total_weeks: u32,
    /// Joriy haftada ajratish bo'lganmi.
    pub this_week_done: bool,
    /// Joriy hafta oralig'i.
    pub current_week: DateRange,
}

/// Ajratish sanalaridan odat statistikasi. Kelajakdagi sanalar hisobga olinmaydi.
///
/// Kalendar chegarasi (juda chetki sanalar) bo'lsa, hafta hisoblanmaydi — bu mahalliy
/// kalendarda amalda uchramaydi.
pub fn habit_stats(saving_dates: &[Date], today: Date) -> Option<HabitStats> {
    let current = week_of(today)?;
    let weeks = saving_weeks(saving_dates, today);
    let this_week_done = weeks.contains(&current.start);
    let end = if this_week_done {
        Some(current.start)
    } else {
        shift_days(current.start, -7)
    };
    Some(HabitStats {
        current_streak_weeks: end.map_or(0, |end| streak_ending_at(&weeks, end, None)),
        total_weeks: u32::try_from(weeks.len()).unwrap_or(u32::MAX),
        this_week_done,
        current_week: current,
    })
}

/// [`since`] sanasi haftasidan keyingi haftalardagi ketma-ketlik (progressiv taklif uchun).
/// `since` tushgan hafta hisobga olinmaydi; `None` bo'lsa — hamma haftalar.
pub fn streak_since(saving_dates: &[Date], today: Date, since: Option<Date>) -> u32 {
    let Some(current) = week_of(today) else {
        return 0;
    };
    let weeks = saving_weeks(saving_dates, today);
    let end = if weeks.contains(&current.start) {
        Some(current.start)
    } else {
        shift_days(current.start, -7)
    };
    let floor = since.and_then(week_of).map(|week| week.start);
    end.map_or(0, |end| streak_ending_at(&weeks, end, floor))
}

/// Ajratish sanalari bo'yicha ajratilgan haftalar boshlari (kelajakdagilar bundan mustasno).
fn saving_weeks(saving_dates: &[Date], today: Date) -> BTreeSet<Date> {
    saving_dates
        .iter()
        .filter(|date| **date <= today)
        .filter_map(|date| week_of(*date).map(|week| week.start))
        .collect()
}

/// [`end`] haftasidan orqaga qarab ketma-ket borlar soni. [`after`] haftasi (qat'iy) hisobga olinmaydi.
fn streak_ending_at(weeks: &BTreeSet<Date>, end: Date, after: Option<Date>) -> u32 {
    let mut count = 0_u32;
    let mut week = end;
    while weeks.contains(&week) && after.is_none_or(|floor| week > floor) {
        count += 1;
        match shift_days(week, -7) {
            Some(previous) => week = previous,
            None => break,
        }
    }
    count
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::date;

    #[test]
    fn payshanba_va_juma_turli_haftalar() {
        let stats = habit_stats(
            &[date!(2026 - 10 - 08), date!(2026 - 10 - 09)],
            date!(2026 - 10 - 09),
        )
        .expect("statistika");
        assert_eq!(stats.total_weeks, 2);
        assert_eq!(stats.current_streak_weeks, 2);
        assert!(stats.this_week_done);
    }

    #[test]
    fn joriy_hafta_bosh_bolsa_streak_uzilmaydi() {
        let stats = habit_stats(
            &[date!(2026 - 09 - 25), date!(2026 - 10 - 02)],
            date!(2026 - 10 - 10),
        )
        .expect("statistika");
        assert!(!stats.this_week_done);
        assert_eq!(stats.current_streak_weeks, 2);
    }

    #[test]
    fn kelajakdagi_yozuv_hisobga_olinmaydi() {
        let stats =
            habit_stats(&[date!(2026 - 10 - 20)], date!(2026 - 10 - 09)).expect("statistika");
        assert_eq!(stats.total_weeks, 0);
    }

    #[test]
    fn since_hafta_hisobga_olinmaydi() {
        let dates = [
            date!(2026 - 09 - 04),
            date!(2026 - 09 - 11),
            date!(2026 - 09 - 18),
            date!(2026 - 09 - 25),
            date!(2026 - 10 - 02),
            date!(2026 - 10 - 09),
        ];
        let today = date!(2026 - 10 - 09);
        assert_eq!(streak_since(&dates, today, None), 6);
        assert_eq!(streak_since(&dates, today, Some(date!(2026 - 09 - 19))), 3);
    }
}
