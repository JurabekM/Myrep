//! 3-qonun (SPEC 2C.3–2C.4): qorovul pul maqsadi, tayyorgarlik darvozasi, ajratma ustuvorligi.
use std::collections::HashMap;

use domain::{
    effective_necessity, emergency_target, guard_months_x100, readiness_gate, split_allocation,
    Category, Date, Expense, GateBypass, GateReason, Meta, Necessity, GATE_REQUIRED_X100,
    GUARD_FULL_MONTHS, GUARD_MILESTONE_MONTHS,
};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{
    learning::{put_setting, setting},
    local_date, obligations, sum_money, vault, Ctx, Env, ServiceError, YearMonth,
};

const KEY_DEBT_PLAN: &str = "gate.debt_plan";
/// Maqsad hisobiga olinadigan oxirgi tugagan oylar soni.
const BASIS_MONTHS: usize = 3;

#[derive(Debug, Clone)]
pub struct Overview {
    /// Oylik `ZARUR + KERAK` o'rtacha ehtiyoj.
    pub monthly_need: Money,
    /// To'liq maqsad (6 oy).
    pub target: Money,
    /// Birinchi bosqich (3 oy).
    pub milestone: Money,
    pub balance: Money,
    /// Necha oylik zaxira (×100).
    pub months_x100: u32,
    pub milestone_reached: bool,
    pub full_reached: bool,
    /// Maqsadgacha yetishmaydi (0 dan kam emas).
    pub gap: Money,
    pub growing_balance: Money,
    /// Maqsad nechta oy ma'lumotiga asoslangan (0 — hisoblab bo'lmaydi).
    pub basis_months: usize,
}

/// Oyning `ZARUR + KERAK` xarajati + doimiy majburiyatlar (audit ikkalasini ajratadi).
fn month_need(
    ym: YearMonth,
    expenses: &[Expense],
    cats: &HashMap<String, Category>,
    ctx: &Ctx,
) -> Result<(Money, bool), ServiceError> {
    let mut any = false;
    let amounts = expenses
        .iter()
        .filter(|e| ym.contains(e.spent_on))
        .filter_map(|e| {
            any = true;
            let nec = effective_necessity(e.necessity, cats.get(&e.category_id)?.necessity);
            matches!(nec, Some(Necessity::Zarur | Necessity::Kerak)).then_some(e.amount)
        })
        .collect::<Vec<_>>();
    Ok((sum_money(ctx.currency, amounts)?, any))
}

/// Oylik ehtiyoj qatorlari: oxirgi 3 tugagan oydan xarajati bor oylar; bo'lmasa joriy oy; u ham
/// bo'lmasa faqat doimiy majburiyatlar.
fn monthly_needs(conn: &Connection, ctx: &Ctx, today: Date) -> Result<Vec<Money>, ServiceError> {
    let cats: HashMap<String, Category> = repo::list::<Category>(conn, &ctx.household_id)?
        .into_iter()
        .map(|c| (c.meta.id.clone(), c))
        .collect();
    let expenses = repo::list::<Expense>(conn, &ctx.household_id)?;
    let fixed = obligations::monthly_total(conn, ctx)?;
    let current = YearMonth::of(today);
    let mut ym = current.previous();
    let mut rows = Vec::new();
    for _ in 0..BASIS_MONTHS {
        let (spent, any) = month_need(ym, &expenses, &cats, ctx)?;
        if any {
            rows.push(spent.checked_add(fixed)?);
        }
        ym = ym.previous();
    }
    if rows.is_empty() {
        let (spent, any) = month_need(current, &expenses, &cats, ctx)?;
        if any {
            rows.push(spent.checked_add(fixed)?);
        } else if fixed.minor() > 0 {
            rows.push(fixed);
        }
    }
    Ok(rows)
}

