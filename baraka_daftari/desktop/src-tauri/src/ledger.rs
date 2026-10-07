//! D4 commandlari: daromad, Kelajagim, audit, majburiyatlar, bosh sahifa. Commandlar yupqa:
//! matnni parse qiladi → `services` ni chaqiradi → tayyor formatlangan DTO qaytaradi.

use domain::{
    ts_to_string, Income, MoneyOwner, Obligation, ObligationKind, PaymentChannel, ShareRule,
    WithdrawalRequest, DEFAULT_COOLDOWN_SECS,
};
use money::{format_money, parse_amount, Locale, Money, MoneyError};
use serde::{Deserialize, Serialize};
use services::{audit, home, income, obligations, rules, vault, Ctx, ServiceError, YearMonth};
use specta::Type;
use tauri::State;

use crate::{
    commands::{with_session, AppSession, CommandError},
    dto::MoneyDto,
};

const LOCALE: Locale = Locale::Uz;

fn m(v: Money) -> MoneyDto {
    MoneyDto::from_money(v, LOCALE)
}

fn bp32(v: i64) -> u32 {
    u32::try_from(v.max(0)).unwrap_or(u32::MAX)
}

fn amount(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    Ok(parse_amount(text, ctx.currency)?)
}

fn month(text: &str) -> Result<YearMonth, ServiceError> {
    YearMonth::parse(text)
}

fn ts(t: domain::OffsetDateTime) -> String {
    ts_to_string(t).unwrap_or_default()
}

// ---------------------------------------------------------------- DTO'lar

#[derive(Debug, Serialize, Type)]
#[serde(tag = "kind")]
pub enum RuleDto {
    Percent { bp: u32 },
    MonthlyFixed { target: MoneyDto },
}

fn rule_dto(r: ShareRule) -> RuleDto {
    match r {
        ShareRule::Percent { bp } => RuleDto::Percent { bp },
        ShareRule::MonthlyFixed { target } => RuleDto::MonthlyFixed { target: m(target) },
    }
}

