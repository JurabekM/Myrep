//! D4 ilova mantig'i (SPEC 2.1–2.5): daromad, «Kelajagim», oylik audit, «Kimning puli?», majburiyat va nasiya.
//!
//! Modul Tauri'dan mustaqil: har funksiya ochiq [`Database`] ustida ishlaydi. Qoidalar `domain`da,
//! saqlash `storage`da; bu yerda ular ulanadi va DTO tayyorlanadi. Pul hisobi frontendda emas.

use std::collections::BTreeMap;

use domain::calendar::{DateRange, month_of, previous_month_of, shift_days, tashkent_date};
use domain::{
    Category, CategoryKey, Channel, DebtPayment, DomainError, Expense, ExpenseDraft, HabitStats,
    Household, Income, IncomeDraft, LedgerInput, Member, MemberRole, MonthLedger, MonthlyReport,
    Obligation, ObligationDraft, ObligationKind, ShareRule, ShareTarget, ShopDebt, VaultEntry,
    VaultMovement, build_month_ledger,
    debt::{outstanding, validate_payment},
    habit_stats, progression_offer, streak_since, suggest_share,
    vault::{balance, saved_in, validate_initial, validate_share, validate_withdrawal},
    whose_money,
};
use money::{Currency, Money, parse_amount};
use storage::{
    CategoryRepo, Database, DebtRepo, ExpenseRepo, HouseholdRepo, IncomeRepo, MemberRepo,
    ObligationRepo, ReportRepo, RuleRepo, StorageError, VaultRepo,
};
use time::format_description::well_known::Iso8601;
use time::{Date, OffsetDateTime};
use uuid::Uuid;

use crate::dto::{
    AuditDto, AuditStatusDto, CategoryDto, CategorySpentDto, DebtDto, HabitDto, HomeDto, IncomeDto,
    IncomeInputDto, IncomeOutcomeDto, MoneyDto, ObligationDto, ObligationInputDto,
    ObligationLineDto, OwnerPartDto, ShareModeDto, ShareRuleDto, ShareRuleInputDto, VaultDto,
    VaultEntryDto, WhoseMoneyDto,
};
use crate::session::SessionError;

/// Qurilma belgisi: har yozuvda `origin_device_id`. Sinxronlashda qurilmalarni ajratadi.
pub const DEVICE_ID: &str = "desktop";
/// Ilova valyutasi (v1 da faqat so'm, SPEC 4.2).
pub const CURRENCY: Currency = Currency::Uzs;

const HOUSEHOLD_NAME: &str = "Asosiy daftar";
const OWNER_NAME: &str = "O'zim";
/// «Kelajagim» tarixida ko'rsatiladigan yozuvlar soni.
const HISTORY_LIMIT: usize = 50;
/// Tez kiritish uchun so'nggi daromadlar soni.
const RECENT_LIMIT: u32 = 10;
/// Ko'rsatiladigan eng uzoq «oy ortga» (`get_whose_money`).
pub const MAX_MONTHS_BACK: u8 = 24;

/// UUIDv7 identifikator generatori (domen `IdGen` traiti).
pub struct UuidV7;

impl domain::IdGen for UuidV7 {
    fn next_id(&self) -> String {
        Uuid::now_v7().to_string()
    }
}

/// Sana matni (`YYYY-MM-DD`). Formatlash xatosi bo'lmaydi (sana har doim to'g'ri).
pub fn date_text(date: Date) -> String {
    date.format(&Iso8601::DATE).unwrap_or_default()
}

/// Joriy kontekst: xonadon, egasi a'zo va Toshkent bugungi sanasi.
pub struct Context {
    /// Xonadon (oylik kun sozlamasi bilan).
    pub household: Household,
    /// Daromad va xarajatni yozadigan a'zo (egasi).
    pub owner_id: String,
    /// Bugungi sana (Toshkent).
    pub today: Date,
}

/// Xonadon, egasi va standart kategoriyalar yo'q bo'lsa, yaratadi; kontekstni qaytaradi.
pub fn context(db: &Database, now: OffsetDateTime) -> Result<Context, SessionError> {
    let conn = db.connection();
    let ids = UuidV7;
    let household = match HouseholdRepo::new(conn).list()?.into_iter().next() {
        Some(existing) => existing,
        None => {
            let created = Household::create(
                &domain::IdGen::next_id(&ids),
                HOUSEHOLD_NAME,
                now,
                DEVICE_ID,
            )?;
            HouseholdRepo::new(conn).insert(&created)?;
            created
        }
    };
    let household_id = household.id.clone();

    let owner_id = match MemberRepo::new(conn)
        .list_for_household(&household_id)?
        .into_iter()
        .next()
    {
        Some(owner) => owner.id,
        None => {
            let owner = Member::create(
                &domain::IdGen::next_id(&ids),
                &household_id,
                OWNER_NAME,
                MemberRole::Adult,
                now,
                DEVICE_ID,
            )?;
            MemberRepo::new(conn).insert(&owner)?;
            owner.id
        }
    };

    let categories = CategoryRepo::new(conn);
    if categories.list(&household_id)?.is_empty() {
        for key in CategoryKey::ALL {
            let category = Category::system(
                &domain::IdGen::next_id(&ids),
                &household_id,
                key,
                now,
                DEVICE_ID,
            )?;
            categories.insert(&category)?;
        }
    }

    Ok(Context {
        household,
        owner_id,
        today: tashkent_date(now),
    })
}