/// # Errors
/// Baza xatosi yoki hisob sig'masa.
pub fn overview(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<Overview, ServiceError> {
    let rows = monthly_needs(conn, ctx, local_date(env.clock.now()))?;
    let target = emergency_target(&rows, GUARD_FULL_MONTHS, ctx.currency)?;
    let milestone = emergency_target(&rows, GUARD_MILESTONE_MONTHS, ctx.currency)?;
    let monthly_need = emergency_target(&rows, 1, ctx.currency)?;
    let balance = vault::guard_balance(conn, ctx)?;
    let months_x100 = guard_months_x100(balance, target, GUARD_FULL_MONTHS)?;
    let target_known = target.minor() > 0;
    Ok(Overview {
        monthly_need,
        target,
        milestone,
        balance,
        months_x100,
        milestone_reached: target_known && balance.minor() >= milestone.minor(),
        full_reached: target_known && balance.minor() >= target.minor(),
        gap: Money::new((target.minor() - balance.minor()).max(0), ctx.currency),
        growing_balance: vault::growing_balance(conn, ctx)?,
        basis_months: rows.len(),
    })
}

#[derive(Debug, Clone)]
pub struct Gate {
    pub rules_open: bool,
    /// Foydalanuvchi qulfni ongli chetlab o'tgan.
    pub bypassed: bool,
    /// Amalda ochiq (qoidalar bo'yicha yoki chetlab o'tilgan).
    pub open: bool,
    pub reasons: Vec<GateReason>,
    pub months_x100: u32,
    pub required_x100: u32,
    pub has_interest_debt: bool,
    pub has_debt_plan: bool,
}

fn flag(conn: &Connection, ctx: &Ctx, key: &str) -> Result<bool, ServiceError> {
    Ok(setting(conn, ctx, key)?.is_some_and(|s| s.value == "1"))
}

fn bypasses(conn: &Connection, ctx: &Ctx) -> Result<Vec<GateBypass>, ServiceError> {
    Ok(repo::list::<GateBypass>(conn, &ctx.household_id)?)
}

/// # Errors
/// Baza xatosi.
pub fn gate(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<Gate, ServiceError> {
    let ov = overview(conn, env, ctx)?;
    gate_with(conn, env, ctx, ov.months_x100)
}

/// «Foizli qarz» — qarz inventaridagi faol, ustamali qarz (jadval jami asosiydan ko'p).
fn gate_with(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    months_x100: u32,
) -> Result<Gate, ServiceError> {
    let has_interest_debt = crate::debts::has_markup_debt(conn, env, ctx)?;
    let has_debt_plan = flag(conn, ctx, KEY_DEBT_PLAN)?;
    let status = readiness_gate(
        months_x100,
        has_interest_debt,
        has_debt_plan,
        GATE_REQUIRED_X100,
    );
    let bypassed = !status.open && !bypasses(conn, ctx)?.is_empty();
    Ok(Gate {
        rules_open: status.open,
        bypassed,
        open: status.open || bypassed,
        reasons: status.reasons,
        months_x100,
        required_x100: GATE_REQUIRED_X100,
        has_interest_debt,
        has_debt_plan,
    })
}

/// Qarzdan chiqish rejasi bor-yo'qligi haqida bayon. Foizli qarz o'zi qarz inventaridan olinadi;
/// `DEBT_RECOVERY` rejimi va to'lov rejalovchisi (D10) tayyor bo'lgach reja ham undan olinadi.
///
/// # Errors
/// Baza xatosi.
pub fn set_debt_plan_declaration(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    has_debt_plan: bool,
) -> Result<(), ServiceError> {
    put_setting(
        db.conn(),
        env,
        ctx,
        KEY_DEBT_PLAN,
        if has_debt_plan { "1" } else { "0" },
    )
}

/// Darvozani ongli chetlab o'tish: tasdiq majburiy; qayd saqlanadi (mahalliy analitika).
///
/// # Errors
/// Tasdiqsiz yoki darvoza allaqachon ochiq bo'lsa.
pub fn bypass(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    confirmed: bool,
) -> Result<(), ServiceError> {
    if !confirmed {
        return Err(ServiceError::Invalid("chetlab o'tishni tasdiqlang"));
    }
    let g = gate(db.conn(), env, ctx)?;
    if g.rules_open {
        return Err(ServiceError::Invalid("darvoza allaqachon ochiq"));
    }
    if g.bypassed {
        return Ok(());
    }
    repo::insert(
        db.conn(),
        &GateBypass {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            guard_months_x100: g.months_x100,
        },
    )?;
    Ok(())
}

/// Chetlab o'tishni bekor qiladi (darvoza yana qoidaga qaytadi).
///
/// # Errors
/// Baza xatosi.
pub fn revoke_bypass(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<(), ServiceError> {
    let now = env.clock.now();
    for b in bypasses(db.conn(), ctx)? {
        repo::soft_delete::<GateBypass>(db.conn(), &b.meta.id, now)?;
    }
    Ok(())
}

/// Ajratmani bo'ladi: avval qorovul maqsadigacha, ortig'i o'sadiganga (darvoza ochiq bo'lsa).
///
/// # Errors
/// Baza xatosi yoki hisob sig'masa.
pub(crate) fn split_share(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    share: Money,
) -> Result<(Money, Money), ServiceError> {
    let ov = overview(conn, env, ctx)?;
    let g = gate_with(conn, env, ctx, ov.months_x100)?;
    Ok(split_allocation(share, ov.balance, ov.target, g.open)?)
}
