//! Qarz inventari (SPEC 2C.7, 2D.3, 2D.5, 2D.6): qarz faqat to'lov jadvali bilan saqlanadi; ustama
//! jadvaldan chiqadi; haqiqiy narx va oylik yuk hisoblanadi.
use domain::{
    burden_bp, debt_cost, fixed_markup_schedule, schedule_summary, BorrowAlternative, BorrowCheck,
    BorrowNeed, Category, CreditorType, Date, Debt, DebtCost, DebtInstalment, DebtPayment, Expense,
    Meta, PaymentChannel, ScheduleKind,
};
use money::{round_half_up, Money};
use storage::Connection;
use storage::{repo, Database};

use crate::{
    income, local_date, setup::DEBT_PAYMENT_CATEGORY, sum_money, Ctx, Env, ServiceError, YearMonth,
};

/// To'lov jadvali kiritish usuli.
#[derive(Debug, Clone)]
pub enum ScheduleInput {
    /// `FIXED_MARKUP`: asosiy + ustama teng bo'laklarga.
    FixedMarkup {
        markup: Money,
        months: u32,
        first_due: Date,
    },
    /// Foydalanuvchi qatorlari (bank shartnomasidagi jadval yoki qo'lda).
    Rows(Vec<(Date, Money)>),
}

#[derive(Debug, Clone)]
pub struct NewDebt {
    pub creditor: String,
    pub creditor_type: CreditorType,
    pub reason: Option<String>,
    pub principal: Money,
    pub schedule_kind: ScheduleKind,
    pub schedule: ScheduleInput,
    pub borrowed_on: Option<Date>,
    pub early_repayment_terms: Option<String>,
    /// «To'xta va o'yla» javoblari; yuki xizmat hisoblaydi.
    pub check: Option<(BorrowNeed, BorrowAlternative)>,
}

#[derive(Debug, Clone)]
pub struct DebtView {
    pub debt: Debt,
    pub instalments: Vec<DebtInstalment>,
    pub paid: Money,
    pub total_scheduled: Money,
    pub remaining: Money,
    /// Ustama = jadval jami − asosiy.
    pub markup: Money,
    pub cost: DebtCost,
    /// Birinchi to'lanmagan qator (jami to'lov jadval bo'yicha taqsimlanadi).
    pub next_due: Option<(Date, Money)>,
    pub overdue: bool,
}

impl DebtView {
    #[must_use]
    pub const fn active(&self) -> bool {
        self.debt.closed_on.is_none()
    }

    #[must_use]
    pub fn has_markup(&self) -> bool {
        self.markup.minor() > 0
    }
}

fn check_text(s: &str, max: usize) -> Option<String> {
    let t = s.trim();
    (!t.is_empty()).then(|| t.chars().take(max).collect())
}

fn rows_for(new: &NewDebt) -> Result<Vec<(Date, Money)>, ServiceError> {
    match (&new.schedule, new.schedule_kind) {
        (
            ScheduleInput::FixedMarkup {
                markup,
                months,
                first_due,
            },
            ScheduleKind::FixedMarkup,
        ) => Ok(fixed_markup_schedule(
            new.principal,
            *markup,
            *months,
            *first_due,
        )?),
        (ScheduleInput::Rows(rows), k) if k != ScheduleKind::FixedMarkup => {
            let mut r = rows.clone();
            r.sort_by_key(|(d, _)| *d);
            Ok(r)
        }
        _ => Err(ServiceError::Invalid(
            "jadval turi va kiritish usuli mos emas",
        )),
    }
}

