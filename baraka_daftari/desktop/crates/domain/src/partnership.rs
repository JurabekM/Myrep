//! 5-qonun (SPEC 2E.1, 2E.2): sheriklik turlari, foyda/zarar taqsimoti va kamayib boruvchi sheriklik
//! (buyout). Sof hisoblar; vektorlar: `profit_distribution`, `buyout`.
use money::{allocate, round_half_up, Money, MoneyError};

use crate::{PartnershipKind, PartyRole};

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PartnershipError {
    /// Kapital egasiga qat'iy summa yoki kafolatlangan daromad — sheriklik emas.
    #[error("Bu sheriklik emas — ribo yoki qarz: foyda faqat sof foydaning foizi bo'lishi mumkin, kafolatlangan summa emas")]
    GuaranteedReturnForbidden,
    #[error("ulushlar yig'indisi 100% bo'lishi kerak")]
    InvalidShares,
    #[error("tomonlar roli yoki kapitali shartnoma turiga mos emas")]
    InvalidParties,
    #[error("summa noto'g'ri")]
    InvalidAmount,
    #[error(transparent)]
    Money(#[from] MoneyError),
}

impl PartnershipError {
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::GuaranteedReturnForbidden => "GUARANTEED_RETURN_FORBIDDEN",
            Self::InvalidShares => "INVALID_SHARES",
            Self::InvalidParties => "INVALID_PARTIES",
            Self::InvalidAmount => "INVALID_AMOUNT",
            Self::Money(_) => "MONEY",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PartyInput {
    pub role: PartyRole,
    pub capital: Money,
    /// Foyda ulushi, bazis punkt (5000 = 50%).
    pub share_bp: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Profit,
    Loss,
}

/// Tomonlar tuzilmasi va ulushlarni tekshiradi (shartnoma turiga qarab).
///
/// # Errors
/// Ulushlar yig'indisi 10000 emas yoki rollar/kapital turga mos kelmasa.
pub fn validate_parties(
    kind: PartnershipKind,
    parties: &[PartyInput],
) -> Result<(), PartnershipError> {
    let sum: u64 = parties.iter().map(|p| u64::from(p.share_bp)).sum();
    if sum != 10_000 {
        return Err(PartnershipError::InvalidShares);
    }
    if parties.iter().any(|p| p.capital.minor() < 0) {
        return Err(PartnershipError::InvalidAmount);
    }
    let providers = parties
        .iter()
        .filter(|p| p.role == PartyRole::CapitalProvider);
    let has_worker = parties.iter().any(|p| p.role == PartyRole::Worker);
    match kind {
        PartnershipKind::Mudaraba => {
            let mut any = false;
            for p in providers {
                any = true;
                if p.capital.minor() <= 0 {
                    return Err(PartnershipError::InvalidParties);
                }
            }
            if !any || !has_worker || parties.iter().any(|p| p.role == PartyRole::Partner) {
                return Err(PartnershipError::InvalidParties);
            }
        }
        PartnershipKind::Musharaka => {
            let total: i64 = parties.iter().map(|p| p.capital.minor()).sum();
            if total <= 0 || parties.iter().any(|p| p.role != PartyRole::Partner) {
                return Err(PartnershipError::InvalidParties);
            }
        }
    }
    Ok(())
}

fn neg(m: Money) -> Money {
    Money::new(-m.minor(), m.currency())
}

/// Foyda yoki zararni taqsimlaydi (SPEC 2E.1). Natija — tomonlar tartibida; zarar manfiy.
///
/// - `MUDARABA`: foyda — kelishilgan ulush; zarar — kapital egasi(lar)i kapitaliga mutanosib,
///   ishchi 0. `negligence = true` bo'lsa zarar ishchi(lar) zimmasiga (ulushlari bo'yicha) o'tadi —
///   faqat beparvolik izohi bilan (izoh talabi xizmat qatlamida).
/// - `MUSHARAKA`: foyda — ulush; zarar — `capital_i / Σcapital`.
/// - `fixed_return` berilsa — doim xato (kafolatli daromad ribo/qarz).
///
/// # Errors
/// Kafolatli summa, noto'g'ri ulush/tomonlar/summa.
pub fn distribute(
    kind: PartnershipKind,
    outcome: Outcome,
    amount: Money,
    parties: &[PartyInput],
    negligence: bool,
    fixed_return: Option<Money>,
) -> Result<Vec<Money>, PartnershipError> {
    if fixed_return.is_some() {
        return Err(PartnershipError::GuaranteedReturnForbidden);
    }
    if amount.minor() < 0 {
        return Err(PartnershipError::InvalidAmount);
    }
    validate_parties(kind, parties)?;
    let cur = amount.currency();
    let zero = Money::new(0, cur);
    match outcome {
        Outcome::Profit => {
            let ratios: Vec<u64> = parties.iter().map(|p| u64::from(p.share_bp)).collect();
            Ok(allocate(amount, &ratios)?)
        }
        Outcome::Loss => {
            let mut out = vec![zero; parties.len()];
            let bearers: Vec<usize> = match kind {
                PartnershipKind::Musharaka => (0..parties.len()).collect(),
                PartnershipKind::Mudaraba if negligence => parties
                    .iter()
                    .enumerate()
                    .filter(|(_, p)| p.role == PartyRole::Worker)
                    .map(|(i, _)| i)
                    .collect(),
                PartnershipKind::Mudaraba => parties
                    .iter()
                    .enumerate()
                    .filter(|(_, p)| p.role == PartyRole::CapitalProvider)
                    .map(|(i, _)| i)
                    .collect(),
            };
            let by_capital = kind == PartnershipKind::Musharaka || !negligence;
            let mut ratios: Vec<u64> = bearers
                .iter()
                .map(|&i| {
                    if by_capital {
                        u64::try_from(parties[i].capital.minor()).unwrap_or(0)
                    } else {
                        u64::from(parties[i].share_bp)
                    }
                })
                .collect();
            if ratios.iter().sum::<u64>() == 0 {
                ratios = vec![1; bearers.len()];
            }
            let parts = allocate(amount, &ratios)?;
            for (k, &i) in bearers.iter().enumerate() {
                out[i] = neg(parts[k]);
            }
            Ok(out)
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BuyoutRow {
    pub period: u32,
    /// Shu davrda qoldiqqa qo'llangan to'lov (qoldiqdan oshmaydi).
    pub applied: Money,
    pub remaining: Money,
    /// Kapital egasining qolgan ulushi (bp, half-up).
    pub provider_bp: u32,
    pub worker_bp: u32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuyoutSchedule {
    pub rows: Vec<BuyoutRow>,
    pub completed: bool,
}

/// Kamayib boruvchi sheriklik: ishchining har davr to'lovi kapital egasining ulushini sotib oladi.
///
/// # Errors
/// Umumiy qiymat/ulush ≤ 0, ulush qiymatdan katta, to'lov manfiy yoki valyuta mos kelmasa.
pub fn buyout_schedule(
    total_value: Money,
    provider_stake: Money,
    payments: &[Money],
) -> Result<BuyoutSchedule, PartnershipError> {
    if total_value.minor() <= 0
        || provider_stake.minor() <= 0
        || provider_stake.minor() > total_value.minor()
        || payments.iter().any(|p| p.minor() < 0)
    {
        return Err(PartnershipError::InvalidAmount);
    }
    let cur = total_value.currency();
    let mut remaining = provider_stake.minor();
    let mut rows = Vec::with_capacity(payments.len());
    for (i, p) in payments.iter().enumerate() {
        let applied = p.minor().min(remaining);
        remaining -= applied;
        let bp = u32::try_from(round_half_up(
            i128::from(remaining) * 10_000,
            i128::from(total_value.minor()),
        )?)
        .unwrap_or(10_000);
        rows.push(BuyoutRow {
            period: u32::try_from(i + 1).unwrap_or(u32::MAX),
            applied: Money::new(applied, cur),
            remaining: Money::new(remaining, cur),
            provider_bp: bp,
            worker_bp: 10_000 - bp,
        });
    }
    Ok(BuyoutSchedule {
        rows,
        completed: remaining == 0,
    })
}

/// Teng bo'laklarga bo'lingan to'lovlar (1..=240 davr).
///
/// # Errors
/// Ulush ≤ 0 yoki davrlar soni 1..=240 emas.
pub fn equal_buyout_payments(
    provider_stake: Money,
    periods: u32,
) -> Result<Vec<Money>, PartnershipError> {
    if provider_stake.minor() <= 0 || periods == 0 || periods > 240 {
        return Err(PartnershipError::InvalidAmount);
    }
    Ok(allocate(provider_stake, &vec![1_u64; periods as usize])?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    /// Qabul mezoni (D12): kafolatli daromad domen darajasida bloklanadi, tushuntirish bilan.
    #[test]
    fn guaranteed_return_is_blocked_with_an_explanation() {
        let parties = [
            PartyInput {
                role: PartyRole::CapitalProvider,
                capital: uzs(100),
                share_bp: 5_000,
            },
            PartyInput {
                role: PartyRole::Worker,
                capital: uzs(0),
                share_bp: 5_000,
            },
        ];
        let e = distribute(
            PartnershipKind::Mudaraba,
            Outcome::Profit,
            uzs(10),
            &parties,
            false,
            Some(uzs(1)),
        )
        .unwrap_err();
        assert_eq!(e, PartnershipError::GuaranteedReturnForbidden);
        assert!(e.to_string().contains("ribo yoki qarz"));
    }

    #[test]
    fn totals_are_conserved() {
        let parties = [
            PartyInput {
                role: PartyRole::CapitalProvider,
                capital: uzs(7),
                share_bp: 3_333,
            },
            PartyInput {
                role: PartyRole::CapitalProvider,
                capital: uzs(3),
                share_bp: 3_333,
            },
            PartyInput {
                role: PartyRole::Worker,
                capital: uzs(0),
                share_bp: 3_334,
            },
        ];
        for (o, n) in [
            (Outcome::Profit, false),
            (Outcome::Loss, false),
            (Outcome::Loss, true),
        ] {
            let r = distribute(PartnershipKind::Mudaraba, o, uzs(1001), &parties, n, None).unwrap();
            let sum: i64 = r.iter().map(|m| m.minor()).sum();
            assert_eq!(sum.abs(), 1001);
        }
    }
}
