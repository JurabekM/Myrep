//! "Kelajagim" jamg'armasi: balans, ajratma, boshlang'ich balans va pauzali pul olish.
use domain::{
    available_at, check_confirm, ts_to_string, Asset, AssetSnapshot, AssetType, ConfirmCheck, Date,
    Meta, VaultSource, VaultTransaction, VaultTxKind, WithdrawalRequest, WithdrawalStatus,
};
use money::Money;
use storage::Connection;
use storage::{repo, Database};

use crate::{local_date, sum_money, Ctx, Env, ServiceError, YearMonth};

fn vault_asset(conn: &Connection, ctx: &Ctx) -> Result<Asset, ServiceError> {
    repo::list::<Asset>(conn, &ctx.household_id)?
        .into_iter()
        .find(|a| a.asset_type == AssetType::Vault)
        .ok_or(ServiceError::NotFound)
}

/// # Errors
/// Baza xatosi.
pub fn balance(conn: &Connection, ctx: &Ctx) -> Result<Money, ServiceError> {
    Ok(Money::new(vault_asset(conn, ctx)?.quantity, ctx.currency))
}

fn transactions(conn: &Connection, ctx: &Ctx) -> Result<Vec<VaultTransaction>, ServiceError> {
    Ok(repo::list::<VaultTransaction>(conn, &ctx.household_id)?)
}

/// Kelajagim balansini o'zgartiruvchi bitta harakat.
pub(crate) struct VaultMove<'a> {
    pub kind: VaultTxKind,
    pub amount: Money,
    pub source: VaultSource,
    pub income_id: Option<&'a str>,
    pub note: Option<&'a str>,
}

/// Balansni o'zgartiradi: tranzaksiya yozuvi + `Asset.quantity` + balans snapshoti.
/// Faqat ochiq DB tranzaksiyasi ichida chaqiriladi.
pub(crate) fn apply(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    mv: &VaultMove<'_>,
) -> Result<(), ServiceError> {
    let VaultMove {
        kind,
        amount,
        source,
        income_id,
        note,
    } = *mv;
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let mut asset = vault_asset(conn, ctx)?;
    let now = env.clock.now();
    let new_qty = match kind {
        VaultTxKind::Deposit => asset.quantity.checked_add(amount.minor()),
        VaultTxKind::Withdraw => asset.quantity.checked_sub(amount.minor()),
    }
    .ok_or(money::MoneyError::Overflow)?;
    if new_qty < 0 {
        return Err(ServiceError::InsufficientFunds);
    }
    repo::insert(
        conn,
        &VaultTransaction {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            asset_id: asset.meta.id.clone(),
            kind,
            amount,
            occurred_at: now,
            note: note.map(str::to_owned),
            source: Some(source),
            income_id: income_id.map(str::to_owned),
        },
    )?;
    asset.quantity = new_qty;
    repo::update(conn, &asset, now)?;
    repo::insert(
        conn,
        &AssetSnapshot {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            asset_id: asset.meta.id.clone(),
            quantity: new_qty,
            taken_at: now,
        },
    )?;
    Ok(())
}

/// "Ro'molcha" stsenariysi: ilovadan oldin yig'ilgan naqd jamg'arma. Faqat bir marta; u
/// "o'zingizga to'langan" va streak hisobiga kirmaydi.
///
/// # Errors
/// Allaqachon kiritilgan bo'lsa yoki summa yaroqsiz bo'lsa.
pub fn set_opening_balance(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    amount: Money,
) -> Result<(), ServiceError> {
    db.transaction(|tx| {
        if transactions(tx, ctx)?
            .iter()
            .any(|t| t.source == Some(VaultSource::Opening))
        {
            return Err(ServiceError::OpeningBalanceExists);
        }
        apply(
            tx,
            env,
            ctx,
            &VaultMove {
                kind: VaultTxKind::Deposit,
                amount,
                source: VaultSource::Opening,
                income_id: None,
                note: Some("Boshlang'ich balans"),
            },
        )
    })
}

/// Ajratma (`ALLOCATION`) qilingan lokal sanalar: streak va "ajratilgan kunlar" uchun.
///
/// # Errors
/// Baza xatosi.
pub fn allocation_dates(conn: &Connection, ctx: &Ctx) -> Result<Vec<Date>, ServiceError> {
    Ok(transactions(conn, ctx)?
        .into_iter()
        .filter(|t| t.kind == VaultTxKind::Deposit && t.source == Some(VaultSource::Allocation))
        .map(|t| local_date(t.occurred_at))
        .collect())
}