#[derive(Debug, Serialize, Type)]
pub struct HomeDto {
    pub month: String,
    /// Bugungi lokal sana (`YYYY-MM-DD`) va shu haftaning boshi (juma).
    pub today: String,
    pub week_start: String,
    pub previous_month: String,
    pub self_paid: MoneyDto,
    /// Oylik daromadga nisbatan, bazis punkt (500 = 5%).
    pub self_paid_bp: u32,
    pub income: MoneyDto,
    pub month_result: MoneyDto,
    pub vault_balance: MoneyDto,
    pub streak_weeks: u32,
    pub best_streak_weeks: u32,
    pub saved_days: u32,
    pub rule: RuleDto,
    pub rate_suggestion_bp: Option<u32>,
    pub pending_withdrawals: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct SuggestionDto {
    pub share: MoneyDto,
    pub allocated_this_month: MoneyDto,
    pub rule: RuleDto,
}

#[derive(Debug, Deserialize, Type)]
pub struct IncomeInput {
    /// Foydalanuvchi yozgan summa (so'mda), Rustda parse qilinadi.
    pub amount: String,
    /// `DAILY_WORK` | `ORDER` | `SALARY` | `OTHER`.
    pub source: String,
    /// `CASH` | `CARD`.
    pub channel: String,
    /// `None` — taklif qilingan ulush.
    pub share: Option<String>,
    /// `TER` | `MOL` | `TAVAKKAL` | `RIBO` (ixtiyoriy; ter / mol / tavakkal testi).
    pub source_type: Option<String>,
}

#[derive(Debug, Serialize, Type)]
pub struct RecordedDto {
    pub income_id: String,
    pub share: MoneyDto,
    pub vault_balance: MoneyDto,
}

#[derive(Debug, Serialize, Type)]
pub struct IncomeDto {
    pub id: String,
    pub source: String,
    pub channel: String,
    pub amount: MoneyDto,
    pub received_on: String,
    /// `TER` | `MOL` | `TAVAKKAL` | `RIBO` yoki belgilanmagan.
    pub source_type: Option<String>,
}

fn income_dto(i: &Income) -> IncomeDto {
    IncomeDto {
        id: i.meta.id.clone(),
        source: i.source.clone(),
        channel: i.channel.as_str().to_owned(),
        amount: m(i.amount),
        received_on: domain::date_to_string(i.received_on).unwrap_or_default(),
        source_type: i.source_type.map(|t| t.as_str().to_owned()),
    }
}

#[derive(Debug, Deserialize, Type)]
pub struct RuleInput {
    /// `PERCENT` (value — bazis punkt, masalan "500") yoki `MONTHLY_FIXED` (value — so'mda summa).
    pub kind: String,
    pub value: String,
}

#[derive(Debug, Serialize, Type)]
pub struct WithdrawalDto {
    pub id: String,
    pub amount: MoneyDto,
    pub reason: String,
    pub available_at: String,
}

fn withdrawal_dto(w: &WithdrawalRequest) -> WithdrawalDto {
    WithdrawalDto {
        id: w.meta.id.clone(),
        amount: m(w.amount),
        reason: w.reason.clone(),
        available_at: ts(w.available_at),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct CategoryTotalDto {
    pub category_id: String,
    pub name: String,
    pub owner: Option<String>,
    pub amount: MoneyDto,
}

#[derive(Debug, Serialize, Type)]
pub struct OwnerShareDto {
    /// `None` — o'zingiz bo'lmagan "boshqa"; egalar `LANDLORD`, `BANK`, `SHOP`, `STATE`, `FUEL`, `OTHER`.
    pub owner: Option<String>,
    pub amount: MoneyDto,
    pub bp: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct OverviewDto {
    pub month: String,
    pub income: MoneyDto,
    pub obligations: MoneyDto,
    pub expenses: MoneyDto,
    pub savings: MoneyDto,
    pub month_result: MoneyDto,
    pub unexplained: MoneyDto,
    pub categories: Vec<CategoryTotalDto>,
    pub owners: Vec<OwnerShareDto>,
    pub self_paid_bp: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct ObligationDto {
    pub id: String,
    pub name: String,
    /// `RECURRING` | `NASIYA`.
    pub kind: String,
    pub owner: String,
    pub amount: MoneyDto,
    pub due_day: u32,
    pub creditor: Option<String>,
    pub remaining: Option<MoneyDto>,
}

fn obligation_dto(o: &Obligation) -> ObligationDto {
    ObligationDto {
        id: o.meta.id.clone(),
        name: o.name.clone(),
        kind: o.kind.as_str().to_owned(),
        owner: o.owner.as_str().to_owned(),
        amount: m(o.amount),
        due_day: u32::from(o.due_day),
        creditor: o.creditor.clone(),
        remaining: o.remaining.map(m),
    }
}

#[derive(Debug, Deserialize, Type)]
pub struct ObligationInput {
    pub name: String,
    pub amount: String,
    pub due_day: u32,
    /// `LANDLORD` | `BANK` | `SHOP` | `STATE` | `FUEL` | `OTHER`.
    pub owner: String,
}

// ---------------------------------------------------------------- commandlar

#[tauri::command]
#[specta::specta]
pub fn home_summary(state: State<'_, AppSession>) -> Result<HomeDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let h = home::summary(db.conn(), env, ctx)?;
            Ok(HomeDto {
                month: h.month.text(),
                today: domain::date_to_string(h.today).unwrap_or_default(),
                week_start: domain::date_to_string(h.week_start).unwrap_or_default(),
                previous_month: h.month.previous().text(),
                self_paid: m(h.self_paid),
                self_paid_bp: bp32(h.self_paid_bp),
                income: m(h.income),
                month_result: m(h.month_result),
                vault_balance: m(h.vault_balance),
                streak_weeks: h.streak.current_weeks,
                best_streak_weeks: h.streak.best_weeks,
                saved_days: h.streak.saved_days,
                rule: rule_dto(h.rule),
                rate_suggestion_bp: h.rate_suggestion,
                pending_withdrawals: u32::try_from(h.pending_withdrawals).unwrap_or(u32::MAX),
            })
        })
    })
}

/// Daromad summasi yozilganda darhol "shundan X so'm — kelajagingiz uchun".
#[tauri::command]
#[specta::specta]
pub fn suggest_share(
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<SuggestionDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let sg = income::suggest(db.conn(), env, ctx, amount(ctx, &amount_text)?)?;
            Ok(SuggestionDto {
                share: m(sg.share),
                allocated_this_month: m(sg.allocated_this_month),
                rule: rule_dto(sg.rule),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn record_income(
    input: IncomeInput,
    state: State<'_, AppSession>,
) -> Result<RecordedDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let channel = PaymentChannel::parse(&input.channel)
                .ok_or(ServiceError::Invalid("kanalni tanlang"))?;
            let share = input
                .share
                .as_deref()
                .map(|t| amount_or_zero(ctx, t))
                .transpose()?;
            let source_type = input
                .source_type
                .as_deref()
                .map(|t| {
                    domain::IncomeSourceType::parse(t)
                        .ok_or(ServiceError::Invalid("manba turi noto'g'ri"))
                })
                .transpose()?;
            let rec = income::record(
                db,
                env,
                ctx,
                income::NewIncome {
                    amount: amount(ctx, &input.amount)?,
                    source: input.source,
                    channel,
                    received_on: None,
                    share,
                    member_id: None,
                    source_type,
                },
            )?;
            Ok(RecordedDto {
                income_id: rec.income_id,
                share: m(rec.share),
                vault_balance: m(vault::balance(db.conn(), ctx)?),
            })
        })
    })
}

/// Ulush maydoni bo'sh yoki "0" bo'lishi mumkin.
fn amount_or_zero(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    if text.trim().is_empty() {
        return Ok(ctx.zero());
    }
    amount(ctx, text)
}