/// Sana uchun oylik davr (xonadon kuni bo'yicha). Kalendar xatosi — domen xatosi sifatida.
fn month_containing(ctx: &Context, date: Date) -> Result<DateRange, SessionError> {
    month_of(date, ctx.household.month_start_day).ok_or_else(|| DomainError::InvalidDay.into())
}

fn previous_month(ctx: &Context, date: Date) -> Result<DateRange, SessionError> {
    previous_month_of(date, ctx.household.month_start_day)
        .ok_or_else(|| DomainError::InvalidDay.into())
}

/// Matnni so'm summasiga aylantiradi (`8 000 000`, `12,5`).
fn parse_money(text: &str) -> Result<Money, SessionError> {
    Ok(parse_amount(text, CURRENCY).map_err(DomainError::from)?)
}

/// «Kelajagim» aktivining identifikatori (yo'q bo'lsa yaratiladi).
fn vault_asset(db: &Database, now: OffsetDateTime) -> Result<String, SessionError> {
    Ok(VaultRepo::new(db.connection()).ensure_asset(
        &domain::IdGen::next_id(&UuidV7),
        &context_household_id(db, now)?,
        CURRENCY,
        now,
        DEVICE_ID,
    )?)
}

fn context_household_id(db: &Database, now: OffsetDateTime) -> Result<String, SessionError> {
    Ok(context(db, now)?.household.id)
}

/// Barcha «Kelajagim» yozuvlari (tarixdan tashqari hisob uchun).
fn vault_entries(db: &Database, now: OffsetDateTime) -> Result<Vec<VaultEntry>, SessionError> {
    let asset = vault_asset(db, now)?;
    Ok(VaultRepo::new(db.connection()).list_entries(&asset)?)
}

/// Saqlangan qoida (yo'q bo'lsa — standart, saqlanmaydi).
fn current_rule(db: &Database, ctx: &Context) -> Result<(Option<String>, ShareRule), SessionError> {
    Ok(
        match RuleRepo::new(db.connection()).find_active(&ctx.household.id, CURRENCY)? {
            Some(stored) => (Some(stored.id), stored.rule),
            None => (None, ShareRule::default_rule()),
        },
    )
}

/// Qoida saqlangan bo'lishini ta'minlaydi (o'zgartirishdan oldin).
fn ensure_rule(
    db: &Database,
    ctx: &Context,
    now: OffsetDateTime,
) -> Result<(String, ShareRule), SessionError> {
    match current_rule(db, ctx)? {
        (Some(id), rule) => Ok((id, rule)),
        (None, rule) => {
            let id = domain::IdGen::next_id(&UuidV7);
            RuleRepo::new(db.connection()).insert(&id, &ctx.household.id, &rule, now, DEVICE_ID)?;
            Ok((id, rule))
        }
    }
}

/// Ajratish sanalari: faqat daromad ulushlari (boshlang'ich balans va pul olish odat emas).
fn saving_dates(entries: &[VaultEntry]) -> Vec<Date> {
    entries
        .iter()
        .filter(|e| e.counts_as_habit())
        .map(|e| e.occurred_on)
        .collect()
}

fn habit_of(dates: &[Date], today: Date) -> Result<HabitStats, SessionError> {
    habit_stats(dates, today).ok_or_else(|| DomainError::InvalidDay.into())
}

/// Davr uchun hisob: daromad, xarajat, majburiyat, «Kelajagim» va ajratilgan/olingan.
fn ledger_for(
    db: &Database,
    ctx: &Context,
    period: DateRange,
    entries: &[VaultEntry],
) -> Result<MonthLedger, SessionError> {
    let conn = db.connection();
    let household = &ctx.household.id;
    let incomes = IncomeRepo::new(conn).list_in_range(household, period)?;
    let expenses = ExpenseRepo::new(conn).list_in_range(household, period)?;
    let obligations = ObligationRepo::new(conn).list_active(household)?;
    Ok(build_month_ledger(&LedgerInput {
        period,
        currency: CURRENCY,
        incomes: &incomes,
        expenses: &expenses,
        obligations: &obligations,
        vault: entries,
    })?)
}

