//! Odat ketma-ketligi (SPEC 2.2): hafta (jumadan boshlanadi) "bajarilgan" hisoblanadi, agar unda
//! kamida bitta ajratma bo'lsa. Joriy hafta tugamagan bo'lsa ketma-ketlikni uzmaydi.
use std::collections::BTreeSet;

use time::{Date, Duration, Weekday};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct StreakSummary {
    pub current_weeks: u32,
    pub best_weeks: u32,
    /// Ajratma qilingan turli kunlar soni.
    pub saved_days: u32,
}

/// Berilgan sanani o'z ichiga olgan haftaning boshlanish kuni (`anchor`).
#[must_use]
pub fn week_start(d: Date, anchor: Weekday) -> Date {
    let from_monday = |w: Weekday| i64::from(w.number_days_from_monday());
    let back = (from_monday(d.weekday()) - from_monday(anchor)).rem_euclid(7);
    d - Duration::days(back)
}

/// `allocation_dates` — ajratma sanalari (tartibsiz, takror bo'lishi mumkin). `today` dan keyingilar
/// e'tiborga olinmaydi.
#[must_use]
pub fn compute_streak(allocation_dates: &[Date], today: Date, anchor: Weekday) -> StreakSummary {
    let days: BTreeSet<Date> = allocation_dates
        .iter()
        .copied()
        .filter(|d| *d <= today)
        .collect();
    let weeks: BTreeSet<Date> = days.iter().map(|d| week_start(*d, anchor)).collect();

    let week = Duration::days(7);
    let this_week = week_start(today, anchor);
    let mut cursor = if weeks.contains(&this_week) {
        this_week
    } else {
        this_week - week
    };
    let mut current = 0;
    while weeks.contains(&cursor) {
        current += 1;
        cursor -= week;
    }

    let (mut best, mut run, mut prev): (u32, u32, Option<Date>) = (0, 0, None);
    for w in &weeks {
        run = if prev.is_some_and(|p| *w - p == week) {
            run + 1
        } else {
            1
        };
        best = best.max(run);
        prev = Some(*w);
    }

    StreakSummary {
        current_weeks: current,
        best_weeks: best,
        saved_days: u32::try_from(days.len()).unwrap_or(u32::MAX),
    }
}

#[cfg(test)]
mod tests {
    use time::macros::date;

    use super::*;

    const FRI: Weekday = Weekday::Friday;

    #[test]
    fn week_starts_on_friday() {
        assert_eq!(
            week_start(date!(2026 - 10 - 02), FRI),
            date!(2026 - 10 - 02)
        ); // juma
        assert_eq!(
            week_start(date!(2026 - 10 - 07), FRI),
            date!(2026 - 10 - 02)
        ); // chorshanba
        assert_eq!(
            week_start(date!(2026 - 10 - 08), FRI),
            date!(2026 - 10 - 02)
        ); // payshanba
        assert_eq!(
            week_start(date!(2026 - 10 - 09), FRI),
            date!(2026 - 10 - 09)
        ); // keyingi juma
        assert_eq!(
            week_start(date!(2026 - 10 - 07), Weekday::Monday),
            date!(2026 - 10 - 05)
        );
    }

    #[test]
    fn empty_is_zero() {
        let s = compute_streak(&[], date!(2026 - 10 - 07), FRI);
        assert_eq!((s.current_weeks, s.best_weeks, s.saved_days), (0, 0, 0));
    }

    #[test]
    fn in_progress_week_does_not_break_streak() {
        // Bugun chorshanba (2026-10-07), bu haftada hali ajratma yo'q; oldingi 2 hafta bor.
        let d = [date!(2026 - 09 - 19), date!(2026 - 09 - 27)];
        let s = compute_streak(&d, date!(2026 - 10 - 07), FRI);
        assert_eq!((s.current_weeks, s.best_weeks, s.saved_days), (2, 2, 2));
    }

    #[test]
    fn missing_a_whole_week_breaks_it() {
        let d = [
            date!(2026 - 09 - 12),
            date!(2026 - 09 - 19),
            date!(2026 - 10 - 03),
        ];
        let s = compute_streak(&d, date!(2026 - 10 - 07), FRI);
        assert_eq!((s.current_weeks, s.best_weeks), (1, 2));
    }

    #[test]
    fn duplicates_and_future_dates_are_ignored() {
        let d = [
            date!(2026 - 10 - 03),
            date!(2026 - 10 - 03),
            date!(2026 - 11 - 01),
        ];
        let s = compute_streak(&d, date!(2026 - 10 - 07), FRI);
        assert_eq!((s.current_weeks, s.saved_days), (1, 1));
    }
}
