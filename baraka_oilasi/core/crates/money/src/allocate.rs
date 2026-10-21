use alloc::vec::Vec;

use crate::{Money, MoneyError};

/// 100% basis points'da.
pub const BP_ONE: i64 = 10_000;

/// Largest remainder taqsimoti minor birliklarda (5.4).
///
/// * `ratios` — har biri `>= 0`, yig'indisi `> 0`;
/// * manfiy `total` — `allocate(-total)` ning manfiy ishorali nusxasi (simmetriya);
/// * qolgan birliklar kasr qismi kattaroq qismlarga, teng bo'lsa kichik indeksga beriladi.
pub fn allocate_minor(total: i64, ratios: &[i64]) -> Result<Vec<i64>, MoneyError> {
    if ratios.is_empty() || ratios.iter().any(|&r| r < 0) {
        return Err(MoneyError::InvalidRatios);
    }
    let sum: i128 = ratios.iter().map(|&r| i128::from(r)).sum();
    if sum <= 0 {
        return Err(MoneyError::InvalidRatios);
    }
    if total < 0 {
        let positive = total.checked_neg().ok_or(MoneyError::Overflow)?;
        return Ok(allocate_minor(positive, ratios)?
            .into_iter()
            .map(|p| -p)
            .collect());
    }

    let t = i128::from(total);
    let mut parts: Vec<i128> = Vec::with_capacity(ratios.len());
    let mut remainders: Vec<(i128, usize)> = Vec::with_capacity(ratios.len());
    for (i, &r) in ratios.iter().enumerate() {
        // t <= i64::MAX va r <= i64::MAX bo'lgani uchun ko'paytma i128 ga sig'adi.
        let product = t * i128::from(r);
        parts.push(product / sum);
        remainders.push((product % sum, i));
    }
    let distributed: i128 = parts.iter().sum();
    let leftover = usize::try_from(t - distributed).map_err(|_| MoneyError::Overflow)?;
    // Kasr qismi kattaroq birinchi; teng bo'lsa kichik indeks birinchi.
    remainders.sort_by(|a, b| b.0.cmp(&a.0).then(a.1.cmp(&b.1)));
    for &(_, i) in remainders.iter().take(leftover) {
        parts[i] += 1;
    }
    parts
        .into_iter()
        .map(|p| i64::try_from(p).map_err(|_| MoneyError::Overflow))
        .collect()
}

/// `Money` uchun taqsimot: har bir qism `total` valyutasida.
pub fn allocate(total: Money, ratios: &[i64]) -> Result<Vec<Money>, MoneyError> {
    Ok(allocate_minor(total.minor(), ratios)?
        .into_iter()
        .map(|m| Money::new(m, total.currency()))
        .collect())
}

/// `percent_of(m, bp) = allocate(m, [bp, 10000 - bp])[0]` (5.5).
pub fn percent_of(amount: Money, bp: i64) -> Result<Money, MoneyError> {
    if !(0..=BP_ONE).contains(&bp) {
        return Err(MoneyError::InvalidBasisPoints);
    }
    let parts = allocate(amount, &[bp, BP_ONE - bp])?;
    parts.first().copied().ok_or(MoneyError::InvalidRatios)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Currency;
    use alloc::vec;
    use proptest::prelude::*;

    #[test]
    fn documented_cases() {
        assert_eq!(allocate_minor(100, &[1, 1, 1]), Ok(vec![34, 33, 33]));
        assert_eq!(
            allocate_minor(800_000_000, &[70, 20, 10]),
            Ok(vec![560_000_000, 160_000_000, 80_000_000])
        );
        assert_eq!(allocate_minor(12_345, &[1000, 9000]), Ok(vec![1235, 11110]));
        assert_eq!(
            allocate_minor(100, &[1; 7]),
            Ok(vec![15, 15, 14, 14, 14, 14, 14])
        );
        assert_eq!(allocate_minor(0, &[1, 2]), Ok(vec![0, 0]));
    }

    #[test]
    fn negative_total_is_symmetric() {
        assert_eq!(allocate_minor(-100, &[1, 1, 1]), Ok(vec![-34, -33, -33]));
        assert_eq!(
            allocate_minor(-300_000_000, &[600_000_000, 200_000_000]),
            Ok(vec![-225_000_000, -75_000_000])
        );
        assert_eq!(allocate_minor(i64::MIN, &[1]), Err(MoneyError::Overflow));
    }

    #[test]
    fn invalid_ratios() {
        assert_eq!(allocate_minor(100, &[]), Err(MoneyError::InvalidRatios));
        assert_eq!(allocate_minor(100, &[0, 0]), Err(MoneyError::InvalidRatios));
        assert_eq!(
            allocate_minor(100, &[2, -1]),
            Err(MoneyError::InvalidRatios)
        );
    }

    #[test]
    fn percent_of_cases() {
        let m = |v| Money::new(v, Currency::Uzs);
        assert_eq!(percent_of(m(800_000_000), 1000), Ok(m(80_000_000)));
        assert_eq!(percent_of(m(12_345), 1000), Ok(m(1235)));
        assert_eq!(
            percent_of(m(100), 10_001),
            Err(MoneyError::InvalidBasisPoints)
        );
        assert_eq!(percent_of(m(100), -1), Err(MoneyError::InvalidBasisPoints));
    }

    proptest! {
        #[test]
        fn sum_is_exact_and_parts_are_bounded(
            total in any::<i64>().prop_filter("MIN", |t| *t != i64::MIN),
            ratios in prop::collection::vec(0i64..=i64::MAX, 1..12),
        ) {
            prop_assume!(ratios.iter().any(|&r| r > 0));
            let parts = allocate_minor(total, &ratios).unwrap();
            let sum: i128 = parts.iter().map(|&p| i128::from(p)).sum();
            prop_assert_eq!(sum, i128::from(total));
            for (p, r) in parts.iter().zip(&ratios) {
                if total >= 0 { prop_assert!(*p >= 0); } else { prop_assert!(*p <= 0); }
                if *r == 0 { prop_assert_eq!(*p, 0); }
            }
        }

        #[test]
        fn symmetric_under_negation(
            total in 0i64..=i64::MAX,
            ratios in prop::collection::vec(0i64..1_000_000, 1..8),
        ) {
            prop_assume!(ratios.iter().any(|&r| r > 0));
            let pos = allocate_minor(total, &ratios).unwrap();
            let neg = allocate_minor(-total, &ratios).unwrap();
            prop_assert_eq!(pos.iter().map(|p| -p).collect::<Vec<_>>(), neg);
        }
    }
}
