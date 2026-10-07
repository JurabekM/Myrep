//! Qarzni bir necha kishi to'lashi (SPEC 2D.4): har bir to'lovchining oylik ulushi va to'lov tarixi.
use std::collections::BTreeMap;

use domain::{DebtContributor, DebtPayment, Meta};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{debts, members, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct ContributorView {
    pub member_id: String,
    pub name: String,
    /// Reja bo'yicha oylik ulush (belgilanmagan bo'lsa `None`).
    pub monthly_share: Option<Money>,
    /// Shu a'zo to'lagan jami.
    pub paid: Money,
}

/// To'lovchilar: ulush belgilanganlar va shu qarzga haqiqatan to'laganlar.
///
/// # Errors
/// Qarz topilmasa yoki baza xatosi.
pub fn list(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    debt_id: &str,
) -> Result<Vec<ContributorView>, ServiceError> {
    debts::get(conn, env, ctx, debt_id)?;
    let shares: BTreeMap<String, Money> = repo::list::<DebtContributor>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|c| c.debt_id == debt_id)
        .map(|c| (c.member_id, c.monthly_share))
        .collect();
    let mut paid: BTreeMap<String, Money> = BTreeMap::new();
    for p in repo::list::<DebtPayment>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|p| p.debt_id == debt_id)
    {
        let e = paid.entry(p.member_id).or_insert_with(|| ctx.zero());
        *e = e.checked_add(p.amount)?;
    }
    let names: BTreeMap<String, String> = members::list(conn, ctx)?
        .into_iter()
        .map(|m| (m.meta.id, m.display_name))
        .collect();
    let mut ids: Vec<&String> = shares.keys().chain(paid.keys()).collect();
    ids.sort();
    ids.dedup();
    Ok(ids
        .into_iter()
        .map(|id| ContributorView {
            member_id: id.clone(),
            name: names.get(id).cloned().unwrap_or_default(),
            monthly_share: shares.get(id).copied(),
            paid: paid.get(id).copied().unwrap_or_else(|| ctx.zero()),
        })
        .collect())
}

/// A'zoning oylik ulushini belgilaydi (mavjud bo'lsa yangilaydi).
///
/// # Errors
/// Qarz yoki a'zo topilmasa, ulush manfiy bo'lsa.
pub fn set_share(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    debt_id: &str,
    member_id: &str,
    share: Money,
) -> Result<(), ServiceError> {
    if share.minor() < 0 || share.currency() != ctx.currency {
        return Err(ServiceError::Invalid("ulush manfiy bo'lmasin"));
    }
    debts::get(db.conn(), env, ctx, debt_id)?;
    if !members::list(db.conn(), ctx)?
        .iter()
        .any(|m| m.meta.id == member_id)
    {
        return Err(ServiceError::NotFound);
    }
    let existing = repo::list::<DebtContributor>(db.conn(), &ctx.household_id)?
        .into_iter()
        .find(|c| c.debt_id == debt_id && c.member_id == member_id);
    match existing {
        Some(mut c) => {
            c.monthly_share = share;
            repo::update(db.conn(), &c, env.clock.now())?;
        }
        None => repo::insert(
            db.conn(),
            &DebtContributor {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                debt_id: debt_id.to_owned(),
                member_id: member_id.to_owned(),
                monthly_share: share,
            },
        )?,
    }
    Ok(())
}

/// # Errors
/// Baza xatosi.
pub fn remove(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    debt_id: &str,
    member_id: &str,
) -> Result<(), ServiceError> {
    let found: Vec<String> = repo::list::<DebtContributor>(db.conn(), &ctx.household_id)?
        .into_iter()
        .filter(|c| c.debt_id == debt_id && c.member_id == member_id)
        .map(|c| c.meta.id)
        .collect();
    for id in found {
        repo::soft_delete::<DebtContributor>(db.conn(), &id, env.clock.now())?;
    }
    Ok(())
}