/// Qarzning jadvali va to'lovlari asosida ko'rinishi.
fn build_view(
    conn: &Connection,
    ctx: &Ctx,
    debt: Debt,
    today: Date,
) -> Result<DebtView, ServiceError> {
    let mut instalments: Vec<DebtInstalment> =
        repo::list::<DebtInstalment>(conn, &ctx.household_id)?
            .into_iter()
            .filter(|i| i.debt_id == debt.meta.id)
            .collect();
    instalments.sort_by_key(|i| (i.due_on, i.meta.id.clone()));
    let paid = sum_money(
        ctx.currency,
        repo::list::<DebtPayment>(conn, &ctx.household_id)?
            .into_iter()
            .filter(|p| p.debt_id == debt.meta.id)
            .map(|p| p.amount),
    )?;
    let total_scheduled = sum_money(ctx.currency, instalments.iter().map(|i| i.amount))?;
    let remaining = Money::new(
        (total_scheduled.minor() - paid.minor()).max(0),
        ctx.currency,
    );
    let markup = Money::new(
        (total_scheduled.minor() - debt.principal.minor()).max(0),
        ctx.currency,
    );
    let cost = debt_cost(debt.principal, paid, remaining)?;
    // To'lovlar jadval qatorlariga ketma-ket taqsimlanadi.
    let mut left = paid.minor();
    let mut next_due = None;
    for i in &instalments {
        if left >= i.amount.minor() {
            left -= i.amount.minor();
        } else {
            next_due = Some((i.due_on, Money::new(i.amount.minor() - left, ctx.currency)));
            break;
        }
    }
    let overdue = debt.closed_on.is_none() && next_due.is_some_and(|(d, _)| d < today);
    Ok(DebtView {
        debt,
        instalments,
        paid,
        total_scheduled,
        remaining,
        markup,
        cost,
        next_due,
        overdue,
    })
}

/// Qarzlar (faol → yopilgan; faollar muddati yaqinidan).
///
/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<Vec<DebtView>, ServiceError> {
    let today = local_date(env.clock.now());
    let mut views = repo::list::<Debt>(conn, &ctx.household_id)?
        .into_iter()
        .map(|d| build_view(conn, ctx, d, today))
        .collect::<Result<Vec<_>, _>>()?;
    views.sort_by_key(|v| {
        (
            !v.active(),
            v.next_due.map_or(Date::MAX, |(d, _)| d),
            v.debt.meta.id.clone(),
        )
    });
    Ok(views)
}

/// # Errors
/// Topilmasa.
pub fn get(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<DebtView, ServiceError> {
    let d = repo::get::<Debt>(conn, id)?.ok_or(ServiceError::NotFound)?;
    if d.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    build_view(conn, ctx, d, local_date(env.clock.now()))
}

/// Daromadga nisbatan oylik yuk uchun daromad: joriy oy, bo'lmasa oldingi oy; ikkalasi ham 0 bo'lsa `None`.
pub(crate) fn reference_income(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
) -> Result<Option<Money>, ServiceError> {
    let this = YearMonth::of(local_date(env.clock.now()));
    for ym in [this, this.previous()] {
        let m = income::month_total(conn, ctx, ym)?;
        if m.minor() > 0 {
            return Ok(Some(m));
        }
    }
    Ok(None)
}

fn monthly_of(total: Money, n: usize) -> Result<Money, ServiceError> {
    let n = i128::try_from(n).map_err(|_| ServiceError::Invalid("jadval juda uzun"))?;
    Ok(Money::new(
        round_half_up(i128::from(total.minor()), n)?,
        total.currency(),
    ))
}

/// Yangi qarz oldidan oylik yuk bashorati (friction ekrani uchun): hozirgi faol qarzlar + yangisi.
/// Daromad ma'lum bo'lmasa `None`.
///
/// # Errors
/// Baza xatosi yoki jadval yaroqsiz bo'lsa.
pub fn burden_preview(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    new: &NewDebt,
) -> Result<Option<u32>, ServiceError> {
    let rows = rows_for(new)?;
    let amounts: Vec<Money> = rows.iter().map(|(_, m)| *m).collect();
    let summary = schedule_summary(new.principal, &amounts)?;
    let new_monthly = monthly_of(summary.total, rows.len())?;
    let Some(income) = reference_income(conn, env, ctx)? else {
        return Ok(None);
    };
    let existing = overview(conn, env, ctx)?.monthly_load;
    Ok(Some(burden_bp(existing.checked_add(new_monthly)?, income)?))
}

/// Qarzni jadval bilan **bitta tranzaksiyada** saqlaydi. Jadvalsiz (bo'sh) qarz qabul qilinmaydi.
///
/// # Errors
/// Kreditor nomi bo'sh, jadval yaroqsiz (bo'sh, asosiydan kam, musbat bo'lmagan qator).
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewDebt,
) -> Result<DebtView, ServiceError> {
    let creditor =
        check_text(&new.creditor, 80).ok_or(ServiceError::Invalid("kreditor nomini yozing"))?;
    if new.principal.currency() != ctx.currency {
        return Err(ServiceError::Invalid("valyuta mos emas"));
    }
    let rows = rows_for(&new)?;
    let amounts: Vec<Money> = rows.iter().map(|(_, m)| *m).collect();
    let summary = schedule_summary(new.principal, &amounts)?;
    let monthly = monthly_of(summary.total, rows.len())?;
    let due_date = rows
        .last()
        .map(|(d, _)| *d)
        .ok_or(ServiceError::Invalid("to'lov rejasi bo'sh"))?;
    let check = match new.check {
        None => None,
        Some((need, alternative)) => Some(BorrowCheck {
            need,
            alternative,
            burden_bp: burden_preview(db.conn(), env, ctx, &new)?.unwrap_or(0),
        }),
    };
    let debt = Debt {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        creditor,
        creditor_type: new.creditor_type,
        reason: new.reason.as_deref().and_then(|r| check_text(r, 120)),
        principal: new.principal,
        schedule_kind: new.schedule_kind,
        monthly_payment: monthly,
        due_date,
        borrowed_on: new
            .borrowed_on
            .unwrap_or_else(|| local_date(env.clock.now())),
        early_repayment_terms: new
            .early_repayment_terms
            .as_deref()
            .and_then(|r| check_text(r, 300)),
        priority: None,
        closed_on: None,
        check,
    };
    db.transaction::<(), ServiceError>(|tx| {
        repo::insert(tx, &debt)?;
        for (due_on, amount) in &rows {
            repo::insert(
                tx,
                &DebtInstalment {
                    meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                    debt_id: debt.meta.id.clone(),
                    due_on: *due_on,
                    amount: *amount,
                },
            )?;
        }
        Ok(())
    })?;
    get(db.conn(), env, ctx, &debt.meta.id)
}

