use crate::{Money, MoneyError, round_half_up_div};

/// 100 % = 10 000 basis point. Foizlar butun sonli basis point (bp) ko'rinishida saqlanadi (qoida 5).
pub const BASIS_POINTS_WHOLE: i64 = 10_000;

/// Summani nisbatlar bo'yicha bo'ladi — **largest remainder** usuli (DESKTOP_PROMPT.md 4-bo'lim, 3-qoida).
///
/// * Har bir qismning aniq ulushi `total × r_i / Σr` — butun sonlarda hisoblanadi;
/// * avval pastga yaxlitlanadi, qolgan minor birliklar kasr qismi eng katta qismlarga bittadan beriladi;
/// * kasrlar teng bo'lsa — ro'yxatda oldinroq turgan qismga;
/// * qismlar yig'indisi har doim `total` ga aniq teng;
/// * manfiy summa uchun ishora qismlarda saqlanadi (modul bo'yicha taqsimlanadi, simmetrik).
///
/// Bo'sh nisbatlar yoki yig'indisi nol bo'lsa [`MoneyError::InvalidRatios`] qaytadi.
pub fn allocate(total: Money, ratios: &[u64]) -> Result<Vec<Money>, MoneyError> {
    if ratios.is_empty() {
        return Err(MoneyError::InvalidRatios);
    }
    let ratio_sum = ratios
        .iter()
        .try_fold(0_u128, |acc, &ratio| acc.checked_add(u128::from(ratio)))
        .ok_or(MoneyError::Overflow)?;
    if ratio_sum == 0 {
        return Err(MoneyError::InvalidRatios);
    }

    let negative = total.minor() < 0;
    // |minor| ≤ 2^63, ratio ≤ 2^64 — ko'paytma u128 ga aniq sig'adi.
    let amount = u128::from(total.minor().unsigned_abs());

    let mut shares = Vec::with_capacity(ratios.len());
    let mut remainders = Vec::with_capacity(ratios.len());
    let mut allocated = 0_u128;
    for &ratio in ratios {
        let exact = amount * u128::from(ratio);
        let share = exact / ratio_sum;
        remainders.push(exact % ratio_sum);
        shares.push(share);
        allocated += share;
    }

    // Qolgan minor birliklar: kasr qismi katta bo'lgan qismlarga; teng bo'lsa — kichik indeks.
    // Qoldiq har doim ratios.len() dan kichik, shuning uchun u tugaydi.
    let mut leftover = amount - allocated;
    let mut order: Vec<usize> = (0..ratios.len()).collect();
    order.sort_by(|&a, &b| remainders[b].cmp(&remainders[a]).then(a.cmp(&b)));
    for index in order {
        if leftover == 0 {
            break;
        }
        if ratios[index] == 0 {
            continue;
        }
        shares[index] += 1;
        leftover -= 1;
    }

    Ok(shares
        .into_iter()
        .map(|share| {
            // share ≤ 2^63: summa modulidan oshmaydi. Shu sababli kesish xavfsiz.
            let magnitude = share as i128;
            let signed = if negative { -magnitude } else { magnitude };
            Money::new(signed as i64, total.currency())
        })
        .collect())
}

