//! D7 byudjet: obunalar, konvertlar, «Qutqarilgan pul» hisobi va «Kelajagim»ga o'tkazish.
//! Pul hisobi domen'da (`rescue`, `subscription`, `envelope`); bu yerda faqat yig'iladi va saqlanadi.

use domain::calendar::{DateRange, month_of, week_of};
use domain::rescue::{
    RescueBreakdown, RescueKind, SavingsRescue, compute_rescue, subscription_savings,
};
use domain::{
    DomainError, Envelope, Expense, Meta, Necessity, Subscription, VaultEntry, VaultMovement,
    envelope,
};
use money::Money;
use storage::{
    CategoryRepo, Database, EnvelopeRepo, ExpenseRepo, RescueRepo, StorageError, SubscriptionRepo,
    transfer_to_vault,
};
use time::format_description::well_known::Iso8601;
use time::{Date, Duration, OffsetDateTime};

use crate::dto::{
    BudgetDto, EnvelopeDto, EnvelopeInputDto, MoneyDto, RescueDto, SubscriptionDto,
    SubscriptionInputDto,
};
use crate::finance::{self, CURRENCY, Context, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::session::SessionError;

/// Bazaviy davr boshlanishi saqlanadigan xonadon sozlamasi kaliti.
const BASELINE_KEY: &str = "baseline_period_start";

fn period_of(ctx: &Context, date: Date) -> Result<DateRange, SessionError> {
    month_of(date, ctx.household.month_start_day).ok_or_else(|| DomainError::InvalidDay.into())
}

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainError::InvalidDay.into())
}

/// Sana davr ichidami (boshlanish kiradi, tugash kirmaydi).
fn in_range(range: &DateRange, date: Date) -> bool {
    date >= range.start && date < range.end
}

fn days_in(range: &DateRange) -> i64 {
    (range.end - range.start).whole_days()
}

fn money_sum(amounts: impl Iterator<Item = Money>) -> Money {
    let minor = amounts.fold(0_i64, |acc, money| acc.saturating_add(money.minor()));
    Money::new(minor, CURRENCY)
}

/// Havas xarajatlari yig'indisi (toifa `HAVAS` bo'lganlari).
fn havas_total(expenses: &[Expense]) -> Money {
    money_sum(
        expenses
            .iter()
            .filter(|e| e.necessity == Necessity::Havas)
            .map(|e| e.amount),
    )
}

/// Konvert kategoriyasi bo'yicha sarflangan. Bog'lanmagan konvert — 0.
fn spent_in_category(expenses: &[Expense], category_id: Option<&str>) -> Money {
    money_sum(
        expenses
            .iter()
            .filter(|e| category_id.is_some() && e.category_id.as_deref() == category_id)
            .map(|e| e.amount),
    )
}

/// Bazaviy davr: sozlamada saqlangan (joriy davrdan oldin bo'lsa), aks holda — o'tgan davr.
fn baseline_period(
    db: &Database,
    ctx: &Context,
    period: &DateRange,
) -> Result<DateRange, SessionError> {
    let stored = RescueRepo::new(db.connection()).setting(&ctx.household.id, BASELINE_KEY)?;
    if let Some(text) = stored {
        let chosen = period_of(ctx, parse_date(&text)?)?;
        if chosen.start < period.start {
            return Ok(chosen);
        }
    }
    period_of(ctx, period.start - Duration::days(1))
}

/// «Qutqarilgan pul» hisobi: joriy davr bo'yicha (domen formulasi).
fn breakdown_for(
    db: &Database,
    ctx: &Context,
    period: &DateRange,
) -> Result<RescueBreakdown, SessionError> {
    let conn = db.connection();
    let household_id = ctx.household.id.as_str();
    let expenses = ExpenseRepo::new(conn).list_in_range(household_id, *period)?;

    let baseline_range = baseline_period(db, ctx, period)?;
    let baseline_expenses = ExpenseRepo::new(conn).list_in_range(household_id, baseline_range)?;
    let baseline = if baseline_expenses.is_empty() {
        None
    } else {
        Some((havas_total(&baseline_expenses), days_in(&baseline_range)))
    };

    let subscriptions = SubscriptionRepo::new(conn).list(household_id)?;
    let cancelled: Vec<(Money, Date)> = subscriptions
        .iter()
        .filter_map(|s| s.cancelled_on.map(|on| (s.monthly, on)))
        .collect();
    let subscription_total = subscription_savings(CURRENCY, &cancelled, *period, ctx.today)?;

    let rescues: Vec<SavingsRescue> = RescueRepo::new(conn)
        .list(household_id)?
        .into_iter()
        .filter(|r| in_range(period, r.occurred_on))
        .collect();
    let envelope_total = money_sum(
        rescues
            .iter()
            .filter(|r| r.kind == RescueKind::EnvelopeLeftover)
            .map(|r| r.amount),
    );
    let transferred = money_sum(
        rescues
            .iter()
            .filter(|r| r.kind == RescueKind::Transfer)
            .map(|r| r.amount),
    );

    let elapsed = (ctx.today - period.start).whole_days() + 1;
    Ok(compute_rescue(
        CURRENCY,
        elapsed,
        havas_total(&expenses),
        baseline,
        subscription_total,
        envelope_total,
        transferred,
    )?)
}

