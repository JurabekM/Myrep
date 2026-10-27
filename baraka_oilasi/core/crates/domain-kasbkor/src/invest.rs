//! K9 — 8-tamoyil «O'zingizga sarmoya qiling» (`docs/kasbkor/SPEC.md` 8A): egasining topgani
//! (soat qiymati uchun) va «O'zim qilaymi yoki o'rgatib topshiraymi?».
//!
//! Soat qiymatining o'zi — umumiy formula (`domain-uy::learning::hour_value`, Uy 2G.1 bilan bir xil
//! yaxlitlash); bu yerda faqat Kasb-kor oyining «egasi topgani».
//!
//! Vektorlar: `spec/test-vectors/kk_owner_hour.json`, `kk_delegate.json`.
use baraka_money::{round_half_up, Money};

use crate::DomainError;

/// Taklif — oxirgi ko'pi bilan 3 ta yopilgan oy («Hisob kuni») o'rtachasi.
pub const OWNER_AVG_MONTHS: usize = 3;
/// Bir oydagi daqiqalar chegarasi (31 kun × 24 soat).
pub const DELEGATE_MAX_MINUTES: u32 = 44_640;

fn to_i64(v: i128) -> Result<i64, DomainError> {
    i64::try_from(v).map_err(|_| DomainError::new("OVERFLOW"))
}

/// Egasi topgani = max(0, o'z mehnati bahosi + haqiqiy foyda) — ya'ni ko'rinadigan foyda − oilaviy
/// mehnat − eskirish (− uskuna chiqib ketishi). Haqiqiy foydadan egasiga **haqiqatda to'langan**
/// maosh emas, o'z mehnati bahosi ayirilgan — shuning uchun maosh qo'shilmaydi.
pub fn owner_earnings(owner_labor: Money, true_profit: Money) -> Result<Money, DomainError> {
    if owner_labor.is_negative() {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "ownerLabor"));
    }
    Ok(owner_labor.checked_add(true_profit)?.clamp_non_negative())
}

/// Yopilgan oylar (ko'pi bilan 3 ta): (o'z mehnati bahosi, haqiqiy foyda) → har oy topgani.
pub fn owner_month_earnings(months: &[(Money, Money)]) -> Result<Vec<Money>, DomainError> {
    if months.len() > OWNER_AVG_MONTHS {
        return Err(DomainError::new("TOO_MANY_MONTHS"));
    }
    months
        .iter()
        .map(|(labor, profit)| owner_earnings(*labor, *profit))
        .collect()
}

// --- 8A.2 «O'zim qilaymi yoki o'rgatib topshiraymi?» ------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DelegateInput {
    /// Egasining 1 soati (minor).
    pub owner_hour_value: i64,
    /// Ishga oyiga ketadigan egasining daqiqalari.
    pub task_minutes: u32,
    /// Yordamchi yoki xodimning 1 soati narxi (minor).
    pub helper_hour_cost: i64,
    /// Bir martalik o'rgatish xarajati (minor).
    pub training_money: i64,
    /// O'rgatishga ketadigan egasining daqiqalari.
    pub training_minutes: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DelegateVerdict {
    /// Topshirish oylik naf beradi.
    Delegate,
    /// «Hozircha o'zingiz qilganingiz arzon» — naf 0 yoki manfiy.
    SelfCheaper,
}

impl DelegateVerdict {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Delegate => "DELEGATE",
            Self::SelfCheaper => "SELF_CHEAPER",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DelegateResult {
    /// Manfiy bo'lishi mumkin (yordamchi qimmatroq).
    pub monthly_benefit: i64,
    pub training_time_cost: i64,
    pub full_cost: i64,
    /// `SelfCheaper` da — `None`; to'liq narx 0 bo'lsa — 0 (darhol).
    pub payback_months: Option<i64>,
    pub verdict: DelegateVerdict,
}

/// Oylik naf = `round_half_up(daqiqa × (egasi − yordamchi) / 60)`; to'liq narx = pul +
/// `round_half_up(o'rgatish daqiqalari × egasi / 60)`; qoplanish = ⌈to'liq narx / naf⌉ oy.
pub fn delegate(i: &DelegateInput) -> Result<DelegateResult, DomainError> {
    let fields = [
        (i.owner_hour_value, "ownerHourValue"),
        (i.helper_hour_cost, "helperHourCost"),
        (i.training_money, "trainingMoney"),
    ];
    for (v, field) in fields {
        if v < 0 {
            return Err(DomainError::on("AMOUNT_NEGATIVE", field));
        }
    }
    if i.owner_hour_value == 0 {
        return Err(DomainError::on("NO_HOUR_VALUE", "ownerHourValue"));
    }
    if !(1..=DELEGATE_MAX_MINUTES).contains(&i.task_minutes) {
        return Err(DomainError::on("INVALID_TIME", "taskMinutes"));
    }
    if i.training_minutes > DELEGATE_MAX_MINUTES {
        return Err(DomainError::on("INVALID_TIME", "trainingMinutes"));
    }
    let owner = i128::from(i.owner_hour_value);
    let benefit = to_i64(round_half_up(
        i128::from(i.task_minutes) * (owner - i128::from(i.helper_hour_cost)),
        60,
    )?)?;
    let time_cost = to_i64(round_half_up(i128::from(i.training_minutes) * owner, 60)?)?;
    let full = i
        .training_money
        .checked_add(time_cost)
        .ok_or(DomainError::new("OVERFLOW"))?;
    let (payback, verdict) = if benefit > 0 {
        // Ikkalasi ham ≥ 0: ⌈a / b⌉ = (a + b − 1) / b.
        let months = (i128::from(full) + i128::from(benefit) - 1) / i128::from(benefit);
        (Some(to_i64(months)?), DelegateVerdict::Delegate)
    } else {
        (None, DelegateVerdict::SelfCheaper)
    };
    Ok(DelegateResult {
        monthly_benefit: benefit,
        training_time_cost: time_cost,
        full_cost: full,
        payback_months: payback,
        verdict,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn som(v: i64) -> Money {
        Money::new(v * 100, Currency::Uzs)
    }

    #[test]
    fn spec_example_salary_is_not_added() {
        // 8A.1: Feruza — o'z mehnati 5 mln + haqiqiy foyda 3,1 mln = 8,1 mln.
        assert_eq!(
            owner_earnings(som(5_000_000), som(3_100_000)).unwrap(),
            som(8_100_000)
        );
        assert_eq!(
            owner_earnings(som(5_000_000), som(-6_000_000)).unwrap(),
            som(0)
        );
        assert_eq!(
            owner_month_earnings(&[(som(1), som(0)); 4])
                .unwrap_err()
                .code,
            "TOO_MANY_MONTHS"
        );
    }

    #[test]
    fn delegate_payback_and_self_cheaper() {
        let base = DelegateInput {
            owner_hour_value: 3_115_385,
            task_minutes: 1_200,
            helper_hour_cost: 1_500_000,
            training_money: 50_000_000,
            training_minutes: 600,
        };
        let r = delegate(&base).unwrap();
        assert_eq!(
            (r.monthly_benefit, r.full_cost, r.payback_months),
            (32_307_700, 81_153_850, Some(3))
        );
        let free = delegate(&DelegateInput {
            training_money: 0,
            training_minutes: 0,
            ..base
        })
        .unwrap();
        assert_eq!(free.payback_months, Some(0));
        let same = delegate(&DelegateInput {
            helper_hour_cost: 3_115_385,
            ..base
        })
        .unwrap();
        assert_eq!(
            (same.verdict, same.payback_months),
            (DelegateVerdict::SelfCheaper, None)
        );
    }
}
