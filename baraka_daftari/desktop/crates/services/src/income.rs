//! Daromad kiritish va ulush taklifi (SPEC 2.1).
use domain::{
    suggest_share, Date, Income, IncomeSourceType, Meta, PaymentChannel, ShareRule, VaultSource,
    VaultTxKind, VaultType,
};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{local_date, rules, sum_money, vault, Ctx, Env, ServiceError, YearMonth};

#[derive(Debug, Clone, Copy)]
pub struct Suggestion {
    pub share: Money,
    pub rule: ShareRule,
    pub allocated_this_month: Money,
}

/// "Shundan X so'm — kelajagingiz uchun": daromad kiritilganda darhol taklif.
///
/// # Errors
/// Summa yaroqsiz yoki baza xatosi.
pub fn suggest(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    amount: Money,
) -> Result<Suggestion, ServiceError> {
    if amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("valyuta mos emas"));
    }
    let rule = rules::current(conn, ctx)?.rule;
    let ym = YearMonth::of(local_date(env.clock.now()));
    let allocated = vault::allocated_in(conn, ctx, ym)?;
    Ok(Suggestion {
        share: suggest_share(rule, amount, allocated)?,
        rule,
        allocated_this_month: allocated,
    })
}

#[derive(Debug, Clone)]
pub struct NewIncome {
    pub amount: Money,
    /// `DAILY_WORK`, `ORDER`, `SALARY`, `OTHER` yoki erkin matn.
    pub source: String,
    pub channel: PaymentChannel,
    pub received_on: Option<Date>,
    /// `None` — taklif qilingan ulush; `Some` — foydalanuvchi o'zgartirgan summa (0 ham mumkin).
    pub share: Option<Money>,
    pub member_id: Option<String>,
    /// Ter / mol / tavakkal testi (ixtiyoriy).
    pub source_type: Option<IncomeSourceType>,
}

#[derive(Debug, Clone)]
pub struct Recorded {
    pub income_id: String,
    pub share: Money,
}

/// Daromad va (bo'lsa) ajratmani bitta tranzaksiyada yozadi.
///
/// # Errors
/// Summa/ulush yaroqsiz, a'zo topilmasa yoki baza xatosi.
pub fn record(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    new: NewIncome,
) -> Result<Recorded, ServiceError> {
    if new.amount.minor() <= 0 || new.amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid(
            "daromad summasi musbat bo'lishi kerak",
        ));
    }
    let source = new.source.trim();
    if source.is_empty() {
        return Err(ServiceError::Invalid("daromad manbasini tanlang"));
    }
    let member_id = new
        .member_id
        .clone()
        .unwrap_or_else(|| ctx.member_id.clone());
    if !repo::list::<domain::Member>(db.conn(), &ctx.household_id)?
        .iter()
        .any(|m| m.meta.id == member_id)
    {
        return Err(ServiceError::NotFound);
    }
    let share = match new.share {
        Some(s) => s,
        None => suggest(db.conn(), env, ctx, new.amount)?.share,
    };
    if share.currency() != ctx.currency || share.minor() < 0 || share.minor() > new.amount.minor() {
        return Err(ServiceError::Invalid(
            "ulush 0 dan daromadgacha bo'lishi kerak",
        ));
    }
    let received_on = new
        .received_on
        .unwrap_or_else(|| local_date(env.clock.now()));

    db.transaction(|tx| {
        let income = Income {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            member_id,
            source: source.to_owned(),
            channel: new.channel,
            amount: new.amount,
            received_on,
            source_type: new.source_type,
        };
        repo::insert(tx, &income)?;
        if share.minor() > 0 {
            // Avval qorovul maqsadiga; ortig'i faqat darvoza ochiq bo'lsa o'sadiganga.
            let (to_guard, to_growing) = crate::guard::split_share(tx, env, ctx, share)?;
            for (vt, amount) in [
                (VaultType::Qorovul, to_guard),
                (VaultType::Osadigan, to_growing),
            ] {
                if amount.minor() > 0 {
                    vault::apply_to(
                        tx,
                        env,
                        ctx,
                        vt,
                        &vault::VaultMove {
                            kind: VaultTxKind::Deposit,
                            amount,
                            source: VaultSource::Allocation,
                            income_id: Some(&income.meta.id),
                            note: None,
                        },
                    )?;
                }
            }
        }
        Ok(Recorded {
            income_id: income.meta.id,
            share,
        })
    })
}

/// Oyning daromadlari (yangi → eski).
///
/// # Errors
/// Baza xatosi.
pub fn list_month(
    conn: &Connection,
    ctx: &Ctx,
    ym: YearMonth,
) -> Result<Vec<Income>, ServiceError> {
    let mut items: Vec<Income> = repo::list::<Income>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|i| ym.contains(i.received_on))
        .collect();
    items.sort_by(|a, b| (b.received_on, &b.meta.id).cmp(&(a.received_on, &a.meta.id)));
    Ok(items)
}

/// # Errors
/// Baza xatosi.
pub fn month_total(conn: &Connection, ctx: &Ctx, ym: YearMonth) -> Result<Money, ServiceError> {
    Ok(sum_money(
        ctx.currency,
        list_month(conn, ctx, ym)?.into_iter().map(|i| i.amount),
    )?)
}
