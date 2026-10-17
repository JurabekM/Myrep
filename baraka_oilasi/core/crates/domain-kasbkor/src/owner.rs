//! K1 — «Ikki cho'ntak» (SPEC 2): oy hisoboti, egasiga to'langan maosh va hamyon qoldiqlari.
//!
//! - **Pul oqimi** = tushum − chiqim. «Egasi oldi», kapital kiritish va maosh o'tkazmasi bu yerga
//!   kirmaydi: ular biznes natijasi emas, egasi bilan biznes orasidagi harakat.
//! - **Egasiga to'langan** = Uy'ga o'tkazilgan maosh + «egasi oldi» (maoshdan avans).
//! - Maosh belgilangan bo'lsa: qoldiq = max(0, maosh − to'langan), ortiqcha = max(0, to'langan − maosh).
//! - Hamyonlar: naqd kassa (`CASH`) va karta/hisob raqami (`CARD`); oy boshidagi qoldiq + harakatlar.
//!   Manfiy qoldiq — xato emas, lekin belgi (yozilmagan tushum yoki xato yozuv).
//!
//! Vektorlar: `spec/test-vectors/kk_owner_pay.json`.
use baraka_money::{Currency, Money};

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Wallet {
    Cash,
    Card,
}

impl Wallet {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "CASH" => Some(Self::Cash),
            "CARD" => Some(Self::Card),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Cash => "CASH",
            Self::Card => "CARD",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MoveKind {
    /// Tushum (savdo, xizmat).
    Sale,
    /// Chiqim (operatsion, tovar xaridi va h.k.).
    Expense,
    /// «Egasi oldi» — maoshdan avans.
    OwnerDraw,
    /// Egasining shaxsiy pulidan kapital kiritish (qarz ham, tushum ham emas).
    OwnerContribution,
    /// Uy makoniga o'tkazilgan maosh.
    OwnerSalary,
    /// Hamyonlar orasida (masalan, kassadan kartaga topshirish).
    Transfer { to: Wallet },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Move {
    pub kind: MoveKind,
    pub wallet: Wallet,
    pub amount: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MonthReport {
    pub revenue: Money,
    pub expenses: Money,
    pub cash_flow: Money,
    pub owner_draws: Money,
    pub owner_salary_transferred: Money,
    pub contributions: Money,
    pub owner_paid: Money,
    /// Maosh belgilanmagan bo'lsa — `None`.
    pub salary_remaining: Option<Money>,
    pub overdrawn: Option<Money>,
    pub cash: Money,
    pub card: Money,
    pub negative_wallets: Vec<Wallet>,
}

/// Oy hisoboti. `salary` nol — maosh belgilanmagan.
pub fn month_report(
    currency: Currency,
    opening_cash: Money,
    opening_card: Money,
    salary: Money,
    moves: &[Move],
) -> Result<MonthReport, DomainError> {
    if salary.is_negative() {
        return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "ownerSalary"));
    }
    let zero = Money::zero(currency);
    let (mut cash, mut card) = (opening_cash, opening_card);
    let (mut revenue, mut expenses, mut draws, mut contributions, mut salary_paid) =
        (zero, zero, zero, zero, zero);
    for m in moves {
        if !m.amount.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        let (plus, minus) = match m.kind {
            MoveKind::Transfer { to } if to == m.wallet => {
                return Err(DomainError::on("SAME_WALLET", "toWallet"));
            }
            MoveKind::Transfer { to } => (Some(to), Some(m.wallet)),
            MoveKind::Sale => {
                revenue = revenue.checked_add(m.amount)?;
                (Some(m.wallet), None)
            }
            MoveKind::OwnerContribution => {
                contributions = contributions.checked_add(m.amount)?;
                (Some(m.wallet), None)
            }
            MoveKind::Expense => {
                expenses = expenses.checked_add(m.amount)?;
                (None, Some(m.wallet))
            }
            MoveKind::OwnerDraw => {
                draws = draws.checked_add(m.amount)?;
                (None, Some(m.wallet))
            }
            MoveKind::OwnerSalary => {
                salary_paid = salary_paid.checked_add(m.amount)?;
                (None, Some(m.wallet))
            }
        };
        for (w, sign) in [(plus, true), (minus, false)] {
            let Some(w) = w else { continue };
            let slot = match w {
                Wallet::Cash => &mut cash,
                Wallet::Card => &mut card,
            };
            *slot = if sign {
                slot.checked_add(m.amount)?
            } else {
                slot.checked_sub(m.amount)?
            };
        }
    }
    let paid = salary_paid.checked_add(draws)?;
    let (salary_remaining, overdrawn) = if salary.is_zero() {
        (None, None)
    } else {
        (
            Some(salary.checked_sub(paid)?.clamp_non_negative()),
            Some(paid.checked_sub(salary)?.clamp_non_negative()),
        )
    };
    let negative_wallets = [(Wallet::Cash, cash), (Wallet::Card, card)]
        .into_iter()
        .filter(|(_, b)| b.is_negative())
        .map(|(w, _)| w)
        .collect();
    Ok(MonthReport {
        revenue,
        expenses,
        cash_flow: revenue.checked_sub(expenses)?,
        owner_draws: draws,
        owner_salary_transferred: salary_paid,
        contributions,
        owner_paid: paid,
        salary_remaining,
        overdrawn,
        cash,
        card,
        negative_wallets,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uzs(major: i64) -> Money {
        Money::new(major * 100, Currency::Uzs)
    }

    fn mv(kind: MoveKind, wallet: Wallet, major: i64) -> Move {
        Move {
            kind,
            wallet,
            amount: uzs(major),
        }
    }

    #[test]
    fn owner_draw_does_not_reduce_cash_flow() {
        let r = month_report(
            Currency::Uzs,
            uzs(0),
            uzs(0),
            uzs(5_000_000),
            &[
                mv(MoveKind::Sale, Wallet::Cash, 18_000_000),
                mv(MoveKind::Expense, Wallet::Cash, 8_500_000),
                mv(MoveKind::OwnerDraw, Wallet::Cash, 1_200_000),
            ],
        )
        .unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(r.cash_flow, uzs(9_500_000));
        assert_eq!(r.owner_paid, uzs(1_200_000));
        assert_eq!(r.salary_remaining, Some(uzs(3_800_000)));
        assert_eq!(r.overdrawn, Some(uzs(0)));
        assert_eq!(r.cash, uzs(8_300_000));
    }

    #[test]
    fn transfer_to_same_wallet_is_rejected() {
        let e = month_report(
            Currency::Uzs,
            uzs(0),
            uzs(0),
            uzs(0),
            &[mv(MoveKind::Transfer { to: Wallet::Card }, Wallet::Card, 1)],
        );
        assert_eq!(e.map(|_| ()).unwrap_err().code, "SAME_WALLET");
    }
}
