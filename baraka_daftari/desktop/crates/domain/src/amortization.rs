//! 4-qonun (SPEC 2D.1–2D.2, 2D.9): amortizatsiya simulyatori, 70/20/10 taqsimoti va bir necha qarzni
//! yopish rejasi. Sof hisoblar; vektorlar: `amortization`, `debt_recovery_split`, `payoff_plan`.
//!
//! Annuitet to'lovi `(1+r)^n` ni aniq kasr sifatida talab qiladi (`i128` ga sig'maydi), shuning uchun
//! `num-bigint` ishlatiladi (u `typst` bog'liqliklari orqali allaqachon lock faylda bor).

use money::{allocate, round_half_up, Money, MoneyError};
use num_bigint::BigUint;

/// Jadval oylarining yuqori chegarasi (cheksiz tsiklga qarshi).
pub const MAX_MONTHS: u32 = 1200;

#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum PlanError {
    #[error("summa noto'g'ri")]
    InvalidAmount,
    #[error("oylar soni 1 dan 1200 gacha")]
    InvalidMonths,
    #[error("taqsimot yig'indisi 100% bo'lishi kerak")]
    InvalidSplit,
    #[error("jamg'arma ulushi kamida 1% bo'lishi kerak")]
    SavingsTooLow,
    #[error("tartib noto'g'ri")]
    InvalidOrder,
    #[error(transparent)]
    Money(#[from] MoneyError),
}

