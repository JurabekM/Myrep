//! M6 — 8-tamoyil «O'zingizga sarmoya qiling» (`docs/musofir/SPEC.md` 6A): soat qiymati uy
//! valyutasida — faqat kiritilgan kurs bilan.
//!
//! Soat qiymatining o'zi (ish valyutasida) — umumiy formula (`domain-uy::learning::hour_value`, Uy 2G.1
//! bilan bir xil yaxlitlash); bu yerda faqat uy valyutasidagi ko'rinish va kurs holati.
//!
//! Vektor: `spec/test-vectors/mf_hour_value.json`.
use baraka_money::{convert, Currency, FxRate, Money};

use crate::DomainError;

/// Kurs shu kundan eski bo'lsa — «kursni yangilang» (SPEC 4.4, OQ-MF4).
pub const STALE_RATE_DAYS: i64 = 30;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RateStatus {
    /// Ish valyutasi uy valyutasi bilan bir xil — kurs kerak emas.
    SameCurrency,
    /// Kurs bor va 30 kundan eski emas.
    Fresh,
    /// Kurs 30 kundan eski: qiymat ko'rsatiladi, «yangilang» belgisi bilan.
    Stale,
    /// Kurs yo'q — uy valyutasidagi qiymat ko'rsatilmaydi (taxmin qilinmaydi).
    NoRate,
}

impl RateStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::SameCurrency => "SAME_CURRENCY",
            Self::Fresh => "FRESH",
            Self::Stale => "STALE",
            Self::NoRate => "NO_RATE",
        }
    }
}

/// Amaldagi kurs va uning yoshi (bugun − kurs sanasi, kunda). Yosh noma'lum (`None`) yoki manfiy —
/// kurs kelajakdagi sanadan deb hisoblanmaydi: `FUTURE_DATE` (oracle bilan bir xil).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RateAt {
    pub rate: FxRate,
    pub age_days: Option<i64>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HomeHourValue {
    pub status: RateStatus,
    /// 1 soat uy valyutasida; `NoRate` da `None`.
    pub hour_value: Option<Money>,
    /// «Ikki barobar maqsad» uy valyutasida = 2 × `hour_value`.
    pub double_target: Option<Money>,
}

/// Ish valyutasidagi 1 soat qiymatini uy valyutasida ko'rsatish: `convert(1 soat)` (daromad emas, soat
/// qiymati aylantiriladi), ikki barobar maqsad — 2 × shu. Bir xil valyutada kurs e'tiborsiz.
pub fn home_hour_value(
    hour_value: Money,
    home: Currency,
    rate: Option<&RateAt>,
) -> Result<HomeHourValue, DomainError> {
    if hour_value.is_negative() {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    let (status, value) = if hour_value.currency() == home {
        (RateStatus::SameCurrency, Some(hour_value))
    } else {
        match rate {
            None => (RateStatus::NoRate, None),
            Some(r) => {
                if r.rate.from != hour_value.currency() || r.rate.to != home {
                    return Err(DomainError::new("CURRENCY_MISMATCH"));
                }
                if r.rate.rate_num <= 0 || r.rate.rate_den <= 0 {
                    return Err(DomainError::on("INVALID_RATE", "rate"));
                }
                let age = match r.age_days {
                    Some(a) if a >= 0 => a,
                    _ => return Err(DomainError::on("FUTURE_DATE", "rateOn")),
                };
                let status = if age > STALE_RATE_DAYS {
                    RateStatus::Stale
                } else {
                    RateStatus::Fresh
                };
                (status, Some(convert(hour_value, &r.rate)?))
            }
        }
    };
    let double_target = match value {
        Some(v) => Some(v.checked_add(v)?),
        None => None,
    };
    Ok(HomeHourValue {
        status,
        hour_value: value,
        double_target,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn krw(v: i64) -> Money {
        Money::new(v, Currency::Krw)
    }

    fn at(num: i64, den: i64, age_days: i64) -> RateAt {
        at_opt(num, den, Some(age_days))
    }

    fn at_opt(num: i64, den: i64, age_days: Option<i64>) -> RateAt {
        RateAt {
            rate: FxRate {
                from: Currency::Krw,
                to: Currency::Uzs,
                rate_num: num,
                rate_den: den,
            },
            age_days,
        }
    }

    #[test]
    fn converts_hour_value_with_rate_and_flags_stale() {
        // 12 045 von × 9,1 = 109 609,50 so'm.
        let h = home_hour_value(krw(12_045), Currency::Uzs, Some(&at(91, 10, 30))).unwrap();
        assert_eq!(h.status, RateStatus::Fresh);
        assert_eq!(h.hour_value.map(|m| m.minor()), Some(10_960_950));
        assert_eq!(h.double_target.map(|m| m.minor()), Some(21_921_900));
        let stale = home_hour_value(krw(12_045), Currency::Uzs, Some(&at(91, 10, 31))).unwrap();
        assert_eq!(stale.status, RateStatus::Stale);
        assert!(stale.hour_value.is_some());
    }

    #[test]
    fn no_rate_means_no_home_value() {
        let h = home_hour_value(krw(12_045), Currency::Uzs, None).unwrap();
        assert_eq!(h.status, RateStatus::NoRate);
        assert_eq!((h.hour_value, h.double_target), (None, None));
    }

    #[test]
    fn same_currency_ignores_rate() {
        let uzs = Money::new(3_009_259, Currency::Uzs);
        let h = home_hour_value(uzs, Currency::Uzs, Some(&at(2, 1, 90))).unwrap();
        assert_eq!(h.status, RateStatus::SameCurrency);
        assert_eq!(h.hour_value, Some(uzs));
    }

    #[test]
    fn double_is_twice_the_rounded_home_value() {
        // 12 045 × 9,125 = 109 910,625 → 109 910,63; ikki barobar — 219 821,26 (convert(24 090) emas).
        let h = home_hour_value(krw(12_045), Currency::Uzs, Some(&at(73, 8, 0))).unwrap();
        assert_eq!(h.hour_value.map(|m| m.minor()), Some(10_991_063));
        assert_eq!(h.double_target.map(|m| m.minor()), Some(21_982_126));
    }

    #[test]
    fn errors() {
        let code = |r: Result<HomeHourValue, DomainError>| r.unwrap_err().code;
        assert_eq!(
            code(home_hour_value(krw(1), Currency::Uzs, Some(&at(0, 10, 1)))),
            "INVALID_RATE"
        );
        assert_eq!(
            code(home_hour_value(
                krw(1),
                Currency::Uzs,
                Some(&at(91, 10, -1))
            )),
            "FUTURE_DATE"
        );
        assert_eq!(
            code(home_hour_value(krw(-1), Currency::Uzs, None)),
            "AMOUNT_NEGATIVE"
        );
        assert_eq!(
            code(home_hour_value(
                krw(1),
                Currency::Uzs,
                Some(&at_opt(91, 10, None))
            )),
            "FUTURE_DATE"
        );
        let mut other = at(91, 10, 1);
        other.rate.from = Currency::Usd;
        assert_eq!(
            code(home_hour_value(krw(1), Currency::Uzs, Some(&other))),
            "CURRENCY_MISMATCH"
        );
    }
}