/// Byudjet sahifasining to'liq holati.
fn build_overview(
    db: &Database,
    ctx: &Context,
    period: &DateRange,
) -> Result<BudgetDto, SessionError> {
    let conn = db.connection();
    let household_id = ctx.household.id.as_str();
    let today = ctx.today;

    let breakdown = breakdown_for(db, ctx, period)?;
    let baseline_start = if breakdown.has_baseline {
        Some(date_text(baseline_period(db, ctx, period)?.start))
    } else {
        None
    };
    let rescue = RescueDto {
        havas: MoneyDto::of(breakdown.havas_shown()),
        subscriptions: MoneyDto::of(breakdown.subscriptions),
        envelopes: MoneyDto::of(breakdown.envelopes),
        total: MoneyDto::of(breakdown.total()?),
        transferred: MoneyDto::of(breakdown.transferred),
        available: MoneyDto::of(breakdown.available()?),
        spent_more: breakdown.spent_more(),
        has_baseline: breakdown.has_baseline,
        baseline_start,
        period_start: date_text(period.start),
        period_end: date_text(period.end),
    };

    let subscriptions = SubscriptionRepo::new(conn)
        .list(household_id)?
        .iter()
        .map(|s| SubscriptionDto {
            id: s.id.clone(),
            name: s.name.clone(),
            monthly: MoneyDto::of(s.monthly),
            yearly: s.yearly.map(MoneyDto::of),
            last_used_on: s.last_used_on.map(date_text),
            cancelled_on: s.cancelled_on.map(date_text),
            forgotten: s.is_forgotten(today),
        })
        .collect();

    let week = week_of(today).ok_or(DomainError::InvalidDay)?;
    let week_expenses = ExpenseRepo::new(conn).list_in_range(household_id, week)?;
    let rescues = RescueRepo::new(conn).list(household_id)?;
    let envelopes = EnvelopeRepo::new(conn)
        .list(household_id)?
        .iter()
        .map(|env| {
            let spent = spent_in_category(&week_expenses, env.category_id.as_deref());
            let closed = rescues.iter().any(|r| {
                r.kind == RescueKind::EnvelopeLeftover
                    && r.source_id.as_deref() == Some(env.id.as_str())
                    && in_range(&week, r.occurred_on)
            });
            EnvelopeDto {
                id: env.id.clone(),
                name: env.name.clone(),
                weekly_limit: MoneyDto::of(env.weekly_limit),
                spent_this_week: MoneyDto::of(spent),
                leftover_this_week: MoneyDto::of(envelope::leftover(env.weekly_limit, spent)),
                closed_this_week: closed,
                category_id: env.category_id.clone(),
            }
        })
        .collect();

    Ok(BudgetDto {
        rescue,
        subscriptions,
        envelopes,
    })
}

/// Byudjet sahifasi (joriy holat).
pub fn overview(db: &Database, now: OffsetDateTime) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let period = period_of(&ctx, ctx.today)?;
    build_overview(db, &ctx, &period)
}

fn load_subscription(db: &Database, id: &str) -> Result<Subscription, SessionError> {
    SubscriptionRepo::new(db.connection())
        .find(id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))
}

fn touch(meta: &mut Meta, now: OffsetDateTime) {
    meta.updated_at = now;
    meta.version += 1;
}

