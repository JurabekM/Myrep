//! 4-qonun: qarzdan chiqish rejalovchisi va «Qarzsiz kun» (uy/SPEC 2D.2, 2D.9; vektorlar:
//! `payoff_projection`, `payoff_plan`).
//!
//! * **Holat** to'lovlar tarixidan qayta hisoblanadi. Bank qarzida (`ANNUITY`, `DIFFERENTIATED`)
//!   odatiy to'lovlar jadval bo'yicha oyma-oy yopiladi, muddatidan oldingi to'lov o'z sanasida
//!   asosiy qarzni kamaytiradi («muddatni qisqartirish»: oylik to'lov o'zgarmaydi). To'liq
//!   bo'lmagan oxirgi odatiy to'lov ham asosiy qarzga yoziladi (taxminiy).
//!   Ustamali va foizsiz rejada odatiy to'lov reja boshidan, muddatidan oldingisi oxiridan yopiladi.
//! * **Prognoz** kalendar oylari bo'yicha: har oyda avval shu oyga to'g'ri kelgan odatiy to'lovlar
//!   (o'tib ketganlari birinchi oyda), keyin qo'shimcha to'lov — tartib bo'yicha birinchi ochiq
//!   qarzga. Jarima/komissiya qo'shimcha to'lov ustiga `fee_bp` bilan qo'shiladi.
use baraka_money::{allocate_minor, percent_of, round_half_up, Currency, Money};
use chrono::{Datelike, Months, NaiveDate};

use crate::amortization::annuity_payment;
use crate::debt::{remaining_lines, PlanLine};
use crate::DomainError;

/// 100 yil: bundan uzoq prognoz — xato (masalan, to'lov foizni ham qoplamasa).
pub const MAX_WINDOWS: u32 = 1_200;
const MONTHLY_DEN: i128 = 120_000;

fn overflow() -> DomainError {
    DomainError::new("OVERFLOW")
}

fn add_months(d: NaiveDate, k: u32) -> Result<NaiveDate, DomainError> {
    d.checked_add_months(Months::new(k))
        .ok_or(DomainError::new("INVALID_DATE"))
}

