use std::sync::Mutex;

use chrono::{DateTime, Datelike, Duration, Months, NaiveDate, Utc, Weekday};
use chrono_tz::Tz;

/// Byudjet davrlari uchun standart vaqt mintaqasi.
pub const DEFAULT_TZ: Tz = chrono_tz::Asia::Tashkent;

/// Haftalik sikl jumadan boshlanadi (sozlanadi).
pub const WEEK_ANCHOR: Weekday = Weekday::Fri;

/// Vaqt manbai. Domen va testlar tizim soatiga bog'lanmaydi.
pub trait Clock: Send + Sync {
    fn now(&self) -> DateTime<Utc>;
}

#[derive(Debug, Default)]
pub struct SystemClock;

impl Clock for SystemClock {
    fn now(&self) -> DateTime<Utc> {
        Utc::now()
    }
}

/// Testlar uchun boshqariladigan soat.
#[derive(Debug)]
pub struct FixedClock {
    now: Mutex<DateTime<Utc>>,
}

impl FixedClock {
    pub fn new(now: DateTime<Utc>) -> Self {
        Self {
            now: Mutex::new(now),
        }
    }

    pub fn set(&self, now: DateTime<Utc>) {
        if let Ok(mut g) = self.now.lock() {
            *g = now;
        }
    }

    pub fn advance(&self, by: Duration) {
        if let Ok(mut g) = self.now.lock() {
            *g += by;
        }
    }
}

impl Clock for FixedClock {
    fn now(&self) -> DateTime<Utc> {
        self.now
            .lock()
            .map(|g| *g)
            .unwrap_or_else(|p| *p.into_inner())
    }
}

/// UTC lahzaning lokal sanasi.
pub fn local_date(instant: DateTime<Utc>, tz: Tz) -> NaiveDate {
    instant.with_timezone(&tz).date_naive()
}

/// `date` tushgan haftaning boshlanish kuni (`anchor` — masalan, juma).
pub fn week_start(date: NaiveDate, anchor: Weekday) -> NaiveDate {
    let days_back = (7 + date.weekday().num_days_from_monday() - anchor.num_days_from_monday()) % 7;
    date - Duration::days(i64::from(days_back))
}

/// Oylik davr: `[start, end)`. `month_start_day` — 1..=28 (oylik kuni).
/// Masalan, oylik kuni 10 bo'lsa, 2026-10-15 → [2026-10-10, 2026-11-10).
pub fn month_period(date: NaiveDate, month_start_day: u32) -> Option<(NaiveDate, NaiveDate)> {
    if !(1..=28).contains(&month_start_day) {
        return None;
    }
    let this_month = date.with_day(month_start_day)?;
    let start = if date.day() >= month_start_day {
        this_month
    } else {
        this_month.checked_sub_months(Months::new(1))?
    };
    let end = start.checked_add_months(Months::new(1))?;
    Some((start, end))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(y: i32, m: u32, day: u32) -> NaiveDate {
        NaiveDate::from_ymd_opt(y, m, day).unwrap()
    }

    #[test]
    fn friday_weeks() {
        // 2026-10-16 — juma
        assert_eq!(week_start(d(2026, 10, 16), WEEK_ANCHOR), d(2026, 10, 16));
        assert_eq!(week_start(d(2026, 10, 22), WEEK_ANCHOR), d(2026, 10, 16));
        assert_eq!(week_start(d(2026, 10, 15), WEEK_ANCHOR), d(2026, 10, 9));
    }

    #[test]
    fn month_periods() {
        assert_eq!(
            month_period(d(2026, 10, 15), 10),
            Some((d(2026, 10, 10), d(2026, 11, 10)))
        );
        assert_eq!(
            month_period(d(2026, 10, 5), 10),
            Some((d(2026, 9, 10), d(2026, 10, 10)))
        );
        assert_eq!(
            month_period(d(2026, 1, 3), 10),
            Some((d(2025, 12, 10), d(2026, 1, 10)))
        );
        assert_eq!(
            month_period(d(2026, 10, 1), 1),
            Some((d(2026, 10, 1), d(2026, 11, 1)))
        );
        assert_eq!(month_period(d(2026, 10, 1), 31), None);
    }

    #[test]
    fn tashkent_local_date() {
        let utc = DateTime::parse_from_rfc3339("2026-10-15T20:30:00Z")
            .unwrap()
            .with_timezone(&Utc);
        assert_eq!(local_date(utc, DEFAULT_TZ), d(2026, 10, 16));
    }
}