impl PlanError {
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::InvalidAmount => "INVALID_AMOUNT",
            Self::InvalidMonths => "INVALID_MONTHS",
            Self::InvalidSplit => "INVALID_SPLIT",
            Self::SavingsTooLow => "SAVINGS_TOO_LOW",
            Self::InvalidOrder => "INVALID_ORDER",
            Self::Money(_) => "MONEY",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoanKind {
    Annuity,
    Differentiated,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ScheduleRow {
    pub month: u32,
    pub interest: Money,
    pub principal: Money,
    pub extra: Money,
    pub balance: Money,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Amortization {
    /// Annuitetda — oylik to'lov; differensialda — birinchi oy to'lovi.
    pub first_payment: Money,
    pub months: u32,
    pub total_interest: Money,
    pub schedule: Vec<ScheduleRow>,
}

/// Oylik foiz stavkasi `bp / 120000` (yillik bp / 12 / 10000).
const RATE_DEN: i128 = 120_000;

/// Annuitet to'lovi: `round_half_up(P·r / (1 − (1+r)^−n))`, aniq kasrda.
fn annuity_payment(principal: i64, annual_bp: u32, n: u32) -> Result<i64, PlanError> {
    if annual_bp == 0 {
        return Ok(round_half_up(i128::from(principal), i128::from(n))?);
    }
    let a = BigUint::from(120_000_u64 + u64::from(annual_bp));
    let b = BigUint::from(120_000_u64);
    let an = a.pow(n);
    let bn = b.pow(n);
    let num = BigUint::from(principal.unsigned_abs()) * BigUint::from(annual_bp) * &an;
    let den = BigUint::from(120_000_u64) * (&an - &bn);
    // round_half_up = (2·num + den) / (2·den)
    let q = (num * 2_u32 + &den) / (den * 2_u32);
    i64::try_from(q).map_err(|_| PlanError::Money(MoneyError::Overflow))
}

/// Muddat chegarasi (50 yil) — `months_to_repay` uchun.
pub const MAX_REPAY_MONTHS: u32 = 600;

/// Oylik imkoniyatga sig'adigan eng kichik muddat (oy): annuitet to'lovi (`amortize` bilan bir xil
/// formula) `capacity` dan oshmaydigan eng kichik `n` (1..=600). Qarz `0` bo'lsa `0` oy.
///
/// # Errors
/// Imkoniyat ≤ 0, qarz < 0 yoki 600 oyda ham sig'masa ([`PlanError::InvalidMonths`]).
pub fn months_to_repay(debt: Money, annual_bp: u32, capacity: Money) -> Result<u32, PlanError> {
    if capacity.minor() <= 0 || debt.minor() < 0 {
        return Err(PlanError::InvalidAmount);
    }
    if debt.minor() == 0 {
        return Ok(0);
    }
    let fits = |n: u32| -> Result<bool, PlanError> {
        Ok(annuity_payment(debt.minor(), annual_bp, n)? <= capacity.minor())
    };
    // To'lov n ortishi bilan kamaymaydi o'smaydi → binar qidiruv.
    if !fits(MAX_REPAY_MONTHS)? {
        return Err(PlanError::InvalidMonths);
    }
    let (mut lo, mut hi) = (1_u32, MAX_REPAY_MONTHS);
    while lo < hi {
        let mid = lo + (hi - lo) / 2;
        if fits(mid)? {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    Ok(lo)
}

/// Jadvalni simulyatsiya qiladi (muddatni qisqartirish: oylik to'lov o'zgarmaydi, `extra` har oy qo'shiladi).
///
/// # Errors
/// Asosiy ≤ 0, oylar 1..=1200 emas, `extra` < 0 yoki hisob sig'masa.
pub fn amortize(
    kind: LoanKind,
    principal: Money,
    annual_bp: u32,
    months: u32,
    extra: Money,
) -> Result<Amortization, PlanError> {
    if principal.minor() <= 0 || extra.minor() < 0 {
        return Err(PlanError::InvalidAmount);
    }
    if months == 0 || months > MAX_MONTHS {
        return Err(PlanError::InvalidMonths);
    }
    let cur = principal.currency();
    let payment = match kind {
        LoanKind::Annuity => Some(annuity_payment(principal.minor(), annual_bp, months)?),
        LoanKind::Differentiated => None,
    };
    let planned = match kind {
        LoanKind::Differentiated => Some(allocate(principal, &vec![1_u64; months as usize])?),
        LoanKind::Annuity => None,
    };
    let mut balance = principal.minor();
    let mut schedule = Vec::new();
    let mut total_interest: i64 = 0;
    let mut first_payment = 0;
    let mut month = 0_u32;
    while balance > 0 {
        month += 1;
        if month > MAX_MONTHS {
            return Err(PlanError::InvalidMonths);
        }
        let interest = round_half_up(i128::from(balance) * i128::from(annual_bp), RATE_DEN)?;
        let last = month >= months;
        let principal_part = match (payment, &planned) {
            (Some(p), _) => {
                let x = p - interest;
                if last || x >= balance {
                    balance
                } else {
                    x
                }
            }
            (None, Some(plan)) => {
                if last {
                    balance
                } else {
                    plan.get(month as usize - 1)
                        .map_or(balance, |m| m.minor().min(balance))
                }
            }
            (None, None) => balance,
        };
        // Qoldiq va to'lov manfiy bo'lib ketmasligi uchun (juda kichik P va katta stavka).
        let principal_part = principal_part.clamp(0, balance);
        balance -= principal_part;
        let ex = extra.minor().min(balance);
        balance -= ex;
        total_interest = total_interest
            .checked_add(interest)
            .ok_or(MoneyError::Overflow)?;
        if month == 1 {
            first_payment = principal_part + interest;
        }
        schedule.push(ScheduleRow {
            month,
            interest: Money::new(interest, cur),
            principal: Money::new(principal_part, cur),
            extra: Money::new(ex, cur),
            balance: Money::new(balance, cur),
        });
    }
    Ok(Amortization {
        first_payment: Money::new(first_payment, cur),
        months: month,
        total_interest: Money::new(total_interest, cur),
        schedule,
    })
}

/// 70/20/10 (yoki oila sozlagan) taqsimot.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RecoverySplit {
    pub living_bp: u32,
    pub extra_bp: u32,
    pub savings_bp: u32,
}

impl RecoverySplit {
    /// Standart: 70 / 20 / 10.
    pub const DEFAULT: Self = Self {
        living_bp: 7_000,
        extra_bp: 2_000,
        savings_bp: 1_000,
    };
    /// Jamg'arma ulushining eng kichik qiymati (1%): 0 ga tushirilmaydi.
    pub const MIN_SAVINGS_BP: u32 = 100;

    /// # Errors
    /// Yig'indi 10000 emas yoki jamg'arma < 1% bo'lsa.
    pub fn validate(self) -> Result<Self, PlanError> {
        if self.living_bp + self.extra_bp + self.savings_bp != 10_000 {
            return Err(PlanError::InvalidSplit);
        }
        if self.savings_bp < Self::MIN_SAVINGS_BP {
            return Err(PlanError::SavingsTooLow);
        }
        Ok(self)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SplitAmounts {
    pub living: Money,
    pub extra: Money,
    pub savings: Money,
}

/// Summani `living / extra / savings` ga bo'ladi (largest remainder: yig'indi aniq saqlanadi).
///
/// # Errors
/// Taqsimot yaroqsiz yoki summa manfiy bo'lsa.
pub fn recovery_split(total: Money, split: RecoverySplit) -> Result<SplitAmounts, PlanError> {
    let s = split.validate()?;
    if total.minor() < 0 {
        return Err(PlanError::InvalidAmount);
    }
    let parts = allocate(
        total,
        &[
            u64::from(s.living_bp),
            u64::from(s.extra_bp),
            u64::from(s.savings_bp),
        ],
    )?;
    Ok(SplitAmounts {
        living: parts[0],
        extra: parts[1],
        savings: parts[2],
    })
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlanDebt {
    /// Qolgan to'lov qatorlari: indeks — hozirdan boshlab oy (0 — joriy davr).
    pub rows: Vec<Money>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PayoffPlan {
    /// Hamma qarz yopilgan oy (1 dan). Qarz yo'q bo'lsa `0`.
    pub months: u32,
    /// Har bir qarz yopilgan oy (kiritilgan tartibda).
    pub per_debt_months: Vec<u32>,
}

/// Bir necha qarzni yopish rejasi (oyma-oy). Har oy jadvaldagi to'lovlar to'lanadi; so'ng hovuz
/// (`monthly_extra` + 0-oyda `one_off` + `snowball` bo'lsa oldin yopilgan qarzlarning shu oydagi
/// jadval qatorlari) `order` (ustuvorlik) bo'yicha qoldiqqa yo'naltiriladi.
///
/// # Errors
/// Manfiy summa, tartib indeksi noto'g'ri yoki hisob sig'masa.
pub fn payoff_plan(
    debts: &[PlanDebt],
    order: &[usize],
    monthly_extra: Money,
    one_off: Money,
    snowball: bool,
) -> Result<PayoffPlan, PlanError> {
    if monthly_extra.minor() < 0 || one_off.minor() < 0 {
        return Err(PlanError::InvalidAmount);
    }
    if order.iter().any(|&i| i >= debts.len()) {
        return Err(PlanError::InvalidOrder);
    }
    let row_at = |d: &PlanDebt, t: usize| d.rows.get(t).map_or(0, |m| m.minor());
    let mut bal: Vec<i64> = Vec::with_capacity(debts.len());
    for d in debts {
        let mut sum: i64 = 0;
        for r in &d.rows {
            if r.minor() < 0 {
                return Err(PlanError::InvalidAmount);
            }
            sum = sum.checked_add(r.minor()).ok_or(MoneyError::Overflow)?;
        }
        bal.push(sum);
    }
    let mut closed: Vec<Option<u32>> = bal.iter().map(|&b| (b == 0).then_some(0)).collect();
    let mut t: usize = 0;
    while bal.iter().any(|&b| b > 0) {
        if t >= MAX_MONTHS as usize {
            return Err(PlanError::InvalidMonths);
        }
        let mut pool = monthly_extra.minor();
        if t == 0 {
            pool = pool
                .checked_add(one_off.minor())
                .ok_or(MoneyError::Overflow)?;
        }
        if snowball {
            for (i, d) in debts.iter().enumerate() {
                if closed[i].is_some_and(|c| c as usize <= t) {
                    pool = pool.checked_add(row_at(d, t)).ok_or(MoneyError::Overflow)?;
                }
            }
        }
        for (i, d) in debts.iter().enumerate() {
            if bal[i] > 0 {
                bal[i] -= row_at(d, t).min(bal[i]);
            }
        }
        for &i in order {
            if bal[i] > 0 && pool > 0 {
                let a = pool.min(bal[i]);
                bal[i] -= a;
                pool -= a;
            }
        }
        let month = u32::try_from(t + 1).map_err(|_| PlanError::InvalidMonths)?;
        for i in 0..debts.len() {
            if bal[i] == 0 && closed[i].is_none() {
                closed[i] = Some(month);
            }
        }
        t += 1;
    }
    let per_debt_months: Vec<u32> = closed.into_iter().map(|c| c.unwrap_or(0)).collect();
    Ok(PayoffPlan {
        months: per_debt_months.iter().copied().max().unwrap_or(0),
        per_debt_months,
    })
}

/// Yopish tartibi uchun qarz haqida ma'lumot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OrderItem {
    pub id: String,
    pub creditor_type: crate::CreditorType,
    /// Ustama / asosiy, bp (0 — ustamasiz).
    pub markup_bp: u32,
    pub next_due: Option<time::Date>,
    /// Qo'lda belgilangan tartib (kichik — avval).
    pub priority: Option<u32>,
}

/// Standart strategiya (SPEC 2D.2, mahsulot taklifi): qo'lda belgilanganlar birinchi; so'ng ustamali
/// (ribo) qarzlar — eng yuqori ustamalisidan; so'ng qarindosh/do'stlarning foizsiz qarzlari — muddati
/// yaqinidan; qolganlar muddat bo'yicha.
#[must_use]
pub fn closing_order(items: &[OrderItem]) -> Vec<String> {
    use crate::CreditorType::{Friend, Relative};
    let rank = |i: &OrderItem| -> (u8, u32, u32, time::Date) {
        let due = i.next_due.unwrap_or(time::Date::MAX);
        if let Some(p) = i.priority {
            return (0, p, 0, due);
        }
        if i.markup_bp > 0 {
            return (1, u32::MAX - i.markup_bp, 0, due);
        }
        if matches!(i.creditor_type, Relative | Friend) {
            return (2, 0, 0, due);
        }
        (3, 0, 0, due)
    };
    let mut v: Vec<&OrderItem> = items.iter().collect();
    v.sort_by(|a, b| rank(a).cmp(&rank(b)).then_with(|| a.id.cmp(&b.id)));
    v.into_iter().map(|i| i.id.clone()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    #[test]
    fn schedule_always_ends_at_zero_and_sums_up() {
        let a = amortize(LoanKind::Annuity, uzs(3_900_000_000), 2_400, 14, uzs(0)).unwrap();
        assert_eq!(a.schedule.last().unwrap().balance.minor(), 0);
        let principal: i64 = a
            .schedule
            .iter()
            .map(|r| r.principal.minor() + r.extra.minor())
            .sum();
        assert_eq!(principal, 3_900_000_000);
    }

    #[test]
    fn zero_rate_is_even_split_and_invalid_inputs_are_rejected() {
        let a = amortize(LoanKind::Annuity, uzs(120), 0, 12, uzs(0)).unwrap();
        assert_eq!((a.first_payment.minor(), a.months), (10, 12));
        assert!(amortize(LoanKind::Annuity, uzs(0), 100, 3, uzs(0)).is_err());
        assert!(amortize(LoanKind::Annuity, uzs(10), 100, 0, uzs(0)).is_err());
        assert!(amortize(LoanKind::Annuity, uzs(10), 100, 1201, uzs(0)).is_err());
        assert!(amortize(LoanKind::Annuity, uzs(10), 100, 3, uzs(-1)).is_err());
    }

    #[test]
    fn long_terms_do_not_overflow() {
        let a = amortize(
            LoanKind::Annuity,
            uzs(1_000_000_000_000_000),
            3_600,
            600,
            uzs(0),
        )
        .unwrap();
        assert_eq!(a.months, 600);
    }

    #[test]
    fn closing_order_puts_markup_first_then_relatives_by_due() {
        use crate::CreditorType::{Bank, Friend, Relative, Shop};
        use time::macros::date;
        let it = |id: &str, t, bp, due: Option<time::Date>, p| OrderItem {
            id: id.into(),
            creditor_type: t,
            markup_bp: bp,
            next_due: due,
            priority: p,
        };
        let items = vec![
            it("bank-low", Bank, 500, Some(date!(2026 - 12 - 01)), None),
            it("friend-late", Friend, 0, Some(date!(2027 - 03 - 01)), None),
            it("shop-high", Shop, 3_000, Some(date!(2027 - 01 - 01)), None),
            it("rel-soon", Relative, 0, Some(date!(2026 - 11 - 01)), None),
            it("plain", Bank, 0, None, None),
            it("manual", Bank, 0, None, Some(1)),
        ];
        assert_eq!(
            closing_order(&items),
            [
                "manual",
                "shop-high",
                "bank-low",
                "rel-soon",
                "friend-late",
                "plain"
            ]
        );
    }

    #[test]
    fn savings_cannot_be_zeroed() {
        let s = RecoverySplit {
            living_bp: 7_000,
            extra_bp: 3_000,
            savings_bp: 0,
        };
        assert_eq!(s.validate(), Err(PlanError::SavingsTooLow));
        assert_eq!(
            RecoverySplit::DEFAULT.validate().unwrap(),
            RecoverySplit::DEFAULT
        );
    }
}
