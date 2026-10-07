//! "Avval o'zingga to'la" ulush qoidasi (SPEC 2.2): bitta faol qoida.
use domain::{AllocationKind, AllocationRule, Meta, OffsetDateTime, ShareRule};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{Ctx, Env, ServiceError};

#[derive(Debug, Clone, Copy)]
pub struct ActiveRule {
    pub rule: ShareRule,
    pub since: OffsetDateTime,
}

/// # Errors
/// Baza xatosi yoki qoida yo'q.
pub fn current(conn: &Connection, ctx: &Ctx) -> Result<ActiveRule, ServiceError> {
    let row = repo::list::<AllocationRule>(conn, &ctx.household_id)?
        .into_iter()
        .next_back()
        .ok_or(ServiceError::NotFound)?;
    let rule = match row.kind {
        AllocationKind::Percent => ShareRule::Percent {
            bp: u32::try_from(row.value).map_err(|_| ServiceError::Invalid("foiz noto'g'ri"))?,
        },
        AllocationKind::FixedAmount => ShareRule::MonthlyFixed {
            target: Money::new(row.value, row.currency.unwrap_or(ctx.currency)),
        },
    };
    Ok(ActiveRule {
        rule,
        since: row.meta.created_at,
    })
}

/// Yangi qoida o'rnatadi (eskisi arxivlanadi: tarix saqlanadi).
///
/// # Errors
/// Qiymat yaroqsiz bo'lsa yoki baza xatosi.
pub fn set(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    rule: ShareRule,
) -> Result<(), ServiceError> {
    let (kind, value, currency) = match rule {
        ShareRule::Percent { bp } if (1..=10_000).contains(&bp) => {
            (AllocationKind::Percent, i64::from(bp), None)
        }
        ShareRule::MonthlyFixed { target }
            if target.minor() > 0 && target.currency() == ctx.currency =>
        {
            (
                AllocationKind::FixedAmount,
                target.minor(),
                Some(target.currency()),
            )
        }
        _ => return Err(ServiceError::Invalid("ulush qiymati yaroqsiz")),
    };
    db.transaction::<(), ServiceError>(|tx| {
        let now = env.clock.now();
        for old in repo::list::<AllocationRule>(tx, &ctx.household_id)? {
            repo::soft_delete::<AllocationRule>(tx, &old.meta.id, now)?;
        }
        repo::insert(
            tx,
            &AllocationRule {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                kind,
                value,
                currency,
            },
        )?;
        Ok(())
    })?;
    Ok(())
}
