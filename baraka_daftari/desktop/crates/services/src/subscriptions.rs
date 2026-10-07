//! Obunalar va avtoto'lovlar auditi (SPEC 2B.5): oylik/yillik narx, «kerakmi?», unutilgan obuna detektori.
//! MVP'da qo'lda kiritiladi. Bekor qilingan obuna «qutqarilgan pul»ga yoziladi.
use domain::{
    is_forgotten, subscription_cost, BillingPeriod, Date, Meta, RescueKind, SavingsRescue,
    Subscription, SubscriptionCost, FORGOTTEN_AFTER_DAYS,
};
use money::Money;
use storage::{repo, Connection, Database};

use crate::{local_date, sum_money, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct SubscriptionView {
    pub sub: Subscription,
    pub cost: SubscriptionCost,
    pub active: bool,
    /// Faol, lekin uzoq vaqt «ishlatdim» deb belgilanmagan.
    pub forgotten: bool,
}

#[derive(Debug, Clone)]
pub struct Totals {
    pub monthly: Money,
    pub yearly: Money,
}

fn cost(sub: &Subscription) -> Result<SubscriptionCost, ServiceError> {
    subscription_cost(sub.amount, sub.period)
        .map_err(|_| ServiceError::Invalid("obuna narxi noto'g'ri"))
}

/// # Errors
/// Nom bo'sh, narx manfiy yoki boshlanish sanasi kelajakda bo'lsa.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    amount: Money,
    period: BillingPeriod,
    started_on: Option<Date>,
) -> Result<Subscription, ServiceError> {
    let name = name.trim();
    if name.is_empty() || name.chars().count() > 60 {
        return Err(ServiceError::Invalid("nom 1..60 belgi bo'lishi kerak"));
    }
    if amount.minor() < 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("narx 0 dan kam bo'lmasligi kerak"));
    }
    let today = local_date(env.clock.now());
    let started_on = started_on.unwrap_or(today);
    if started_on > today {
        return Err(ServiceError::Invalid(
            "boshlanish sanasi kelajakda bo'lishi mumkin emas",
        ));
    }
    let sub = Subscription {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        amount,
        period,
        started_on,
        last_used_on: None,
        cancelled_on: None,
        needed: None,
    };
    cost(&sub)?;
    repo::insert(db.conn(), &sub)?;
    Ok(sub)
}

fn find(conn: &Connection, ctx: &Ctx, id: &str) -> Result<Subscription, ServiceError> {
    repo::get::<Subscription>(conn, id)?
        .filter(|s| s.meta.household_id == ctx.household_id)
        .ok_or(ServiceError::NotFound)
}

/// Faol obunalar avval, bekor qilinganlar oxirida.
///
/// # Errors
/// Baza xatosi.
pub fn list(
    conn: &Connection,
    ctx: &Ctx,
    today: Date,
) -> Result<Vec<SubscriptionView>, ServiceError> {
    let mut out = repo::list::<Subscription>(conn, &ctx.household_id)?
        .into_iter()
        .map(|sub| {
            let active = sub.cancelled_on.is_none();
            Ok(SubscriptionView {
                cost: cost(&sub)?,
                forgotten: active
                    && is_forgotten(
                        sub.last_used_on,
                        sub.started_on,
                        today,
                        FORGOTTEN_AFTER_DAYS,
                    ),
                active,
                sub,
            })
        })
        .collect::<Result<Vec<_>, ServiceError>>()?;
    out.sort_by_key(|v| !v.active);
    Ok(out)
}

/// Faol obunalarning oylik va yillik jami.
///
/// # Errors
/// Baza xatosi.
pub fn totals(conn: &Connection, ctx: &Ctx, today: Date) -> Result<Totals, ServiceError> {
    let active: Vec<_> = list(conn, ctx, today)?
        .into_iter()
        .filter(|v| v.active)
        .collect();
    Ok(Totals {
        monthly: sum_money(ctx.currency, active.iter().map(|v| v.cost.monthly))?,
        yearly: sum_money(ctx.currency, active.iter().map(|v| v.cost.yearly))?,
    })
}

/// «Ishlatdim» belgisi (bugungi sana).
///
/// # Errors
/// Topilmasa yoki bekor qilingan bo'lsa.
pub fn mark_used(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<(), ServiceError> {
    let mut s = find(db.conn(), ctx, id)?;
    if s.cancelled_on.is_some() {
        return Err(ServiceError::Invalid("obuna bekor qilingan"));
    }
    s.last_used_on = Some(local_date(env.clock.now()));
    repo::update(db.conn(), &s, env.clock.now())?;
    Ok(())
}

/// «Kerakmi?» javobi; `None` — javobni olib tashlash.
///
/// # Errors
/// Topilmasa.
pub fn set_needed(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    needed: Option<bool>,
) -> Result<(), ServiceError> {
    let mut s = find(db.conn(), ctx, id)?;
    s.needed = needed;
    repo::update(db.conn(), &s, env.clock.now())?;
    Ok(())
}

/// Obunani bekor qiladi va bitta oylik narxni «qutqarilgan pul»ga yozadi (va'da emas: yillik prognoz yo'q).
///
/// # Errors
/// Topilmasa yoki allaqachon bekor qilingan bo'lsa.
pub fn cancel(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<Option<SavingsRescue>, ServiceError> {
    let mut s = find(db.conn(), ctx, id)?;
    if s.cancelled_on.is_some() {
        return Err(ServiceError::Invalid("obuna allaqachon bekor qilingan"));
    }
    let monthly = cost(&s)?.monthly;
    let now = env.clock.now();
    db.transaction::<Option<SavingsRescue>, ServiceError>(|tx| {
        s.cancelled_on = Some(local_date(now));
        repo::update(tx, &s, now)?;
        if monthly.minor() <= 0 {
            return Ok(None);
        }
        let rescue = SavingsRescue {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            kind: RescueKind::Subscription,
            amount: monthly,
            week_start: None,
            note: Some(s.name.clone()),
            transferred_at: None,
        };
        repo::insert(tx, &rescue)?;
        Ok(Some(rescue))
    })
}

/// Obunani butunlay o'chiradi (qutqarilgan pul yozilmaydi: kiritish xatosini tuzatish uchun).
///
/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    find(db.conn(), ctx, id)?;
    repo::soft_delete::<Subscription>(db.conn(), id, env.clock.now())?;
    Ok(())
}
