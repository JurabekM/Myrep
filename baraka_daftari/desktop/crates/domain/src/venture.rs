//! 5-qonun (SPEC 2E.3–2E.5): davr yopilishi (taqsimot + buyout), «Hunardan ishga» stsenariylari va
//! taklif detektori. Sof hisoblar; vektorlar: `venture_settlement`, `craft_payback`, `offer_check`.
use money::{round_half_up, Money, MoneyError};

use crate::{distribute, Outcome, PartnershipError, PartnershipKind, PartyInput};

/// Buyout to'lovi: `payer` ulushidan `due` (qoldiqdan oshmagan) `seller` ulushiga o'tadi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BuyoutDue {
    pub payer: usize,
    pub seller: usize,
    pub due: Money,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Settlement {
    /// Tomonlar tartibida: foyda musbat, zarar manfiy (buyout hisobga olingan).
    pub shares: Vec<Money>,
    pub buyout_applied: Money,
}

/// Davr natijasi: sof foyda = kirim − xarajat (manfiy bo'lishi mumkin).
///
/// # Errors
/// Valyuta mos kelmasa.
pub fn net_result(income: Money, expenses: Money) -> Result<Money, MoneyError> {
    income.checked_sub(expenses)
}

/// Davrni yopishdagi taqsimot (SPEC 2E.3): natija 2E.1 qoidalari bo'yicha bo'linadi; foyda bo'lsa
/// buyout to'lovi to'lovchining ulushidan sotuvchining ulushiga o'tadi (to'lovchining foyda ulushidan
/// oshmaydi). Zararda buyout qo'llanmaydi.
///
/// # Errors
/// Tomonlar/ulushlar yaroqsiz yoki buyout indekslari noto'g'ri bo'lsa.
pub fn settle_period(
    kind: PartnershipKind,
    net: Money,
    parties: &[PartyInput],
    negligence: bool,
    buyout: Option<BuyoutDue>,
) -> Result<Settlement, PartnershipError> {
    let zero = Money::new(0, net.currency());
    let (outcome, amount) = if net.minor() >= 0 {
        (Outcome::Profit, net)
    } else {
        (
            Outcome::Loss,
            Money::new(
                net.minor().checked_neg().ok_or(MoneyError::Overflow)?,
                net.currency(),
            ),
        )
    };
    let mut shares = distribute(kind, outcome, amount, parties, negligence, None)?;
    let mut applied = zero;
    if let (Outcome::Profit, Some(b)) = (outcome, buyout) {
        if b.payer >= shares.len() || b.seller >= shares.len() || b.payer == b.seller {
            return Err(PartnershipError::InvalidParties);
        }
        if b.due.minor() < 0 {
            return Err(PartnershipError::InvalidAmount);
        }
        let take = b.due.minor().min(shares[b.payer].minor().max(0));
        applied = Money::new(take, net.currency());
        shares[b.payer] = shares[b.payer].checked_sub(applied)?;
        shares[b.seller] = shares[b.seller].checked_add(applied)?;
    }
    Ok(Settlement {
        shares,
        buyout_applied: applied,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CraftScenarioInput {
    pub income: Money,
    pub expense: Money,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CraftScenario {
    pub net: Money,
    /// Sheriklik ulushidan keyin (ulush berilmasa — `net`).
    pub net_after_share: Money,
    /// `None` — foyda ≤ 0, qoplanmaydi.
    pub payback_months: Option<u32>,
}

/// «Hunardan ishga» (SPEC 2E.4): har stsenariy uchun sof oylik foyda, ulushdan keyingi foyda va
/// qoplanish muddati (`ceil(boshlang'ich xarajat / foyda)`).
///
/// # Errors
/// Boshlang'ich xarajat manfiy yoki ulush > 10000 bo'lsa.
pub fn craft_payback(
    capex: Money,
    scenarios: &[CraftScenarioInput],
    share_bp: Option<u32>,
) -> Result<Vec<CraftScenario>, PartnershipError> {
    if capex.minor() < 0 || share_bp.is_some_and(|s| s > 10_000) {
        return Err(PartnershipError::InvalidAmount);
    }
    scenarios
        .iter()
        .map(|s| {
            let net = net_result(s.income, s.expense)?;
            let after = match share_bp {
                Some(bp) if net.minor() > 0 => Money::new(
                    round_half_up(i128::from(net.minor()) * i128::from(bp), 10_000)?,
                    net.currency(),
                ),
                _ => net,
            };
            let base = if share_bp.is_some() { after } else { net };
            let payback_months = if capex.minor() == 0 {
                Some(0)
            } else if base.minor() > 0 {
                let m = (i128::from(capex.minor()) + i128::from(base.minor()) - 1)
                    / i128::from(base.minor());
                Some(u32::try_from(m).unwrap_or(u32::MAX))
            } else {
                None
            };
            Ok(CraftScenario {
                net,
                net_after_share: after,
                payback_months,
            })
        })
        .collect()
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OfferAnswers {
    pub guaranteed_profit: bool,
    pub loss_shared: bool,
    pub real_goods_or_work: bool,
    pub requires_recruiting: bool,
    pub pressure_to_hurry: bool,
    pub written_contract: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OfferFlag {
    GuaranteedProfit,
    NoLossSharing,
    NoRealActivity,
    RecruitmentRequired,
    Pressure,
    NoWrittenContract,
}

impl OfferFlag {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::GuaranteedProfit => "GUARANTEED_PROFIT",
            Self::NoLossSharing => "NO_LOSS_SHARING",
            Self::NoRealActivity => "NO_REAL_ACTIVITY",
            Self::RecruitmentRequired => "RECRUITMENT_REQUIRED",
            Self::Pressure => "PRESSURE",
            Self::NoWrittenContract => "NO_WRITTEN_CONTRACT",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Green,
    Yellow,
    Red,
}

impl Verdict {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Green => "GREEN",
            Self::Yellow => "YELLOW",
            Self::Red => "RED",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OfferCheck {
    pub verdict: Verdict,
    pub flags: Vec<OfferFlag>,
}

/// «Kafolatlangan foyda» detektori (SPEC 2E.5): qizil — kafolatlangan foyda, a'zo jalb qilish talabi yoki
/// real mol/ish yo'qligi; sariq — zarar bo'lishilmaydi, shoshiltirish yoki yozma shartnoma yo'q.
#[must_use]
pub fn offer_check(a: OfferAnswers) -> OfferCheck {
    let mut flags = Vec::new();
    if a.guaranteed_profit {
        flags.push(OfferFlag::GuaranteedProfit);
    }
    if !a.loss_shared {
        flags.push(OfferFlag::NoLossSharing);
    }
    if !a.real_goods_or_work {
        flags.push(OfferFlag::NoRealActivity);
    }
    if a.requires_recruiting {
        flags.push(OfferFlag::RecruitmentRequired);
    }
    if a.pressure_to_hurry {
        flags.push(OfferFlag::Pressure);
    }
    if !a.written_contract {
        flags.push(OfferFlag::NoWrittenContract);
    }
    let red = a.guaranteed_profit || a.requires_recruiting || !a.real_goods_or_work;
    let yellow = !a.loss_shared || a.pressure_to_hurry || !a.written_contract;
    let verdict = if red {
        Verdict::Red
    } else if yellow {
        Verdict::Yellow
    } else {
        Verdict::Green
    };
    OfferCheck { verdict, flags }
}
