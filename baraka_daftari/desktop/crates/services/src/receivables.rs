//! Foydalanuvchi bergan qarzlar (SPEC 2C.7, 2D.5). Faqat foizsiz (qarzi hasana): foiz maydoni yo'q.
//! Muddat kelganda xushmuomala eslatma; majburlash yo'q.
use domain::{Date, Meta, Receivable};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{local_date, sum_money, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct ReceivableView {
    pub item: Receivable,
    pub outstanding: Money,
    /// Muddat kelgan (yoki o'tgan) va hali to'liq qaytmagan: eslatma ko'rsatiladi.
    pub due: bool,
}

fn view(r: Receivable, today: Date) -> Result<ReceivableView, ServiceError> {
    let outstanding = r.amount.checked_sub(r.returned)?;
    let due = outstanding.minor() > 0 && r.due_on.is_some_and(|d| d <= today);
    Ok(ReceivableView {
        item: r,
        outstanding,
        due,
    })
}

/// # Errors
/// Baza xatosi.
pub fn list(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
) -> Result<Vec<ReceivableView>, ServiceError> {
    let today = local_date(env.clock.now());
    let mut v = repo::list::<Receivable>(conn, &ctx.household_id)?
        .into_iter()
        .map(|r| view(r, today))
        .collect::<Result<Vec<_>, _>>()?;
    v.sort_by_key(|x| {
        (
            x.outstanding.minor() == 0,
            x.item.due_on.unwrap_or(Date::MAX),
            x.item.meta.id.clone(),
        )
    });
    Ok(v)
}

/// Berilgan qarzlarning qaytmagan jami.
///
/// # Errors
/// Baza xatosi.
pub fn outstanding_total(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
) -> Result<Money, ServiceError> {
    Ok(sum_money(
        ctx.currency,
        list(conn, env, ctx)?.iter().map(|v| v.outstanding),
    )?)
}

/// Berilgan qarz ma'lumotlari.
#[derive(Debug, Clone, Copy)]
pub struct NewReceivable<'a> {
    pub debtor: &'a str,
    pub amount: Money,
    pub given_on: Option<Date>,
    pub due_on: Option<Date>,
    pub note: Option<&'a str>,
}

/// # Errors
/// Ism bo'sh, summa musbat emas yoki muddat berilgan sanadan oldin bo'lsa.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewReceivable<'_>,
) -> Result<Receivable, ServiceError> {
    let NewReceivable {
        debtor,
        amount,
        given_on,
        due_on,
        note,
    } = new;
    let debtor = debtor.trim();
    if debtor.is_empty() || debtor.chars().count() > 80 {
        return Err(ServiceError::Invalid("qarzdor ismini yozing"));
    }
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let given_on = given_on.unwrap_or_else(|| local_date(env.clock.now()));
    if due_on.is_some_and(|d| d < given_on) {
        return Err(ServiceError::Invalid(
            "muddat berilgan sanadan oldin bo'lmasin",
        ));
    }
    let r = Receivable {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        debtor: debtor.to_owned(),
        amount,
        given_on,
        due_on,
        note: note
            .map(str::trim)
            .filter(|n| !n.is_empty())
            .map(|n| n.chars().take(200).collect()),
        returned: ctx.zero(),
    };
    repo::insert(db.conn(), &r)?;
    Ok(r)
}

/// Qaytarilgan qismni qayd qiladi (qoldiqdan ko'p bo'lmasin).
///
/// # Errors
/// Topilmasa yoki summa yaroqsiz bo'lsa.
pub fn record_return(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    amount: Money,
) -> Result<(), ServiceError> {
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let mut r = repo::get::<Receivable>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if r.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    let new_returned = r.returned.checked_add(amount)?;
    if new_returned.minor() > r.amount.minor() {
        return Err(ServiceError::Invalid("qaytarilgan summa qarzdan ko'p"));
    }
    r.returned = new_returned;
    repo::update(db.conn(), &r, env.clock.now())?;
    Ok(())
}

/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let r = repo::get::<Receivable>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if r.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    repo::soft_delete::<Receivable>(db.conn(), id, env.clock.now())?;
    Ok(())
}