#[tauri::command]
#[specta::specta]
pub fn list_incomes(
    month_text: String,
    state: State<'_, AppSession>,
) -> Result<Vec<IncomeDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(income::list_month(db.conn(), ctx, month(&month_text)?)?
                .iter()
                .map(income_dto)
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_rule(input: RuleInput, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let rule = match input.kind.as_str() {
                "PERCENT" => ShareRule::Percent {
                    bp: input
                        .value
                        .trim()
                        .parse()
                        .map_err(|_| ServiceError::Invalid("foiz butun son bo'lishi kerak"))?,
                },
                "MONTHLY_FIXED" => ShareRule::MonthlyFixed {
                    target: amount(ctx, &input.value)?,
                },
                _ => return Err(ServiceError::Invalid("noma'lum qoida")),
            };
            rules::set(db, env, ctx, rule)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_opening_balance(
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<MoneyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            vault::set_opening_balance(db, env, ctx, amount(ctx, &amount_text)?)?;
            Ok(m(vault::balance(db.conn(), ctx)?))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn request_withdrawal(
    amount_text: String,
    reason: String,
    emergency_confirmed: bool,
    state: State<'_, AppSession>,
) -> Result<WithdrawalDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let req = vault::request_withdrawal(
                db,
                env,
                ctx,
                amount(ctx, &amount_text)?,
                &reason,
                DEFAULT_COOLDOWN_SECS,
                emergency_confirmed,
            )?;
            Ok(withdrawal_dto(&req))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn confirm_withdrawal(
    id: String,
    state: State<'_, AppSession>,
) -> Result<MoneyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            vault::confirm_withdrawal(db, env, ctx, &id)?;
            Ok(m(vault::balance(db.conn(), ctx)?))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn cancel_withdrawal(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| vault::cancel_withdrawal(db, env, ctx, &id))
    })
}

#[tauri::command]
#[specta::specta]
pub fn list_withdrawals(state: State<'_, AppSession>) -> Result<Vec<WithdrawalDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(vault::pending_withdrawals(db.conn(), ctx)?
                .iter()
                .map(withdrawal_dto)
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn audit_overview(
    month_text: String,
    state: State<'_, AppSession>,
) -> Result<OverviewDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            let o = audit::overview(db.conn(), ctx, month(&month_text)?)?;
            Ok(OverviewDto {
                month: o.month.text(),
                income: m(o.income),
                obligations: m(o.obligations),
                expenses: m(o.expenses),
                savings: m(o.savings),
                month_result: m(o.month_result),
                unexplained: m(o.unexplained),
                categories: o
                    .categories
                    .into_iter()
                    .map(|c| CategoryTotalDto {
                        category_id: c.category_id,
                        name: c.name,
                        owner: c.owner.map(|x| x.as_str().to_owned()),
                        amount: m(c.amount),
                    })
                    .collect(),
                owners: o
                    .whose
                    .shares
                    .into_iter()
                    .map(|sh| OwnerShareDto {
                        owner: sh.owner.map(|x| x.as_str().to_owned()),
                        amount: m(sh.amount),
                        bp: bp32(sh.bp),
                    })
                    .collect(),
                self_paid_bp: bp32(o.whose.self_paid_bp),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn audit_set_category(
    month_text: String,
    category_id: String,
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            audit::set_category_total(
                db,
                env,
                ctx,
                month(&month_text)?,
                &category_id,
                amount_or_zero(ctx, &amount_text)?,
            )
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn list_obligations(state: State<'_, AppSession>) -> Result<Vec<ObligationDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(obligations::list(db.conn(), ctx)?
                .iter()
                .map(obligation_dto)
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_obligation(
    input: ObligationInput,
    state: State<'_, AppSession>,
) -> Result<ObligationDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let owner = MoneyOwner::parse(&input.owner)
                .ok_or(ServiceError::Invalid("kimga to'lanishini tanlang"))?;
            let due = u8::try_from(input.due_day)
                .map_err(|_| ServiceError::Invalid("to'lov kuni 1..31"))?;
            let o = obligations::add_recurring(
                db,
                env,
                ctx,
                &input.name,
                amount(ctx, &input.amount)?,
                due,
                owner,
            )?;
            Ok(obligation_dto(&o))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_nasiya(
    creditor: String,
    total_text: String,
    state: State<'_, AppSession>,
) -> Result<ObligationDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let o = obligations::add_nasiya(db, env, ctx, &creditor, amount(ctx, &total_text)?)?;
            Ok(obligation_dto(&o))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn pay_nasiya(
    id: String,
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<MoneyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            Ok(m(obligations::pay_nasiya(
                db,
                env,
                ctx,
                &id,
                amount(ctx, &amount_text)?,
                None,
            )?))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_obligation(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| obligations::remove(db, env, ctx, &id))
    })
}

// Ishlatilmaydigan importlar uchun yagona joy (kelajak commandlari D5+ da qo'shadi).
const _: fn() = || {
    let _ = (
        ObligationKind::Recurring,
        MoneyError::Overflow,
        format_money,
    );
};