/// `amount` ning `basis_points` qismi (1 % = 100 bp). Masalan, 10 % — `percent_of(income, 1000)`.
///
/// 0..=10 000 oralig'ida spec ta'rifi bo'yicha: `allocate(amount, [bp, 10000 − bp])[0]`.
/// Oraliqdan tashqarida (masalan, 120 % ustama) — `round_half_up(amount × bp / 10000)`.
/// Oraliqda ikkala ta'rif bir xil natija beradi (xususiyat testi bilan tekshiriladi).
pub fn percent_of(amount: Money, basis_points: i64) -> Result<Money, MoneyError> {
    if (0..=BASIS_POINTS_WHOLE).contains(&basis_points) {
        // Oraliq tekshirilgan: ikkala qiymat ham manfiy emas.
        let bp = basis_points as u64;
        let complement = (BASIS_POINTS_WHOLE - basis_points) as u64;
        let parts = allocate(amount, &[bp, complement])?;
        return Ok(parts[0]);
    }

    let numerator = i128::from(amount.minor()) * i128::from(basis_points);
    let rounded = round_half_up_div(numerator, i128::from(BASIS_POINTS_WHOLE))?;
    let minor = i64::try_from(rounded).map_err(|_| MoneyError::Overflow)?;
    Ok(Money::new(minor, amount.currency()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Currency;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    fn minors(parts: &[Money]) -> Vec<i64> {
        parts.iter().map(|part| part.minor()).collect()
    }

    #[test]
    fn largest_remainder_misollari() {
        assert_eq!(
            minors(&allocate(uzs(100), &[1, 1, 1]).expect("hisoblanadi")),
            vec![34, 33, 33]
        );
        assert_eq!(
            minors(&allocate(uzs(100), &[1, 1, 1, 1, 1, 1, 1]).expect("hisoblanadi")),
            vec![15, 15, 14, 14, 14, 14, 14]
        );
        assert_eq!(
            minors(&allocate(uzs(0), &[1, 2]).expect("hisoblanadi")),
            vec![0, 0]
        );
    }

    #[test]
    fn manfiy_summa_ishorasi_saqlanadi() {
        // Musharaka zarari kapital bo'yicha (DESKTOP 5.3, dist-003): −225 000 000 va −75 000 000.
        assert_eq!(
            minors(&allocate(uzs(-300_000_000), &[600_000_000, 200_000_000]).expect("hisoblanadi")),
            vec![-225_000_000, -75_000_000]
        );
        // Simmetriya: manfiy summa — musbat summaning aksi.
        let positive = allocate(uzs(100), &[1, 1, 1]).expect("hisoblanadi");
        let negative = allocate(uzs(-100), &[1, 1, 1]).expect("hisoblanadi");
        for (plus, minus) in positive.iter().zip(&negative) {
            assert_eq!(minus.minor(), -plus.minor());
        }
    }

    #[test]
    fn eng_kichik_summa_taqsimlanadi() {
        assert_eq!(
            minors(&allocate(uzs(i64::MIN), &[1]).expect("hisoblanadi")),
            vec![i64::MIN]
        );
        assert_eq!(
            minors(&allocate(uzs(i64::MAX), &[1, 1]).expect("hisoblanadi")),
            vec![4_611_686_018_427_387_904, 4_611_686_018_427_387_903]
        );
    }

    #[test]
    fn nisbati_nol_bolgan_qism_nol_oladi() {
        assert_eq!(
            minors(&allocate(uzs(1000), &[0, 5, 0, 5]).expect("hisoblanadi")),
            vec![0, 500, 0, 500]
        );
    }

    #[test]
    fn nisbat_xatolari() {
        assert_eq!(allocate(uzs(100), &[]), Err(MoneyError::InvalidRatios));
        assert_eq!(allocate(uzs(100), &[0, 0]), Err(MoneyError::InvalidRatios));
    }

    #[test]
    fn percent_of_spec_talabi() {
        assert_eq!(
            percent_of(uzs(800_000_000), 1000)
                .expect("hisoblanadi")
                .minor(),
            80_000_000
        );
        assert_eq!(
            percent_of(uzs(12345), 1000).expect("hisoblanadi").minor(),
            1235
        );
        assert_eq!(percent_of(uzs(12345), 0).expect("hisoblanadi").minor(), 0);
        assert_eq!(
            percent_of(uzs(12345), BASIS_POINTS_WHOLE)
                .expect("hisoblanadi")
                .minor(),
            12345
        );
    }

    #[test]
    fn percent_of_oraliqdan_tashqarida() {
        // 120 % ustama: 100 → 120.
        assert_eq!(
            percent_of(uzs(100), 12_000).expect("hisoblanadi").minor(),
            120
        );
        // Manfiy foiz: −10 %.
        assert_eq!(
            percent_of(uzs(100), -1000).expect("hisoblanadi").minor(),
            -10
        );
        // 1 tiyin × 50 % = 0,5 tiyin → yarmi noldan uzoqqa: 1.
        assert_eq!(percent_of(uzs(1), 5000).expect("hisoblanadi").minor(), 1);
    }

    #[test]
    fn percent_of_chegaradan_oshsa_xato() {
        assert_eq!(
            percent_of(uzs(i64::MAX), i64::MAX),
            Err(MoneyError::Overflow)
        );
    }
}
