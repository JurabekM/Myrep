//! Qarzdan chiqish rejalovchisi (SPEC 2D.2, 2D.9): odatiy va tezlashtirilgan grafik, yopish tartibi,
//! «qarzsiz kun». Natijalar taxminiy: muddatidan oldin to'lash shartlari shartnomaga bog'liq.
use domain::{
    add_months, amortize, closing_order, payoff_plan, Amortization, Date, Debt, LoanKind,
    OrderItem, PlanDebt,
};
use money::{round_half_up, Money};
use storage::Connection;
use storage::{repo, Database};

use crate::{debts, rescue, sellables, Ctx, Env, ServiceError, YearMonth};

/// Rejaga ulanadigan manbalar (SPEC 2D.2): 20% ulush, qutqarilgan pul, sotiladigan buyumlar.
#[derive(Debug, Clone)]
pub struct ExtraSources {
    /// `DEBT_RECOVERY` taqsimotidagi oylik qo'shimcha to'lov ulushi (daromad ma'lum bo'lsa).
    pub monthly_share: Option<Money>,
    /// Hali «Kelajagim»ga o'tkazilmagan qutqarilgan pul (bir martalik manba).
    pub rescued_available: Money,
    /// Sotilmagan buyumlarning taxminiy narxi jami (bir martalik manba).
    pub sellable_listed: Money,
}

