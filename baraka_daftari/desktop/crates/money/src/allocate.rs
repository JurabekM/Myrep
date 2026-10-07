use crate::{Money, MoneyError};

/// Largest remainder taqsimoti (DESKTOP_PROMPT 4.3).
///
/// - aniq ulush `total × r_i / Σr` (butun sonlarda), avval `floor`;
/// - qolgan birliklar kasr qismi kattaroq qismlarga bittadan beriladi;
/// - kasrlar teng bo'lsa, kichik indeksli qism ustun;
/// - yig'indi har doim `total` ga teng. Manfiy `total` uchun modul bo'yicha
///   taqsimlanib, ishora qaytariladi.
///
/// # Errors
/// `ratios` bo'sh yoki yig'indisi nol bo'lsa, yoki overflow bo'lsa.
pub fn allocate(total: Money, ratios: &[u64]) -> Result<Vec<Money>, MoneyError> {
    let sum: u128 = ratios.iter().map(|r| u128::from(*r)).sum();
    if ratios.is_empty() || sum == 0 {
        return Err(MoneyError::InvalidRatios);
    }
    let sum = i128::try_from(sum).map_err(|_| MoneyError::Overflow)?;
    let abs_total = i128::from(total.minor()).abs();
    let negative = total.minor() < 0;

    let mut floors = Vec::with_capacity(ratios.len());
    let mut remainders = Vec::with_capacity(ratios.len());
    let mut assigned: i128 = 0;
    for r in ratios {
        let product = abs_total
            .checked_mul(i128::from(*r))
            .ok_or(MoneyError::Overflow)?;
        let floor = product / sum;
        floors.push(floor);
        remainders.push(product % sum);
        assigned += floor;
    }

    let leftover = usize::try_from(abs_total - assigned).map_err(|_| MoneyError::Overflow)?;
    // Kasr bo'yicha kamayish, teng bo'lsa indeks bo'yicha o'sish.
    let mut order: Vec<usize> = (0..ratios.len()).collect();
    order.sort_by(|a, b| remainders[*b].cmp(&remainders[*a]).then(a.cmp(b)));
    for idx in order.into_iter().take(leftover) {
        floors[idx] += 1;
    }

    floors
        .into_iter()
        .map(|v| {
            let signed = if negative { -v } else { v };
            i64::try_from(signed)
                .map(|m| Money::new(m, total.currency()))
                .map_err(|_| MoneyError::Overflow)
        })
        .collect()
}

