//! Haftalik konvertlar (SPEC 2B.6). Karta bilan to'langan pul «sezilmay» ketmasligi uchun kartadagi
//! xarajatlar ham konvertdan ayriladi. Hafta oxirida naqd qoldiq kiritiladi.
use domain::{
    cash_to_fill, closing_difference, counts_as_havas, effective_necessity, envelope_status,
    week_start, Category, Date, Envelope, EnvelopePeriod, EnvelopeStatus, Expense, Meta, Necessity,
};
use money::Money;
use std::collections::HashMap;
use storage::{repo, Connection, Database};
use time::Duration;

use crate::{home::WEEK_ANCHOR, local_date, sum_money, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct EnvelopeView {
    pub envelope: Envelope,
    pub week_start: Date,
    pub spent: Money,
    pub status: EnvelopeStatus,
    /// Jismoniy konvertga hozir solinadigan naqd.
    pub cash_to_fill: Money,
    /// Shu hafta yopilgan bo'lsa.
    pub closed: Option<EnvelopePeriod>,
}

/// # Errors
/// Nom bo'sh, limit musbat emas yoki kategoriya topilmasa.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    weekly_limit: Money,
    category_id: Option<String>,
    necessity: Option<Necessity>,
) -> Result<Envelope, ServiceError> {
    let name = name.trim();
    if name.is_empty() || name.chars().count() > 60 {
        return Err(ServiceError::Invalid("nom 1..60 belgi bo'lishi kerak"));
    }
    if weekly_limit.minor() <= 0 || weekly_limit.currency() != ctx.currency {
        return Err(ServiceError::Invalid(
            "haftalik limit musbat bo'lishi kerak",
        ));
    }
    if let Some(id) = &category_id {
        if !crate::categories::list(db.conn(), ctx)?
            .iter()
            .any(|c| &c.meta.id == id)
        {
            return Err(ServiceError::NotFound);
        }
    }
    let e = Envelope {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        weekly_limit,
        category_id,
        necessity,
        active: true,
    };
    repo::insert(db.conn(), &e)?;
    Ok(e)
}

fn find(conn: &Connection, ctx: &Ctx, id: &str) -> Result<Envelope, ServiceError> {
    repo::get::<Envelope>(conn, id)?
        .filter(|e| e.meta.household_id == ctx.household_id)
        .ok_or(ServiceError::NotFound)
}

/// # Errors
/// Topilmasa.
pub fn set_active(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    active: bool,
) -> Result<(), ServiceError> {
    let mut e = find(db.conn(), ctx, id)?;
    if e.active != active {
        e.active = active;
        repo::update(db.conn(), &e, env.clock.now())?;
    }
    Ok(())
}

/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    find(db.conn(), ctx, id)?;
    repo::soft_delete::<Envelope>(db.conn(), id, env.clock.now())?;
    Ok(())
}

/// Xarajat konvertga tegishlimi: aniq `envelope_id`, yoki (belgilanmagan bo'lsa) kategoriya/toifa bo'yicha.
/// Sadaqa hech qachon konvertga kirmaydi; «Havas» konverti sovg'ani ham hisobga olmaydi (havas qoidasi bilan bir xil).
fn belongs(env: &Envelope, e: &Expense, cat: &Category) -> bool {
    if cat.is_charity {
        return false;
    }
    if let Some(id) = &e.envelope_id {
        return *id == env.meta.id;
    }
    let nec = effective_necessity(e.necessity, cat.necessity);
    let by_category = env.category_id.as_deref() == Some(cat.meta.id.as_str());
    let by_necessity = match env.necessity {
        Some(Necessity::Havas) => counts_as_havas(nec, e.is_gift == Some(true), cat.is_charity),
        Some(n) => nec == Some(n),
        None => false,
    };
    by_category || by_necessity
}

fn spent_in_week(
    envelope: &Envelope,
    expenses: &[Expense],
    categories: &HashMap<String, Category>,
    ws: Date,
    currency: money::Currency,
) -> Result<Money, ServiceError> {
    let end = ws + Duration::days(6);
    Ok(sum_money(
        currency,
        expenses
            .iter()
            .filter(|e| e.spent_on >= ws && e.spent_on <= end)
            .filter(|e| {
                categories
                    .get(&e.category_id)
                    .is_some_and(|c| belongs(envelope, e, c))
            })
            .map(|e| e.amount),
    )?)
}

