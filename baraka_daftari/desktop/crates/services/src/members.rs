//! Oila a'zolari va ularning shaxsiy PIN'i (havas chegarasiga rozilik uchun).
use domain::{Member, MemberCredential, MemberRole, Meta};
use security::{hash_pin, is_valid_pin, lockout_delay_secs, verify_pin, KdfParams};
use storage::{repo, Connection, Database};

use crate::{Ctx, Env, ServiceError};

/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<Member>, ServiceError> {
    Ok(repo::list::<Member>(conn, &ctx.household_id)?)
}

/// Barcha kattalar (`ADULT`): rozilik shularga bog'liq.
///
/// # Errors
/// Baza xatosi.
pub fn adults(conn: &Connection, ctx: &Ctx) -> Result<Vec<Member>, ServiceError> {
    Ok(list(conn, ctx)?
        .into_iter()
        .filter(|m| m.role == MemberRole::Adult)
        .collect())
}

/// # Errors
/// Ism bo'sh yoki bir xil ism bor bo'lsa.
pub fn add(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    name: &str,
    role: MemberRole,
) -> Result<Member, ServiceError> {
    let name = name.trim();
    if name.is_empty() || name.chars().count() > 60 {
        return Err(ServiceError::Invalid("ism 1..60 belgi bo'lishi kerak"));
    }
    if list(db.conn(), ctx)?
        .iter()
        .any(|m| m.display_name.to_lowercase() == name.to_lowercase())
    {
        return Err(ServiceError::Invalid("bunday ismli a'zo allaqachon bor"));
    }
    let m = Member {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        display_name: name.to_owned(),
        role,
    };
    repo::insert(db.conn(), &m)?;
    Ok(m)
}

fn credential(
    conn: &Connection,
    ctx: &Ctx,
    member_id: &str,
) -> Result<Option<MemberCredential>, ServiceError> {
    Ok(repo::list::<MemberCredential>(conn, &ctx.household_id)?
        .into_iter()
        .find(|c| c.member_id == member_id))
}

/// # Errors
/// Baza xatosi.
pub fn has_pin(conn: &Connection, ctx: &Ctx, member_id: &str) -> Result<bool, ServiceError> {
    Ok(credential(conn, ctx, member_id)?.is_some())
}

fn ensure_member(conn: &Connection, ctx: &Ctx, member_id: &str) -> Result<(), ServiceError> {
    if list(conn, ctx)?.iter().any(|m| m.meta.id == member_id) {
        Ok(())
    } else {
        Err(ServiceError::NotFound)
    }
}

/// A'zoning PIN'ini o'rnatadi yoki almashtiradi (urinishlar hisoblagichi nolga tushadi).
///
/// # Errors
/// PIN formati noto'g'ri yoki a'zo topilmasa.
pub fn set_pin(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    member_id: &str,
    pin: &str,
    kdf: KdfParams,
) -> Result<(), ServiceError> {
    if !is_valid_pin(pin) {
        return Err(ServiceError::Invalid(
            "PIN aniq 6 ta raqamdan iborat bo'lishi kerak",
        ));
    }
    ensure_member(db.conn(), ctx, member_id)?;
    let hash = hash_pin(pin, kdf).map_err(|_| ServiceError::Invalid("PIN o'rnatilmadi"))?;
    match credential(db.conn(), ctx, member_id)? {
        Some(mut c) => {
            c.pin_hash = hash;
            c.failures = 0;
            c.locked_until = 0;
            repo::update(db.conn(), &c, env.clock.now())?;
        }
        None => repo::insert(
            db.conn(),
            &MemberCredential {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                member_id: member_id.to_owned(),
                pin_hash: hash,
                failures: 0,
                locked_until: 0,
            },
        )?,
    }
    Ok(())
}

/// A'zo PIN'ini tekshiradi; xato urinishlar sekinlashtiriladi (vault bilan bir xil jadval).
///
/// # Errors
/// [`ServiceError::NoPin`], [`ServiceError::PinLocked`], [`ServiceError::WrongPin`].
pub fn verify(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    member_id: &str,
    pin: &str,
) -> Result<(), ServiceError> {
    ensure_member(db.conn(), ctx, member_id)?;
    let mut c = credential(db.conn(), ctx, member_id)?.ok_or(ServiceError::NoPin)?;
    let now = env.clock.now();
    let now_secs = now.unix_timestamp();
    if c.locked_until > now_secs {
        return Err(ServiceError::PinLocked {
            retry_after_secs: u64::try_from(c.locked_until - now_secs).unwrap_or(0),
        });
    }
    if verify_pin(pin, &c.pin_hash) {
        if c.failures != 0 || c.locked_until != 0 {
            c.failures = 0;
            c.locked_until = 0;
            repo::update(db.conn(), &c, now)?;
        }
        return Ok(());
    }
    c.failures = c.failures.saturating_add(1);
    let delay = lockout_delay_secs(c.failures);
    c.locked_until = if delay == 0 {
        0
    } else {
        now_secs.saturating_add_unsigned(delay)
    };
    repo::update(db.conn(), &c, now)?;
    Err(ServiceError::WrongPin)
}

/// PIN almashtirish: PIN bor bo'lsa eskisi tekshiriladi (xato urinishlar hisoblanadi).
///
/// # Errors
/// Eski PIN noto'g'ri, yangi PIN formati yaroqsiz yoki a'zo topilmasa.
pub fn change_pin(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    member_id: &str,
    old_pin: Option<&str>,
    new_pin: &str,
    kdf: KdfParams,
) -> Result<(), ServiceError> {
    ensure_member(db.conn(), ctx, member_id)?;
    if has_pin(db.conn(), ctx, member_id)? {
        verify(db, env, ctx, member_id, old_pin.unwrap_or(""))?;
    }
    set_pin(db, env, ctx, member_id, new_pin, kdf)
}
