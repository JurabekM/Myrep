//! K7 — «Hisob kuni» konvertlari (SPEC 4.5, 8.2): soliq zaxirasi, zaxira, aylanma, kengayish, sadaqa. Har
//! bayonnoma qo'shadi, foydalanish ayiradi (soliq zaxirasidan — to'langan soliq); qoldiqdan ko'p ishlatib
//! bo'lmaydi. Bu pul harakati emas — hamyondagi pulning qaysi maqsadga ajratilgani.
//!
//! Vektorlar: `spec/test-vectors/kk_funds.json`.
use baraka_money::{Currency, Money};

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Fund {
    Tax,
    Reserve,
    Working,
    Expansion,
    Sadaqa,
}

impl Fund {
    pub const ALL: [Self; 5] = [
        Self::Tax,
        Self::Reserve,
        Self::Working,
        Self::Expansion,
        Self::Sadaqa,
    ];

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|f| f.as_str() == s)
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Tax => "TAX",
            Self::Reserve => "RESERVE",
            Self::Working => "WORKING",
            Self::Expansion => "EXPANSION",
            Self::Sadaqa => "SADAQA",
        }
    }

    fn index(self) -> usize {
        self as usize
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FundEvent {
    /// Bayonnoma: har konvertga qo'shiladigan summa (`Fund::ALL` tartibida).
    Close([Money; 5]),
    Use {
        fund: Fund,
        amount: Money,
    },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FundState {
    pub fund: Fund,
    pub added: Money,
    pub used: Money,
    pub balance: Money,
}

pub fn funds(currency: Currency, events: &[FundEvent]) -> Result<Vec<FundState>, DomainError> {
    let zero = Money::zero(currency);
    let mut st: Vec<FundState> = Fund::ALL
        .iter()
        .map(|&fund| FundState {
            fund,
            added: zero,
            used: zero,
            balance: zero,
        })
        .collect();
    for e in events {
        match e {
            FundEvent::Close(amounts) => {
                for (s, a) in st.iter_mut().zip(amounts) {
                    if a.is_negative() {
                        return Err(DomainError::on("AMOUNT_NEGATIVE", "amount"));
                    }
                    s.added = s.added.checked_add(*a)?;
                    s.balance = s.balance.checked_add(*a)?;
                }
            }
            FundEvent::Use { fund, amount } => {
                if !amount.is_positive() {
                    return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
                }
                let s = &mut st[fund.index()];
                if amount.compare(&s.balance)?.is_gt() {
                    return Err(DomainError::on("FUND_INSUFFICIENT", "amount"));
                }
                s.used = s.used.checked_add(*amount)?;
                s.balance = s.balance.checked_sub(*amount)?;
            }
        }
    }
    Ok(st)
}