/// Oy davomida ajratilgan jami ("o'zingizga to'langan").
///
/// # Errors
/// Baza xatosi.
pub fn allocated_in(conn: &Connection, ctx: &Ctx, ym: YearMonth) -> Result<Money, ServiceError> {
    Ok(sum_money(
        ctx.currency,
        transactions(conn, ctx)?
            .into_iter()
            .filter(|t| {
                t.kind == VaultTxKind::Deposit
                    && t.source == Some(VaultSource::Allocation)
                    && ym.contains(local_date(t.occurred_at))
            })
            .map(|t| t.amount),
    )?)
}

/// Pul olish so'rovi: pul darrov chiqmaydi, pauza tugagach tasdiqlanadi.
///
/// # Errors
/// Summa yoki sabab yaroqsiz, yoki balansdan ko'p bo'lsa.
pub fn request_withdrawal(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    amount: Money,
    reason: &str,
    cooldown_secs: i64,
) -> Result<WithdrawalRequest, ServiceError> {
    let reason = reason.trim();
    if reason.is_empty() {
        return Err(ServiceError::Invalid("sababni yozing"));
    }
    if amount.minor() <= 0 || amount.currency() != ctx.currency {
        return Err(ServiceError::Invalid("summa musbat bo'lishi kerak"));
    }
    let asset = vault_asset(db.conn(), ctx)?;
    if amount.minor() > asset.quantity {
        return Err(ServiceError::InsufficientFunds);
    }
    let req = WithdrawalRequest {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        asset_id: asset.meta.id,
        amount,
        reason: reason.to_owned(),
        available_at: available_at(env.clock.now(), cooldown_secs),
        status: WithdrawalStatus::Pending,
    };
    repo::insert(db.conn(), &req)?;
    Ok(req)
}

/// # Errors
/// Pauza tugamagan ([`ServiceError::Cooling`]), so'rov topilmadi yoki mablag' yetmasa.
pub fn confirm_withdrawal(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<(), ServiceError> {
    let mut req = repo::get::<WithdrawalRequest>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if req.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    let now = env.clock.now();
    match check_confirm(req.status, req.available_at, now) {
        ConfirmCheck::Ok => {}
        ConfirmCheck::Cooling { remaining_secs } => {
            return Err(ServiceError::Cooling { remaining_secs })
        }
        ConfirmCheck::NotPending => return Err(ServiceError::Invalid("so'rov kutilmayapti")),
    }
    db.transaction(|tx| {
        apply(
            tx,
            env,
            ctx,
            &VaultMove {
                kind: VaultTxKind::Withdraw,
                amount: req.amount,
                source: VaultSource::Manual,
                income_id: None,
                note: Some(&req.reason),
            },
        )?;
        req.status = WithdrawalStatus::Confirmed;
        repo::update(tx, &req, now)?;
        Ok(())
    })
}

/// # Errors
/// So'rov topilmasa yoki kutilmayotgan bo'lsa.
pub fn cancel_withdrawal(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    id: &str,
) -> Result<(), ServiceError> {
    let mut req = repo::get::<WithdrawalRequest>(db.conn(), id)?.ok_or(ServiceError::NotFound)?;
    if req.meta.household_id != ctx.household_id {
        return Err(ServiceError::NotFound);
    }
    if req.status != WithdrawalStatus::Pending {
        return Err(ServiceError::Invalid("so'rov kutilmayapti"));
    }
    req.status = WithdrawalStatus::Cancelled;
    repo::update(db.conn(), &req, env.clock.now())?;
    Ok(())
}

/// Kutilayotgan so'rovlar.
///
/// # Errors
/// Baza xatosi.
pub fn pending_withdrawals(
    conn: &Connection,
    ctx: &Ctx,
) -> Result<Vec<WithdrawalRequest>, ServiceError> {
    Ok(repo::list::<WithdrawalRequest>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|r| r.status == WithdrawalStatus::Pending)
        .collect())
}

/// Matn ko'rinishi (UI uchun).
///
/// # Errors
/// Formatlash xatosi.
pub fn ts_text(t: domain::OffsetDateTime) -> Result<String, ServiceError> {
    ts_to_string(t).map_err(|_| ServiceError::Invalid("vaqt formati"))
}