/// Qarzga to'lov: to'lov yozuvi + «Qarz to'lovi» xarajati (ZARUR). Qoldiq nolga tushsa qarz yopiladi.
///
/// # Errors
/// Qarz topilmasa/yopilgan bo'lsa, summa qoldiqdan ko'p yoki yaroqsiz bo'lsa.
pub fn pay(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    debt_id: &str,
    amount: Money,
    paid_on: Option<Date>,
    member_id: Option<&str>,
) -> Result<DebtView, ServiceError> {
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let view = get(db.conn(), env, ctx, debt_id)?;
    if !view.active() {
        return Err(ServiceError::Invalid("qarz allaqachon yopilgan"));
    }
    if amount.minor() > view.remaining.minor() {
        return Err(ServiceError::Invalid("to'lov qoldiqdan ko'p"));
    }
    let member = member_id.unwrap_or(&ctx.member_id).to_owned();
    let date = paid_on.unwrap_or_else(|| local_date(env.clock.now()));
    let category = repo::list::<Category>(db.conn(), &ctx.household_id)?
        .into_iter()
        .find(|c| c.name == DEBT_PAYMENT_CATEGORY)
        .ok_or(ServiceError::NotFound)?;
    let closes = amount.minor() == view.remaining.minor();
    db.transaction::<(), ServiceError>(|tx| {
        let expense_id = {
            let e = Expense {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                member_id: member.clone(),
                category_id: category.meta.id,
                amount,
                spent_on: date,
                payment_channel: PaymentChannel::Cash,
                necessity: None,
                envelope_id: None,
                is_gift: None,
                is_ostentation: None,
                funded_by_debt: None,
                audit_month: None,
                note: Some(format!("Qarz: {}", view.debt.creditor)),
            };
            repo::insert(tx, &e)?;
            e.meta.id
        };
        repo::insert(
            tx,
            &DebtPayment {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                debt_id: debt_id.to_owned(),
                member_id: member,
                paid_on: date,
                amount,
                expense_id: Some(expense_id),
            },
        )?;
        if closes {
            let mut d = view.debt.clone();
            d.closed_on = Some(date);
            repo::update(tx, &d, env.clock.now())?;
        }
        Ok(())
    })?;
    // Oxirgi qarz yopilsa `DEBT_RECOVERY` avtomatik `STANDARD` ga qaytadi.
    crate::recovery::sync(db, env, ctx)?;
    get(db.conn(), env, ctx, debt_id)
}

