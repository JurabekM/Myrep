//! Kalendar: Toshkent sanasi, haftalar (jumadan boshlanadi) va oylar (oylik kuni bo'yicha).
//!
//! `Asia/Tashkent` — UTC+5, 1992 yildan beri yozgi vaqt yo'q: doimiy siljish yetarli va deterministik
//! (mobil `calendar.dart` bilan bir xil). Barcha sanalar Toshkent kalendar sanasida.

use time::{Date, Duration, Month, OffsetDateTime, UtcOffset, Weekday};

/// Toshkent vaqtining UTC'dan siljishi, soatlarda.
pub const TASHKENT_HOURS: i64 = 5;

/// Oylik davrning standart boshlanish kuni (oyning 1-sanasi).
pub const DEFAULT_MONTH_START_DAY: u8 = 1;

/// UTC instant → Toshkentdagi kalendar sanasi.
pub fn tashkent_date(instant: OffsetDateTime) -> Date {
    (instant.to_offset(UtcOffset::UTC) + Duration::hours(TASHKENT_HOURS)).date()
}

/// Yarim ochiq sana oralig'i: `[start, end)`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DateRange {
    /// Boshlanish sanasi (kiradi).
    pub start: Date,
    /// Tugash sanasi (kirmaydi).
    pub end: Date,
}

impl DateRange {
    /// Sana oraliqqa kiradimi.
    pub fn contains(&self, date: Date) -> bool {
        date >= self.start && date < self.end
    }
}

/// [`date`] dan `days` kun siljitadi. Kalendar chegarasidan oshsa — `None`.
pub fn shift_days(date: Date, days: i64) -> Option<Date> {
    date.checked_add(Duration::days(days))
}

/// Sana joylashgan hafta: jumadan boshlanadi, 7 kun.
pub fn week_of(date: Date) -> Option<DateRange> {
    let friday = i64::from(Weekday::Friday.number_days_from_monday());
    let back = (i64::from(date.weekday().number_days_from_monday()) - friday + 7) % 7;
    let start = shift_days(date, -back)?;
    Some(DateRange {
        start,
        end: shift_days(start, 7)?,
    })
}

/// Oylik davr: har oy [`month_start_day`] kunidan boshlanadi. Oyda shu kun bo'lmasa
/// (masalan, 31 → fevral), oyning oxirgi kuni olinadi.
pub fn month_of(date: Date, month_start_day: u8) -> Option<DateRange> {
    let this_start = start_in(date.year(), date.month(), month_start_day)?;
    let start = if date < this_start {
        let (year, month) = previous_month(date.year(), date.month());
        start_in(year, month, month_start_day)?
    } else {
        this_start
    };
    let (next_year, next_month) = next_month(start.year(), start.month());
    Some(DateRange {
        start,
        end: start_in(next_year, next_month, month_start_day)?,
    })
}

/// [`date`] dan oldingi to'liq oy (oylik audit shu davr uchun o'tkaziladi).
pub fn previous_month_of(date: Date, month_start_day: u8) -> Option<DateRange> {
    let current = month_of(date, month_start_day)?;
    month_of(shift_days(current.start, -1)?, month_start_day)
}

/// Berilgan yil va oyda [`day`] kunli sana. Kun oyga sig'masa — oyning oxirgi kuni.
fn start_in(year: i32, month: Month, day: u8) -> Option<Date> {
    (1..=day.clamp(1, 31))
        .rev()
        .find_map(|candidate| Date::from_calendar_date(year, month, candidate).ok())
}

fn previous_month(year: i32, month: Month) -> (i32, Month) {
    if month == Month::January {
        (year - 1, Month::December)
    } else {
        (year, month.previous())
    }
}

fn next_month(year: i32, month: Month) -> (i32, Month) {
    if month == Month::December {
        (year + 1, Month::January)
    } else {
        (year, month.next())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::{date, datetime};

    #[test]
    fn toshkent_sanasi_utc_dan_besh_soat_oldin_emas_keyin() {
        // 2026-10-08 19:30 UTC = 2026-10-09 00:30 Toshkent (juma).
        assert_eq!(
            tashkent_date(datetime!(2026-10-08 19:30 UTC)),
            date!(2026 - 10 - 09)
        );
        // 2026-10-08 18:59 UTC = 23:59 Toshkent (payshanba).
        assert_eq!(
            tashkent_date(datetime!(2026-10-08 18:59 UTC)),
            date!(2026 - 10 - 08)
        );
    }

    #[test]
    fn hafta_jumadan_boshlanadi() {
        let thursday = week_of(date!(2026 - 10 - 08)).expect("hafta");
        assert_eq!(thursday.start, date!(2026 - 10 - 02));
        let friday = week_of(date!(2026 - 10 - 09)).expect("hafta");
        assert_eq!(friday.start, date!(2026 - 10 - 09));
        assert_eq!(friday.end, date!(2026 - 10 - 16));
    }

    #[test]
    fn oy_birinchi_kundan_va_oylik_kunidan() {
        let march = month_of(date!(2026 - 03 - 15), 1).expect("oy");
        assert_eq!(march.start, date!(2026 - 03 - 01));
        assert_eq!(march.end, date!(2026 - 04 - 01));

        // Oylik 10-sanada: 5-mart 10-februarga tegishli.
        let before = month_of(date!(2026 - 03 - 05), 10).expect("oy");
        assert_eq!(before.start, date!(2026 - 02 - 10));
        assert_eq!(before.end, date!(2026 - 03 - 10));
    }

    #[test]
    fn oy_kuni_mavjud_bolmasa_oxirgi_kun() {
        // 31-kun fevralda yo'q: fevralning oxirgi kuni (28) boshlanish.
        let feb = month_of(date!(2026 - 02 - 27), 31).expect("oy");
        assert_eq!(feb.start, date!(2026 - 01 - 31));
        assert_eq!(feb.end, date!(2026 - 02 - 28));
    }

    #[test]
    fn otgan_oy_yanvarda_yil_orqaga_ketadi() {
        let prev = previous_month_of(date!(2026 - 01 - 15), 1).expect("oy");
        assert_eq!(prev.start, date!(2025 - 12 - 01));
        assert_eq!(prev.end, date!(2026 - 01 - 01));
    }
}
