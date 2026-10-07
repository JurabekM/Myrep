//! Majburiyatlar va nasiya daftari (SPEC 2.5).
use domain::{
    Category, Date, Expense, Meta, MoneyOwner, Obligation, ObligationKind, PaymentChannel,
};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{local_date, setup::NASIYA_CATEGORY, sum_money, Ctx, Env, ServiceError};

/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<Obligation>, ServiceError> {
    Ok(repo::list::<Obligation>(conn, &ctx.household_id)?)
}

/// Oylik doimiy to'lovlar yig'indisi (nasiya qarzi kirmaydi: uning to'lovlari xarajat sifatida).
///
/// # Errors
/// Baza xatosi yoki valyuta mos kelmasa.
pub fn monthly_total(conn: &Connection, ctx: &Ctx) -> Result<Money, ServiceError> {
    Ok(sum_money(
        ctx.currency,
        list(conn, ctx)?
            .into_iter()
            .filter(|o| o.kind == ObligationKind::Recurring)
            .map(|o| o.amount),
    )?)
}

fn check_money(ctx: &Ctx, amount: Money) -> Result<(), ServiceError> {
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    Ok(())
}

/// # Errors
/// Nom bo'sh, summa yoki to'lov kuni yaroqsiz, yoki baza xatosi.
pub fn add_recurring(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    amount: Money,
    due_day: u8,
    owner: MoneyOwner,
) -> Result<Obligation, ServiceError> {
    let name = name.trim();
    if name.is_empty() {
        return Err(ServiceError::Invalid("nomini yozing"));
    }
    check_money(ctx, amount)?;
    if !(1..=31).contains(&due_day) {
        return Err(ServiceError::Invalid("to'lov kuni 1..31"));
    }
    let o = Obligation {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        amount,
        due_day,
        kind: ObligationKind::Recurring,
        owner,
        creditor: None,
        remaining: None,
    };
    repo::insert(db.conn(), &o)?;
    Ok(o)
}

/// Do'kondagi nasiya: kimga va qancha qarzdorligi.
///
/// # Errors
/// Kreditor nomi bo'sh yoki summa yaroqsiz bo'lsa.
pub fn add_nasiya(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    creditor: &str,
    total: Money,
) -> Result<Obligation, ServiceError> {
    let creditor = creditor.trim();
    if creditor.is_empty() {
        return Err(ServiceError::Invalid("do'kondor nomini yozing"));
    }
    check_money(ctx, total)?;
    let o = Obligation {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: format!("Nasiya: {creditor}"),
        amount: total,
        due_day: 1,
        kind: ObligationKind::Nasiya,
        owner: MoneyOwner::Shop,
        creditor: Some(creditor.to_owned()),
        remaining: Some(total),
    };
    repo::insert(db.conn(), &o)?;
    Ok(o)
}

/// Nasiyaga to'lov: qoldiq kamayadi va "Nasiya to'lovi" xarajati yoziladi. Yangi qoldiqni qaytaradi.
///
/// # Errors
/// Nasiya topilmasa, summa qoldiqdan ko'p yoki yaroqsiz bo'lsa.
pub fn pay_nasiya(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    amount: Money,
    paid_on: Option<Date>,
) -> Result<Money, ServiceError> {
    check_money(ctx, amount)?;
    let mut o = repo::get::<Obligation>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if o.meta.household_id != ctx.household_id || o.kind != ObligationKind::Nasiya {
        return Err(ServiceError::NotFound);
    }
    let remaining = o.remaining.ok_or(ServiceError::NotFound)?;
    if amount.minor() > remaining.minor() {
        return Err(ServiceError::Invalid("to'lov qoldiqdan ko'p"));
    }
    let category = repo::list::<Category>(db.conn(), &ctx.household_id)?
        .into_iter()
        .find(|c| c.name == NASIYA_CATEGORY)
        .ok_or(ServiceError::NotFound)?;
    let left = remaining.checked_sub(amount)?;
    db.transaction(|tx| {
        repo::insert(
            tx,
            &Expense {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                member_id: ctx.member_id.clone(),
                category_id: category.meta.id,
                amount,
                spent_on: paid_on.unwrap_or_else(|| local_date(env.clock.now())),
                payment_channel: PaymentChannel::Cash,
                necessity: None,
                envelope_id: None,
                is_gift: None,
                is_ostentation: None,
                funded_by_debt: None,
                audit_month: None,
            },
        )?;
        o.remaining = Some(left);
        repo::update(tx, &o, env.clock.now())?;
        Ok(left)
    })
}

/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let o = repo::get::<Obligation>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if o.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    repo::soft_delete::<Obligation>(db.conn(), id, env.clock.now())?;
    Ok(())
}
