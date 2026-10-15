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

/// Tuzilma qoidasi (SPEC 2E.1, D12): `MUDARABA` — kapital faqat bir tomondan, kamida bitta mehnat tomoni;
/// `MUSHARAKA` — kamida ikki tomon kapital kiritadi. Kafolatli summa har qanday turda taqiq.
pub fn validate_structure(
    kind: PartnershipKind,
    parties: &[PartnerInput],
) -> Result<(), DomainError> {
    if parties.len() < 2 {
        return Err(DomainError::PartnershipStructureInvalid);
    }
    if parties.iter().any(|party| party.fixed_return.is_some()) {
        return Err(DomainError::GuaranteedReturnForbidden);
    }
    let with_capital = parties
        .iter()
        .filter(|party| party.capital.minor() > 0)
        .count();
    let ok = match kind {
        PartnershipKind::Mudaraba => with_capital == 1 && with_capital < parties.len(),
        PartnershipKind::Musharaka => with_capital >= 2,
    };
    if ok {
        Ok(())
    } else {
        Err(DomainError::PartnershipStructureInvalid)
    }
}

/// Kamayib boruvchi sheriklik (buyout) qadami: mehnat egasi kapital egasining ulushini bo'lib sotib oladi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuyoutStep {
    /// Tartib (1 dan).
    pub seq: u32,
    /// To'lov sanasi.
    pub due_on: time::Date,
    /// To'lov summasi.
    pub amount: Money,
    /// Shu to'lovdan keyin kapital egasida qolgan ulush (bp).
    pub remaining_share_bp: u64,
}

/// Buyout jadvali: `total` teng bo'laklarga (`allocate`, yig'indi aniq), sanalar oyma-oy `start` dan.
pub fn buyout_schedule(
    total: Money,
    months: u32,
    start: time::Date,
) -> Result<Vec<BuyoutStep>, DomainError> {
    if total.minor() <= 0 {
        return Err(DomainError::AmountNotPositive);
    }
    if months == 0 {
        return Err(DomainError::InvalidRule);
    }
    let parts = allocate(total, &vec![1; months as usize])?;
    let mut steps = Vec::with_capacity(parts.len());
    let mut paid: i128 = 0;
    for (index, amount) in parts.into_iter().enumerate() {
        paid += i128::from(amount.minor());
        let remaining = i128::from(total.minor()) - paid;
        let remaining_share_bp = money::round_half_up_div(
            remaining * i128::from(FULL_SHARE_BP),
            i128::from(total.minor()),
        )?;
        steps.push(BuyoutStep {
            seq: u32::try_from(index + 1).unwrap_or(u32::MAX),
            due_on: crate::loans::add_months(start, i64::try_from(index).unwrap_or(0))?,
            amount,
            remaining_share_bp: u64::try_from(remaining_share_bp).unwrap_or(0),
        });
    }
    Ok(steps)
}

#[cfg(test)]
mod structure_tests {
    use super::*;
    use money::Currency;
    use time::macros::date;

    fn party(capital: i64) -> PartnerInput {
        PartnerInput {
            share_bp: 5_000,
            capital: Money::new(capital, Currency::Uzs),
            fixed_return: None,
            is_capital_provider: capital > 0,
        }
    }

    #[test]
    fn mudaraba_bitta_kapital_musharaka_ikki_kapital() {
        assert!(validate_structure(PartnershipKind::Mudaraba, &[party(100), party(0)]).is_ok());
        assert_eq!(
            validate_structure(PartnershipKind::Mudaraba, &[party(100), party(50)]),
            Err(DomainError::PartnershipStructureInvalid)
        );
        assert!(validate_structure(PartnershipKind::Musharaka, &[party(100), party(50)]).is_ok());
        assert_eq!(
            validate_structure(PartnershipKind::Musharaka, &[party(100), party(0)]),
            Err(DomainError::PartnershipStructureInvalid)
        );
        let mut fixed = party(100);
        fixed.fixed_return = Some(Money::new(10, Currency::Uzs));
        assert_eq!(
            validate_structure(PartnershipKind::Mudaraba, &[fixed, party(0)]),
            Err(DomainError::GuaranteedReturnForbidden)
        );
    }

    #[test]
    fn buyout_jadvali_yigindisi_aniq_va_ulush_kamayadi() {
        let steps = buyout_schedule(
            Money::new(1_000_000_000, Currency::Uzs),
            3,
            date!(2026 - 11 - 15),
        )
        .expect("jadval");
        assert_eq!(steps.len(), 3);
        let sum: i64 = steps.iter().map(|s| s.amount.minor()).sum();
        assert_eq!(sum, 1_000_000_000);
        assert_eq!(steps[0].remaining_share_bp, 6_667);
        assert_eq!(steps[1].remaining_share_bp, 3_333);
        assert_eq!(steps[2].remaining_share_bp, 0);
        assert_eq!(steps[2].due_on, date!(2027 - 01 - 15));
    }
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