/// Muddatidan oldin to'lash shartlari (jarima, komissiya) — foydalanuvchi kiritadi.
///
/// # Errors
/// Qarz topilmasa.
pub fn set_early_terms(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    terms: &str,
) -> Result<(), ServiceError> {
    let mut d = get(db.conn(), env, ctx, id)?.debt;
    d.early_repayment_terms = check_text(terms, 300);
    repo::update(db.conn(), &d, env.clock.now())?;
    Ok(())
}

/// Qarz va uning jadvali/to'lovlari o'chiriladi (xarajat yozuvlari qoladi).
///
/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let view = get(db.conn(), env, ctx, id)?;
    let pays: Vec<String> = repo::list::<DebtPayment>(db.conn(), &ctx.household_id)?
        .into_iter()
        .filter(|p| p.debt_id == id)
        .map(|p| p.meta.id)
        .collect();
    let now = env.clock.now();
    db.transaction::<(), ServiceError>(|tx| {
        for i in &view.instalments {
            repo::soft_delete::<DebtInstalment>(tx, &i.meta.id, now)?;
        }
        for p in &pays {
            repo::soft_delete::<DebtPayment>(tx, p, now)?;
        }
        repo::soft_delete::<Debt>(tx, id, now)?;
        Ok(())
    })
}

#[derive(Debug, Clone)]
pub struct Overview {
    pub active_count: usize,
    /// Faol qarzlar bo'yicha jadvaldagi qoldiq + do'kon nasiyasi qoldig'i.
    pub total_remaining: Money,
    pub nasiya_remaining: Money,
    /// Faol qarzlarning o'rtacha oylik to'lovlari yig'indisi.
    pub monthly_load: Money,
    /// Oylik yuk / daromad (bp); daromad yo'q bo'lsa `None`.
    pub burden_bp: Option<u32>,
    /// Faol qarzlardagi ortiqcha to'lov (haqiqiy narx) jami.
    pub excess_total: Money,
    /// Faol, ustamali qarz bor (darvoza «foizli qarz» sharti).
    pub has_markup_debt: bool,
    /// Muddati o'tgan to'lov bor.
    pub any_overdue: bool,
}

/// # Errors
/// Baza xatosi.
pub fn overview(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<Overview, ServiceError> {
    let views = list(conn, env, ctx)?;
    let active: Vec<&DebtView> = views.iter().filter(|v| v.active()).collect();
    let nasiya = crate::obligations::list(conn, ctx)?
        .into_iter()
        .filter_map(|o| o.remaining)
        .collect::<Vec<_>>();
    let nasiya_remaining = sum_money(ctx.currency, nasiya)?;
    let remaining = sum_money(ctx.currency, active.iter().map(|v| v.remaining))?;
    let monthly_load = sum_money(ctx.currency, active.iter().map(|v| v.debt.monthly_payment))?;
    let burden = match reference_income(conn, env, ctx)? {
        Some(inc) => Some(burden_bp(monthly_load, inc)?),
        None => None,
    };
    Ok(Overview {
        active_count: active.len(),
        total_remaining: remaining.checked_add(nasiya_remaining)?,
        nasiya_remaining,
        monthly_load,
        burden_bp: burden,
        excess_total: sum_money(ctx.currency, active.iter().map(|v| v.cost.excess))?,
        has_markup_debt: active.iter().any(|v| v.has_markup()),
        any_overdue: active.iter().any(|v| v.overdue),
    })
}

/// Faol ustamali qarz bormi (darvoza uchun).
///
/// # Errors
/// Baza xatosi.
pub fn has_markup_debt(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<bool, ServiceError> {
    Ok(overview(conn, env, ctx)?.has_markup_debt)
}
