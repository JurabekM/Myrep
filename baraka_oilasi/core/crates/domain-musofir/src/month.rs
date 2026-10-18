//! M1 — Musofir oy hisoboti (musofir/SPEC 2.1, 3), ish valyutasida.
//!
//! ```text
//! Daromad        = maosh + boshqa daromad
//! Jamg'armaga    = qo'yilgan − olingan                       (sof)
//! Qo'ldagi pul   = boshlang'ich + daromad − xarajat − uyga yuborilgan − komissiya − jamg'armaga
//! Ulush maqsadi  = percent_of(daromad, share_bp);  yetmagani = max(0, maqsad − jamg'armaga)
//! ```
//! Jamg'armadan olish qoldiqdan oshmaydi (yozuvlar tartibida).
//!
//! Vektorlar: `spec/test-vectors/mf_month.json`.
use baraka_money::{percent_of, Money};

use crate::{bp_of, DomainError};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MfKind {
    Salary,
    OtherIncome,
    Expense,
    SentHome,
    FundIn,
    FundOut,
    Opening,
    FundOpening,
}

impl MfKind {
    pub fn parse(s: &str) -> Option<Self> {
        Some(match s {
            "SALARY" => Self::Salary,
            "OTHER_INCOME" => Self::OtherIncome,
            "EXPENSE" => Self::Expense,
            "SENT_HOME" => Self::SentHome,
            "FUND_IN" => Self::FundIn,
            "FUND_OUT" => Self::FundOut,
            "OPENING" => Self::Opening,
            "FUND_OPENING" => Self::FundOpening,
            _ => return None,
        })
    }

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Salary => "SALARY",
            Self::OtherIncome => "OTHER_INCOME",
            Self::Expense => "EXPENSE",
            Self::SentHome => "SENT_HOME",
            Self::FundIn => "FUND_IN",
            Self::FundOut => "FUND_OUT",
            Self::Opening => "OPENING",
            Self::FundOpening => "FUND_OPENING",
        }
    }
}

/// Bitta yozuv; `fee` faqat `SENT_HOME` uchun hisobga olinadi.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MfMove {
    pub kind: MfKind,
    pub amount: Money,
    pub fee: Option<Money>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MfWarning {
    PocketNegative,
    NoShare,
    ShareBelowTarget,
    FundWithdrawn,
}