/// `percent_of(m, bp) = allocate(m, [bp, 10000 − bp])[0]` (bazis punkt, `0..=10000`).
///
/// # Errors
/// `bp > 10000` bo'lsa yoki overflow bo'lsa.
pub fn percent_of(amount: Money, bp: u32) -> Result<Money, MoneyError> {
    if bp > 10_000 {
        return Err(MoneyError::InvalidBasisPoints);
    }
    let parts = allocate(amount, &[u64::from(bp), u64::from(10_000 - bp)])?;
    parts.first().copied().ok_or(MoneyError::InvalidRatios)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Currency;
    use proptest::prelude::*;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    fn minors(parts: &[Money]) -> Vec<i64> {
        parts.iter().map(|m| m.minor()).collect()
    }

    #[test]
    fn spec_examples() {
        assert_eq!(
            minors(&allocate(uzs(100), &[1, 1, 1]).unwrap()),
            [34, 33, 33]
        );
        assert_eq!(
            minors(&allocate(uzs(100), &[1; 7]).unwrap()),
            [15, 15, 14, 14, 14, 14, 14]
        );
        assert_eq!(
            minors(&allocate(uzs(12345), &[1000, 9000]).unwrap()),
            [1235, 11110]
        );
        assert_eq!(minors(&allocate(uzs(0), &[1, 2]).unwrap()), [0, 0]);
    }

    #[test]
    fn negative_total_mirrors_positive() {
        assert_eq!(
            minors(&allocate(uzs(-100), &[1, 1, 1]).unwrap()),
            [-34, -33, -33]
        );
    }

    #[test]
    fn invalid_ratios() {
        assert_eq!(allocate(uzs(10), &[]), Err(MoneyError::InvalidRatios));
        assert_eq!(allocate(uzs(10), &[0, 0]), Err(MoneyError::InvalidRatios));
    }

    #[test]
    fn extreme_totals_do_not_overflow() {
        let parts = allocate(uzs(i64::MAX), &[1, 1, 1]).unwrap();
        assert_eq!(
            parts.iter().map(|m| i128::from(m.minor())).sum::<i128>(),
            i128::from(i64::MAX)
        );
        let parts = allocate(uzs(i64::MIN), &[3, 7]).unwrap();
        assert_eq!(
            parts.iter().map(|m| i128::from(m.minor())).sum::<i128>(),
            i128::from(i64::MIN)
        );
    }

    #[test]
    fn percent_of_rejects_bp_over_100_percent() {
        assert_eq!(
            percent_of(uzs(100), 10_001),
            Err(MoneyError::InvalidBasisPoints)
        );
    }

    #[test]
    fn percent_of_spec_examples() {
        assert_eq!(
            percent_of(uzs(800_000_000), 1000).unwrap().minor(),
            80_000_000
        );
        assert_eq!(percent_of(uzs(12345), 1000).unwrap().minor(), 1235);
        assert_eq!(percent_of(uzs(12345), 10_000).unwrap().minor(), 12345);
        assert_eq!(percent_of(uzs(12345), 0).unwrap().minor(), 0);
    }

    proptest! {
        #[test]
        fn sum_is_always_total(total in any::<i64>(), ratios in prop::collection::vec(0u64..1_000_000, 1..12)) {
            prop_assume!(ratios.iter().any(|r| *r > 0));
            let parts = allocate(uzs(total), &ratios).unwrap();
            prop_assert_eq!(parts.len(), ratios.len());
            let sum: i128 = parts.iter().map(|m| i128::from(m.minor())).sum();
            prop_assert_eq!(sum, i128::from(total));
        }

        #[test]
        fn no_negative_part_for_non_negative_total(total in 0i64.., ratios in prop::collection::vec(0u64..1_000_000, 1..12)) {
            prop_assume!(ratios.iter().any(|r| *r > 0));
            let parts = allocate(uzs(total), &ratios).unwrap();
            prop_assert!(parts.iter().all(|m| m.minor() >= 0));
        }

        #[test]
        fn zero_ratio_gets_zero(total in 0i64.., ratios in prop::collection::vec(0u64..1000, 2..8)) {
            prop_assume!(ratios.iter().any(|r| *r > 0));
            let parts = allocate(uzs(total), &ratios).unwrap();
            for (p, r) in parts.iter().zip(&ratios) {
                if *r == 0 { prop_assert_eq!(p.minor(), 0); }
            }
        }

        #[test]
        fn part_within_one_of_exact_share(total in 0i64..1_000_000_000_000, ratios in prop::collection::vec(1u64..10_000, 1..10)) {
            let sum: i128 = ratios.iter().map(|r| i128::from(*r)).sum();
            let parts = allocate(uzs(total), &ratios).unwrap();
            for (p, r) in parts.iter().zip(&ratios) {
                let exact_floor = i128::from(total) * i128::from(*r) / sum;
                let diff = i128::from(p.minor()) - exact_floor;
                prop_assert!(diff == 0 || diff == 1);
            }
        }

        #[test]
        fn percent_of_plus_rest_is_total(total in any::<i64>(), bp in 0u32..=10_000) {
            let part = percent_of(uzs(total), bp).unwrap();
            let rest = percent_of(uzs(total), 10_000 - bp).unwrap();
            // Ikkala ulush yig'indisi umumiy summadan 1 tiyindan ko'p farq qilmaydi.
            let diff = (i128::from(part.minor()) + i128::from(rest.minor()) - i128::from(total)).abs();
            prop_assert!(diff <= 1);
        }
    }
}
