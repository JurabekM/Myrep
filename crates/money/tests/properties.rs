//! Xususiyat testlari (proptest): taqsimot va foiz invariantlari (DESKTOP_PROMPT.md, D2 qabul mezonlari).
//! Testlarda `unwrap`/`expect` ruxsat etiladi (clippy.toml), chunki xato — test muvaffaqiyatsizligi.
#![allow(clippy::expect_used, clippy::unwrap_used)]

use money::{Currency, Money, allocate, percent_of, round_half_up_div};
use proptest::prelude::*;

/// Kamida bitta musbat nisbat bo'lgan, 1 dan 8 tagacha qismli nisbatlar.
fn ratios() -> impl Strategy<Value = Vec<u64>> {
    prop::collection::vec(0_u64..=1_000_000, 1..=8)
        .prop_filter("kamida bitta musbat nisbat", |values| {
            values.iter().any(|&value| value > 0)
        })
}

fn uzs(minor: i64) -> Money {
    Money::new(minor, Currency::Uzs)
}

proptest! {
    /// Qismlar yig'indisi summaga aniq teng: bitta tiyin ham yo'qolmaydi.
    #[test]
    fn allocate_yigindisi_summaga_teng(total in any::<i64>(), ratios in ratios()) {
        let parts = allocate(uzs(total), &ratios).expect("hisoblanishi kerak");
        let sum: i128 = parts.iter().map(|part| i128::from(part.minor())).sum();
        prop_assert_eq!(sum, i128::from(total));
    }

    /// Ishora saqlanadi: musbat summada manfiy qism yo'q, manfiyda musbat qism yo'q.
    #[test]
    fn allocate_ishora_saqlanadi(total in any::<i64>(), ratios in ratios()) {
        let parts = allocate(uzs(total), &ratios).expect("hisoblanishi kerak");
        for part in &parts {
            if total >= 0 {
                prop_assert!(part.minor() >= 0);
            } else {
                prop_assert!(part.minor() <= 0);
            }
        }
    }

    /// Adolat: har bir qism aniq ulushdan bir minor birlikdan ko'pga og'maydi.
    /// Tekshiruv butun sonlarda: |part·R − total·r| < R, bu yerda R — nisbatlar yig'indisi.
    #[test]
    fn allocate_aniq_ulushdan_bittadan_oshmaydi(total in any::<i64>(), ratios in ratios()) {
        let parts = allocate(uzs(total), &ratios).expect("hisoblanishi kerak");
        let ratio_sum: i128 = ratios.iter().map(|&ratio| i128::from(ratio)).sum();
        for (part, &ratio) in parts.iter().zip(&ratios) {
            let deviation = i128::from(part.minor()) * ratio_sum
                - i128::from(total) * i128::from(ratio);
            prop_assert!(deviation.abs() < ratio_sum);
        }
    }

    /// Nisbati nol bo'lgan qism doim nolga teng.
    #[test]
    fn allocate_nol_nisbat_nol_qism(total in any::<i64>(), ratios in ratios()) {
        let parts = allocate(uzs(total), &ratios).expect("hisoblanishi kerak");
        for (part, &ratio) in parts.iter().zip(&ratios) {
            if ratio == 0 {
                prop_assert_eq!(part.minor(), 0);
            }
        }
    }

    /// Spec ta'rifi: 0..=10 000 oralig'ida percent_of = allocate([bp, 10000 − bp])[0].
    #[test]
    fn percent_of_allocate_bilan_teng(amount in any::<i64>(), bp in 0_i64..=10_000) {
        let direct = percent_of(uzs(amount), bp).expect("hisoblanishi kerak");
        let bp_u64 = u64::try_from(bp).expect("manfiy emas");
        let complement = u64::try_from(10_000 - bp).expect("manfiy emas");
        let via_allocate = allocate(uzs(amount), &[bp_u64, complement]).expect("hisoblanishi kerak")[0];
        prop_assert_eq!(direct, via_allocate);
    }

    /// Yaxlitlash simmetrik: round(−x) = −round(x), shu jumladan yarim qiymatlarda.
    #[test]
    fn yaxlitlash_simmetrik(numerator in -1_000_000_000_000_000_000_i128..=1_000_000_000_000_000_000_i128, denominator in 1_i128..=1_000_000_000_i128) {
        let positive = round_half_up_div(numerator, denominator).expect("musbat maxraj");
        let negative = round_half_up_div(-numerator, denominator).expect("musbat maxraj");
        prop_assert_eq!(negative, -positive);
    }
}
