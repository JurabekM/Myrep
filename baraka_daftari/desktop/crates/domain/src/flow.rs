//! Oylik pul oqimi: izohsiz summa (SPEC 2.3) va "Kimning puli?" taqsimoti (SPEC 2.4).
use money::{round_half_up, Money, MoneyError};

use crate::MoneyOwner;

/// `daromad − majburiyatlar − xarajatlar − jamg'arma`. Manfiy bo'lsa — hisobdan ortiq sarflangan.
///
/// # Errors
/// Valyuta mos kelmasa yoki overflow bo'lsa.
pub fn unexplained_gap(
    income: Money,
    obligations: Money,
    expenses: Money,
    savings: Money,
) -> Result<Money, MoneyError> {
    month_result(income, obligations, expenses)?.checked_sub(savings)
}

/// Oy yakuni: `daromad − majburiyatlar − xarajatlar` (jamg'arma egasida qoladi).
///
/// # Errors
/// Valyuta mos kelmasa yoki overflow bo'lsa.
pub fn month_result(
    income: Money,
    obligations: Money,
    expenses: Money,
) -> Result<Money, MoneyError> {
    income.checked_sub(obligations)?.checked_sub(expenses)
}

/// `amount / total` bazis punktda (half-up). `total <= 0` bo'lsa 0.
///
/// # Errors
/// Overflow bo'lsa.
pub fn share_bp(amount: Money, total: Money) -> Result<i64, MoneyError> {
    if total.minor() <= 0 {
        return Ok(0);
    }
    let num = i128::from(amount.minor())
        .checked_mul(10_000)
        .ok_or(MoneyError::Overflow)?;
    round_half_up(num, i128::from(total.minor()))
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OwnerShare {
    /// `None` — "o'zingiz".
    pub owner: Option<MoneyOwner>,
    pub amount: Money,
    pub bp: i64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WhoseMoney {
    pub shares: Vec<OwnerShare>,
    /// Hisobga olinmagan summa ("somsaga bir million").
    pub unexplained: Money,
    /// "O'zingizga to'langan" (jamg'armaga ajratilgan).
    pub self_paid: Money,
    pub self_paid_bp: i64,
}

/// Oylik daromadni egalarga bo'ladi. `owner_amounts` — majburiyat va xarajatlar egalar bo'yicha
/// jamlangan (bir egadan bir nechta yozuv bo'lishi mumkin). Tartib barqaror: `MoneyOwner` tartibida.
///
/// # Errors
/// Valyuta mos kelmasa yoki overflow bo'lsa.
pub fn whose_money(
    income: Money,
    owner_amounts: &[(MoneyOwner, Money)],
    savings: Money,
) -> Result<WhoseMoney, MoneyError> {
    const ORDER: [MoneyOwner; 6] = [
        MoneyOwner::Landlord,
        MoneyOwner::Bank,
        MoneyOwner::Shop,
        MoneyOwner::State,
        MoneyOwner::Fuel,
        MoneyOwner::Other,
    ];
    let mut shares = Vec::new();
    let mut spent = Money::zero(income.currency());
    for owner in ORDER {
        let mut total = Money::zero(income.currency());
        for (o, m) in owner_amounts.iter().filter(|(o, _)| *o == owner) {
            let _ = o;
            total = total.checked_add(*m)?;
        }
        if total.minor() != 0 {
            spent = spent.checked_add(total)?;
            shares.push(OwnerShare {
                owner: Some(owner),
                amount: total,
                bp: share_bp(total, income)?,
            });
        }
    }
    let unexplained = income.checked_sub(spent)?.checked_sub(savings)?;
    Ok(WhoseMoney {
        shares,
        unexplained,
        self_paid: savings,
        self_paid_bp: share_bp(savings, income)?,
    })
}

#[cfg(test)]
mod tests {
    use money::Currency;

    use super::*;

    fn m(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn story_example_leaves_one_million_unexplained() {
        let gap = unexplained_gap(m(800_000_000), m(535_000_000), m(165_000_000), m(0)).unwrap();
        assert_eq!(gap.minor(), 100_000_000);
    }

    #[test]
    fn overspending_is_negative() {
        let gap = unexplained_gap(m(100), m(80), m(50), m(0)).unwrap();
        assert_eq!(gap.minor(), -30);
        assert_eq!(month_result(m(100), m(80), m(50)).unwrap().minor(), -30);
    }

    #[test]
    fn savings_reduce_the_gap_but_not_the_result() {
        assert_eq!(month_result(m(100), m(20), m(30)).unwrap().minor(), 50);
        assert_eq!(
            unexplained_gap(m(100), m(20), m(30), m(50))
                .unwrap()
                .minor(),
            0
        );
    }

    #[test]
    fn whose_money_groups_and_computes_bp() {
        let w = whose_money(
            m(1000),
            &[
                (MoneyOwner::Landlord, m(300)),
                (MoneyOwner::Fuel, m(100)),
                (MoneyOwner::Landlord, m(50)),
            ],
            m(100),
        )
        .unwrap();
        assert_eq!(w.shares.len(), 2);
        assert_eq!(
            (
                w.shares[0].owner,
                w.shares[0].amount.minor(),
                w.shares[0].bp
            ),
            (Some(MoneyOwner::Landlord), 350, 3500)
        );
        assert_eq!(w.shares[1].owner, Some(MoneyOwner::Fuel));
        assert_eq!(w.unexplained.minor(), 1000 - 450 - 100);
        assert_eq!((w.self_paid.minor(), w.self_paid_bp), (100, 1000));
    }

    #[test]
    fn zero_income_gives_zero_bp() {
        assert_eq!(share_bp(m(5), m(0)).unwrap(), 0);
        let w = whose_money(m(0), &[], m(0)).unwrap();
        assert_eq!((w.self_paid_bp, w.unexplained.minor()), (0, 0));
    }

    #[test]
    fn currency_mismatch_is_error() {
        let usd = Money::new(1, Currency::Usd);
        assert!(unexplained_gap(m(10), usd, m(0), m(0)).is_err());
    }
}
