//! Sheriklik kassa daftari va «Hunardan ishga» (SPEC 2E.3, 2E.4; DESKTOP_PROMPT D13).
//!
//! * Davr yakuni: kirim − xarajat (fors-major ham xarajat sifatida) = sof natija; taqsimot — [`crate::partnership::distribute`].
//! * «Hunardan ishga»: uch stsenariy (pessimistik, o'rtacha, optimistik) — kirim va xarajat koeffitsiyentlari bp'da,
//!   payback = CAPEX ÷ oylik sof foyda (yuqoriga yaxlitlangan). Hamma hisob butun sonlarda.

use money::{Money, round_half_up_div};

use crate::DomainError;

/// Stsenariy nomi (kod).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ScenarioName {
    /// Pessimistik: kirim 70 %, xarajat 120 %.
    Pessimistic,
    /// O'rtacha: kiritilgan raqamlar.
    Average,
    /// Optimistik: kirim 130 %, xarajat 90 %.
    Optimistic,
}

impl ScenarioName {
    /// Kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Pessimistic => "PESSIMISTIC",
            Self::Average => "AVERAGE",
            Self::Optimistic => "OPTIMISTIC",
        }
    }

    /// (kirim koeffitsiyenti, xarajat koeffitsiyenti) bp'da.
    const fn factors(self) -> (i128, i128) {
        match self {
            Self::Pessimistic => (7_000, 12_000),
            Self::Average => (10_000, 10_000),
            Self::Optimistic => (13_000, 9_000),
        }
    }
}

/// «Hunardan ishga» kirishi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HustleInput {
    /// Boshlang'ich xarajat (CAPEX) jami.
    pub capex: Money,
    /// Kutilayotgan oylik kirim.
    pub monthly_income: Money,
    /// Kutilayotgan oylik xarajat.
    pub monthly_expense: Money,
    /// Mening foyda ulushim (bp); sheriksiz — 10 000.
    pub my_share_bp: u64,
}

/// Stsenariy natijasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HustleScenario {
    /// Nomi.
    pub name: ScenarioName,
    /// Oylik kirim (koeffitsiyent bilan).
    pub income: Money,
    /// Oylik xarajat (koeffitsiyent bilan).
    pub expense: Money,
    /// Sof natija (manfiy bo'lishi mumkin).
    pub net: Money,
    /// Mening ulushim (sof foydadan; zarar bo'lsa — 0 emas, ulushga mutanosib manfiy emas: 0).
    pub my_net: Money,
    /// Qoplanish muddati (oy); foyda bo'lmasa — yo'q.
    pub payback_months: Option<u32>,
}

fn scaled(amount: Money, bp: i128) -> Result<Money, DomainError> {
    let minor = round_half_up_div(i128::from(amount.minor()) * bp, 10_000)?;
    Ok(Money::new(
        i64::try_from(minor).map_err(|_| DomainError::InvalidRule)?,
        amount.currency(),
    ))
}

/// Sof natija: kirim − xarajat (manfiy bo'lishi mumkin).
pub fn net_of(income: Money, expense: Money) -> Result<Money, DomainError> {
    Ok(income.checked_sub(expense)?)
}

/// Qoplanish muddati: `capex ÷ monthly_net` yuqoriga; foyda ≤ 0 bo'lsa — yo'q; CAPEX ≤ 0 — 0 oy.
pub fn payback_months(capex: Money, monthly_net: Money) -> Option<u32> {
    if monthly_net.minor() <= 0 {
        return None;
    }
    if capex.minor() <= 0 {
        return Some(0);
    }
    let months = (i128::from(capex.minor()) + i128::from(monthly_net.minor()) - 1)
        / i128::from(monthly_net.minor());
    Some(u32::try_from(months).unwrap_or(u32::MAX))
}

/// Uch stsenariy («hisob-kitobni uch marta qildim»).
pub fn hustle_scenarios(input: &HustleInput) -> Result<[HustleScenario; 3], DomainError> {
    if input.my_share_bp > 10_000 {
        return Err(DomainError::InvalidRule);
    }
    let build = |name: ScenarioName| -> Result<HustleScenario, DomainError> {
        let (income_bp, expense_bp) = name.factors();
        let income = scaled(input.monthly_income, income_bp)?;
        let expense = scaled(input.monthly_expense, expense_bp)?;
        let net = net_of(income, expense)?;
        let my_net = if net.minor() > 0 {
            scaled(net, i128::from(input.my_share_bp))?
        } else {
            Money::zero(net.currency())
        };
        Ok(HustleScenario {
            name,
            income,
            expense,
            net,
            my_net,
            payback_months: payback_months(input.capex, my_net),
        })
    };
    Ok([
        build(ScenarioName::Pessimistic)?,
        build(ScenarioName::Average)?,
        build(ScenarioName::Optimistic)?,
    ])
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn uch_stsenariy_va_payback() {
        let plan = hustle_scenarios(&HustleInput {
            capex: uzs(800_000_000),
            monthly_income: uzs(600_000_000),
            monthly_expense: uzs(400_000_000),
            my_share_bp: 6_000,
        })
        .expect("reja");
        // O'rtacha: sof 2 000 000, mening 60 % = 1 200 000, payback = ceil(8 000 000 / 1 200 000) = 7.
        assert_eq!(plan[1].net, uzs(200_000_000));
        assert_eq!(plan[1].my_net, uzs(120_000_000));
        assert_eq!(plan[1].payback_months, Some(7));
        // Pessimistik: kirim 4 200 000, xarajat 4 800 000 → zarar, payback yo'q.
        assert_eq!(plan[0].net, uzs(-60_000_000));
        assert_eq!(plan[0].my_net, uzs(0));
        assert_eq!(plan[0].payback_months, None);
        // Optimistik: kirim 7 800 000, xarajat 3 600 000 → sof 4 200 000, mening 2 520 000, payback 4.
        assert_eq!(plan[2].net, uzs(420_000_000));
        assert_eq!(plan[2].payback_months, Some(4));
    }

    #[test]
    fn payback_chegaralari() {
        assert_eq!(payback_months(uzs(0), uzs(10)), Some(0));
        assert_eq!(payback_months(uzs(100), uzs(0)), None);
        assert_eq!(payback_months(uzs(100), uzs(30)), Some(4));
        assert_eq!(payback_months(uzs(90), uzs(30)), Some(3));
    }
}
