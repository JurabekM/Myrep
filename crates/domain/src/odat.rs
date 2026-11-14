//! Odat statistikasi (SPEC 2B.9): foydalanuvchi tanlagan odat (masalan, chekish) xarajatlari.
//!
//! Faqat hisob: «oyiga X, yiliga Y». Ayblov, uyaltirish va kamaytirish rejasi yo'q.

use money::{Currency, Money};
use time::Date;

use crate::calendar::DateRange;

/// Odat jami: joriy oy, joriy yil va yil ichidagi yozuvlar soni.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HabitTotals {
    /// Joriy oy jami.
    pub month: Money,
    /// Joriy yil jami.
    pub year: Money,
    /// Yil ichidagi yozuvlar soni.
    pub entries_year: u32,
}

/// Odat yozuvlaridan (sana, summa) jami hisoblaydi. Oy va yil — yarim ochiq oraliqlar.
pub fn totals(
    entries: &[(Date, Money)],
    month: DateRange,
    year: DateRange,
    currency: Currency,
) -> HabitTotals {
    let mut month_minor = 0_i64;
    let mut year_minor = 0_i64;
    let mut entries_year = 0_u32;
    for (date, amount) in entries {
        if year.contains(*date) {
            year_minor = year_minor.saturating_add(amount.minor());
            entries_year = entries_year.saturating_add(1);
            if month.contains(*date) {
                month_minor = month_minor.saturating_add(amount.minor());
            }
        }
    }
    HabitTotals {
        month: Money::new(month_minor, currency),
        year: Money::new(year_minor, currency),
        entries_year,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::calendar::month_of;
    use time::macros::date;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn oy_va_yil_alohida_hisoblanadi() {
        let month = month_of(date!(2026 - 10 - 15), 1).expect("oy");
        let year = DateRange {
            start: date!(2026 - 01 - 01),
            end: date!(2027 - 01 - 01),
        };
        let entries = [
            (date!(2026 - 03 - 02), uzs(100)),
            (date!(2026 - 10 - 03), uzs(200)),
            (date!(2025 - 12 - 31), uzs(900)),
        ];
        let result = totals(&entries, month, year, Currency::Uzs);
        assert_eq!(result.month, uzs(200));
        assert_eq!(result.year, uzs(300));
        assert_eq!(result.entries_year, 2);
    }

    #[test]
    fn yozuv_bo_lmasa_nol() {
        let month = month_of(date!(2026 - 10 - 15), 1).expect("oy");
        let year = DateRange {
            start: date!(2026 - 01 - 01),
            end: date!(2027 - 01 - 01),
        };
        let result = totals(&[], month, year, Currency::Uzs);
        assert_eq!(result.month, uzs(0));
        assert_eq!(result.entries_year, 0);
    }
}
