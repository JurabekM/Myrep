//! 5-qonun: mudoraba va musharaka bo'yicha foyda/zarar taqsimoti (uy/SPEC 2E.1).
//!
//! Ochiq savollar: OQ-D1 (zararni keyingi foydadan qoplash) va OQ-D2 (Hanafiy: ishlamaydigan
//! sherik ulushi) ulamo qaroridan keyin qo'shiladi.
use baraka_money::{allocate, Money, BP_ONE};

use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PartnershipKind {
    Mudaraba,
    Musharaka,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PartnerRole {
    CapitalProvider,
    Worker,
    Both,
}

impl PartnerRole {
    const fn provides_capital(self) -> bool {
        matches!(self, Self::CapitalProvider | Self::Both)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Partner {
    pub id: String,
    pub role: PartnerRole,
    pub profit_share_bp: i64,
    pub capital: Money,
}

/// Mudorabada ishchining beparvoligi yoki shart buzilishi — izoh majburiy.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Negligence {
    pub partner_id: String,
    pub note: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DistributionInput {
    pub kind: PartnershipKind,
    /// Davr natijasi: musbat — foyda, manfiy — zarar.
    pub result: Money,
    pub partners: Vec<Partner>,
    pub negligence: Option<Negligence>,
    /// Kafolatli (qat'iy) daromad urinishini ifodalaydi — har doim rad etiladi.
    pub fixed_return: Option<Money>,
}

fn by_capital(
    total: Money,
    partners: &[Partner],
    eligible: impl Fn(&Partner) -> bool,
) -> Result<Vec<Money>, DomainError> {
    let ratios: Vec<i64> = partners
        .iter()
        .map(|p| {
            if eligible(p) {
                p.capital.minor().max(0)
            } else {
                0
            }
        })
        .collect();
    if ratios.iter().all(|r| *r == 0) {
        return Err(DomainError::on("NO_CAPITAL", "capital"));
    }
    Ok(allocate(total, &ratios)?)
}

/// Har bir sherikka tushadigan ulush (zararda — manfiy), `partners` tartibida.
pub fn distribute(input: &DistributionInput) -> Result<Vec<Money>, DomainError> {
    if input.fixed_return.is_some() {
        return Err(DomainError::on(
            "GUARANTEED_RETURN_FORBIDDEN",
            "fixed_return",
        ));
    }
    if input.partners.len() < 2 {
        return Err(DomainError::on("MIN_TWO_PARTNERS", "partners"));
    }
    for p in &input.partners {
        input.result.compare(&p.capital)?;
        if p.capital.is_negative() {
            return Err(DomainError::on("CAPITAL_NEGATIVE", "capital"));
        }
    }
    let shares: Vec<i64> = input.partners.iter().map(|p| p.profit_share_bp).collect();
    if shares.iter().any(|s| *s < 0) || shares.iter().sum::<i64>() != BP_ONE {
        return Err(DomainError::on("PROFIT_SHARES_NOT_100", "profit_share_bp"));
    }
    if !input.result.is_negative() {
        return Ok(allocate(input.result, &shares)?);
    }
    match input.kind {
        PartnershipKind::Musharaka => by_capital(input.result, &input.partners, |_| true),
        PartnershipKind::Mudaraba => match &input.negligence {
            Some(n) => {
                if n.note.trim().is_empty() {
                    return Err(DomainError::on("NEGLIGENCE_NOTE_REQUIRED", "negligence"));
                }
                let found = input
                    .partners
                    .iter()
                    .any(|p| p.id == n.partner_id && p.role == PartnerRole::Worker);
                if !found {
                    return Err(DomainError::on("NEGLIGENCE_PARTY_NOT_WORKER", "negligence"));
                }
                let ratios: Vec<i64> = input
                    .partners
                    .iter()
                    .map(|p| i64::from(p.id == n.partner_id))
                    .collect();
                Ok(allocate(input.result, &ratios)?)
            }
            None => by_capital(input.result, &input.partners, |p| p.role.provides_capital()),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    fn mudaraba(result: i64) -> DistributionInput {
        DistributionInput {
            kind: PartnershipKind::Mudaraba,
            result: uzs(result),
            partners: vec![
                Partner {
                    id: "sobir".into(),
                    role: PartnerRole::CapitalProvider,
                    profit_share_bp: 5000,
                    capital: uzs(800_000_000),
                },
                Partner {
                    id: "nilufar".into(),
                    role: PartnerRole::Worker,
                    profit_share_bp: 5000,
                    capital: uzs(0),
                },
            ],
            negligence: None,
            fixed_return: None,
        }
    }

    #[test]
    fn documented_vectors() {
        assert_eq!(
            distribute(&mudaraba(300_000_000)),
            Ok(vec![uzs(150_000_000), uzs(150_000_000)])
        );
        assert_eq!(
            distribute(&mudaraba(-200_000_000)),
            Ok(vec![uzs(-200_000_000), uzs(0)])
        );
        let mush = DistributionInput {
            kind: PartnershipKind::Musharaka,
            result: uzs(-300_000_000),
            partners: vec![
                Partner {
                    id: "a".into(),
                    role: PartnerRole::Both,
                    profit_share_bp: 6000,
                    capital: uzs(600_000_000),
                },
                Partner {
                    id: "b".into(),
                    role: PartnerRole::Both,
                    profit_share_bp: 4000,
                    capital: uzs(200_000_000),
                },
            ],
            negligence: None,
            fixed_return: None,
        };
        assert_eq!(
            distribute(&mush),
            Ok(vec![uzs(-225_000_000), uzs(-75_000_000)])
        );
        let mut fixed = mudaraba(300_000_000);
        fixed.fixed_return = Some(uzs(50_000_000));
        assert_eq!(
            distribute(&fixed).map_err(|e| e.code),
            Err("GUARANTEED_RETURN_FORBIDDEN")
        );
    }

    #[test]
    fn negligence_rules() {
        let mut i = mudaraba(-200_000_000);
        i.negligence = Some(Negligence {
            partner_id: "nilufar".into(),
            note: " ".into(),
        });
        assert_eq!(
            distribute(&i).map_err(|e| e.code),
            Err("NEGLIGENCE_NOTE_REQUIRED")
        );
        i.negligence = Some(Negligence {
            partner_id: "nilufar".into(),
            note: "shart buzildi".into(),
        });
        assert_eq!(distribute(&i), Ok(vec![uzs(0), uzs(-200_000_000)]));
        i.negligence = Some(Negligence {
            partner_id: "sobir".into(),
            note: "x".into(),
        });
        assert_eq!(
            distribute(&i).map_err(|e| e.code),
            Err("NEGLIGENCE_PARTY_NOT_WORKER")
        );
    }

    #[test]
    fn shares_must_sum_to_100() {
        let mut i = mudaraba(100);
        i.partners[0].profit_share_bp = 6000;
        assert_eq!(
            distribute(&i).map_err(|e| e.code),
            Err("PROFIT_SHARES_NOT_100")
        );
    }
}