/// «Kelajagim» holati: balans, shu oy, odat, taklif va tarix.
fn vault_overview(
    db: &Database,
    ctx: &Context,
    now: OffsetDateTime,
) -> Result<VaultDto, SessionError> {
    let entries = vault_entries(db, now)?;
    let (_, rule) = current_rule(db, ctx)?;
    let dates = saving_dates(&entries);
    let habit = habit_of(&dates, ctx.today)?;
    let month = month_containing(ctx, ctx.today)?;
    let weeks = streak_since(&dates, ctx.today, rule.progression_offered_on);
    let offer = progression_offer(&rule, weeks).and_then(|bp| u32::try_from(bp).ok());

    let mut history: Vec<&VaultEntry> = entries.iter().collect();
    history.sort_by(|a, b| {
        b.occurred_on
            .cmp(&a.occurred_on)
            .then(b.meta.created_at.cmp(&a.meta.created_at))
    });
    let history = history
        .into_iter()
        .take(HISTORY_LIMIT)
        .map(vault_entry_dto)
        .collect();

    Ok(VaultDto {
        balance: MoneyDto::of(balance(&entries, CURRENCY)?),
        saved_this_month: MoneyDto::of(saved_in(&entries, month, CURRENCY)?),
        has_initial: entries.iter().any(|e| e.movement == VaultMovement::Initial),
        rule: ShareRuleDto::of(&rule),
        habit: HabitDto::from(&habit),
        progression_offer_bp: offer,
        history,
    })
}

fn vault_entry_dto(entry: &VaultEntry) -> VaultEntryDto {
    let (kind, reason, income_id) = match &entry.movement {
        VaultMovement::Initial => ("INITIAL", None, None),
        VaultMovement::IncomeShare { income_id } => ("INCOME_SHARE", None, Some(income_id.clone())),
        VaultMovement::Withdrawal { reason } => ("WITHDRAWAL", Some(reason.clone()), None),
    };
    VaultEntryDto {
        id: entry.id.clone(),
        kind: kind.to_owned(),
        amount: MoneyDto::of(entry.amount),
        occurred_on: date_text(entry.occurred_on),
        reason,
        income_id,
    }
}

/// Bosh ekran ko'rsatkichlari.
pub fn home(db: &Database, now: OffsetDateTime) -> Result<HomeDto, SessionError> {
    let ctx = context(db, now)?;
    let entries = vault_entries(db, now)?;
    let period = month_containing(&ctx, ctx.today)?;
    let ledger = ledger_for(db, &ctx, period, &entries)?;
    let audit_period = previous_month(&ctx, ctx.today)?;
    let audit_done =
        ReportRepo::new(db.connection()).exists_for(&ctx.household.id, audit_period.start)?;
    let habit = habit_of(&saving_dates(&entries), ctx.today)?;
    Ok(HomeDto {
        paid_to_self: MoneyDto::of(ledger.saved_deposited),
        vault_balance: MoneyDto::of(balance(&entries, CURRENCY)?),
        income: MoneyDto::of(ledger.income),
        month_result: MoneyDto::of(ledger.unexplained()?),
        habit: HabitDto::from(&habit),
        audit: AuditStatusDto {
            done: audit_done,
            period_start: date_text(audit_period.start),
            period_end: date_text(audit_period.end),
        },
    })
}

/// Joriy oydagi daromadlar, eng yangisi birinchi.
pub fn incomes_this_month(
    db: &Database,
    now: OffsetDateTime,
) -> Result<Vec<IncomeDto>, SessionError> {
    let ctx = context(db, now)?;
    let period = month_containing(&ctx, ctx.today)?;
    let incomes = IncomeRepo::new(db.connection()).list_in_range(&ctx.household.id, period)?;
    Ok(incomes.iter().map(IncomeDto::of).collect())
}

/// Daromad saqlanadi va ulush taklifi qaytadi (`Shundan X so'm — kelajagingiz uchun`).
pub fn create_income(
    db: &Database,
    now: OffsetDateTime,
    input: IncomeInputDto,
) -> Result<IncomeOutcomeDto, SessionError> {
    let ctx = context(db, now)?;
    let amount = parse_money(&input.amount)?;
    let income = Income::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        IncomeDraft {
            member_id: ctx.owner_id.clone(),
            source: input.source,
            channel: Channel::from(input.channel),
            amount,
            occurred_on: ctx.today,
            note: input.note,
        },
        now,
        DEVICE_ID,
    )?;
    IncomeRepo::new(db.connection()).insert(&income)?;

    let (_, rule) = current_rule(db, &ctx)?;
    let entries = vault_entries(db, now)?;
    let month = month_containing(&ctx, ctx.today)?;
    let saved = saved_in(&entries, month, CURRENCY)?;
    let suggestion = suggest_share(income.amount, &rule, saved)
        .map_err(DomainError::from)?
        .map(MoneyDto::of);
    Ok(IncomeOutcomeDto {
        income: IncomeDto::of(&income),
        share_suggestion: suggestion,
    })
}

/// So'nggi daromadlar (tez kiritish shablonlari uchun).
pub fn recent_incomes(db: &Database, now: OffsetDateTime) -> Result<Vec<IncomeDto>, SessionError> {
    let ctx = context(db, now)?;
    let incomes = IncomeRepo::new(db.connection()).list_recent(&ctx.household.id, RECENT_LIMIT)?;
    Ok(incomes.iter().map(IncomeDto::of).collect())
}

