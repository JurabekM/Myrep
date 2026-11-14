//! Ulush qoidasi («Kelajagim»ga ajratish, SPEC 2.2) va daromad uchun ajratish taklifi.
//!
//! Foiz rejimi: `percent_of(daromad, bp)` → yuqoriga 1 000 so'mgacha (kichik summada — butun so'mgacha)
//! yaxlitlanadi, lekin daromaddan oshmaydi. Qat'iy oylik summa: oy maqsadidan qolgan qism.
//! Progressiv rejim: 4 hafta ketma-ket ajratilsa, ulushni +1 % oshirish taklif qilinadi (10 % gacha).
//! Qoidalar `spec/test-vectors/income_share.json` va `streak.json` bilan bir xil.

use money::{Money, MoneyError, ceil_to_step, percent_of};
use time::Date;

use crate::DomainError;

/// Boshlang'ich ulush: 5 % (500 bp).
pub const DEFAULT_BASIS_POINTS: i64 = 500;
/// Maqsad ulush: 10 % (har daromadning 1/10 qismi, SPEC 1-qonun).
pub const TARGET_BASIS_POINTS: i64 = 1000;
/// Bir martalik progressiv qadam: +1 % (100 bp).
pub const PROGRESSION_STEP_BASIS_POINTS: i64 = 100;
/// Progressiv taklif uchun ketma-ket haftalar soni.
pub const PROGRESSION_WEEKS: u32 = 4;
/// Yuqoriga yaxlitlash qadami: 1 000 so'm (valyuta birligida).
const ROUND_STEP_MAJOR: i64 = 1000;

/// Ulush maqsadi: foiz (bp) yoki oylik qat'iy summa.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ShareTarget {
    /// Daromadning foizi, basis points (1 % = 100 bp).
    Percent(i64),
    /// Oyiga qat'iy summa (maqsad).
    Fixed(Money),
}

/// Ulush qoidasi va progressiv rejim holati.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ShareRule {
    /// Maqsad: foiz yoki oylik summa.
    pub target: ShareTarget,
    /// Progressiv rejim (faqat foiz bilan).
    pub progressive: bool,
    /// Oxirgi progressiv taklif (qabul yoki rad) sanasi; shundan keyingi haftalar sanaladi.
    pub progression_offered_on: Option<Date>,
}

impl ShareRule {
    /// Standart qoida: 5 %, progressiv emas.
    pub const fn default_rule() -> Self {
        Self {
            target: ShareTarget::Percent(DEFAULT_BASIS_POINTS),
            progressive: false,
            progression_offered_on: None,
        }
    }

    /// Qoida to'g'riligini tekshiradi: foiz 0 dan katta va 100 % dan oshmaydi; oylik summa musbat;
    /// progressiv rejim faqat foiz bilan.
    pub fn validate(&self) -> Result<(), DomainError> {
        match self.target {
            ShareTarget::Percent(bp) if (1..=10_000).contains(&bp) => Ok(()),
            ShareTarget::Fixed(amount) if amount.minor() > 0 && !self.progressive => Ok(()),
            _ => Err(DomainError::InvalidRule),
        }
    }
}

/// Daromaddan ajratish taklifi. `None` — taklif yo'q (maqsad bajarilgan, summa nol, valyuta boshqa).
///
/// `saved_this_month` — shu oy «Kelajagim»ga ajratilgan summa (faqat qat'iy rejim uchun ishlatiladi).
pub fn suggest_share(
    income: Money,
    rule: &ShareRule,
    saved_this_month: Money,
) -> Result<Option<Money>, MoneyError> {
    if income.minor() <= 0 {
        return Ok(None);
    }
    match rule.target {
        ShareTarget::Fixed(monthly_target) => {
            if monthly_target.currency() != income.currency() {
                return Ok(None);
            }
            let left = monthly_target.checked_sub(saved_this_month)?;
            if left.minor() <= 0 {
                return Ok(None);
            }
            Ok(Some(min_money(left, income)))
        }
        ShareTarget::Percent(bp) => {
            let raw = percent_of(income, bp)?;
            if raw.minor() <= 0 {
                return Ok(None);
            }
            let rounded = ceil_to_step(raw, rounding_step(raw))?;
            Ok(Some(min_money(rounded, income)))
        }
    }
}

