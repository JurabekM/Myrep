//! 3-qonun: «Narx daftari» va shaxsiy inflyatsiya indeksi (uy/SPEC 2C.1).
use baraka_money::{round_half_up, Money};

use crate::DomainError;

/// Savatdagi bitta mahsulot: og'irligi (bp) va ikki sanadagi narxi.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BasketPoint {
    pub weight_bp: i64,
    pub old_price: Money,
    pub new_price: Money,
}

/// Narx o'zgarishi, bp: `round_half_up((new − old) × 10000 / old)`.
pub fn price_change_bp(old: Money, new: Money) -> Result<i64, DomainError> {
    new.compare(&old)?;
    if !old.is_positive() {
        return Err(DomainError::on("PRICE_NOT_POSITIVE", "old_price"));
    }
    let delta = i128::from(new.minor()) - i128::from(old.minor());
    let v = round_half_up(delta * 10_000, i128::from(old.minor()))?;
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

/// Mahsulotlar o'zgarishi va og'irlikli indeks (bp):
/// `round_half_up(Σ weight_i × change_i / Σ weight_i)`.
pub fn personal_index(items: &[BasketPoint]) -> Result<(Vec<i64>, i64), DomainError> {
    if items.is_empty() {
        return Err(DomainError::on("EMPTY_BASKET", "items"));
    }
    let mut changes = Vec::with_capacity(items.len());
    let mut weighted: i128 = 0;
    let mut weights: i128 = 0;
    for it in items {
        if it.weight_bp < 0 {
            return Err(DomainError::on("INVALID_WEIGHT", "weight_bp"));
        }
        let c = price_change_bp(it.old_price, it.new_price)?;
        changes.push(c);
        weighted += i128::from(it.weight_bp) * i128::from(c);
        weights += i128::from(it.weight_bp);
    }
    if weights == 0 {
        return Err(DomainError::on("INVALID_WEIGHT", "weight_bp"));
    }
    let index = i64::try_from(round_half_up(weighted, weights)?)
        .map_err(|_| DomainError::new("OVERFLOW"))?;
    Ok((changes, index))
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn documented() {
        let basket = [
            BasketPoint {
                weight_bp: 5000,
                old_price: uzs(8_000_000),
                new_price: uzs(13_000_000),
            },
            BasketPoint {
                weight_bp: 5000,
                old_price: uzs(200_000),
                new_price: uzs(300_000),
            },
        ];
        assert_eq!(personal_index(&basket), Ok((vec![6250, 5000], 5625)));
    }

    #[test]
    fn deflation_and_errors() {
        assert_eq!(price_change_bp(uzs(300_000), uzs(200_000)), Ok(-3333));
        assert!(price_change_bp(uzs(0), uzs(1)).is_err());
        assert!(personal_index(&[]).is_err());
    }
}