impl MfWarning {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::PocketNegative => "POCKET_NEGATIVE",
            Self::NoShare => "NO_SHARE",
            Self::ShareBelowTarget => "SHARE_BELOW_TARGET",
            Self::FundWithdrawn => "FUND_WITHDRAWN",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MfMonth {
    pub income: Money,
    pub expenses: Money,
    pub sent_home: Money,
    pub fees: Money,
    pub fund_in: Money,
    pub fund_out: Money,
    pub fund_net: Money,
    /// Oy oxiridagi jamg'arma qoldig'i.
    pub fund_balance: Money,
    /// Oy oxiridagi qo'ldagi pul.
    pub pocket: Money,
    pub share_target: Money,
    pub share_gap: Money,
    /// Daromaddan ulushlar (bp); daromad bo'lmasa `None`.
    pub expenses_bp: Option<i64>,
    pub sent_bp: Option<i64>,
    pub fund_bp: Option<i64>,
    pub warnings: Vec<MfWarning>,
}

/// `opening` — oy boshidagi qo'ldagi pul, `fund_opening` — jamg'arma qoldig'i.
pub fn month_report(
    opening: Money,
    fund_opening: Money,
    share_bp: i64,
    moves: &[MfMove],
) -> Result<MfMonth, DomainError> {
    if !(0..=10_000).contains(&share_bp) {
        return Err(DomainError::on("INVALID_BP", "shareBp"));
    }
    if fund_opening.is_negative() {
        return Err(DomainError::new("AMOUNT_NEGATIVE"));
    }
    let zero = Money::zero(opening.currency());
    let [mut salary, mut other, mut expenses, mut sent, mut fees, mut fund_in, mut fund_out, mut open] =
        [zero; 8];
    let mut fund = fund_opening;
    for m in moves {
        if !m.amount.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        let a = m.amount;
        match m.kind {
            MfKind::Salary => salary = salary.checked_add(a)?,
            MfKind::OtherIncome => other = other.checked_add(a)?,
            MfKind::Expense => expenses = expenses.checked_add(a)?,
            MfKind::SentHome => {
                let fee = m.fee.unwrap_or(zero);
                if fee.is_negative() {
                    return Err(DomainError::on("FEE_NEGATIVE", "fee"));
                }
                sent = sent.checked_add(a)?;
                fees = fees.checked_add(fee)?;
            }
            MfKind::FundIn => {
                fund_in = fund_in.checked_add(a)?;
                fund = fund.checked_add(a)?;
            }
            MfKind::FundOpening => fund = fund.checked_add(a)?,
            MfKind::FundOut => {
                if a.compare(&fund)?.is_gt() {
                    return Err(DomainError::on("FUND_INSUFFICIENT", "amount"));
                }
                fund_out = fund_out.checked_add(a)?;
                fund = fund.checked_sub(a)?;
            }
            MfKind::Opening => open = open.checked_add(a)?,
        }
    }
    let income = salary.checked_add(other)?;
    let fund_net = fund_in.checked_sub(fund_out)?;
    let pocket = opening
        .checked_add(open)?
        .checked_add(income)?
        .checked_sub(expenses)?
        .checked_sub(sent)?
        .checked_sub(fees)?
        .checked_sub(fund_net)?;
    let share_target = percent_of(income, share_bp)?;
    let share_gap = share_target.checked_sub(fund_net)?.clamp_non_negative();
    let mut warnings = Vec::new();
    if pocket.is_negative() {
        warnings.push(MfWarning::PocketNegative);
    }
    if share_target.is_positive() && !fund_net.is_positive() {
        warnings.push(MfWarning::NoShare);
    } else if fund_net.is_positive() && fund_net.compare(&share_target)?.is_lt() {
        warnings.push(MfWarning::ShareBelowTarget);
    }
    if fund_out.is_positive() {
        warnings.push(MfWarning::FundWithdrawn);
    }
    let bp = |x: Money| -> Result<Option<i64>, DomainError> {
        if income.is_positive() {
            bp_of(x.minor(), income.minor()).map(Some)
        } else {
            Ok(None)
        }
    };
    Ok(MfMonth {
        income,
        expenses,
        sent_home: sent,
        fees,
        fund_in,
        fund_out,
        fund_net,
        fund_balance: fund,
        pocket,
        share_target,
        share_gap,
        expenses_bp: bp(expenses)?,
        sent_bp: bp(sent.checked_add(fees)?)?,
        fund_bp: bp(fund_net)?,
        warnings,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn k(minor: i64) -> Money {
        Money::new(minor, Currency::Krw)
    }

    fn mv(kind: MfKind, a: i64) -> MfMove {
        MfMove {
            kind,
            amount: k(a),
            fee: None,
        }
    }

    #[test]
    fn rustam_share_met() {
        let moves = [
            mv(MfKind::Salary, 2_600_000),
            mv(MfKind::Expense, 810_000),
            MfMove {
                kind: MfKind::SentHome,
                amount: k(1_200_000),
                fee: Some(k(5_000)),
            },
            mv(MfKind::FundIn, 520_000),
        ];
        let r = month_report(k(150_000), k(0), 2_000, &moves).unwrap();
        assert_eq!(r.pocket, k(215_000));
        assert_eq!(r.share_gap, k(0));
        assert_eq!(r.sent_bp, Some(4_635));
        assert!(r.warnings.is_empty());
    }

    #[test]
    fn withdrawal_cannot_exceed_fund() {
        let moves = [mv(MfKind::FundIn, 50), mv(MfKind::FundOut, 151)];
        let e = month_report(k(0), k(100), 2_000, &moves).unwrap_err();
        assert_eq!(e.code, "FUND_INSUFFICIENT");
    }
}