/// Obuna qo'shadi.
pub fn add_subscription(
    db: &Database,
    now: OffsetDateTime,
    input: SubscriptionInputDto,
) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let monthly = parse_money(&input.monthly)?;
    let yearly = input
        .yearly
        .as_deref()
        .filter(|text| !text.trim().is_empty())
        .map(parse_money)
        .transpose()?;
    let subscription = Subscription::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        &input.name,
        monthly,
        yearly,
        now,
        DEVICE_ID,
    )?;
    SubscriptionRepo::new(db.connection()).insert(&subscription)?;
    let period = period_of(&ctx, ctx.today)?;
    build_overview(db, &ctx, &period)
}

/// «Ishlatdim» deb belgilaydi.
pub fn mark_subscription_used(
    db: &Database,
    now: OffsetDateTime,
    id: &str,
) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let mut updated = load_subscription(db, id)?.mark_used(ctx.today)?;
    touch(&mut updated.meta, now);
    SubscriptionRepo::new(db.connection()).update(&updated)?;
    let period = period_of(&ctx, ctx.today)?;
    build_overview(db, &ctx, &period)
}

/// Obunani bekor qiladi. Tejam bekor qilingan kundan boshlab hisoblanadi.
pub fn cancel_subscription(
    db: &Database,
    now: OffsetDateTime,
    id: &str,
) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let mut updated = load_subscription(db, id)?.cancel(ctx.today)?;
    touch(&mut updated.meta, now);
    SubscriptionRepo::new(db.connection()).update(&updated)?;
    let period = period_of(&ctx, ctx.today)?;
    build_overview(db, &ctx, &period)
}

/// Konvert qo'shadi. Bog'langan kategoriya xonadonda bo'lishi kerak.
pub fn add_envelope(
    db: &Database,
    now: OffsetDateTime,
    input: EnvelopeInputDto,
) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let limit = parse_money(&input.weekly_limit)?;
    let known_category = match input.category_id.as_deref() {
        None => true,
        Some(category_id) => CategoryRepo::new(db.connection())
            .list(&ctx.household.id)?
            .iter()
            .any(|c| c.id == category_id),
    };
    if !known_category {
        return Err(SessionError::from(StorageError::NotFound));
    }
    let envelope = Envelope::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        &input.name,
        limit,
        input.category_id,
        now,
        DEVICE_ID,
    )?;
    EnvelopeRepo::new(db.connection()).insert(&envelope)?;
    let period = period_of(&ctx, ctx.today)?;
    build_overview(db, &ctx, &period)
}

/// Konvertning shu haftadagi qoldig'ini «Qutqarilgan pul» ga yozadi. Hafta uchun bir marta.
pub fn close_envelope_week(
    db: &Database,
    now: OffsetDateTime,
    envelope_id: &str,
) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let conn = db.connection();
    let envelope = EnvelopeRepo::new(conn)
        .find(envelope_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let week = week_of(ctx.today).ok_or(DomainError::InvalidDay)?;
    let rescues = RescueRepo::new(conn).list(&ctx.household.id)?;
    let already_closed = rescues.iter().any(|r| {
        r.kind == RescueKind::EnvelopeLeftover
            && r.source_id.as_deref() == Some(envelope_id)
            && in_range(&week, r.occurred_on)
    });
    if already_closed {
        return Err(DomainError::EnvelopeWeekClosed.into());
    }
    let week_expenses = ExpenseRepo::new(conn).list_in_range(&ctx.household.id, week)?;
    let spent = spent_in_category(&week_expenses, envelope.category_id.as_deref());
    let leftover = envelope::leftover(envelope.weekly_limit, spent);
    let rescue = SavingsRescue::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        RescueKind::EnvelopeLeftover,
        leftover,
        ctx.today,
        now,
        DEVICE_ID,
    )?
    .with_source(Some(envelope.id.clone()));
    RescueRepo::new(conn).insert(&rescue)?;
    let period = period_of(&ctx, ctx.today)?;
    build_overview(db, &ctx, &period)
}

