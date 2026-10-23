//! 7-qonun hisoblari (SPEC 2G.3–2G.5): va'da qilingan foyda yillikka, piramida qavatlari, «oilaviy zaxira» taqsimoti.
//!
//! Hammasi butun sonlarda (`bp` — bazis punkt, `10 000 = 1 barobar`); yaxlitlash — yarmi yuqoriga
//! (`money::round_half_up_div`). Vektorlar: `promised_return.json`, `pyramid_levels.json`, `lump_sum_split.json`.
//! Bu hisoblar **faqat ogohlantirish** uchun: natija hech qayerda «muqobil daromad» sifatida ko'rsatilmaydi (SPEC 3).

use money::{Money, round_half_up_div};

use crate::DomainError;

/// Bazis punktlarda 1 barobar.
const ONE_BP: i128 = 10_000;
/// Oylar chegarasi (ta'limiy hisob, 2 yil).
pub const MAX_MONTHS: u32 = 24;
/// Oylik va'da chegarasi (1 000 % oyiga — undan katta raqam ma'nosiz).
pub const MAX_MONTHLY_BP: u32 = 100_000;

/// Va'da qilingan oylik foydaning yillik (yoki `months` oylik) ko'paytmasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PromisedReturn {
    /// Oddiy: `10000 + months × monthlyBp`.
    pub simple_multiple_bp: u32,
    /// Murakkab: har oy `x = half_up(x × (10000 + monthlyBp) / 10000)`; `u32` dan oshsa — xato (ma'nosiz raqam).
    pub compound_multiple_bp: u32,
}

/// Oyiga `monthly_bp` va'dasi `months` oyda necha barobar bo'ladi.
pub fn promised_return(monthly_bp: u32, months: u32) -> Result<PromisedReturn, DomainError> {
    if months == 0 || months > MAX_MONTHS || monthly_bp > MAX_MONTHLY_BP {
        return Err(DomainError::InvalidRule);
    }
    let rate = i128::from(monthly_bp);
    let simple = ONE_BP + i128::from(months) * rate;
    let mut compound = ONE_BP;
    for _ in 0..months {
        let product = compound
            .checked_mul(ONE_BP + rate)
            .ok_or(DomainError::InvalidRule)?;
        compound = round_half_up_div(product, ONE_BP)?;
    }
    Ok(PromisedReturn {
        simple_multiple_bp: u32::try_from(simple).map_err(|_| DomainError::InvalidRule)?,
        compound_multiple_bp: u32::try_from(compound).map_err(|_| DomainError::InvalidRule)?,
    })
}

/// Piramida modeli: `i`-qavatda `k^i` kishi; aholi tugaganda cho'kadi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PyramidModel {
    /// Qavatlar soni (to'lmagan oxirgi qavat ham sanaladi).
    pub levels: u32,
    /// Jami ishtirokchilar (aholi tugasa — aholi).
    pub participants: u64,
    /// Oxirgi qavatdagi odamlar.
    pub last_level: u64,
    /// Oxirgi qavat ulushi, bp.
    pub last_level_share_bp: u32,
    /// Oxirgi qavat to'liq to'lganmi (aks holda aholi yetmay qoldi).
    pub last_level_full: bool,
}

/// Har ishtirokchi `recruits_per_person` odam olib keladi; `population` — aholi (yoki shahar) soni.
pub fn pyramid_levels(
    recruits_per_person: u64,
    population: u64,
) -> Result<PyramidModel, DomainError> {
    if recruits_per_person < 2 || population == 0 {
        return Err(DomainError::InvalidRule);
    }
    let mut levels: u32 = 0;
    let mut participants: u64 = 0;
    let mut last_level: u64 = 0;
    let mut size: u64 = 1;
    let mut full = true;
    loop {
        let remaining = population - participants;
        if size > remaining {
            if remaining > 0 {
                levels += 1;
                last_level = remaining;
                participants = population;
                full = false;
            }
            break;
        }
        levels += 1;
        participants += size;
        last_level = size;
        let Some(next) = size.checked_mul(recruits_per_person) else {
            break;
        };
        size = next;
    }
    let share = round_half_up_div(
        i128::from(last_level) * ONE_BP,
        i128::from(participants.max(1)),
    )?;
    Ok(PyramidModel {
        levels,
        participants,
        last_level,
        last_level_share_bp: u32::try_from(share).map_err(|_| DomainError::InvalidRule)?,
        last_level_full: full,
    })
}

/// «Oilaviy zaxira» taqsimoti (SPEC 2G.5).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LumpSumSplit {
    /// Avval zaxira kamomadiga.
    pub to_reserve: Money,
    /// Qolgani sarmoya uchun.
    pub to_invest: Money,
}

/// `to_reserve = min(amount, reserve_missing)`, `to_invest = amount − to_reserve`. Valyutalar bir xil bo'lishi shart.
pub fn lump_sum_split(amount: Money, reserve_missing: Money) -> Result<LumpSumSplit, DomainError> {
    if amount.minor() < 0 || reserve_missing.minor() < 0 {
        return Err(DomainError::AmountNotPositive);
    }
    if amount.currency() != reserve_missing.currency() {
        return Err(money::MoneyError::CurrencyMismatch {
            expected: amount.currency(),
            actual: reserve_missing.currency(),
        }
        .into());
    }
    let to_reserve = Money::new(
        amount.minor().min(reserve_missing.minor()),
        amount.currency(),
    );
    let to_invest = amount.checked_sub(to_reserve)?;
    Ok(LumpSumSplit {
        to_reserve,
        to_invest,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    #[test]
    fn oyiga_35_foiz_yiliga_5_2_va_36_6_barobar() {
        let r = promised_return(3_500, 12).expect("hisob");
        assert_eq!(r.simple_multiple_bp, 52_000);
        assert_eq!(r.compound_multiple_bp, 366_439);
        assert!(promised_return(3_500, 0).is_err());
        assert!(promised_return(MAX_MONTHLY_BP + 1, 12).is_err());
    }

    #[test]
    fn piramida_shahar_tugaganda_chokadi() {
        let p = pyramid_levels(5, 1_000_000).expect("model");
        assert_eq!(
            (p.levels, p.last_level, p.last_level_share_bp),
            (10, 511_719, 5_117)
        );
        assert!(!p.last_level_full);
        let p = pyramid_levels(2, 7).expect("model");
        assert_eq!((p.levels, p.participants, p.last_level), (3, 7, 4));
        assert!(p.last_level_full);
        assert!(pyramid_levels(1, 10).is_err());
    }

    #[test]
    fn qala_devori_avval_toladi() {
        let uzs = Currency::Uzs;
        let s = lump_sum_split(Money::new(500, uzs), Money::new(1_800, uzs)).expect("taqsimot");
        assert_eq!((s.to_reserve.minor(), s.to_invest.minor()), (500, 0));
        let s = lump_sum_split(Money::new(2_000, uzs), Money::new(0, uzs)).expect("taqsimot");
        assert_eq!((s.to_reserve.minor(), s.to_invest.minor()), (0, 2_000));
        assert!(lump_sum_split(Money::new(-1, uzs), Money::new(0, uzs)).is_err());
    }
}
