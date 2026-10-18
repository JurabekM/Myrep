//! K4 — kunlik kassa yopish (SPEC 5.1).
//!
//! ```text
//! Kutilgan = Ochilish + Naqd tushum − Naqd chiqim − «Egasi oldi» (naqd) − Kartaga topshirildi + boshqa naqd kirim − boshqa naqd chiqim
//! Farq     = Sanalgan − Kutilgan
//! ```
//! Karta harakatlari kassaga ta'sir qilmaydi. Farq nol bo'lmasa — sabab tanlanadi. Oxirgi 4 haftada
//! (shu kun bilan) 3 va undan ko'p kamomad — «xato qidirish» taklifi; hech qachon ayblov emas.
//!
//! Vektorlar: `spec/test-vectors/kk_cash_close.json`.
use baraka_money::Money;

use crate::owner::{Move, MoveKind, Wallet};
use crate::DomainError;

/// Takrorlanuvchi kamomad chegarasi (4 hafta ichida).
pub const SHORTAGE_REPEAT: usize = 3;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CashReason {
    UnrecordedExpense,
    ChangeError,
    GivenOnCredit,
    OwnerTook,
    Unknown,
}

impl CashReason {
    pub fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "UNRECORDED_EXPENSE" => Self::UnrecordedExpense,
            "CHANGE_ERROR" => Self::ChangeError,
            "GIVEN_ON_CREDIT" => Self::GivenOnCredit,
            "OWNER_TOOK" => Self::OwnerTook,
            "UNKNOWN" => Self::Unknown,
            _ => return None,
        })
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::UnrecordedExpense => "UNRECORDED_EXPENSE",
            Self::ChangeError => "CHANGE_ERROR",
            Self::GivenOnCredit => "GIVEN_ON_CREDIT",
            Self::OwnerTook => "OWNER_TOOK",
            Self::Unknown => "UNKNOWN",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CashStatus {
    Exact,
    Short,
    Over,
}

impl CashStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Exact => "EXACT",
            Self::Short => "SHORT",
            Self::Over => "OVER",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CashClose {
    pub cash_sales: Money,
    pub cash_expenses: Money,
    pub owner_draws: Money,
    pub handed_over: Money,
    pub other_in: Money,
    pub other_out: Money,
    pub expected: Money,
    pub difference: Money,
    pub status: CashStatus,
    /// Farq nol bo'lsa — `None`.
    pub reason: Option<CashReason>,
    pub suggest_search: bool,
}

/// `opening` — kun boshidagi naqd kassa; `moves` — shu kun harakatlari (karta ham bo'lishi mumkin);
/// `recent` — oxirgi 4 hafta oldingi yopilgan kunlar farqlari.
pub fn cash_close(
    opening: Money,
    moves: &[Move],
    counted: Money,
    reason: Option<CashReason>,
    recent: &[Money],
) -> Result<CashClose, DomainError> {
    if counted.is_negative() || opening.is_negative() {
        return Err(DomainError::on("AMOUNT_NEGATIVE", "counted"));
    }
    let zero = Money::zero(opening.currency());
    let [mut sales, mut expenses, mut draws, mut handed, mut other_in, mut other_out] = [zero; 6];
    for m in moves {
        if !m.amount.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        let slot = match (m.kind, m.wallet) {
            (MoveKind::Transfer { to }, _) if to == m.wallet => {
                return Err(DomainError::on("SAME_WALLET", "toWallet"))
            }
            (MoveKind::Transfer { .. }, Wallet::Cash) => &mut handed,
            (MoveKind::Transfer { .. }, Wallet::Card) => &mut other_in,
            (_, Wallet::Card) => continue,
            (MoveKind::Sale, _) => &mut sales,
            (MoveKind::Expense, _) => &mut expenses,
            (MoveKind::OwnerDraw, _) => &mut draws,
            (MoveKind::OwnerContribution | MoveKind::EquipmentSale | MoveKind::CashOver, _) => {
                &mut other_in
            }
            (
                MoveKind::OwnerSalary
                | MoveKind::EquipmentPurchase
                | MoveKind::CashShort
                | MoveKind::StockPurchase,
                _,
            ) => &mut other_out,
        };
        *slot = slot.checked_add(m.amount)?;
    }
    let expected = opening
        .checked_add(sales)?
        .checked_sub(expenses)?
        .checked_sub(draws)?
        .checked_sub(handed)?
        .checked_add(other_in)?
        .checked_sub(other_out)?;
    let difference = counted.checked_sub(expected)?;
    let status = if difference.is_zero() {
        CashStatus::Exact
    } else if difference.is_negative() {
        CashStatus::Short
    } else {
        CashStatus::Over
    };
    let reason = match status {
        CashStatus::Exact => None,
        _ => Some(reason.ok_or(DomainError::on("REASON_REQUIRED", "reason"))?),
    };
    let shortages = recent.iter().filter(|d| d.is_negative()).count()
        + usize::from(status == CashStatus::Short);
    Ok(CashClose {
        cash_sales: sales,
        cash_expenses: expenses,
        owner_draws: draws,
        handed_over: handed,
        other_in,
        other_out,
        expected,
        difference,
        status,
        reason,
        suggest_search: status == CashStatus::Short && shortages >= SHORTAGE_REPEAT,
    })
}
