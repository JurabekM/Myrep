//! Odat ko'rsatkichi: «Kelajagim»ga ajratilgan haftalar ketma-ketligi (uy/SPEC 2.2).
use std::collections::BTreeSet;

use chrono::{Duration, NaiveDate, Weekday};

use baraka_domain_common::week_start;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StreakInfo {
    /// Hozirgi ketma-ketlik (haftalarda). Joriy hafta hali tugamagani uchun, unda ajratma
    /// bo'lmasa ham ketma-ketlik o'tgan haftadan hisoblanadi.
    pub current_weeks: u32,
    pub longest_weeks: u32,
    pub total_weeks: u32,
    pub current_week_done: bool,
}

/// `deposit_dates` — ajratma qilingan lokal sanalar. OQ-P4 («dam haftasi») hal bo'lguncha
/// har bir hafta talab qilinadi.
pub fn compute_streak(
    deposit_dates: &[NaiveDate],
    today: NaiveDate,
    anchor: Weekday,
) -> StreakInfo {
    let weeks: BTreeSet<NaiveDate> = deposit_dates
        .iter()
        .filter(|d| **d <= today)
        .map(|d| week_start(*d, anchor))
        .collect();
    let this_week = week_start(today, anchor);
    let current_week_done = weeks.contains(&this_week);

    let mut cursor = if current_week_done {
        this_week
    } else {
        this_week - Duration::days(7)
    };
    let mut current = 0;
    while weeks.contains(&cursor) {
        current += 1;
        cursor -= Duration::days(7);
    }

    let mut longest = 0;
    let mut run = 0;
    let mut prev: Option<NaiveDate> = None;
    for w in &weeks {
        run = match prev {
            Some(p) if *w - p == Duration::days(7) => run + 1,
            _ => 1,
        };
        longest = longest.max(run);
        prev = Some(*w);
    }

    StreakInfo {
        current_weeks: current,
        longest_weeks: longest,
        total_weeks: u32::try_from(weeks.len()).unwrap_or(u32::MAX),
        current_week_done,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_domain_common::WEEK_ANCHOR;

    fn d(m: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(2026, m, day).unwrap()
    }

    #[test]
    fn friday_anchored() {
        // Haftalar: 9.25, 10.2, 10.9 (juma) — 10.15 (payshanba) 10.9 haftasiga tegishli.
        let deposits = [d(9, 26), d(10, 3), d(10, 15)];
        let s = compute_streak(&deposits, d(10, 15), WEEK_ANCHOR);
        assert_eq!(
            s,
            StreakInfo {
                current_weeks: 3,
                longest_weeks: 3,
                total_weeks: 3,
                current_week_done: true
            }
        );
        // Juma 10.16 — yangi hafta boshlandi, hali ajratma yo'q: ketma-ketlik uzilmaydi.
        let s = compute_streak(&deposits, d(10, 16), WEEK_ANCHOR);
        assert_eq!(s.current_weeks, 3);
        assert!(!s.current_week_done);
        // Bir hafta o'tkazib yuborildi.
        let s = compute_streak(&deposits, d(10, 23), WEEK_ANCHOR);
        assert_eq!(s.current_weeks, 0);
        assert_eq!(s.longest_weeks, 3);
    }

    #[test]
    fn future_dates_ignored_and_gaps() {
        let deposits = [d(9, 4), d(9, 25), d(10, 2), d(12, 1)];
        let s = compute_streak(&deposits, d(10, 3), WEEK_ANCHOR);
        assert_eq!(s.current_weeks, 2);
        assert_eq!(s.total_weeks, 3);
    }
}