/// Taklif qabul qilinadi: daromaddan «Kelajagim»ga ulush yoziladi.
pub fn accept_share(
    db: &Database,
    now: OffsetDateTime,
    income_id: &str,
    amount_text: &str,
) -> Result<VaultDto, SessionError> {
    let ctx = context(db, now)?;
    let income = IncomeRepo::new(db.connection())
        .find(income_id)?
        .ok_or(StorageError::NotFound)?;
    let share = parse_money(amount_text)?;
    let entries = vault_entries(db, now)?;
    validate_share(&entries, &income.id, income.amount, share)?;
    insert_vault_entry(
        db,
        now,
        &ctx,
        share,
        VaultMovement::IncomeShare {
            income_id: income.id.clone(),
        },
    )?;
    vault_overview(db, &ctx, now)
}

/// Yozuv qo'shadi (ulush, boshlang'ich balans yoki pul olish).
fn insert_vault_entry(
    db: &Database,
    now: OffsetDateTime,
    ctx: &Context,
    amount: Money,
    movement: VaultMovement,
) -> Result<(), SessionError> {
    let asset = vault_asset(db, now)?;
    let entry = VaultEntry {
        id: domain::IdGen::next_id(&UuidV7),
        amount,
        occurred_on: ctx.today,
        movement,
        meta: domain::Meta::created(now, DEVICE_ID),
    };
    VaultRepo::new(db.connection()).insert_entry(&asset, &ctx.household.id, &entry)?;
    Ok(())
}

/// «Kelajagim» ekrani.
pub fn vault(db: &Database, now: OffsetDateTime) -> Result<VaultDto, SessionError> {
    let ctx = context(db, now)?;
    vault_overview(db, &ctx, now)
}

/// Progressiv taklifni qabul qiladi yoki rad etadi. Ikkala holatda ketma-ketlik yangidan sanaladi.
pub fn respond_progression(
    db: &Database,
    now: OffsetDateTime,
    accept: bool,
) -> Result<VaultDto, SessionError> {
    let ctx = context(db, now)?;
    let (rule_id, rule) = ensure_rule(db, &ctx, now)?;
    let entries = vault_entries(db, now)?;
    let weeks = streak_since(
        &saving_dates(&entries),
        ctx.today,
        rule.progression_offered_on,
    );
    let offer = progression_offer(&rule, weeks).ok_or(DomainError::InvalidRule)?;
    let target = if accept {
        ShareTarget::Percent(offer)
    } else {
        rule.target
    };
    let next = ShareRule {
        target,
        progressive: rule.progressive,
        progression_offered_on: Some(ctx.today),
    };
    RuleRepo::new(db.connection()).update(&rule_id, &next, now)?;
    vault_overview(db, &ctx, now)
}

/// Ulush qoidasini o'zgartiradi: foiz yoki oylik summa, progressiv rejim bilan.
pub fn set_share_rule(
    db: &Database,
    now: OffsetDateTime,
    input: ShareRuleInputDto,
) -> Result<VaultDto, SessionError> {
    let ctx = context(db, now)?;
    let (rule_id, old) = ensure_rule(db, &ctx, now)?;
    let target = match input.mode {
        ShareModeDto::Percent => {
            let bp = input.basis_points.ok_or(DomainError::InvalidRule)?;
            ShareTarget::Percent(i64::from(bp))
        }
        ShareModeDto::Fixed => {
            let text = input.fixed_amount.ok_or(DomainError::InvalidRule)?;
            ShareTarget::Fixed(parse_money(&text)?)
        }
    };
    // Progressiv rejimga yangi kirilsa, ketma-ketlik shu kundan boshlanadi.
    let offered_on = if input.progressive && !old.progressive {
        Some(ctx.today)
    } else {
        old.progression_offered_on
    };
    let next = ShareRule {
        target,
        progressive: input.progressive,
        progression_offered_on: offered_on,
    };
    next.validate()?;
    RuleRepo::new(db.connection()).update(&rule_id, &next, now)?;
    vault_overview(db, &ctx, now)
}

/// Boshlang'ich balans (ro'molcha): bir marta.
pub fn set_initial_balance(
    db: &Database,
    now: OffsetDateTime,
    amount_text: &str,
) -> Result<VaultDto, SessionError> {
    let ctx = context(db, now)?;
    let amount = parse_money(amount_text)?;
    validate_initial(&vault_entries(db, now)?)?;
    if amount.minor() <= 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    insert_vault_entry(db, now, &ctx, amount, VaultMovement::Initial)?;
    vault_overview(db, &ctx, now)
}

/// Pul olish: sabab majburiy, balansdan oshmaydi. PIN tekshiruvi chaqiruvchida.
pub fn withdraw(
    db: &Database,
    now: OffsetDateTime,
    amount_text: &str,
    reason: &str,
) -> Result<VaultDto, SessionError> {
    let ctx = context(db, now)?;
    let amount = parse_money(amount_text)?;
    let current = balance(&vault_entries(db, now)?, CURRENCY)?;
    let reason = validate_withdrawal(current, amount, reason)?;
    insert_vault_entry(db, now, &ctx, amount, VaultMovement::Withdrawal { reason })?;
    vault_overview(db, &ctx, now)
}

/// Audit davri: o'tgan oy.
fn audit_period(ctx: &Context) -> Result<DateRange, SessionError> {
    previous_month(ctx, ctx.today)
}

