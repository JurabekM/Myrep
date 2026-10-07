//! Qutqarilgan pul, obunalar va haftalik konvertlar (SPEC 2B.5–2B.7). Sof hisoblar.
use money::{round_half_up, Money, MoneyError};
use time::Date;

use crate::{havas_status, HavasError, HavasState};

/// «Qutqarilgan pul» = `max(0, avvalgi davr − joriy davr)` (havas). Joriy davr ko'p bo'lsa — `0`:
/// ilova hech qachon «manfiy qutqarish» ko'rsatmaydi va ayblamaydi.
///
/// # Errors
/// Manfiy summa yoki valyuta mos kelmasa.
pub fn rescued_money(baseline: Money, current: Money) -> Result<Money, HavasError> {
    if baseline.minor() < 0 || current.minor() < 0 {
        return Err(HavasError::InvalidAmount);
    }
    let diff = baseline.checked_sub(current)?;
    Ok(Money::new(diff.minor().max(0), diff.currency()))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BillingPeriod {
    Weekly,
    Monthly,
    Quarterly,
    Yearly,
}

impl BillingPeriod {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Weekly => "WEEKLY",
            Self::Monthly => "MONTHLY",
            Self::Quarterly => "QUARTERLY",
            Self::Yearly => "YEARLY",
        }
    }

    #[must_use]
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "WEEKLY" => Some(Self::Weekly),
            "MONTHLY" => Some(Self::Monthly),
            "QUARTERLY" => Some(Self::Quarterly),
            "YEARLY" => Some(Self::Yearly),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SubscriptionCost {
    pub monthly: Money,
    pub yearly: Money,
}

/// Obunaning oylik va yillik narxi (haftalik: yiliga ×52, oyiga ×52/12; barchasi half-up).
///
/// # Errors
/// Manfiy summa yoki overflow.
pub fn subscription_cost(
    amount: Money,
    period: BillingPeriod,
) -> Result<SubscriptionCost, HavasError> {
    if amount.minor() < 0 {
        return Err(HavasError::InvalidAmount);
    }
    let a = i128::from(amount.minor());
    let cur = amount.currency();
    let make = |num: i128, den: i128| -> Result<Money, MoneyError> {
        Ok(Money::new(round_half_up(num, den)?, cur))
    };
    let (monthly, yearly) = match period {
        BillingPeriod::Weekly => (make(a * 52, 12)?, make(a * 52, 1)?),
        BillingPeriod::Monthly => (make(a, 1)?, make(a * 12, 1)?),
        BillingPeriod::Quarterly => (make(a, 3)?, make(a * 4, 1)?),
        BillingPeriod::Yearly => (make(a, 12)?, make(a, 1)?),
    };
    Ok(SubscriptionCost { monthly, yearly })
}

/// Shuncha kundan keyin «hali kerakmi?» deb so'raladi.
pub const FORGOTTEN_AFTER_DAYS: i64 = 60;

/// Unutilgan obuna: oxirgi «ishlatdim» (yo'q bo'lsa — boshlangan) sanadan beri kamida `threshold_days` o'tgan.
#[must_use]
pub fn is_forgotten(
    last_used_on: Option<Date>,
    started_on: Date,
    today: Date,
    threshold_days: i64,
) -> bool {
    let anchor = last_used_on.unwrap_or(started_on);
    (today - anchor).whole_days() >= threshold_days
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EnvelopeStatus {
    /// `limit − spent`; manfiy bo'lishi mumkin.
    pub remaining: Money,
    pub state: HavasState,
    pub used_bp: i64,
}

/// Haftalik konvert holati. Kartadagi xarajatlar ham konvertdan ayriladi (`spent` — barcha kanallar).
///
/// # Errors
/// `limit <= 0`, `spent < 0` yoki valyuta mos kelmasa.
pub fn envelope_status(limit: Money, spent: Money) -> Result<EnvelopeStatus, HavasError> {
    let s = havas_status(spent, limit)?;
    Ok(EnvelopeStatus {
        remaining: limit.checked_sub(spent)?,
        state: s.state,
        used_bp: s.used_bp,
    })
}

/// Jismoniy konvertga hozir qancha naqd solish kerak: `max(0, limit − spent)`.
///
/// # Errors
/// [`envelope_status`] bilan bir xil.
pub fn cash_to_fill(limit: Money, spent: Money) -> Result<Money, HavasError> {
    let st = envelope_status(limit, spent)?;
    Ok(Money::new(st.remaining.minor().max(0), limit.currency()))
}

/// Hafta oxiri: kutilgan naqd qoldiq (`max(0, limit − spent)`) minus haqiqiy qoldiq.
/// Musbat — naqd kam chiqdi (yozilmagan xarajat bor), manfiy — ortiqcha.
///
/// # Errors
/// [`envelope_status`] bilan bir xil yoki valyuta mos kelmasa.
pub fn closing_difference(
    limit: Money,
    spent: Money,
    leftover_cash: Money,
) -> Result<Money, HavasError> {
    Ok(cash_to_fill(limit, spent)?.checked_sub(leftover_cash)?)
}

#[cfg(test)]
mod tests {
    use money::Currency;
    use time::macros::date;

    use super::*;

    fn m(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn rescued_never_negative() {
        assert_eq!(rescued_money(m(50), m(30)).unwrap().minor(), 20);
        assert_eq!(rescued_money(m(30), m(50)).unwrap().minor(), 0);
        assert!(rescued_money(m(-1), m(0)).is_err());
        assert!(rescued_money(Money::new(1, Currency::Usd), m(1)).is_err());
    }

    #[test]
    fn subscription_rounding_and_overflow() {
        let c = subscription_cost(m(1_000_000), BillingPeriod::Weekly).unwrap();
        assert_eq!(
            (c.monthly.minor(), c.yearly.minor()),
            (4_333_333, 52_000_000)
        );
        assert!(subscription_cost(m(-1), BillingPeriod::Monthly).is_err());
        assert!(subscription_cost(m(i64::MAX), BillingPeriod::Monthly).is_err());
        for p in [
            BillingPeriod::Weekly,
            BillingPeriod::Monthly,
            BillingPeriod::Quarterly,
            BillingPeriod::Yearly,
        ] {
            assert_eq!(BillingPeriod::parse(p.as_str()), Some(p));
        }
        assert_eq!(BillingPeriod::parse("DAILY"), None);
    }

    #[test]
    fn forgotten_boundaries() {
        let start = date!(2026 - 01 - 01);
        assert!(!is_forgotten(
            None,
            start,
            date!(2026 - 03 - 01),
            FORGOTTEN_AFTER_DAYS
        ));
        assert!(is_forgotten(
            None,
            start,
            date!(2026 - 03 - 02),
            FORGOTTEN_AFTER_DAYS
        ));
        assert!(!is_forgotten(
            Some(date!(2026 - 10 - 10)),
            start,
            date!(2026 - 10 - 07),
            60
        ));
    }

    #[test]
    fn envelope_math() {
        let st = envelope_status(m(100_000), m(130_000)).unwrap();
        assert_eq!(
            (st.remaining.minor(), st.state),
            (-30_000, HavasState::Over)
        );
        assert_eq!(cash_to_fill(m(100_000), m(130_000)).unwrap().minor(), 0);
        assert_eq!(
            closing_difference(m(100_000), m(80_000), m(15_000))
                .unwrap()
                .minor(),
            5_000
        );
        assert_eq!(
            closing_difference(m(100_000), m(80_000), m(25_000))
                .unwrap()
                .minor(),
            -5_000
        );
        assert!(envelope_status(m(0), m(1)).is_err());
    }
}