/// «Qutqarilgan pul»dan «Kelajagim»ga o'tkazadi. Summa hali o'tkazilmagan qismidan oshmaydi.
pub fn transfer_to_vault_from_rescue(
    db: &Database,
    now: OffsetDateTime,
    amount_text: &str,
) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let period = period_of(&ctx, ctx.today)?;
    let amount = parse_money(amount_text)?;
    let breakdown = breakdown_for(db, &ctx, &period)?;
    if amount.minor() > breakdown.available()?.minor() {
        return Err(DomainError::RescueExceedsAvailable.into());
    }
    let asset = finance::vault_asset(db, now)?;
    let rescue_id = domain::IdGen::next_id(&UuidV7);
    let rescue = SavingsRescue::create(
        &rescue_id,
        &ctx.household.id,
        RescueKind::Transfer,
        amount,
        ctx.today,
        now,
        DEVICE_ID,
    )?;
    let entry = VaultEntry {
        id: domain::IdGen::next_id(&UuidV7),
        amount,
        occurred_on: ctx.today,
        movement: VaultMovement::RescueDeposit { rescue_id },
        meta: Meta::created(now, DEVICE_ID),
    };
    transfer_to_vault(db.connection(), &rescue, &asset, &entry)?;
    build_overview(db, &ctx, &period)
}

/// Bazaviy davrni tanlaydi. Faqat joriy davrdan oldingi davr qabul qilinadi.
pub fn set_baseline_period(
    db: &Database,
    now: OffsetDateTime,
    period_start: &str,
) -> Result<BudgetDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let period = period_of(&ctx, ctx.today)?;
    let chosen = period_of(&ctx, parse_date(period_start)?)?;
    if chosen.start >= period.start {
        return Err(DomainError::BaselineNotPast.into());
    }
    RescueRepo::new(db.connection()).set_setting(
        &ctx.household.id,
        BASELINE_KEY,
        &date_text(chosen.start),
    )?;
    build_overview(db, &ctx, &period)
}

#[cfg(test)]
mod tests {
    use super::*;
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-10-15 06:00 UTC);

    fn database_with_pin() -> Database {
        Database::open_in_memory(&SecretKey::from_array([10; 32])).expect("xotirada baza")
    }

    fn sub_input(monthly_major: &str) -> SubscriptionInputDto {
        SubscriptionInputDto {
            name: "Telegram Premium".to_owned(),
            monthly: monthly_major.to_owned(),
            yearly: None,
        }
    }

    #[test]
    fn bekor_qilingan_obuna_tejami_va_ortiqcha_otkazish_rad_etiladi() {
        let db = database_with_pin();
        let view = add_subscription(&db, NOW, sub_input("300 000")).expect("obuna");
        let id = view.subscriptions[0].id.clone();
        let cancelled = cancel_subscription(&db, NOW, &id).expect("bekor");
        // Bekor qilingan kun bugun: 1 kun × 300 000 / 30 = 10 000 so'm.
        assert_eq!(cancelled.rescue.subscriptions.minor, "1000000");
        assert_eq!(cancelled.rescue.available.minor, "1000000");

        let too_much = transfer_to_vault_from_rescue(&db, NOW, "20 000");
        assert!(matches!(
            too_much,
            Err(SessionError::Domain(DomainError::RescueExceedsAvailable))
        ));

        let after = transfer_to_vault_from_rescue(&db, NOW, "4 000").expect("o'tkazildi");
        assert_eq!(after.rescue.transferred.minor, "400000");
        assert_eq!(after.rescue.available.minor, "600000");
    }

    #[test]
    fn konvert_hafta_bir_marta_yopiladi() {
        let db = database_with_pin();
        let view = add_envelope(
            &db,
            NOW,
            EnvelopeInputDto {
                name: "Bozor".to_owned(),
                weekly_limit: "500 000".to_owned(),
                category_id: None,
            },
        )
        .expect("konvert");
        let envelope_id = view.envelopes[0].id.clone();
        let closed = close_envelope_week(&db, NOW, &envelope_id).expect("yopildi");
        assert!(closed.envelopes[0].closed_this_week);
        assert_eq!(closed.rescue.envelopes.minor, "50000000");
        assert!(matches!(
            close_envelope_week(&db, NOW, &envelope_id),
            Err(SessionError::Domain(DomainError::EnvelopeWeekClosed))
        ));
    }

    #[test]
    fn bazaviy_davr_faqat_otgan_davr_bolishi_mumkin() {
        let db = database_with_pin();
        assert!(matches!(
            set_baseline_period(&db, NOW, "2026-10-01"),
            Err(SessionError::Domain(DomainError::BaselineNotPast))
        ));
        let view = set_baseline_period(&db, NOW, "2026-09-01").expect("tanlandi");
        assert_eq!(view.rescue.baseline_start, None);
    }
}