/// O'tgan oy uchun audit ekrani.
pub fn audit(db: &Database, now: OffsetDateTime) -> Result<AuditDto, SessionError> {
    let ctx = context(db, now)?;
    let period = audit_period(&ctx)?;
    build_audit(db, &ctx, now, period)
}

fn build_audit(
    db: &Database,
    ctx: &Context,
    now: OffsetDateTime,
    period: DateRange,
) -> Result<AuditDto, SessionError> {
    let entries = vault_entries(db, now)?;
    let ledger = ledger_for(db, ctx, period, &entries)?;
    let categories = CategoryRepo::new(db.connection()).list(&ctx.household.id)?;
    let names: BTreeMap<&str, &Category> = categories.iter().map(|c| (c.id.as_str(), c)).collect();
    let spent = ledger
        .expenses_by_category
        .iter()
        .map(|(category_id, amount)| {
            let category = category_id.as_deref().and_then(|id| names.get(id).copied());
            CategorySpentDto {
                category_id: category_id.clone(),
                name: category.map(|c| c.name.clone()),
                system_key: category
                    .and_then(|c| c.system_key)
                    .map(|k| k.code().to_owned()),
                amount: MoneyDto::of(*amount),
            }
        })
        .collect();
    let lines = ledger
        .obligations
        .iter()
        .map(|line| ObligationLineDto {
            title: line.title.clone(),
            kind: line.kind.code().to_owned(),
            amount: MoneyDto::of(line.amount),
            recorded: MoneyDto::of(line.recorded),
            remainder: MoneyDto::of(line.remainder),
        })
        .collect();
    let done = ReportRepo::new(db.connection()).exists_for(&ctx.household.id, period.start)?;
    Ok(AuditDto {
        period_start: date_text(period.start),
        period_end: date_text(period.end),
        done,
        income: MoneyDto::of(ledger.income),
        expenses: MoneyDto::of(ledger.expenses),
        obligations_total: MoneyDto::of(ledger.obligations_total()?),
        obligations_unrecorded: MoneyDto::of(ledger.obligations_unrecorded()?),
        net_savings: MoneyDto::of(ledger.net_savings()?),
        unexplained: MoneyDto::of(ledger.unexplained()?),
        lines,
        spent,
        categories: categories.iter().map(category_dto).collect(),
    })
}

fn category_dto(category: &Category) -> CategoryDto {
    CategoryDto {
        id: category.id.clone(),
        name: category.name.clone(),
        system_key: category.system_key.map(|k| k.code().to_owned()),
    }
}

/// Audit davrida bo'lmagan yoki yakunlangan bo'lsa — xato.
fn ensure_audit_open(db: &Database, ctx: &Context, period: DateRange) -> Result<(), SessionError> {
    if ReportRepo::new(db.connection()).exists_for(&ctx.household.id, period.start)? {
        return Err(DomainError::AuditAlreadyDone.into());
    }
    Ok(())
}

/// Audit davri oxirgi kuni: qo'lda kiritilgan xarajat va belgilangan izohsiz summa shu kunga yoziladi.
fn last_day(period: DateRange) -> Result<Date, SessionError> {
    shift_days(period.end, -1).ok_or_else(|| DomainError::InvalidDay.into())
}

/// Audit davriga xarajat qo'shadi (kategoriya bilan).
pub fn add_audit_expense(
    db: &Database,
    now: OffsetDateTime,
    amount_text: &str,
    category_id: &str,
    note: Option<String>,
) -> Result<AuditDto, SessionError> {
    let ctx = context(db, now)?;
    let period = audit_period(&ctx)?;
    ensure_audit_open(db, &ctx, period)?;
    let amount = parse_money(amount_text)?;
    let known = CategoryRepo::new(db.connection())
        .list(&ctx.household.id)?
        .iter()
        .any(|c| c.id == category_id);
    if !known {
        return Err(StorageError::NotFound.into());
    }
    insert_expense(
        db,
        now,
        &ctx,
        amount,
        Some(category_id.to_owned()),
        last_day(period)?,
        note,
    )?;
    build_audit(db, &ctx, now, period)
}

fn insert_expense(
    db: &Database,
    now: OffsetDateTime,
    ctx: &Context,
    amount: Money,
    category_id: Option<String>,
    occurred_on: Date,
    note: Option<String>,
) -> Result<(), SessionError> {
    let expense = Expense::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        ExpenseDraft {
            member_id: ctx.owner_id.clone(),
            category_id,
            amount,
            occurred_on,
            note,
        },
        now,
        DEVICE_ID,
    )?;
    ExpenseRepo::new(db.connection()).insert(&expense)?;
    Ok(())
}

/// Izohsiz qolgan summani «mayda kundalik xarajat» deb belgilaydi.
pub fn mark_unexplained_as_daily(
    db: &Database,
    now: OffsetDateTime,
) -> Result<AuditDto, SessionError> {
    let ctx = context(db, now)?;
    let period = audit_period(&ctx)?;
    ensure_audit_open(db, &ctx, period)?;
    let entries = vault_entries(db, now)?;
    let gap = ledger_for(db, &ctx, period, &entries)?.unexplained()?;
    if gap.minor() <= 0 {
        return Err(DomainError::NothingToMark.into());
    }
    let daily = CategoryRepo::new(db.connection())
        .find_system(&ctx.household.id, CategoryKey::DailySmall)?
        .ok_or(StorageError::NotFound)?;
    insert_expense(db, now, &ctx, gap, Some(daily), last_day(period)?, None)?;
    build_audit(db, &ctx, now, period)
}

