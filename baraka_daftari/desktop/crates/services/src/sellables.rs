//! «Sotiladigan buyumlar» (SPEC 2D.7): sotilgan buyum tushumi bir bosishda qarzga qo'shimcha to'lov bo'ladi.
use domain::{Date, Meta, SellStatus, SellableItem};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{debts, local_date, Ctx, Env, ServiceError};

/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<SellableItem>, ServiceError> {
    let mut v = repo::list::<SellableItem>(conn, &ctx.household_id)?;
    v.sort_by_key(|i| (i.status == SellStatus::Sold, i.meta.id.clone()));
    Ok(v)
}

/// E'lon qilinmagan (sotilmagan) buyumlarning taxminiy narxi jami.
///
/// # Errors
/// Baza xatosi.
pub fn listed_total(conn: &Connection, ctx: &Ctx) -> Result<Money, ServiceError> {
    Ok(crate::sum_money(
        ctx.currency,
        list(conn, ctx)?
            .into_iter()
            .filter(|i| i.status == SellStatus::Listed)
            .map(|i| i.estimated_price),
    )?)
}

/// # Errors
/// Nom bo'sh yoki narx musbat bo'lmasa.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    price: Money,
    unused_since: Option<Date>,
) -> Result<SellableItem, ServiceError> {
    let name = name.trim();
    if name.is_empty() || name.chars().count() > 80 {
        return Err(ServiceError::Invalid("buyum nomini yozing"));
    }
    if price.minor() <= 0 || price.currency() != ctx.currency {
        return Err(ServiceError::Invalid("narx musbat bo'lishi kerak"));
    }
    let item = SellableItem {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        estimated_price: price,
        unused_since,
        status: SellStatus::Listed,
        sold_amount: None,
        sold_on: None,
        debt_id: None,
    };
    repo::insert(db.conn(), &item)?;
    Ok(item)
}

/// Buyumni sotilgan deb belgilaydi. `debt_id` berilsa, tushum (qarz qoldig'idan oshmagan qismi)
/// shu qarzga qo'shimcha to'lov bo'ladi. To'langan summani qaytaradi.
///
/// # Errors
/// Buyum/qarz topilmasa, allaqachon sotilgan yoki summa yaroqsiz bo'lsa.
pub fn sell(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    amount: Money,
    debt_id: Option<&str>,
) -> Result<Money, ServiceError> {
    let mut item = repo::get::<SellableItem>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if item.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    if item.status == SellStatus::Sold {
        return Err(ServiceError::Invalid("buyum allaqachon sotilgan"));
    }
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let mut paid = ctx.zero();
    if let Some(did) = debt_id {
        let remaining = debts::get(db.conn(), env, ctx, did)?.remaining;
        paid = Money::new(amount.minor().min(remaining.minor()), ctx.currency);
        if paid.minor() > 0 {
            debts::pay(db, env, ctx, did, paid, None, None)?;
        }
    }
    item.status = SellStatus::Sold;
    item.sold_amount = Some(amount);
    item.sold_on = Some(local_date(env.clock.now()));
    item.debt_id = debt_id.map(str::to_owned);
    repo::update(db.conn(), &item, env.clock.now())?;
    Ok(paid)
}

/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let item = repo::get::<SellableItem>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if item.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    repo::soft_delete::<SellableItem>(db.conn(), id, env.clock.now())?;
    Ok(())
}
