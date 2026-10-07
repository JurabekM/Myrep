//! «Juma shirinligi» (SPEC 2B.4): kundalik havasni haftalik ritualga aylantirish.
use domain::{Date, Expense, Meta, PaymentChannel, ScheduledTreat};
use money::Money;
use storage::{repo, Connection, Database};

use crate::{local_date, setup::TREAT_CATEGORY, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct TreatToday {
    pub treat: ScheduledTreat,
    pub logged_today: bool,
}

/// # Errors
/// Nom bo'sh, summa yoki hafta kuni yaroqsiz bo'lsa.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    amount: Money,
    weekday: u8,
) -> Result<ScheduledTreat, ServiceError> {
    let name = name.trim();
    if name.is_empty() || name.chars().count() > 60 {
        return Err(ServiceError::Invalid("nom 1..60 belgi bo'lishi kerak"));
    }
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    if !(1..=7).contains(&weekday) {
        return Err(ServiceError::Invalid("hafta kuni 1..7"));
    }
    let t = ScheduledTreat {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        amount,
        weekday,
        active: true,
    };
    repo::insert(db.conn(), &t)?;
    Ok(t)
}

/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<ScheduledTreat>, ServiceError> {
    Ok(repo::list::<ScheduledTreat>(conn, &ctx.household_id)?)
}

fn find(conn: &Connection, ctx: &Ctx, id: &str) -> Result<ScheduledTreat, ServiceError> {
    repo::get::<ScheduledTreat>(conn, id)?
        .filter(|t| t.meta.household_id == ctx.household_id)
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
    let mut t = find(db.conn(), ctx, id)?;
    if t.active != active {
        t.active = active;
        repo::update(db.conn(), &t, env.clock.now())?;
    }
    Ok(())
}

/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    find(db.conn(), ctx, id)?;
    repo::soft_delete::<ScheduledTreat>(db.conn(), id, env.clock.now())?;
    Ok(())
}

fn weekday_number(d: Date) -> u8 {
    d.weekday().number_from_monday()
}

fn treat_category(conn: &Connection, ctx: &Ctx) -> Result<String, ServiceError> {
    crate::categories::by_name(conn, ctx, TREAT_CATEGORY)?
        .map(|c| c.meta.id)
        .ok_or(ServiceError::NotFound)
}

fn logged_on(
    conn: &Connection,
    ctx: &Ctx,
    t: &ScheduledTreat,
    day: Date,
) -> Result<bool, ServiceError> {
    let cat = treat_category(conn, ctx)?;
    Ok(repo::list::<Expense>(conn, &ctx.household_id)?
        .iter()
        .any(|e| {
            e.spent_on == day && e.category_id == cat && e.note.as_deref() == Some(t.name.as_str())
        }))
}

/// Bugun rejalashtirilgan faol shirinliklar.
///
/// # Errors
/// Baza xatosi.
pub fn due_today(
    conn: &Connection,
    ctx: &Ctx,
    today: Date,
) -> Result<Vec<TreatToday>, ServiceError> {
    list(conn, ctx)?
        .into_iter()
        .filter(|t| t.active && t.weekday == weekday_number(today))
        .map(|t| {
            Ok(TreatToday {
                logged_today: logged_on(conn, ctx, &t, today)?,
                treat: t,
            })
        })
        .collect()
}

/// Shirinlikni bugungi xarajat sifatida yozadi (havas chegarasiga kiradi). Kuniga bir marta.
///
/// # Errors
/// Topilmasa yoki bugun allaqachon yozilgan bo'lsa.
pub fn log(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let t = find(db.conn(), ctx, id)?;
    let today = local_date(env.clock.now());
    if logged_on(db.conn(), ctx, &t, today)? {
        return Err(ServiceError::Invalid("bugun allaqachon yozilgan"));
    }
    let category_id = treat_category(db.conn(), ctx)?;
    repo::insert(
        db.conn(),
        &Expense {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            member_id: ctx.member_id.clone(),
            category_id,
            amount: t.amount,
            spent_on: today,
            payment_channel: PaymentChannel::Cash,
            necessity: None,
            envelope_id: None,
            is_gift: Some(false),
            is_ostentation: Some(false),
            funded_by_debt: Some(false),
            audit_month: None,
            note: Some(t.name),
        },
    )?;
    Ok(())
}
