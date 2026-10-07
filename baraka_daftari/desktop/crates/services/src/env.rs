use domain::{Clock, Date, IdGen, OffsetDateTime};
use money::{Currency, Money, MoneyError};
use time::UtcOffset;

use crate::ServiceError;

/// O'zbekiston (`Asia/Tashkent`) yil bo'yi UTC+5: yozgi/qishki vaqt yo'q, shuning uchun
/// `chrono-tz` kerak emas. Agar qoida o'zgarsa, shu yagona joy yangilanadi.
pub const TASHKENT_OFFSET_HOURS: i8 = 5;

pub struct Env<'a> {
    pub clock: &'a dyn Clock,
    pub ids: &'a dyn IdGen,
    pub device_id: &'a str,
}

/// Joriy xonadon va a'zo (birinchi ishga tushirishda yaratiladi).
#[derive(Debug, Clone)]
pub struct Ctx {
    pub household_id: String,
    pub member_id: String,
    pub currency: Currency,
}

impl Ctx {
    #[must_use]
    pub const fn zero(&self) -> Money {
        Money::zero(self.currency)
    }
}

/// UTC instant → lokal (Toshkent) sana. Byudjet davrlari shu sana bo'yicha.
#[must_use]
pub fn local_date(t: OffsetDateTime) -> Date {
    let offset = UtcOffset::from_hms(TASHKENT_OFFSET_HOURS, 0, 0).unwrap_or(UtcOffset::UTC);
    t.to_offset(offset).date()
}

/// Kalendar oy (`YYYY-MM`). Oylik kuni sozlamasi keyingi vazifada qo'shiladi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct YearMonth {
    pub year: i32,
    pub month: time::Month,
}

impl YearMonth {
    #[must_use]
    pub fn of(d: Date) -> Self {
        Self {
            year: d.year(),
            month: d.month(),
        }
    }

    /// # Errors
    /// `YYYY-MM` bo'lmasa.
    pub fn parse(s: &str) -> Result<Self, ServiceError> {
        let (y, m) = s
            .split_once('-')
            .ok_or(ServiceError::Invalid("oy YYYY-MM bo'lishi kerak"))?;
        let year: i32 = y
            .parse()
            .map_err(|_| ServiceError::Invalid("yil noto'g'ri"))?;
        let month_n: u8 = m
            .parse()
            .map_err(|_| ServiceError::Invalid("oy noto'g'ri"))?;
        let month =
            time::Month::try_from(month_n).map_err(|_| ServiceError::Invalid("oy 1..12"))?;
        Ok(Self { year, month })
    }

    #[must_use]
    pub fn text(self) -> String {
        format!("{:04}-{:02}", self.year, u8::from(self.month))
    }

    #[must_use]
    pub fn first_day(self) -> Date {
        Date::from_calendar_date(self.year, self.month, 1).unwrap_or(Date::MIN)
    }

    #[must_use]
    pub fn last_day(self) -> Date {
        Date::from_calendar_date(self.year, self.month, self.month.length(self.year))
            .unwrap_or(Date::MAX)
    }

    #[must_use]
    pub fn contains(self, d: Date) -> bool {
        d.year() == self.year && d.month() == self.month
    }

    #[must_use]
    pub fn previous(self) -> Self {
        let first = self.first_day();
        Self::of(first.previous_day().unwrap_or(first))
    }
}

/// Bir valyutadagi summalar yig'indisi.
///
/// # Errors
/// Valyuta mos kelmasa yoki overflow bo'lsa.
pub fn sum_money(
    currency: Currency,
    items: impl IntoIterator<Item = Money>,
) -> Result<Money, MoneyError> {
    items
        .into_iter()
        .try_fold(Money::zero(currency), Money::checked_add)
}

#[cfg(test)]
mod tests {
    use time::macros::{date, datetime};

    use super::*;

    #[test]
    fn local_date_is_utc_plus_five() {
        assert_eq!(
            local_date(datetime!(2026-10-07 20:30 UTC)),
            date!(2026 - 10 - 08)
        );
        assert_eq!(
            local_date(datetime!(2026-10-07 18:59 UTC)),
            date!(2026 - 10 - 07)
        );
    }

    #[test]
    fn year_month_roundtrip_and_bounds() {
        let ym = YearMonth::parse("2026-02").unwrap();
        assert_eq!(ym.text(), "2026-02");
        assert_eq!(
            (ym.first_day(), ym.last_day()),
            (date!(2026 - 02 - 01), date!(2026 - 02 - 28))
        );
        assert_eq!(
            YearMonth::parse("2024-02").unwrap().last_day(),
            date!(2024 - 02 - 29)
        );
        assert_eq!(ym.previous().text(), "2026-01");
        assert_eq!(
            YearMonth::parse("2026-01").unwrap().previous().text(),
            "2025-12"
        );
        assert!(ym.contains(date!(2026 - 02 - 10)) && !ym.contains(date!(2026 - 03 - 01)));
        for bad in ["", "2026", "2026-13", "x-01", "2026-00"] {
            assert!(YearMonth::parse(bad).is_err(), "{bad}");
        }
    }
}
