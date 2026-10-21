//! 2-qonun: «Qutqarilgan pul» (uy/SPEC 2B.7). Bazaviy davr tanlovi — OQ-P3.
use baraka_money::Money;

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RescueInput {
    /// Bazaviy davrdagi havas va oqib ketgan xarajatlar.
    pub baseline_leak: Money,
    /// Joriy davrdagi havas va oqib ketgan xarajatlar.
    pub current_leak: Money,
    /// Shu davrda bekor qilingan obunalarning oylik narxi.
    pub cancelled_subscriptions: Money,
    /// Konvertlarda qolgan qoldiqlar.
    pub envelope_leftovers: Money,
}

/// `max(0, baseline − current) + cancelled + leftovers`. Ko'proq sarflangan bo'lsa —
/// ilova ayblamaydi, taqqoslash qismi 0 bo'ladi.
pub fn rescued_money(i: &RescueInput) -> Result<Money, DomainError> {
    let saved = i
        .baseline_leak
        .checked_sub(i.current_leak)?
        .clamp_non_negative();
    if i.cancelled_subscriptions.is_negative() || i.envelope_leftovers.is_negative() {
        return Err(DomainError::on("NEGATIVE_COMPONENT", "rescue"));
    }
    Ok(saved
        .checked_add(i.cancelled_subscriptions)?
        .checked_add(i.envelope_leftovers)?)
}

/// Bekor qilingan obunaning yillik tejami.
pub fn annual_saving(monthly_price: Money) -> Result<Money, DomainError> {
    Ok(monthly_price.checked_mul(12)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn rescued() {
        let mut i = RescueInput {
            baseline_leak: uzs(150_000_000),
            current_leak: uzs(90_000_000),
            cancelled_subscriptions: uzs(5_000_000),
            envelope_leftovers: uzs(3_000_000),
        };
        assert_eq!(rescued_money(&i), Ok(uzs(68_000_000)));
        i.current_leak = uzs(200_000_000);
        assert_eq!(rescued_money(&i), Ok(uzs(8_000_000)));
        assert_eq!(annual_saving(uzs(9_900_000)), Ok(uzs(118_800_000)));
    }
}
