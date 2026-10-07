//! «Qutqarilgan pul» (SPEC 2B.7): teshikdan qutqarilgan summa — havasning oldingi haftaga nisbatan
//! kamayishi (manfiy holat — 0) va bekor qilingan obunalar. Bir bosishda «Kelajagim»ga o'tkaziladi.
//! Tejash ko'rsatkichi sadaqa yoki zarur xarajatni kamaytirishni hech qachon «yutuq» deb hisoblamaydi:
//! faqat havas hisobga kiradi.
use domain::{
    rescued_money, week_start, Date, Meta, RescueKind, SavingsRescue, VaultSource, VaultTxKind,
};
use money::Money;
use storage::{repo, Connection, Database};
use time::Duration;

use crate::{havas, home::WEEK_ANCHOR, local_date, sum_money, vault, Ctx, Env, ServiceError};

#[derive(Debug, Clone)]
pub struct WeeklyRescue {
    /// Tugagan oxirgi hafta (jumasi) va undan oldingi hafta.
    pub week: Date,
    pub baseline_week: Date,
    pub baseline: Money,
    pub current: Money,
    pub rescued: Money,
    /// Shu hafta uchun allaqachon yozilgan yozuv.
    pub claimed: Option<SavingsRescue>,
}

fn week_range(ws: Date) -> (Date, Date) {
    (ws, ws + Duration::days(6))
}

/// Oxirgi **tugagan** haftaning hisoboti: «Bu hafta qancha qutqardingiz?».
///
/// # Errors
/// Baza xatosi.
pub fn weekly_report(
    conn: &Connection,
    ctx: &Ctx,
    today: Date,
) -> Result<WeeklyRescue, ServiceError> {
    let this_week = week_start(today, WEEK_ANCHOR);
    let week = this_week - Duration::days(7);
    let baseline_week = week - Duration::days(7);
    let (bf, bt) = week_range(baseline_week);
    let (cf, ct) = week_range(week);
    let baseline = havas::spent_between(conn, ctx, bf, bt)?;
    let current = havas::spent_between(conn, ctx, cf, ct)?;
    let rescued = rescued_money(baseline, current)
        .map_err(|_| ServiceError::Invalid("qutqarilgan pul hisoblanmadi"))?;
    let claimed = repo::list::<SavingsRescue>(conn, &ctx.household_id)?
        .into_iter()
        .find(|r| r.kind == RescueKind::HavasDrop && r.week_start == Some(week));
    Ok(WeeklyRescue {
        week,
        baseline_week,
        baseline,
        current,
        rescued,
        claimed,
    })
}

/// Tugagan haftaning qutqarilgan pulini yozadi (bir hafta uchun bir marta; summa 0 bo'lsa yozilmaydi).
///
/// # Errors
/// Baza xatosi.
pub fn claim_week(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
) -> Result<Option<SavingsRescue>, ServiceError> {
    let report = weekly_report(db.conn(), ctx, local_date(env.clock.now()))?;
    if report.claimed.is_some() || report.rescued.minor() <= 0 {
        return Ok(report.claimed);
    }
    let r = SavingsRescue {
        meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
        kind: RescueKind::HavasDrop,
        amount: report.rescued,
        week_start: Some(report.week),
        note: None,
        transferred_at: None,
    };
    repo::insert(db.conn(), &r)?;
    Ok(Some(r))
}

/// Barcha yozuvlar (eski → yangi).
///
/// # Errors
/// Baza xatosi.
pub fn list(conn: &Connection, ctx: &Ctx) -> Result<Vec<SavingsRescue>, ServiceError> {
    Ok(repo::list::<SavingsRescue>(conn, &ctx.household_id)?)
}

/// Hali «Kelajagim»ga o'tkazilmagan jami.
///
/// # Errors
/// Baza xatosi.
pub fn available(conn: &Connection, ctx: &Ctx) -> Result<Money, ServiceError> {
    Ok(sum_money(
        ctx.currency,
        list(conn, ctx)?
            .into_iter()
            .filter(|r| r.transferred_at.is_none())
            .map(|r| r.amount),
    )?)
}

/// Bir yozuvni «Kelajagim»ga o'tkazadi (ajratma sifatida: «o'zingizga to'langan» va ketma-ketlikka qo'shiladi).
///
/// # Errors
/// Topilmasa yoki allaqachon o'tkazilgan bo'lsa.
pub fn transfer(db: &mut Database, env: &Env<'_>, ctx: &Ctx, id: &str) -> Result<(), ServiceError> {
    let mut r = repo::get::<SavingsRescue>(db.conn(), id)?
        .filter(|r| r.meta.household_id == ctx.household_id)
        .ok_or(ServiceError::NotFound)?;
    if r.transferred_at.is_some() {
        return Err(ServiceError::Invalid("bu summa allaqachon o'tkazilgan"));
    }
    let now = env.clock.now();
    db.transaction::<(), ServiceError>(|tx| {
        vault::apply(
            tx,
            env,
            ctx,
            &vault::VaultMove {
                kind: VaultTxKind::Deposit,
                amount: r.amount,
                source: VaultSource::Allocation,
                income_id: None,
                note: Some("Qutqarilgan pul"),
            },
        )?;
        r.transferred_at = Some(now);
        repo::update(tx, &r, now)?;
        Ok(())
    })
}

/// Hali o'tkazilmagan hamma yozuvni bir bosishda o'tkazadi; o'tkazilgan jami summani qaytaradi.
///
/// # Errors
/// Baza xatosi.
pub fn transfer_all(db: &mut Database, env: &Env<'_>, ctx: &Ctx) -> Result<Money, ServiceError> {
    let pending: Vec<SavingsRescue> = list(db.conn(), ctx)?
        .into_iter()
        .filter(|r| r.transferred_at.is_none())
        .collect();
    let total = sum_money(ctx.currency, pending.iter().map(|r| r.amount))?;
    db.transaction::<(), ServiceError>(|tx| {
        let now = env.clock.now();
        for mut r in pending {
            vault::apply(
                tx,
                env,
                ctx,
                &vault::VaultMove {
                    kind: VaultTxKind::Deposit,
                    amount: r.amount,
                    source: VaultSource::Allocation,
                    income_id: None,
                    note: Some("Qutqarilgan pul"),
                },
            )?;
            r.transferred_at = Some(now);
            repo::update(tx, &r, now)?;
        }
        Ok(())
    })?;
    Ok(total)
}