fn month_start(d: NaiveDate) -> Result<NaiveDate, DomainError> {
    NaiveDate::from_ymd_opt(d.year(), d.month(), 1).ok_or(DomainError::new("INVALID_DATE"))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Payment {
    pub date: NaiveDate,
    pub amount: Money,
    /// Muddatidan oldingi (qo'shimcha) to'lov.
    pub prepayment: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BankTerms {
    pub differentiated: bool,
    pub principal: Money,
    pub annual_bp: i64,
    pub months: u32,
    pub first_date: NaiveDate,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Amortizing {
    cur: Currency,
    differentiated: bool,
    bp: i64,
    first: NaiveDate,
    n: u32,
    parts: Vec<i64>,
    payment: i64,
    balance: i64,
    k: u32,
    left: u32,
}

impl Amortizing {
    /// Bank qarzining bugungi holati: shartnoma shartlari + yozilgan to'lovlar.
    pub fn replay(t: &BankTerms, payments: &[Payment]) -> Result<Self, DomainError> {
        let cur = t.principal.currency();
        if !t.principal.is_positive() {
            return Err(DomainError::on("PRINCIPAL_NOT_POSITIVE", "principal"));
        }
        if t.months == 0 || t.months > 600 {
            return Err(DomainError::on("INVALID_TERM", "months"));
        }
        if !(0..=100_000).contains(&t.annual_bp) {
            return Err(DomainError::on("INVALID_RATE", "annual_bp"));
        }
        let p = t.principal.minor();
        let mut s = Self {
            cur,
            differentiated: t.differentiated,
            bp: t.annual_bp,
            first: t.first_date,
            n: t.months,
            parts: if t.differentiated {
                allocate_minor(p, &vec![1; t.months as usize])?
            } else {
                Vec::new()
            },
            payment: if t.differentiated {
                0
            } else {
                annuity_payment(p, t.annual_bp, t.months)?
            },
            balance: p,
            k: 1,
            left: t.months,
        };
        let (mut regular, mut pre) = split_payments(payments, cur)?;
        pre.sort_by_key(|x| x.0);
        let mut j = 0;
        loop {
            let d = s.next_date()?;
            while j < pre.len() && pre[j].0 < d {
                s.balance -= pre[j].1.min(s.balance);
                j += 1;
            }
            if s.balance == 0 || s.left == 0 {
                break;
            }
            let (i, pr) = s.inst()?;
            if regular >= i + pr {
                regular -= i + pr;
                s.pay()?;
            } else {
                break;
            }
        }
        for (_, a) in &pre[j..] {
            s.balance -= (*a).min(s.balance);
        }
        s.balance -= regular.min(s.balance);
        Ok(s)
    }

    fn next_date(&self) -> Result<NaiveDate, DomainError> {
        add_months(self.first, self.k - 1)
    }

    fn inst(&self) -> Result<(i64, i64), DomainError> {
        let i = i64::try_from(round_half_up(
            i128::from(self.balance) * i128::from(self.bp),
            MONTHLY_DEN,
        )?)
        .map_err(|_| overflow())?;
        let mut p = if self.differentiated {
            self.parts
                .get(self.k as usize - 1)
                .copied()
                .unwrap_or(self.balance)
        } else {
            self.payment - i
        };
        if p >= self.balance || self.left <= 1 {
            p = self.balance;
        }
        Ok((i, p.max(0)))
    }

    fn pay(&mut self) -> Result<(i64, i64), DomainError> {
        let (i, p) = self.inst()?;
        self.balance -= p;
        self.k += 1;
        self.left = self.left.saturating_sub(1);
        Ok((i, p))
    }
}

fn split_payments(
    payments: &[Payment],
    cur: Currency,
) -> Result<(i64, Vec<(NaiveDate, i64)>), DomainError> {
    let mut regular: i64 = 0;
    let mut pre = Vec::new();
    for p in payments {
        if p.amount.currency() != cur {
            return Err(DomainError::on("CURRENCY_MISMATCH", "amount"));
        }
        if !p.amount.is_positive() {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        if p.prepayment {
            pre.push((p.date, p.amount.minor()));
        } else {
            regular = regular.checked_add(p.amount.minor()).ok_or_else(overflow)?;
        }
    }
    Ok((regular, pre))
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Scheduled {
    cur: Currency,
    lines: Vec<PlanLine>,
}

impl Scheduled {
    pub fn new(lines: &[PlanLine], payments: &[Payment]) -> Result<Self, DomainError> {
        let cur = lines
            .first()
            .map(|l| l.amount.currency())
            .ok_or(DomainError::on("SCHEDULE_REQUIRED", "schedule"))?;
        let (regular, pre) = split_payments(payments, cur)?;
        let prepaid = pre
            .iter()
            .try_fold(0i64, |a, (_, x)| a.checked_add(*x))
            .ok_or_else(overflow)?;
        Ok(Self {
            cur,
            lines: remaining_lines(lines, Money::new(regular, cur), Money::new(prepaid, cur))?,
        })
    }
}

/// Bitta qarzning prognoz uchun holati.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DebtState {
    Amortizing(Amortizing),
    Scheduled(Scheduled),
}

/// Bir oydagi odatiy to'lovlar natijasi.
struct Regular {
    due: i64,
    interest: i64,
    last: Option<NaiveDate>,
    installments: Vec<(NaiveDate, i64)>,
}

impl DebtState {
    pub fn currency(&self) -> Currency {
        match self {
            Self::Amortizing(a) => a.cur,
            Self::Scheduled(s) => s.cur,
        }
    }

    /// Bank qarzida — asosiy qarz qoldig'i, ustamali/foizsiz rejada — qolgan to'lovlar.
    pub fn balance(&self) -> Money {
        let v = match self {
            Self::Amortizing(a) => a.balance,
            Self::Scheduled(s) => s.lines.iter().map(|l| l.amount.minor()).sum(),
        };
        Money::new(v, self.currency())
    }

    pub fn next_date(&self) -> Result<Option<NaiveDate>, DomainError> {
        if !self.balance().is_positive() {
            return Ok(None);
        }
        Ok(match self {
            Self::Amortizing(a) => Some(a.next_date()?),
            Self::Scheduled(s) => s.lines.first().map(|l| l.date),
        })
    }

    fn regular(&mut self, window_end: NaiveDate) -> Result<Regular, DomainError> {
        let mut r = Regular {
            due: 0,
            interest: 0,
            last: None,
            installments: Vec::new(),
        };
        match self {
            Self::Amortizing(a) => {
                while a.balance > 0 && a.next_date()? < window_end {
                    let d = a.next_date()?;
                    let (i, p) = a.pay()?;
                    r.due += i + p;
                    r.interest += i;
                    r.last = Some(d);
                    r.installments.push((d, i + p));
                }
            }
            Self::Scheduled(s) => {
                while s.lines.first().is_some_and(|l| l.date < window_end) {
                    let l = s.lines.remove(0);
                    r.due += l.amount.minor();
                    r.last = Some(l.date);
                    r.installments.push((l.date, l.amount.minor()));
                }
            }
        }
        Ok(r)
    }

    fn extra(&mut self, ex: i64) {
        match self {
            Self::Amortizing(a) => a.balance -= ex,
            Self::Scheduled(s) => {
                let mut ex = ex;
                for l in s.lines.iter_mut().rev() {
                    let take = ex.min(l.amount.minor());
                    l.amount = Money::new(l.amount.minor() - take, s.cur);
                    ex -= take;
                }
                s.lines.retain(|l| l.amount.is_positive());
            }
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ProjRow {
    pub date: NaiveDate,
    pub due: Money,
    pub interest: Money,
    pub extra: Money,
    pub fee: Money,
    pub balance: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DebtProjection {
    pub id: String,
    pub rows: Vec<ProjRow>,
    /// Har bir odatiy to'lov alohida (holat va eslatma uchun).
    pub installments: Vec<PlanLine>,
    pub payoff_date: Option<NaiveDate>,
    /// Bugungi oydan boshlab necha kalendar oyida yopiladi.
    pub months: u32,
    pub interest: Money,
    pub fees: Money,
    pub paid: Money,
}

/// Bir kalendar oyi bo'yicha barcha qarzlar yig'indisi (grafik va katta jadval uchun).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct WindowTotal {
    pub month: NaiveDate,
    pub due: Money,
    pub interest: Money,
    pub extra: Money,
    pub fee: Money,
    /// Oy oxiridagi qoldiq (bank qarzida asosiy qarz, boshqalarida qolgan to'lovlar).
    pub balance: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlanTotals {
    pub payoff_date: Option<NaiveDate>,
    pub months: u32,
    pub interest: Money,
    pub fees: Money,
    pub paid: Money,
    pub timeline: Vec<WindowTotal>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlanDebt {
    pub id: String,
    pub state: DebtState,
    /// Muddatidan oldin to'lash jarimasi/komissiyasi, qo'shimcha to'lovdan bp.
    pub fee_bp: i64,
}

/// Tartiblangan qarzlar uchun oyma-oy prognoz. `pool` — har oy qo'shimcha to'lov.
pub fn payoff_plan(
    debts: Vec<PlanDebt>,
    today: NaiveDate,
    pool: Money,
) -> Result<(Vec<DebtProjection>, PlanTotals), DomainError> {
    let cur = pool.currency();
    if pool.is_negative() {
        return Err(DomainError::on("EXTRA_NEGATIVE", "extra"));
    }
    let mut debts = debts;
    for d in &debts {
        if d.state.currency() != cur {
            return Err(DomainError::on("CURRENCY_MISMATCH", "extra"));
        }
        if !(0..=10_000).contains(&d.fee_bp) {
            return Err(DomainError::on("INVALID_BP", "prepaymentFeeBp"));
        }
    }
    let zero = Money::zero(cur);
    let mut out: Vec<DebtProjection> = debts
        .iter()
        .map(|d| DebtProjection {
            id: d.id.clone(),
            rows: Vec::new(),
            installments: Vec::new(),
            payoff_date: None,
            months: 0,
            interest: zero,
            fees: zero,
            paid: zero,
        })
        .collect();
    let ws0 = month_start(today)?;
    let mut w: u32 = 0;
    let mut timeline = Vec::new();
    while debts.iter().any(|d| d.state.balance().is_positive()) {
        if w >= MAX_WINDOWS {
            return Err(DomainError::new("NOT_CONVERGING"));
        }
        let ws = add_months(ws0, w)?;
        let we = add_months(ws0, w + 1)?;
        let mut acts: Vec<Option<(Regular, i64, i64)>> = Vec::with_capacity(debts.len());
        for d in debts.iter_mut() {
            acts.push(if d.state.balance().is_positive() {
                Some((d.state.regular(we)?, 0, 0))
            } else {
                None
            });
        }
        let mut rest = pool.minor();
        for (d, act) in debts.iter_mut().zip(acts.iter_mut()) {
            let bal = d.state.balance().minor();
            if let Some(a) = act {
                if bal > 0 && rest > 0 {
                    let ex = rest.min(bal);
                    d.state.extra(ex);
                    rest -= ex;
                    a.1 = ex;
                    a.2 = percent_of(Money::new(ex, cur), d.fee_bp)?.minor();
                }
            }
        }
        let m = |v: i64| Money::new(v, cur);
        let mut wt = WindowTotal {
            month: ws,
            due: zero,
            interest: zero,
            extra: zero,
            fee: zero,
            balance: Money::sum(debts.iter().map(|d| d.state.balance()), cur)?,
        };
        for ((d, act), p) in debts.iter().zip(acts).zip(out.iter_mut()) {
            let Some((r, ex, fee)) = act else {
                continue;
            };
            wt.due = wt.due.checked_add(m(r.due))?;
            wt.interest = wt.interest.checked_add(m(r.interest))?;
            wt.extra = wt.extra.checked_add(m(ex))?;
            wt.fee = wt.fee.checked_add(m(fee))?;
            p.installments
                .extend(r.installments.iter().map(|(dt, a)| PlanLine {
                    date: *dt,
                    amount: Money::new(*a, cur),
                }));
            if r.due == 0 && ex == 0 {
                continue;
            }
            let date = r.last.unwrap_or(ws.max(today));
            p.rows.push(ProjRow {
                date,
                due: m(r.due),
                interest: m(r.interest),
                extra: m(ex),
                fee: m(fee),
                balance: d.state.balance(),
            });
            p.interest = p.interest.checked_add(m(r.interest))?;
            p.fees = p.fees.checked_add(m(fee))?;
            p.paid = p.paid.checked_add(m(r.due + ex + fee))?;
            if !d.state.balance().is_positive() {
                p.payoff_date = Some(date);
                p.months = w + 1;
            }
        }
        timeline.push(wt);
        w += 1;
    }
    let totals = PlanTotals {
        payoff_date: out.iter().filter_map(|p| p.payoff_date).max(),
        months: out.iter().map(|p| p.months).max().unwrap_or(0),
        interest: Money::sum(out.iter().map(|p| p.interest), cur)?,
        fees: Money::sum(out.iter().map(|p| p.fees), cur)?,
        paid: Money::sum(out.iter().map(|p| p.paid), cur)?,
        timeline,
    };
    Ok((out, totals))
}

/// Yopish tartibi kaliti.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OrderKey {
    pub id: String,
    pub ribo: bool,
    /// Qarz «narxi»: bank qarzida yillik stavka, ustamalida ortiqcha to'lov ulushi (bp).
    pub cost_bp: i64,
    pub payoff_date: Option<NaiveDate>,
    /// Foydalanuvchi qo'lda qo'ygan tartib (1 — birinchi).
    pub priority: Option<i64>,
}

/// Standart tartib (uy/SPEC 2D.2): qo'lda belgilanganlari birinchi; keyin foizli qarzlar —
/// eng qimmati birinchi; keyin foizsizlar — muddati yaqini birinchi.
pub fn default_order(keys: &[OrderKey]) -> Vec<String> {
    let mut k: Vec<&OrderKey> = keys.iter().collect();
    k.sort_by_key(|o| {
        (
            o.priority.is_none(),
            o.priority.unwrap_or(0),
            !o.ribo,
            if o.ribo { -o.cost_bp } else { 0 },
            o.payoff_date.unwrap_or(NaiveDate::MAX),
            o.id.clone(),
        )
    });
    k.into_iter().map(|o| o.id.clone()).collect()
}

/// Ikki kalendar oyi orasidagi farq (b − a), «N oy erta» uchun.
pub fn months_between(a: NaiveDate, b: NaiveDate) -> i64 {
    i64::from(b.year() - a.year()) * 12 + i64::from(b.month()) - i64::from(a.month())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    fn d(s: &str) -> NaiveDate {
        NaiveDate::parse_from_str(s, "%Y-%m-%d").unwrap()
    }

    #[test]
    fn closed_debt_has_no_rows_and_order_is_stable() {
        let lines = [PlanLine {
            date: d("2026-11-15"),
            amount: uzs(100),
        }];
        let paid = [Payment {
            date: d("2026-11-15"),
            amount: uzs(100),
            prepayment: false,
        }];
        let st = DebtState::Scheduled(Scheduled::new(&lines, &paid).unwrap());
        assert_eq!(st.next_date().unwrap(), None);
        let (p, t) = payoff_plan(
            vec![PlanDebt {
                id: "a".into(),
                state: st,
                fee_bp: 0,
            }],
            d("2026-11-20"),
            uzs(0),
        )
        .unwrap();
        assert!(p[0].rows.is_empty());
        assert_eq!((t.months, t.payoff_date), (0, None));
        let key = |id: &str, ribo, cost, pr| OrderKey {
            id: id.into(),
            ribo,
            cost_bp: cost,
            payoff_date: None,
            priority: pr,
        };
        assert_eq!(
            default_order(&[
                key("c", false, 0, None),
                key("b", true, 100, None),
                key("a", true, 900, None),
                key("z", false, 0, Some(1))
            ]),
            ["z", "a", "b", "c"]
        );
        assert_eq!(months_between(d("2027-12-05"), d("2027-06-20")), -6);
    }
}