fn view(
    conn: &Connection,
    ctx: &Ctx,
    envelope: Envelope,
    ws: Date,
    expenses: &[Expense],
    categories: &HashMap<String, Category>,
) -> Result<EnvelopeView, ServiceError> {
    let spent = spent_in_week(&envelope, expenses, categories, ws, ctx.currency)?;
    let invalid = |_| ServiceError::Invalid("konvert hisoblanmadi");
    let status = envelope_status(envelope.weekly_limit, spent).map_err(invalid)?;
    let fill = cash_to_fill(envelope.weekly_limit, spent).map_err(invalid)?;
    let closed = repo::list::<EnvelopePeriod>(conn, &ctx.household_id)?
        .into_iter()
        .find(|p| p.envelope_id == envelope.meta.id && p.week_start == ws);
    Ok(EnvelopeView {
        envelope,
        week_start: ws,
        spent,
        status,
        cash_to_fill: fill,
        closed,
    })
}

/// Hafta (`any_day` kiritilgan haftaning jumasi) uchun barcha faol konvertlar holati.
///
/// # Errors
/// Baza xatosi.
pub fn status(
    conn: &Connection,
    ctx: &Ctx,
    any_day: Date,
) -> Result<Vec<EnvelopeView>, ServiceError> {
    let ws = week_start(any_day, WEEK_ANCHOR);
    let expenses = repo::list::<Expense>(conn, &ctx.household_id)?;
    let categories: HashMap<String, Category> = repo::list::<Category>(conn, &ctx.household_id)?
        .into_iter()
        .map(|c| (c.meta.id.clone(), c))
        .collect();
    repo::list::<Envelope>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| e.active)
        .map(|e| view(conn, ctx, e, ws, &expenses, &categories))
        .collect()
}

/// Haftani yopadi: naqd qoldiqni yozadi va farqni hisoblaydi (qayta yopilsa yangilanadi).
/// Kelajak haftasini yopib bo'lmaydi.
///
/// # Errors
/// Konvert topilmasa, qoldiq manfiy yoki hafta kelajakda bo'lsa.
pub fn close_week(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    envelope_id: &str,
    any_day: Date,
    leftover_cash: Money,
) -> Result<EnvelopePeriod, ServiceError> {
    if leftover_cash.minor() < 0 || leftover_cash.currency() != ctx.currency {
        return Err(ServiceError::Invalid(
            "naqd qoldiq 0 dan kam bo'lmasligi kerak",
        ));
    }
    let envelope = find(db.conn(), ctx, envelope_id)?;
    let ws = week_start(any_day, WEEK_ANCHOR);
    if ws > local_date(env.clock.now()) {
        return Err(ServiceError::Invalid("kelajak haftasini yopib bo'lmaydi"));
    }
    let expenses = repo::list::<Expense>(db.conn(), &ctx.household_id)?;
    let categories: HashMap<String, Category> =
        repo::list::<Category>(db.conn(), &ctx.household_id)?
            .into_iter()
            .map(|c| (c.meta.id.clone(), c))
            .collect();
    let spent = spent_in_week(&envelope, &expenses, &categories, ws, ctx.currency)?;
    let difference = closing_difference(envelope.weekly_limit, spent, leftover_cash)
        .map_err(|_| ServiceError::Invalid("farq hisoblanmadi"))?;
    let existing = repo::list::<EnvelopePeriod>(db.conn(), &ctx.household_id)?
        .into_iter()
        .find(|p| p.envelope_id == envelope_id && p.week_start == ws);
    match existing {
        Some(mut p) => {
            p.limit = envelope.weekly_limit;
            p.spent = spent;
            p.leftover_cash = leftover_cash;
            p.difference = difference;
            repo::update(db.conn(), &p, env.clock.now())?;
            Ok(p)
        }
        None => {
            let p = EnvelopePeriod {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                envelope_id: envelope_id.to_owned(),
                week_start: ws,
                limit: envelope.weekly_limit,
                spent,
                leftover_cash,
                difference,
            };
            repo::insert(db.conn(), &p)?;
            Ok(p)
        }
    }
}