/// Progressiv taklif: ulush hozircha maqsaddan past, rejim progressiv va [`PROGRESSION_WEEKS`]
/// ketma-ket hafta bo'lsa — yangi ulush (bp), aks holda `None`.
pub fn progression_offer(rule: &ShareRule, weeks_since_offer: u32) -> Option<i64> {
    match rule.target {
        ShareTarget::Percent(bp)
            if rule.progressive
                && bp < TARGET_BASIS_POINTS
                && weeks_since_offer >= PROGRESSION_WEEKS =>
        {
            Some((bp + PROGRESSION_STEP_BASIS_POINTS).min(TARGET_BASIS_POINTS))
        }
        _ => None,
    }
}

/// Yuqoriga yaxlitlash qadami (minor birlikda): `raw` 1 000 so'mdan katta yoki teng bo'lsa — 1 000 so'm,
/// aks holda — butun so'm (mobil `suggestShare` bilan bir xil).
fn rounding_step(raw: Money) -> i64 {
    let per_major = raw.currency().minor_per_major();
    let thousand = ROUND_STEP_MAJOR * per_major;
    if raw.minor() >= thousand {
        thousand
    } else {
        per_major
    }
}

fn min_money(a: Money, b: Money) -> Money {
    if a.minor() <= b.minor() { a } else { b }
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency::Uzs;

    fn som(major: i64) -> Money {
        Money::new(major * 100, Uzs)
    }

    fn minor(value: i64) -> Money {
        Money::new(value, Uzs)
    }

    #[test]
    fn besh_foiz_yuqoriga_ming_somgacha() {
        let rule = ShareRule::default_rule();
        assert_eq!(
            suggest_share(som(150_000), &rule, Money::zero(Uzs)),
            Ok(Some(som(8000)))
        );
    }

    #[test]
    fn kichik_summa_butun_somgacha() {
        let rule = ShareRule::default_rule();
        assert_eq!(
            suggest_share(som(500), &rule, Money::zero(Uzs)),
            Ok(Some(som(25)))
        );
        assert_eq!(
            suggest_share(minor(100), &rule, Money::zero(Uzs)),
            Ok(Some(minor(100)))
        );
    }

    #[test]
    fn nol_va_manfiy_daromad_taklif_qilmaydi() {
        let rule = ShareRule::default_rule();
        assert_eq!(suggest_share(minor(0), &rule, Money::zero(Uzs)), Ok(None));
        assert_eq!(suggest_share(minor(-5), &rule, Money::zero(Uzs)), Ok(None));
        assert_eq!(suggest_share(minor(1), &rule, Money::zero(Uzs)), Ok(None));
    }

    #[test]
    fn qatiy_oylik_maqsaddan_qolgani() {
        let rule = ShareRule {
            target: ShareTarget::Fixed(som(300_000)),
            progressive: false,
            progression_offered_on: None,
        };
        assert_eq!(
            suggest_share(som(500_000), &rule, som(200_000)),
            Ok(Some(som(100_000)))
        );
        assert_eq!(suggest_share(som(500_000), &rule, som(300_000)), Ok(None));
    }

    #[test]
    fn progressiv_taklif_to_rt_hafta_va_chegara() {
        let progressive = ShareRule {
            target: ShareTarget::Percent(500),
            progressive: true,
            progression_offered_on: None,
        };
        assert_eq!(progression_offer(&progressive, 3), None);
        assert_eq!(progression_offer(&progressive, 4), Some(600));

        let near_target = ShareRule {
            target: ShareTarget::Percent(950),
            progressive: true,
            progression_offered_on: None,
        };
        assert_eq!(progression_offer(&near_target, 4), Some(1000));

        let at_target = ShareRule {
            target: ShareTarget::Percent(TARGET_BASIS_POINTS),
            progressive: true,
            progression_offered_on: None,
        };
        assert_eq!(progression_offer(&at_target, 9), None);
    }

    #[test]
    fn notogri_qoida_rad_etiladi() {
        let zero_percent = ShareRule {
            target: ShareTarget::Percent(0),
            progressive: false,
            progression_offered_on: None,
        };
        assert_eq!(zero_percent.validate(), Err(DomainError::InvalidRule));
        let progressive_fixed = ShareRule {
            target: ShareTarget::Fixed(som(1)),
            progressive: true,
            progression_offered_on: None,
        };
        assert_eq!(progressive_fixed.validate(), Err(DomainError::InvalidRule));
        assert_eq!(ShareRule::default_rule().validate(), Ok(()));
    }
}
