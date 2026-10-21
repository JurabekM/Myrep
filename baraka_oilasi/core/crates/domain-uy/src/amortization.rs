//! 4-qonun: qarz to'lov jadvali simulyatori (uy/DESKTOP_PROMPT 5.3, BARAKA_OILASI 5.8).
//!
//! «Muddatni qisqartirish» rejimi: oylik to'lov o'zgarmaydi, qo'shimcha to'lov qoldiqdan
//! ayriladi. FIXED_MARKUP va MANUAL jadval turlari U9 vazifasida qo'shiladi.
use baraka_money::{allocate_minor, round_half_up, Money};
use num_bigint::BigInt;
use num_traits::{Signed, ToPrimitive};

use crate::DomainError;

/// Yillik stavka bp dan oylik stavka maxraji: r = bp / (10000 × 12).
const MONTHLY_DEN: i64 = 120_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ScheduleKind {
    /// Teng oylik to'lov.
    Annuity,
    /// Asosiy qarz teng bo'laklarda, foiz qoldiqqa.
    Differentiated,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LoanTerms {
    pub principal: Money,
    pub annual_bp: i64,
    pub months: u32,
    pub kind: ScheduleKind,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ScheduleRow {
    pub month: u32,
    pub interest: Money,
    pub principal: Money,
    pub extra: Money,
    pub balance: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Schedule {
    /// Annuitetda — o'zgarmas oylik to'lov; differensialda — birinchi oy to'lovi.
    pub payment: Money,
    pub rows: Vec<ScheduleRow>,
    pub total_interest: Money,
    pub total_paid: Money,
}

impl Schedule {
    pub fn months(&self) -> u32 {
        self.rows.last().map_or(0, |r| r.month)
    }
}

/// Odatiy va tezlashtirilgan grafikni solishtirish: «N oy erta», «X so'm tejaldi».
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Acceleration {
    pub months_saved: u32,
    pub interest_saved: Money,
}

fn overflow() -> DomainError {
    DomainError::new("OVERFLOW")
}

fn to_i64(v: i128) -> Result<i64, DomainError> {
    i64::try_from(v).map_err(|_| overflow())
}

/// `round_half_up(P·r / (1 − (1+r)^−n)) = round_half_up(P·bp·A^n / (B·(A^n − B^n)))`,
/// bu yerda `B = 120000`, `A = B + bp`. Katta darajalar uchun `BigInt`.
pub(crate) fn annuity_payment(
    principal: i64,
    annual_bp: i64,
    months: u32,
) -> Result<i64, DomainError> {
    if annual_bp == 0 {
        return to_i64(round_half_up(i128::from(principal), i128::from(months))?);
    }
    let b = BigInt::from(MONTHLY_DEN);
    let a = BigInt::from(MONTHLY_DEN + annual_bp);
    let an = num_traits::pow(a, months as usize);
    let bn = num_traits::pow(b.clone(), months as usize);
    let num = BigInt::from(principal) * BigInt::from(annual_bp) * &an;
    let den = b * (an - bn);
    // Musbat sonlar uchun half-up: floor((2·num + den) / (2·den)).
    let two = BigInt::from(2);
    let q: BigInt = (&two * num + &den) / (&two * den);
    if q.is_negative() {
        return Err(overflow());
    }
    q.to_i64().ok_or_else(overflow)
}

fn validate(terms: &LoanTerms, extra: Money) -> Result<(), DomainError> {
    if !terms.principal.is_positive() {
        return Err(DomainError::on("PRINCIPAL_NOT_POSITIVE", "principal"));
    }
    if terms.months == 0 || terms.months > 600 {
        return Err(DomainError::on("INVALID_TERM", "months"));
    }
    if !(0..=100_000).contains(&terms.annual_bp) {
        return Err(DomainError::on("INVALID_RATE", "annual_bp"));
    }
    if extra.is_negative() {
        return Err(DomainError::on("EXTRA_NEGATIVE", "extra"));
    }
    terms.principal.compare(&extra)?;
    Ok(())
}

/// Oyma-oy jadval. `extra_per_month` — har oy odatiy to'lovdan tashqari qo'shimcha to'lov.
pub fn simulate(terms: &LoanTerms, extra_per_month: Money) -> Result<Schedule, DomainError> {
    validate(terms, extra_per_month)?;
    let cur = terms.principal.currency();
    let p = terms.principal.minor();
    let n = terms.months;
    let annuity = annuity_payment(p, terms.annual_bp, n)?;
    let planned_principal = match terms.kind {
        ScheduleKind::Annuity => Vec::new(),
        ScheduleKind::Differentiated => allocate_minor(p, &vec![1; n as usize])?,
    };

    let mut balance = p;
    let mut rows = Vec::new();
    let mut total_interest: i64 = 0;
    let mut total_paid: i64 = 0;
    let mut month = 0u32;
    let mut first_payment = 0i64;
    while balance > 0 {
        month += 1;
        let interest = to_i64(round_half_up(
            i128::from(balance) * i128::from(terms.annual_bp),
            i128::from(MONTHLY_DEN),
        )?)?;
        let mut principal = match terms.kind {
            ScheduleKind::Annuity => annuity - interest,
            ScheduleKind::Differentiated => planned_principal
                .get(month as usize - 1)
                .copied()
                .unwrap_or(balance),
        };
        if principal >= balance || month >= n {
            principal = balance;
        }
        // Juda yuqori stavkada annuitet foizni ham qoplamasa, asosiy qarz manfiy bo'lmaydi.
        principal = principal.max(0);
        balance -= principal;
        let extra = extra_per_month.minor().min(balance);
        balance -= extra;
        if month == 1 {
            first_payment = interest + principal;
        }
        total_interest = total_interest.checked_add(interest).ok_or_else(overflow)?;
        total_paid = total_paid
            .checked_add(interest + principal + extra)
            .ok_or_else(overflow)?;
        rows.push(ScheduleRow {
            month,
            interest: Money::new(interest, cur),
            principal: Money::new(principal, cur),
            extra: Money::new(extra, cur),
            balance: Money::new(balance, cur),
        });
    }
    let payment = match terms.kind {
        ScheduleKind::Annuity => annuity,
        ScheduleKind::Differentiated => first_payment,
    };
    Ok(Schedule {
        payment: Money::new(payment, cur),
        rows,
        total_interest: Money::new(total_interest, cur),
        total_paid: Money::new(total_paid, cur),
    })
}

pub fn compare(base: &Schedule, accelerated: &Schedule) -> Result<Acceleration, DomainError> {
    Ok(Acceleration {
        months_saved: base.months().saturating_sub(accelerated.months()),
        interest_saved: base
            .total_interest
            .checked_sub(accelerated.total_interest)?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use baraka_money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    fn anvar() -> LoanTerms {
        LoanTerms {
            principal: uzs(3_900_000_000),
            annual_bp: 2400,
            months: 14,
            kind: ScheduleKind::Annuity,
        }
    }

    #[test]
    fn documented_vectors() {
        for (extra, months, interest) in [
            (0, 14, 610_067_573),
            (160_000_000, 9, 397_018_667),
            (240_000_000, 8, 341_756_885),
        ] {
            let s = simulate(&anvar(), uzs(extra)).unwrap();
            assert_eq!(s.payment, uzs(322_147_684));
            assert_eq!(s.months(), months);
            assert_eq!(s.total_interest, uzs(interest));
            assert_eq!(s.rows.last().map(|r| r.balance), Some(uzs(0)));
        }
        let s = simulate(&anvar(), uzs(160_000_000)).unwrap();
        assert_eq!(
            s.rows[8],
            ScheduleRow {
                month: 9,
                interest: uzs(8_624_259),
                principal: uzs(313_523_425),
                extra: uzs(117_689_511),
                balance: uzs(0)
            }
        );
    }

    #[test]
    fn acceleration() {
        let base = simulate(&anvar(), uzs(0)).unwrap();
        let fast = simulate(&anvar(), uzs(160_000_000)).unwrap();
        let a = compare(&base, &fast).unwrap();
        assert_eq!(a.months_saved, 5);
        assert_eq!(a.interest_saved, uzs(213_048_906));
    }

    #[test]
    fn zero_rate_and_differentiated() {
        let t = LoanTerms {
            principal: uzs(1_000),
            annual_bp: 0,
            months: 3,
            kind: ScheduleKind::Annuity,
        };
        let s = simulate(&t, uzs(0)).unwrap();
        assert_eq!(s.total_interest, uzs(0));
        assert_eq!(s.total_paid, uzs(1_000));
        let d = LoanTerms {
            kind: ScheduleKind::Differentiated,
            annual_bp: 2400,
            ..t
        };
        let s = simulate(&d, uzs(0)).unwrap();
        assert_eq!(
            s.rows
                .iter()
                .map(|r| r.principal.minor())
                .collect::<Vec<_>>(),
            vec![334, 333, 333]
        );
        assert_eq!(
            s.rows
                .iter()
                .map(|r| r.interest.minor())
                .collect::<Vec<_>>(),
            vec![20, 13, 7]
        );
    }

    #[test]
    fn long_terms_do_not_overflow() {
        let t = LoanTerms {
            principal: uzs(50_000_000_000),
            annual_bp: 1800,
            months: 360,
            kind: ScheduleKind::Annuity,
        };
        let s = simulate(&t, uzs(0)).unwrap();
        assert_eq!(s.months(), 360);
        assert_eq!(s.rows.last().map(|r| r.balance), Some(uzs(0)));
    }

    #[test]
    fn validation() {
        let mut t = anvar();
        t.months = 0;
        assert!(simulate(&t, uzs(0)).is_err());
        assert!(simulate(&anvar(), uzs(-1)).is_err());
        assert!(simulate(&anvar(), Money::new(1, Currency::Usd)).is_err());
    }
}