/// Auditni yakunlaydi: davr uchun o'zgarmas hisobot yoziladi.
pub fn finish_audit(db: &Database, now: OffsetDateTime) -> Result<AuditDto, SessionError> {
    let ctx = context(db, now)?;
    let period = audit_period(&ctx)?;
    ensure_audit_open(db, &ctx, period)?;
    let entries = vault_entries(db, now)?;
    let ledger = ledger_for(db, &ctx, period, &entries)?;
    let report = MonthlyReport::from_ledger(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        &ledger,
        now,
        DEVICE_ID,
    )?;
    ReportRepo::new(db.connection()).insert(&report)?;
    build_audit(db, &ctx, now, period)
}

/// «Kimning puli?»: `months_back` oy oldingi davr (0 — joriy oy).
pub fn whose_money_for(
    db: &Database,
    now: OffsetDateTime,
    months_back: u8,
) -> Result<WhoseMoneyDto, SessionError> {
    let ctx = context(db, now)?;
    let mut period = month_containing(&ctx, ctx.today)?;
    for _ in 0..months_back.min(MAX_MONTHS_BACK) {
        period = previous_month(&ctx, period.start)?;
    }
    let entries = vault_entries(db, now)?;
    let ledger = ledger_for(db, &ctx, period, &entries)?;
    let keys: BTreeMap<String, CategoryKey> = CategoryRepo::new(db.connection())
        .list(&ctx.household.id)?
        .into_iter()
        .filter_map(|c| c.system_key.map(|key| (c.id, key)))
        .collect();
    let shares = whose_money(&ledger, &keys)?;
    let total = shares
        .iter()
        .try_fold(Money::zero(CURRENCY), |acc, (_, amount)| {
            acc.checked_add(*amount)
        })
        .map_err(DomainError::from)?;
    let parts = shares
        .into_iter()
        .map(|(owner, amount)| {
            let bp = money::round_half_up_div(
                i128::from(amount.minor()) * 10_000,
                i128::from(total.minor().max(1)),
            )
            .map_err(DomainError::from)?;
            Ok(OwnerPartDto {
                owner: owner.code().to_owned(),
                amount: MoneyDto::of(amount),
                share_bp: u32::try_from(bp).unwrap_or(0),
            })
        })
        .collect::<Result<Vec<_>, SessionError>>()?;
    Ok(WhoseMoneyDto {
        period_start: date_text(period.start),
        period_end: date_text(period.end),
        total: MoneyDto::of(total),
        parts,
    })
}

/// Kategoriyalar ro'yxati.
pub fn categories(db: &Database, now: OffsetDateTime) -> Result<Vec<CategoryDto>, SessionError> {
    let ctx = context(db, now)?;
    let list = CategoryRepo::new(db.connection()).list(&ctx.household.id)?;
    Ok(list.iter().map(category_dto).collect())
}

/// Majburiyatlar ro'yxati (faol).
pub fn obligations(db: &Database, now: OffsetDateTime) -> Result<Vec<ObligationDto>, SessionError> {
    let ctx = context(db, now)?;
    let list = ObligationRepo::new(db.connection()).list_active(&ctx.household.id)?;
    Ok(list
        .iter()
        .map(|o| ObligationDto {
            id: o.id.clone(),
            title: o.title.clone(),
            kind: o.kind.code().to_owned(),
            amount: MoneyDto::of(o.amount),
            due_day: o.due_day,
            active: o.active,
        })
        .collect())
}

/// Majburiyat qo'shadi: turiga mos standart kategoriyaga bog'lanadi.
pub fn add_obligation(
    db: &Database,
    now: OffsetDateTime,
    input: ObligationInputDto,
) -> Result<Vec<ObligationDto>, SessionError> {
    let ctx = context(db, now)?;
    let kind = ObligationKind::from(input.kind);
    let category = CategoryRepo::new(db.connection())
        .find_system(&ctx.household.id, kind.default_category())?;
    let obligation = Obligation::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        ObligationDraft {
            title: input.title,
            kind,
            amount: parse_money(&input.amount)?,
            due_day: input.due_day,
            category_id: category,
        },
        now,
        DEVICE_ID,
    )?;
    ObligationRepo::new(db.connection()).insert(&obligation)?;
    obligations(db, now)
}

/// Majburiyatni faolligini o'zgartiradi (o'chirilgani hisobda qolmaydi).
pub fn set_obligation_active(
    db: &Database,
    now: OffsetDateTime,
    id: &str,
    active: bool,
) -> Result<Vec<ObligationDto>, SessionError> {
    ObligationRepo::new(db.connection()).set_active(id, active, now)?;
    obligations(db, now)
}

