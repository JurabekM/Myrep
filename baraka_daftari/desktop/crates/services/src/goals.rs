//! Maqsadli jamg'armalar (`Goal`) va «imkoniyat narxi» taqqoslashi (SPEC 2D.3, 2D.8).
//! MVP'da virtual: haqiqiy pul harakati yo'q, faqat kuzatuv.
use domain::{quantity_milli, Date, Goal, Meta};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{Ctx, Env, ServiceError};

/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<Goal>, ServiceError> {
    Ok(repo::list::<Goal>(conn, &ctx.household_id)?)
}

/// # Errors
/// Nom bo'sh yoki maqsad summasi musbat bo'lmasa.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    target: Money,
    due_on: Option<Date>,
) -> Result<Goal, ServiceError> {
    let name = name.trim();
    if name.is_empty() || name.chars().count() > 80 {
        return Err(ServiceError::Invalid("maqsad nomini yozing"));
    }
    if target.minor() <= 0 || target.currency() != ctx.currency {
        return Err(ServiceError::Invalid(
            "maqsad summasi musbat bo'lishi kerak",
        ));
    }
    let g = Goal {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        name: name.to_owned(),
        target,
        saved: ctx.zero(),
        due_on,
    };
    repo::insert(db.conn(), &g)?;
    Ok(g)
}

/// Maqsadga hissa (virtual).
///
/// # Errors
/// Topilmasa yoki summa musbat bo'lmasa.
pub fn contribute(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
    amount: Money,
) -> Result<Goal, ServiceError> {
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let mut g = repo::get::<Goal>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if g.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    g.saved = g.saved.checked_add(amount)?;
    repo::update(db.conn(), &g, env.clock.now())?;
    Ok(g)
}

/// # Errors
/// Topilmasa.
pub fn remove(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let g = repo::get::<Goal>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if g.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    repo::soft_delete::<Goal>(db.conn(), id, env.clock.now())?;
    Ok(())
}

#[derive(Debug, Clone)]
pub struct Equivalence {
    pub goal_name: String,
    pub goal_target: Money,
    /// `amount` nechta maqsadga teng (1/1000 aniqlikda).
    pub times_milli: i64,
}

/// Imkoniyat narxi: ortiqcha to'langan summa foydalanuvchi maqsadlari bilan taqqoslanadi
/// («bu summa N yillik kontraktga teng»). Faqat summa maqsadning kamida 1/10 qismiga yetsa.
///
/// # Errors
/// Baza xatosi.
pub fn equivalences(
    conn: &Connection,
    ctx: &Ctx,
    amount: Money,
) -> Result<Vec<Equivalence>, ServiceError> {
    if amount.minor() <= 0 {
        return Ok(Vec::new());
    }
    list(conn, ctx)?
        .into_iter()
        .map(|g| {
            let times = quantity_milli(amount, g.target)?;
            Ok((g, times))
        })
        .collect::<Result<Vec<_>, ServiceError>>()
        .map(|v| {
            v.into_iter()
                .filter(|(_, t)| *t >= 100)
                .map(|(g, t)| Equivalence {
                    goal_name: g.name,
                    goal_target: g.target,
                    times_milli: t,
                })
                .collect()
        })
}
