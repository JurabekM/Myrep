//! Marosimlarni rejalash (SPEC 2D.8, DESKTOP_PROMPT D11): byudjet qatorlari va moliyalash manbasi.
//!
//! Asosiy qoida: qarz bilan moliyalashtirilgan qator bo'lsa, marosim `CONFIRMED` holatiga oilaviy muhokamadan
//! keyin o'tadi. Muhokama yozib qo'yilmasa — [`confirm`] rad etadi (`FAMILY_DISCUSSION_REQUIRED`).

use money::Money;

use crate::DomainError;

/// Moliyalash manbasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FundingSource {
    /// Jamg'arma.
    Savings,
    /// Oila hissasi.
    FamilyContribution,
    /// Kutilayotgan to'yona.
    ExpectedGift,
    /// Qarz.
    Debt,
}

/// Byudjet qatori: `miqdor × birlik narxi`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BudgetLine {
    /// Nomi (osh, xonanda, kiyim-kechak, ...).
    pub name: String,
    /// Miqdori (mehmon soni, dona, ...).
    pub quantity: u64,
    /// Birlik narxi.
    pub unit_price: Money,
    /// Moliyalash manbasi.
    pub funding: FundingSource,
}

impl BudgetLine {
    /// Qator jami summasi.
    pub fn total(&self) -> Result<Money, DomainError> {
        let quantity = i64::try_from(self.quantity).map_err(|_| DomainError::InvalidRule)?;
        let minor = self
            .unit_price
            .minor()
            .checked_mul(quantity)
            .ok_or(DomainError::InvalidRule)?;
        Ok(Money::new(minor, self.unit_price.currency()))
    }
}

/// Marosim holati.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CeremonyStatus {
    /// Rejalashtirilmoqda.
    Planned,
    /// Tasdiqlangan (oilaviy muhokama bilan).
    Confirmed,
}

/// Marosim rejasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CeremonyPlan {
    /// Byudjet qatorlari.
    pub lines: Vec<BudgetLine>,
    /// Oilaviy muhokama o'tkazilganmi.
    pub family_discussed: bool,
    /// Holat.
    pub status: CeremonyStatus,
}

impl CeremonyPlan {
    /// Bo'sh reja.
    pub fn new() -> Self {
        Self {
            lines: Vec::new(),
            family_discussed: false,
            status: CeremonyStatus::Planned,
        }
    }

    /// Umumiy xarajat.
    pub fn total(&self) -> Result<Money, DomainError> {
        let currency = self
            .lines
            .first()
            .map_or(money::Currency::Uzs, |line| line.unit_price.currency());
        let mut total = Money::zero(currency);
        for line in &self.lines {
            total = total.checked_add(line.total()?)?;
        }
        Ok(total)
    }

    /// Qarz bilan qoplanadigan qism.
    pub fn debt_part(&self) -> Result<Money, DomainError> {
        let currency = self
            .lines
            .first()
            .map_or(money::Currency::Uzs, |line| line.unit_price.currency());
        let mut total = Money::zero(currency);
        for line in self
            .lines
            .iter()
            .filter(|line| line.funding == FundingSource::Debt)
        {
            total = total.checked_add(line.total()?)?;
        }
        Ok(total)
    }

    /// Oilaviy muhokama o'tkazilganini qayd etadi.
    pub fn record_family_discussion(&mut self) {
        self.family_discussed = true;
    }
}

impl Default for CeremonyPlan {
    fn default() -> Self {
        Self::new()
    }
}

/// Marosimni tasdiqlaydi. Qarz qatori bo'lsa, oilaviy muhokama shart.
pub fn confirm(plan: &mut CeremonyPlan) -> Result<(), DomainError> {
    let has_debt = plan
        .lines
        .iter()
        .any(|line| line.funding == FundingSource::Debt);
    if has_debt && !plan.family_discussed {
        return Err(DomainError::FamilyDiscussionRequired);
    }
    plan.status = CeremonyStatus::Confirmed;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn line(funding: FundingSource) -> BudgetLine {
        BudgetLine {
            name: "Osh".to_owned(),
            quantity: 200,
            unit_price: Money::new(1_500_000, Currency::Uzs),
            funding,
        }
    }

    #[test]
    fn qarzli_marosim_muhokamasiz_tasdiqlanmaydi() {
        let mut plan = CeremonyPlan::new();
        plan.lines.push(line(FundingSource::Debt));
        assert_eq!(
            confirm(&mut plan),
            Err(DomainError::FamilyDiscussionRequired)
        );
        assert_eq!(plan.status, CeremonyStatus::Planned);

        plan.record_family_discussion();
        confirm(&mut plan).expect("tasdiqlansin");
        assert_eq!(plan.status, CeremonyStatus::Confirmed);
    }

    #[test]
    fn qarzsiz_marosim_darhol_tasdiqlanadi() {
        let mut plan = CeremonyPlan::new();
        plan.lines.push(line(FundingSource::Savings));
        confirm(&mut plan).expect("tasdiqlansin");
        assert_eq!(plan.debt_part().expect("qarz"), Money::zero(Currency::Uzs));
    }
}