fn debt_dto(db: &Database, debt: &ShopDebt) -> Result<DebtDto, SessionError> {
    let payments = DebtRepo::new(db.connection()).payment_amounts(&debt.id, CURRENCY)?;
    let left = outstanding(debt.principal, &payments)?;
    Ok(DebtDto {
        id: debt.id.clone(),
        creditor: debt.creditor.clone(),
        principal: MoneyDto::of(debt.principal),
        outstanding: MoneyDto::of(left),
        incurred_on: date_text(debt.incurred_on),
        note: debt.note.clone(),
    })
}

/// Nasiyalar ro'yxati va har birining qoldig'i.
pub fn debts(db: &Database, now: OffsetDateTime) -> Result<Vec<DebtDto>, SessionError> {
    let ctx = context(db, now)?;
    let list = DebtRepo::new(db.connection()).list_debts(&ctx.household.id)?;
    list.iter().map(|debt| debt_dto(db, debt)).collect()
}

/// Nasiya qo'shadi.
pub fn add_debt(
    db: &Database,
    now: OffsetDateTime,
    creditor: &str,
    amount_text: &str,
    note: Option<String>,
) -> Result<Vec<DebtDto>, SessionError> {
    let ctx = context(db, now)?;
    let debt = ShopDebt::create(
        &domain::IdGen::next_id(&UuidV7),
        &ctx.household.id,
        creditor,
        parse_money(amount_text)?,
        ctx.today,
        now,
        DEVICE_ID,
    )?
    .with_note(note);
    DebtRepo::new(db.connection()).insert_debt(&debt)?;
    debts(db, now)
}

/// Nasiyaga qisman to'lov. Qoldiqdan oshsa — xato.
pub fn pay_debt(
    db: &Database,
    now: OffsetDateTime,
    debt_id: &str,
    amount_text: &str,
) -> Result<Vec<DebtDto>, SessionError> {
    let ctx = context(db, now)?;
    let debt = DebtRepo::new(db.connection())
        .list_debts(&ctx.household.id)?
        .into_iter()
        .find(|d| d.id == debt_id)
        .ok_or(StorageError::NotFound)?;
    let payments = DebtRepo::new(db.connection()).payment_amounts(&debt.id, CURRENCY)?;
    let left = outstanding(debt.principal, &payments)?;
    let amount = parse_money(amount_text)?;
    validate_payment(left, amount)?;
    let payment = DebtPayment {
        id: domain::IdGen::next_id(&UuidV7),
        debt_id: debt.id.clone(),
        amount,
        paid_on: ctx.today,
        meta: domain::Meta::created(now, DEVICE_ID),
    };
    DebtRepo::new(db.connection()).insert_payment(&ctx.household.id, &payment)?;
    debts(db, now)
}

#[cfg(test)]
mod tests {
    use super::*;
    use domain::IdGen;

    #[test]
    fn uuid_v7_domen_tekshiruvidan_otadi() {
        let id = UuidV7.next_id();
        assert!(domain::validate_uuid_v7(&id).is_ok(), "{id}");
    }

    use security::SecretKey;
    use storage::{Database as Db, IncomeRepo as Incomes, ObligationRepo as Obligations};
    use time::macros::datetime;

    fn fresh() -> Db {
        Db::open_in_memory(&SecretKey::from_array([7; 32])).expect("xotirada baza")
    }

    fn now() -> OffsetDateTime {
        datetime!(2026-10-14 06:00 UTC)
    }

    fn share_input(amount: &str) -> IncomeInputDto {
        IncomeInputDto {
            amount: amount.to_owned(),
            source: "Kunlik ish".to_owned(),
            channel: crate::dto::ChannelDto::Cash,
            note: None,
        }
    }

    fn rule_code(error: SessionError) -> String {
        match error {
            SessionError::Domain(domain_error) => domain_error.code().to_owned(),
            other => format!("{other}"),
        }
    }

    #[test]
    fn daromad_ulush_kelajagim_balansi_oqimi() {
        let db = fresh();
        let outcome = create_income(&db, now(), share_input("150 000")).expect("daromad");
        let suggestion = outcome.share_suggestion.expect("taklif bor");
        assert_eq!(suggestion.minor, "800000", "5 % → 8 000 so'm");

        // UI taklif summasini `formatted` ko'rinishida qaytaradi (`8 000 soʻm`): parser shuni qabul qiladi.
        let vault =
            accept_share(&db, now(), &outcome.income.id, &suggestion.formatted).expect("ulush");
        assert_eq!(vault.balance.minor, "800000");
        assert_eq!(vault.history.len(), 1);
        assert_eq!(vault.history[0].kind, "INCOME_SHARE");
        assert_eq!(
            vault.history[0].income_id.as_deref(),
            Some(outcome.income.id.as_str())
        );

        let home = home(&db, now()).expect("bosh sahifa");
        assert_eq!(home.paid_to_self.minor, "800000");
        assert_eq!(home.habit.current_streak_weeks, 1);
    }

    #[test]
    fn bir_daromaddan_ikki_marta_ulush_olinmaydi() {
        let db = fresh();
        let outcome = create_income(&db, now(), share_input("150 000")).expect("daromad");
        accept_share(&db, now(), &outcome.income.id, "8000").expect("birinchi");
        let error = accept_share(&db, now(), &outcome.income.id, "1000").expect_err("takror");
        assert_eq!(rule_code(error), "INCOME_ALREADY_SHARED");
    }

