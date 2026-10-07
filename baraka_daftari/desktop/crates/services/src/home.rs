//! Bosh sahifa ko'rsatkichlari (SPEC 2.4: birinchi raqam — "O'zingizga qancha to'ladingiz?").
use domain::{compute_streak, suggest_rate_increase, ShareRule, StreakSummary};
use money::Money;
use storage::Connection;
use time::Weekday;

use crate::{audit, local_date, rules, vault, Ctx, Env, ServiceError, YearMonth};

#[derive(Debug, Clone)]
pub struct Home {
    pub month: YearMonth,
    /// Bugungi lokal sana va shu haftaning boshi (juma).
    pub today: domain::Date,
    pub week_start: domain::Date,
    pub self_paid: Money,
    pub self_paid_bp: i64,
    pub income: Money,
    pub month_result: Money,
    pub vault_balance: Money,
    pub streak: StreakSummary,
    pub rule: ShareRule,
    /// Ulushni oshirish taklifi (bazis punkt), faqat foizli qoidada.
    pub rate_suggestion: Option<u32>,
    pub pending_withdrawals: usize,
}

/// Hafta jumadan boshlanadi (`weekAnchor = FRIDAY`); sozlanadigan qiladi — keyingi vazifada.
pub const WEEK_ANCHOR: Weekday = Weekday::Friday;

/// # Errors
/// Baza xatosi.
pub fn summary(conn: &Connection, env: &Env<'_>, ctx: &Ctx) -> Result<Home, ServiceError> {
    let now = env.clock.now();
    let today = local_date(now);
    let ym = YearMonth::of(today);
    let overview = audit::overview(conn, ctx, ym)?;
    let streak = compute_streak(&vault::allocation_dates(conn, ctx)?, today, WEEK_ANCHOR);
    let active = rules::current(conn, ctx)?;
    let weeks_at_rate =
        u32::try_from((now - active.since).whole_weeks().max(0)).unwrap_or(u32::MAX);
    let rate_suggestion = match active.rule {
        ShareRule::Percent { bp } => suggest_rate_increase(bp, streak.current_weeks, weeks_at_rate),
        ShareRule::MonthlyFixed { .. } => None,
    };
    Ok(Home {
        month: ym,
        today,
        week_start: domain::week_start(today, WEEK_ANCHOR),
        self_paid: overview.whose.self_paid,
        self_paid_bp: overview.whose.self_paid_bp,
        income: overview.income,
        month_result: overview.month_result,
        vault_balance: vault::balance(conn, ctx)?,
        streak,
        rule: active.rule,
        rate_suggestion,
        pending_withdrawals: vault::pending_withdrawals(conn, ctx)?.len(),
    })
}
