//! Oylik audit: «izohsiz qolgan summa» (`docs/BARAKA_OILASI.md` 5.9).
use baraka_money::Money;

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GapInput {
    pub income: Money,
    pub obligations_paid: Money,
    pub expenses: Money,
    /// Davr ichida jamg'armaga kirgan − chiqqan.
    pub vault_net: Money,
    /// Naqd va karta qoldig'ining davr oxiri − boshi farqi.
    pub balance_delta: Money,
}

/// `gap = income − obligations − expenses − vault_net − Δ(CASH + BANK_CARD)`.
/// Musbat — izohsiz chiqib ketgan; manfiy — yozilmagan daromad yoki qoldiq xatosi.
pub fn unexplained_gap(i: &GapInput) -> Result<Money, DomainError> {
    Ok(i.income
        .checked_sub(i.obligations_paid)?
        .checked_sub(i.expenses)?
        .checked_sub(i.vault_net)?
        .checked_sub(i.balance_delta)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn documented_and_balance_aware() {
        let mut i = GapInput {
            income: uzs(800_000_000),
            obligations_paid: uzs(535_000_000),
            expenses: uzs(165_000_000),
            vault_net: uzs(0),
            balance_delta: uzs(0),
        };
        assert_eq!(unexplained_gap(&i), Ok(uzs(100_000_000)));
        i.balance_delta = uzs(60_000_000);
        assert_eq!(unexplained_gap(&i), Ok(uzs(40_000_000)));
        i.balance_delta = uzs(160_000_000);
        assert_eq!(unexplained_gap(&i), Ok(uzs(-60_000_000)));
    }
}