    #[test]
    fn pul_olish_sabab_va_balans_qoidasi() {
        let db = fresh();
        set_initial_balance(&db, now(), "100 000").expect("ro'molcha");
        let missing = withdraw(&db, now(), "200 000", "Dori").expect_err("balansdan ko'p");
        assert_eq!(rule_code(missing), "INSUFFICIENT_BALANCE");
        let no_reason = withdraw(&db, now(), "1 000", "   ").expect_err("sababsiz");
        assert_eq!(rule_code(no_reason), "REASON_REQUIRED");

        let vault = withdraw(&db, now(), "30 000", "Dori").expect("pul olish");
        assert_eq!(vault.balance.minor, "7000000");
        // Bir xil sana va vaqt (test soati qotirilgan): tartib emas, yozuv turi tekshiriladi.
        assert!(
            vault
                .history
                .iter()
                .any(|entry| entry.kind == "WITHDRAWAL" && entry.reason.as_deref() == Some("Dori"))
        );
    }

    #[test]
    fn boshlangich_balans_bir_marta() {
        let db = fresh();
        set_initial_balance(&db, now(), "100 000").expect("birinchi");
        let again = set_initial_balance(&db, now(), "50 000").expect_err("ikkinchi");
        assert_eq!(rule_code(again), "INITIAL_ALREADY_SET");
        let vault = vault(&db, now()).expect("kelajagim");
        assert!(vault.has_initial);
        assert_eq!(vault.habit.total_weeks, 0, "ro'molcha odat emas");
    }

    #[test]
    fn oylik_audit_izohsiz_summa_va_yakun() {
        let db = fresh();
        let ctx = context(&db, now()).expect("kontekst");
        // Audit davri: sentabr 2026. Yozuvlar shu oyga tegishli sanalar bilan kiritiladi.
        let september = date_of(2026, 9, 10);
        let income = Income::create(
            &UuidV7.next_id(),
            &ctx.household.id,
            IncomeDraft {
                member_id: ctx.owner_id.clone(),
                source: "Oylik".to_owned(),
                channel: Channel::Card,
                amount: Money::new(300_000_000, CURRENCY),
                occurred_on: september,
                note: None,
            },
            now(),
            DEVICE_ID,
        )
        .expect("daromad");
        Incomes::new(db.connection())
            .insert(&income)
            .expect("saqlansin");

        let categories = CategoryRepo::new(db.connection())
            .list(&ctx.household.id)
            .expect("kategoriyalar");
        let rent = categories
            .iter()
            .find(|c| c.system_key == Some(CategoryKey::Rent))
            .expect("ijara kategoriyasi")
            .id
            .clone();
        let obligation = Obligation::create(
            &UuidV7.next_id(),
            &ctx.household.id,
            ObligationDraft {
                title: "Ijara".to_owned(),
                kind: ObligationKind::Rent,
                amount: Money::new(150_000_000, CURRENCY),
                due_day: Some(5),
                category_id: Some(rent.clone()),
            },
            // Sentabr oxirigacha yaratilgan bo'lishi kerak (aks holda o'tgan oyga kirmaydi).
            datetime!(2026-08-20 06:00 UTC),
            DEVICE_ID,
        )
        .expect("majburiyat");
        Obligations::new(db.connection())
            .insert(&obligation)
            .expect("saqlansin");

        // Ijara 1,5 mln, kategoriyada 1,5 mln yozilgan — majburiyat qoplanadi, qo'shimcha hisob yo'q.
        let audit_first = add_audit_expense(&db, now(), "1 500 000", &rent, None).expect("xarajat");
        assert_eq!(
            audit_first.unexplained.minor, "150000000",
            "3 mln − 1,5 mln ijara − 0 = 1,5 mln"
        );
        assert!(!audit_first.done);

        let daily = mark_unexplained_as_daily(&db, now()).expect("izohsiz belgilash");
        assert_eq!(daily.unexplained.minor, "0");

        let finished = finish_audit(&db, now()).expect("yakun");
        assert!(finished.done);
        let closed = add_audit_expense(&db, now(), "1000", &rent, None).expect_err("yopiq");
        assert_eq!(rule_code(closed), "AUDIT_ALREADY_DONE");

        let expenses = ExpenseRepo::new(db.connection())
            .list_in_range(
                &ctx.household.id,
                domain::calendar::month_of(september, 1).expect("oy"),
            )
            .expect("xarajatlar");
        assert_eq!(expenses.len(), 2, "ijara va mayda kundalik");
    }

    fn date_of(year: i32, month: u8, day: u8) -> Date {
        Date::from_calendar_date(year, time::Month::try_from(month).expect("oy"), day)
            .expect("sana")
    }

    #[test]
    fn sana_matni_iso_formatda() {
        let date = Date::from_calendar_date(2026, time::Month::October, 9).expect("sana");
        assert_eq!(date_text(date), "2026-10-09");
    }
}
