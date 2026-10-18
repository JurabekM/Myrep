//! M2 — «Ikki qirg'oq»: yuborilgan pulning maqsadlari va uy tomonidagi qoldiq (musofir/SPEC 5).
//!
//! ```text
//! Har qabul qilingan summa → allocate(summa, ulushlar)        (kanonik maqsadlar tartibida)
//! Maqsad qoldig'i = Σ olingan − Σ sarflangan                 (manfiy — OVERSPENT, taqiqlanmaydi)
//! ```
//! Qabul qilinmagan yuborish «yo'lda» — qoldiqqa kirmaydi.
//!
//! Vektorlar: `spec/test-vectors/mf_remittance.json`.
use baraka_money::{allocate, Currency, Money};

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Purpose {
    Household,
    Debt,
    Build,
    Education,
    Ceremony,
    Savings,
    Other,
}

impl Purpose {
    /// Kanonik tartib (ekranda ham shu tartib).
    pub const ALL: [Purpose; 7] = [
        Self::Household,
        Self::Debt,
        Self::Build,
        Self::Education,
        Self::Ceremony,
        Self::Savings,
        Self::Other,
    ];

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.iter().copied().find(|p| p.as_str() == s)
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Household => "HOUSEHOLD",
            Self::Debt => "DEBT",
            Self::Build => "BUILD",
            Self::Education => "EDUCATION",
            Self::Ceremony => "CEREMONY",
            Self::Savings => "SAVINGS",
            Self::Other => "OTHER",
        }
    }
}

/// Maqsad ulushi (bp).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Share {
    pub purpose: Purpose,
    pub bp: i64,
}

/// Ulushlarni tekshiradi va kanonik tartibda qaytaradi: har biri 1–10000 bp, maqsad takrorlanmaydi,
/// yig'indisi 100 %.
pub fn check_shares(shares: &[Share]) -> Result<Vec<Share>, DomainError> {
    let mut seen = Vec::new();
    let mut sum: i64 = 0;
    for s in shares {
        if seen.contains(&s.purpose) {
            return Err(DomainError::on("DUPLICATE_PURPOSE", "shares"));
        }
        if !(1..=10_000).contains(&s.bp) {
            return Err(DomainError::on("INVALID_BP", "shares"));
        }
        seen.push(s.purpose);
        sum += s.bp;
    }
    if sum != 10_000 {
        return Err(DomainError::on("SHARES_NOT_FULL", "shares"));
    }
    let mut out = shares.to_vec();
    out.sort_by_key(|s| s.purpose);
    Ok(out)
}

/// Summani ulushlar bo'yicha bo'lish (largest remainder, kanonik tartibda).
pub fn split(amount: Money, shares: &[Share]) -> Result<Vec<(Purpose, Money)>, DomainError> {
    let ordered = check_shares(shares)?;
    let parts = allocate(amount, &ordered.iter().map(|s| s.bp).collect::<Vec<_>>())?;
    Ok(ordered.iter().map(|s| s.purpose).zip(parts).collect())
}

/// Bitta yuborish: ulushlar va (qabul qilingan bo'lsa) uyda olingan summa.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Remittance {
    pub received: Option<Money>,
    pub shares: Vec<Share>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PurposeBalance {
    pub purpose: Purpose,
    pub received: Money,
    pub spent: Money,
    pub balance: Money,
    pub overspent: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RemittanceBook {
    /// Ulushda yoki xarajatda uchragan maqsadlar, kanonik tartibda.
    pub purposes: Vec<PurposeBalance>,
    pub received: Money,
    pub spent: Money,
    pub balance: Money,
    /// Qabul qilinmagan yuborishlar soni.
    pub pending: usize,
    pub overspent: bool,
    /// Har yuborish uchun bo'linish (yo'ldagisi — `None`).
    pub allocations: Vec<Option<Vec<(Purpose, Money)>>>,
}

/// `currency` — uy valyutasi (qabul va xarajatlar shu valyutada).
pub fn remittance_book(
    currency: Currency,
    remittances: &[Remittance],
    spends: &[(Purpose, Money)],
) -> Result<RemittanceBook, DomainError> {
    let zero = Money::zero(currency);
    let mut received = [zero; 7];
    let mut spent = [zero; 7];
    let mut used = [false; 7];
    let idx = |p: Purpose| Purpose::ALL.iter().position(|x| *x == p).unwrap_or(0);
    let mut pending = 0;
    let mut allocations = Vec::new();
    for r in remittances {
        let ordered = check_shares(&r.shares)?;
        for s in &ordered {
            used[idx(s.purpose)] = true;
        }
        let Some(amount) = r.received else {
            pending += 1;
            allocations.push(None);
            continue;
        };
        if !amount.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "received"));
        }
        let parts = split(amount, &ordered)?;
        for (p, m) in &parts {
            let i = idx(*p);
            received[i] = received[i].checked_add(*m)?;
        }
        allocations.push(Some(parts));
    }
    for (p, m) in spends {
        if !m.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        let i = idx(*p);
        spent[i] = spent[i].checked_add(*m)?;
        used[i] = true;
    }
    let mut purposes = Vec::new();
    for (i, p) in Purpose::ALL.iter().enumerate() {
        if used[i] {
            let balance = received[i].checked_sub(spent[i])?;
            purposes.push(PurposeBalance {
                purpose: *p,
                received: received[i],
                spent: spent[i],
                balance,
                overspent: balance.is_negative(),
            });
        }
    }
    let total_received = Money::sum(received, currency)?;
    let total_spent = Money::sum(spent, currency)?;
    Ok(RemittanceBook {
        overspent: purposes.iter().any(|p| p.overspent),
        purposes,
        received: total_received,
        spent: total_spent,
        balance: total_received.checked_sub(total_spent)?,
        pending,
        allocations,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(purpose: Purpose, bp: i64) -> Share {
        Share { purpose, bp }
    }

    #[test]
    fn gulnora_split_and_balance() {
        let u = |m| Money::new(m, Currency::Uzs);
        let shares = vec![
            s(Purpose::Build, 2_000),
            s(Purpose::Household, 5_000),
            s(Purpose::Debt, 3_000),
        ];
        let b = remittance_book(
            Currency::Uzs,
            &[Remittance {
                received: Some(u(1_090_000_000)),
                shares,
            }],
            &[(Purpose::Household, u(600_000_000))],
        )
        .unwrap();
        assert_eq!(b.purposes[0].purpose, Purpose::Household);
        assert_eq!(b.purposes[0].balance, u(-55_000_000));
        assert!(b.overspent);
    }

    #[test]
    fn shares_must_be_full() {
        let e = check_shares(&[s(Purpose::Household, 9_000)]).unwrap_err();
        assert_eq!(e.code, "SHARES_NOT_FULL");
    }
}
