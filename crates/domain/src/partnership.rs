//! Sheriklik taqsimoti (SPEC 2E.1, DESKTOP_PROMPT D12): `MUDARABA` va `MUSHARAKA`.
//!
//! * Foyda — ulush bo'yicha (bp, yig'indisi 10 000).
//! * Zarar — `MUDARABA`da faqat kapital kiritgan tomonga; `MUSHARAKA`da kapitalga mutanosib.
//! * Kafolatli (qat'iy) summa — taqiqlangan, har qanday turda (`GUARANTEED_RETURN_FORBIDDEN`).
//!
//! Qismlar [`money::allocate`] bo'yicha bo'linadi: yig'indisi har doim `net` ga teng. Zarar — manfiy qismlar.

use money::{Money, allocate};

use crate::DomainError;

/// To'liq ulush (bp).
pub const FULL_SHARE_BP: u64 = 10_000;

/// Sheriklik turi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PartnershipKind {
    /// Mudaraba: kapital bir tomonda, ish ikkinchisida.
    Mudaraba,
    /// Musharaka: ikki tomon ham kapital kiritadi.
    Musharaka,
}

/// Sherik kirishi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartnerInput {
    /// Ulush, bp (foyda uchun).
    pub share_bp: u64,
    /// Kiritilgan kapital (minor, manfiy emas).
    pub capital: Money,
    /// Kafolatli qat'iy summa — bo'lsa, taqiqlanadi.
    pub fixed_return: Option<Money>,
    /// Mudaraba: kapital kiritgan tomonmi (zararni shu tomon ko'taradi).
    pub is_capital_provider: bool,
}

/// Taqsimot. `net` musbat bo'lsa — foyda, manfiy bo'lsa — zarar. Qaytaradi: har bir sherikka qism.
pub fn distribute(
    kind: PartnershipKind,
    net: Money,
    parties: &[PartnerInput],
) -> Result<Vec<Money>, DomainError> {
    if parties.is_empty() {
        return Err(DomainError::InvalidRule);
    }
    if parties.iter().any(|party| party.fixed_return.is_some()) {
        return Err(DomainError::GuaranteedReturnForbidden);
    }
    let share_total = parties
        .iter()
        .fold(0_u64, |acc, party| acc.saturating_add(party.share_bp));
    if share_total != FULL_SHARE_BP {
        return Err(DomainError::ProfitSharesNotHundred);
    }
    let currency = net.currency();
    if net.minor() == 0 {
        return Ok(vec![Money::zero(currency); parties.len()]);
    }

    if net.minor() > 0 {
        return split_by(net, &ratios_of(parties, |party| party.share_bp));
    }

    // Zarar. Mudaraba: kapital kiritgan tomon hammasini ko'taradi (beparvolik yo'q).
    let magnitude = Money::new(
        net.minor().checked_neg().ok_or(DomainError::InvalidRule)?,
        currency,
    );
    match kind {
        PartnershipKind::Mudaraba => {
            let provider = parties
                .iter()
                .position(|party| party.is_capital_provider)
                .ok_or(DomainError::InvalidRule)?;
            Ok(parties
                .iter()
                .enumerate()
                .map(|(index, _)| {
                    if index == provider {
                        net
                    } else {
                        Money::zero(currency)
                    }
                })
                .collect())
        }
        PartnershipKind::Musharaka => {
            let total_capital: u64 = parties
                .iter()
                .map(|party| u64::try_from(party.capital.minor()).unwrap_or(0))
                .fold(0_u64, u64::saturating_add);
            if total_capital == 0 {
                return Err(DomainError::InvalidRule);
            }
            let shares = split_by(
                magnitude,
                &ratios_of(parties, |party| {
                    u64::try_from(party.capital.minor()).unwrap_or(0)
                }),
            )?;
            Ok(shares
                .into_iter()
                .map(|share| negate(share, currency))
                .collect())
        }
    }
}

fn ratios_of(parties: &[PartnerInput], pick: impl Fn(&PartnerInput) -> u64) -> Vec<u64> {
    parties.iter().map(pick).collect()
}

fn split_by(total: Money, ratios: &[u64]) -> Result<Vec<Money>, DomainError> {
    Ok(allocate(total, ratios)?)
}

fn negate(money: Money, currency: money::Currency) -> Money {
    Money::new(-money.minor(), currency)
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn nol_foyda_nol_qism() {
        let parties = [
            PartnerInput {
                share_bp: 5_000,
                capital: uzs(100),
                fixed_return: None,
                is_capital_provider: true,
            },
            PartnerInput {
                share_bp: 5_000,
                capital: uzs(0),
                fixed_return: None,
                is_capital_provider: false,
            },
        ];
        assert_eq!(
            distribute(PartnershipKind::Mudaraba, uzs(0), &parties).expect("nol"),
            vec![uzs(0), uzs(0)]
        );
    }
}