/// # Errors
/// Baza xatosi.
pub fn sources(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<ExtraSources, ServiceError> {
    let split = crate::recovery::split(conn, ctx)?;
    let monthly_share = match debts::reference_income(conn, env, ctx)? {
        Some(inc) => Some(domain::recovery_split(inc, split)?.extra),
        None => None,
    };
    Ok(ExtraSources {
        monthly_share,
        rescued_available: rescue::available(conn, ctx)?,
        sellable_listed: sellables::listed_total(conn, ctx)?,
    })
}

#[derive(Debug, Clone)]
pub struct DebtLine {
    pub id: String,
    pub creditor: String,
    pub baseline_months: u32,
    pub accelerated_months: u32,
}

#[derive(Debug, Clone)]
pub struct PlanView {
    /// Yopish tartibi (qarz identifikatorlari; birinchisi — ustuvor).
    pub order: Vec<String>,
    /// `true` — tartib foydalanuvchi qo'lda belgilagan.
    pub manual_order: bool,
    pub lines: Vec<DebtLine>,
    pub monthly_extra: Money,
    pub one_off: Money,
    pub baseline_months: u32,
    pub accelerated_months: u32,
    pub months_saved: u32,
    /// «Qarzsiz kun» (oyning oxirgi kuni): odatiy va tezlashtirilgan.
    pub debt_free_baseline: Option<Date>,
    pub debt_free_accelerated: Option<Date>,
}

fn month_index(d: Date) -> i64 {
    i64::from(d.year()) * 12 + i64::from(u8::from(d.month())) - 1
}

/// Qarzning qolgan to'lov qatorlari (to'langan summa jadvalga ketma-ket taqsimlanadi); indeks — joriy
/// oydan boshlab oy. O'tib ketgan qatorlar 0-oyga yig'iladi.
fn remaining_rows(v: &debts::DebtView, today: Date) -> Result<Vec<Money>, ServiceError> {
    let cur = v.remaining.currency();
    let mut left = v.paid.minor();
    let mut rows: Vec<i64> = Vec::new();
    for i in &v.instalments {
        let amount = i.amount.minor();
        if left >= amount {
            left -= amount;
            continue;
        }
        let rest = amount - left;
        left = 0;
        let off = usize::try_from((month_index(i.due_on) - month_index(today)).max(0))
            .map_err(|_| ServiceError::Invalid("jadval juda uzun"))?;
        if off >= 1200 {
            return Err(ServiceError::Invalid("jadval 100 yildan uzun"));
        }
        if rows.len() <= off {
            rows.resize(off + 1, 0);
        }
        rows[off] += rest;
    }
    Ok(rows.into_iter().map(|m| Money::new(m, cur)).collect())
}

fn order_item(v: &debts::DebtView) -> Result<OrderItem, ServiceError> {
    let markup_bp = if v.debt.principal.minor() > 0 {
        u32::try_from(round_half_up(
            i128::from(v.markup.minor()) * 10_000,
            i128::from(v.debt.principal.minor()),
        )?)
        .unwrap_or(u32::MAX)
    } else {
        0
    };
    Ok(OrderItem {
        id: v.debt.meta.id.clone(),
        creditor_type: v.debt.creditor_type,
        markup_bp,
        next_due: v.next_due.map(|(d, _)| d),
        priority: v.debt.priority,
    })
}

fn debt_free(today: Date, months: u32) -> Option<Date> {
    if months == 0 {
        return None;
    }
    let d = add_months(YearMonth::of(today).first_day(), months - 1);
    Some(YearMonth::of(d).last_day())
}

/// Rejani hisoblaydi. Faol qarz bo'lmasa `None`.
///
/// # Errors
/// Baza xatosi, manfiy summa yoki hisob sig'masa.
pub fn plan(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    monthly_extra: Money,
    one_off: Money,
) -> Result<Option<PlanView>, ServiceError> {
    let today = crate::local_date(env.clock.now());
    let active: Vec<debts::DebtView> = debts::list(conn, env, ctx)?
        .into_iter()
        .filter(debts::DebtView::active)
        .collect();
    if active.is_empty() {
        return Ok(None);
    }
    let items = active
        .iter()
        .map(order_item)
        .collect::<Result<Vec<_>, _>>()?;
    let manual_order = items.iter().any(|i| i.priority.is_some());
    let order_ids = closing_order(&items);
    let order: Vec<usize> = order_ids
        .iter()
        .filter_map(|id| active.iter().position(|v| &v.debt.meta.id == id))
        .collect();
    let plan_debts = active
        .iter()
        .map(|v| {
            Ok(PlanDebt {
                rows: remaining_rows(v, today)?,
            })
        })
        .collect::<Result<Vec<_>, ServiceError>>()?;
    let zero = ctx.zero();
    let base = payoff_plan(&plan_debts, &order, zero, zero, true)?;
    let fast = payoff_plan(&plan_debts, &order, monthly_extra, one_off, true)?;
    Ok(Some(PlanView {
        order: order_ids,
        manual_order,
        lines: active
            .iter()
            .enumerate()
            .map(|(i, v)| DebtLine {
                id: v.debt.meta.id.clone(),
                creditor: v.debt.creditor.clone(),
                baseline_months: base.per_debt_months[i],
                accelerated_months: fast.per_debt_months[i],
            })
            .collect(),
        monthly_extra,
        one_off,
        baseline_months: base.months,
        accelerated_months: fast.months,
        months_saved: base.months.saturating_sub(fast.months),
        debt_free_baseline: debt_free(today, base.months),
        debt_free_accelerated: debt_free(today, fast.months),
    }))
}

/// Qo'lda tartib: berilgan identifikatorlar ro'yxat tartibida ustuvor bo'ladi, qolganlarniki tozalanadi.
///
/// # Errors
/// Qarz topilmasa.
pub fn set_order(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    ordered_ids: &[String],
) -> Result<(), ServiceError> {
    let all = repo::list::<Debt>(db.conn(), &ctx.household_id)?;
    if ordered_ids
        .iter()
        .any(|id| !all.iter().any(|d| &d.meta.id == id))
    {
        return Err(ServiceError::NotFound);
    }
    let now = env.clock.now();
    db.transaction::<(), ServiceError>(|tx| {
        for mut d in all {
            let p = ordered_ids
                .iter()
                .position(|id| *id == d.meta.id)
                .map(|i| u32::try_from(i).unwrap_or(u32::MAX));
            if d.priority != p {
                d.priority = p;
                repo::update(tx, &d, now)?;
            }
        }
        Ok(())
    })
}

/// Standart tartibga qaytish.
///
/// # Errors
/// Baza xatosi.
pub fn clear_order(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<(), ServiceError> {
    set_order(db, env, ctx, &[])
}

#[derive(Debug, Clone)]
pub struct Calculator {
    pub baseline: Amortization,
    pub accelerated: Amortization,
    pub months_saved: u32,
    pub interest_saved: Money,
}

/// «Nima bo'ladi, agar...» kalkulyatori: yangi yoki tasavvuriy annuitet/differensial kredit
/// (masalan, avtokredit 39 mln, 14 oy) — odatiy va qo'shimcha to'lovli jadval yonma-yon.
///
/// # Errors
/// Kirish qiymatlari yaroqsiz bo'lsa.
pub fn calculator(
    kind: LoanKind,
    principal: Money,
    annual_bp: u32,
    months: u32,
    extra: Money,
) -> Result<Calculator, ServiceError> {
    let zero = Money::zero(principal.currency());
    let baseline = amortize(kind, principal, annual_bp, months, zero)?;
    let accelerated = amortize(kind, principal, annual_bp, months, extra)?;
    Ok(Calculator {
        months_saved: baseline.months.saturating_sub(accelerated.months),
        interest_saved: baseline
            .total_interest
            .checked_sub(accelerated.total_interest)?,
        baseline,
        accelerated,
    })
}
