//! "Pul qayerga ketdi?" oylik audit va "Kimning puli?" (SPEC 2.3, 2.4).
use domain::{
    month_result, unexplained_gap, whose_money, Category, Expense, Meta, MoneyOwner,
    PaymentChannel, WhoseMoney,
};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{income, obligations, sum_money, vault, Ctx, Env, ServiceError, YearMonth};

#[derive(Debug, Clone)]
pub struct CategoryTotal {
    pub category_id: String,
    pub name: String,
    pub owner: Option<MoneyOwner>,
    pub amount: Money,
}

#[derive(Debug, Clone)]
pub struct Overview {
    pub month: YearMonth,
    pub income: Money,
    pub obligations: Money,
    pub expenses: Money,
    /// Shu oy "Kelajagim"ga ajratilgan.
    pub savings: Money,
    /// Oy yakuni: plyus yoki minus.
    pub month_result: Money,
    pub unexplained: Money,
    pub categories: Vec<CategoryTotal>,
    pub whose: WhoseMoney,
}

fn month_expenses(
    conn: &Connection,
    ctx: &Ctx,
    ym: YearMonth,
) -> Result<Vec<Expense>, ServiceError> {
    Ok(repo::list::<Expense>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| ym.contains(e.spent_on))
        .collect())
}

/// # Errors
/// Baza xatosi yoki valyuta mos kelmasa.
pub fn overview(conn: &Connection, ctx: &Ctx, ym: YearMonth) -> Result<Overview, ServiceError> {
    let cur = ctx.currency;
    let categories = repo::list::<Category>(conn, &ctx.household_id)?;
    let expenses = month_expenses(conn, ctx, ym)?;

    let totals = categories
        .iter()
        .map(|c| {
            let amount = sum_money(
                cur,
                expenses
                    .iter()
                    .filter(|e| e.category_id == c.meta.id)
                    .map(|e| e.amount),
            )?;
            Ok(CategoryTotal {
                category_id: c.meta.id.clone(),
                name: c.name.clone(),
                owner: c.owner,
                amount,
            })
        })
        .collect::<Result<Vec<_>, ServiceError>>()?;

    let income_total = income::month_total(conn, ctx, ym)?;
    let obligations_total = obligations::monthly_total(conn, ctx)?;
    let expenses_total = sum_money(cur, expenses.iter().map(|e| e.amount))?;
    let savings = vault::allocated_in(conn, ctx, ym)?;

    let mut owner_amounts: Vec<(MoneyOwner, Money)> = obligations::list(conn, ctx)?
        .into_iter()
        .filter(|o| o.kind == domain::ObligationKind::Recurring)
        .map(|o| (o.owner, o.amount))
        .collect();
    owner_amounts.extend(
        totals
            .iter()
            .map(|c| (c.owner.unwrap_or(MoneyOwner::Other), c.amount)),
    );

    Ok(Overview {
        month: ym,
        income: income_total,
        obligations: obligations_total,
        expenses: expenses_total,
        savings,
        month_result: month_result(income_total, obligations_total, expenses_total)?,
        unexplained: unexplained_gap(income_total, obligations_total, expenses_total, savings)?,
        categories: totals,
        whose: whose_money(income_total, &owner_amounts, savings)?,
    })
}

/// Audit ustasi bitta kategoriya uchun oylik jami kiritadi. Oldingi audit yozuvi almashtiriladi
/// (qayta kiritish ikki marta hisoblanmaydi). `0` — yozuvni olib tashlaydi.
///
/// # Errors
/// Kategoriya topilmasa, summa manfiy yoki valyuta mos kelmasa.
pub fn set_category_total(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    ym: YearMonth,
    category_id: &str,
    amount: Money,
) -> Result<(), ServiceError> {
    if amount.minor() < 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa 0 dan kam bo'lmasligi kerak"));
    }
    let category = repo::get::<Category>(db.conn(), category_id)?.ok_or(ServiceError::NotFound)?;
    if category.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    let month_text = ym.text();
    db.transaction(|tx| {
        let now = env.clock.now();
        for old in repo::list::<Expense>(tx, &ctx.household_id)?
            .into_iter()
            .filter(|e| {
                e.audit_month.as_deref() == Some(month_text.as_str())
                    && e.category_id == category_id
            })
        {
            repo::soft_delete::<Expense>(tx, &old.meta.id, now)?;
        }
        if amount.minor() > 0 {
            repo::insert(
                tx,
                &Expense {
                    meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                    member_id: ctx.member_id.clone(),
                    category_id: category_id.to_owned(),
                    amount,
                    spent_on: ym.last_day(),
                    payment_channel: PaymentChannel::Cash,
                    necessity: None,
                    envelope_id: None,
                    is_gift: None,
                    is_ostentation: None,
                    funded_by_debt: None,
                    audit_month: Some(month_text.clone()),
                },
            )?;
        }
        Ok(())
    })
}
