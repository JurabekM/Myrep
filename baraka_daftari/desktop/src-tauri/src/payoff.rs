//! D10 commandlari (4-qonun): `DEBT_RECOVERY` rejimi (70/20/10), qarzdan chiqish rejalovchisi,
//! kalkulyator, to'lovchilar va sotiladigan buyumlar.

use domain::{date_from_str, date_to_string, BudgetMode, LoanKind, RecoverySplit, SellStatus};
use money::{parse_amount, Locale, Money};
use serde::Serialize;
use services::{contributors, payoff, recovery, sellables, Ctx, ServiceError};
use specta::Type;
use tauri::State;

use crate::{
    commands::{with_session, AppSession, CommandError},
    dto::MoneyDto,
    guard::percent_to_bp,
};

const LOCALE: Locale = Locale::Uz;

fn m(v: Money) -> MoneyDto {
    MoneyDto::from_money(v, LOCALE)
}

fn amount(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    Ok(parse_amount(text, ctx.currency)?)
}

fn zero_or(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    if text.trim().is_empty() {
        Ok(ctx.zero())
    } else {
        amount(ctx, text)
    }
}

fn ds(d: domain::Date) -> String {
    date_to_string(d).unwrap_or_default()
}

// ---------------------------------------------------------------- rejim

#[derive(Debug, Serialize, Type)]
pub struct SplitAmountsDto {
    pub living: MoneyDto,
    pub extra: MoneyDto,
    pub savings: MoneyDto,
}

#[derive(Debug, Serialize, Type)]
pub struct RecoveryDto {
    /// `STANDARD` | `DEBT_RECOVERY`.
    pub mode: String,
    pub living_bp: u32,
    pub extra_bp: u32,
    pub savings_bp: u32,
    pub suggest_recovery: bool,
    /// Barcha qarz yopilgani uchun rejim avtomatik qaytdi.
    pub reverted_notice: bool,
    pub amounts: Option<SplitAmountsDto>,
}

#[tauri::command]
#[specta::specta]
pub fn recovery_status(state: State<'_, AppSession>) -> Result<RecoveryDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let st = recovery::status(db, env, ctx)?;
            Ok(RecoveryDto {
                mode: st.mode.as_str().to_owned(),
                living_bp: st.split.living_bp,
                extra_bp: st.split.extra_bp,
                savings_bp: st.split.savings_bp,
                suggest_recovery: st.suggest_recovery,
                reverted_notice: st.reverted_notice,
                amounts: st.amounts.map(|a| SplitAmountsDto {
                    living: m(a.living),
                    extra: m(a.extra),
                    savings: m(a.savings),
                }),
            })
        })
    })
}

/// `mode`: `STANDARD` | `DEBT_RECOVERY`.
#[tauri::command]
#[specta::specta]
pub fn set_budget_mode(mode: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let new = BudgetMode::parse(&mode).ok_or(ServiceError::Invalid("rejim noto'g'ri"))?;
            recovery::set_mode(db, env, ctx, new)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_recovery_split(
    living_bp: u32,
    extra_bp: u32,
    savings_bp: u32,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            recovery::set_split(
                db,
                env,
                ctx,
                RecoverySplit {
                    living_bp,
                    extra_bp,
                    savings_bp,
                },
            )
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn dismiss_recovery_notice(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| s.run(recovery::dismiss_notice))
}

// ---------------------------------------------------------------- rejalovchi

#[derive(Debug, Serialize, Type)]
pub struct SourcesDto {
    pub monthly_share: Option<MoneyDto>,
    pub rescued_available: MoneyDto,
    pub sellable_listed: MoneyDto,
}

#[tauri::command]
#[specta::specta]
pub fn payoff_sources(state: State<'_, AppSession>) -> Result<SourcesDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let x = payoff::sources(db.conn(), env, ctx)?;
            Ok(SourcesDto {
                monthly_share: x.monthly_share.map(m),
                rescued_available: m(x.rescued_available),
                sellable_listed: m(x.sellable_listed),
            })
        })
    })
}

#[derive(Debug, Serialize, Type)]
pub struct DebtLineDto {
    pub id: String,
    pub creditor: String,
    pub baseline_months: u32,
    pub accelerated_months: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct PlanDto {
    pub order: Vec<String>,
    pub manual_order: bool,
    pub lines: Vec<DebtLineDto>,
    pub baseline_months: u32,
    pub accelerated_months: u32,
    pub months_saved: u32,
    /// «Qarzsiz kun» (`YYYY-MM-DD`, oyning oxirgi kuni).
    pub debt_free_baseline: Option<String>,
    pub debt_free_accelerated: Option<String>,
}

/// `monthly_extra` va `one_off` — foydalanuvchi matni (bo'sh — 0).
#[tauri::command]
#[specta::specta]
pub fn payoff_plan(
    monthly_extra: String,
    one_off: String,
    state: State<'_, AppSession>,
) -> Result<Option<PlanDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let p = payoff::plan(
                db.conn(),
                env,
                ctx,
                zero_or(ctx, &monthly_extra)?,
                zero_or(ctx, &one_off)?,
            )?;
            Ok(p.map(|p| PlanDto {
                order: p.order,
                manual_order: p.manual_order,
                lines: p
                    .lines
                    .into_iter()
                    .map(|l| DebtLineDto {
                        id: l.id,
                        creditor: l.creditor,
                        baseline_months: l.baseline_months,
                        accelerated_months: l.accelerated_months,
                    })
                    .collect(),
                baseline_months: p.baseline_months,
                accelerated_months: p.accelerated_months,
                months_saved: p.months_saved,
                debt_free_baseline: p.debt_free_baseline.map(ds),
                debt_free_accelerated: p.debt_free_accelerated.map(ds),
            }))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_closing_order(
    ids: Vec<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| payoff::set_order(db, env, ctx, &ids))
    })
}

#[tauri::command]
#[specta::specta]
pub fn clear_closing_order(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| s.run(payoff::clear_order))
}

// ---------------------------------------------------------------- kalkulyator

#[derive(Debug, Serialize, Type)]
pub struct ScheduleRowDto {
    pub month: u32,
    pub interest: MoneyDto,
    pub principal: MoneyDto,
    pub extra: MoneyDto,
    pub balance: MoneyDto,
}

#[derive(Debug, Serialize, Type)]
pub struct AmortizationDto {
    pub first_payment: MoneyDto,
    pub months: u32,
    pub total_interest: MoneyDto,
    pub schedule: Vec<ScheduleRowDto>,
}

fn amort_dto(a: &domain::Amortization) -> AmortizationDto {
    AmortizationDto {
        first_payment: m(a.first_payment),
        months: a.months,
        total_interest: m(a.total_interest),
        schedule: a
            .schedule
            .iter()
            .map(|r| ScheduleRowDto {
                month: r.month,
                interest: m(r.interest),
                principal: m(r.principal),
                extra: m(r.extra),
                balance: m(r.balance),
            })
            .collect(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct CalculatorDto {
    pub baseline: AmortizationDto,
    pub accelerated: AmortizationDto,
    pub months_saved: u32,
    pub interest_saved: MoneyDto,
}

/// Kalkulyator: `kind` — `ANNUITY` | `DIFFERENTIATED`; `annual_percent` — yillik foiz matni
/// (masalan, `24`). Natija faqat taxminiy.
#[tauri::command]
#[specta::specta]
pub fn loan_calculator(
    kind: String,
    principal: String,
    annual_percent: String,
    months: u32,
    extra: String,
    state: State<'_, AppSession>,
) -> Result<CalculatorDto, CommandError> {
    with_session(&state, |s| {
        s.run(|_, _, ctx| {
            let k = match kind.as_str() {
                "ANNUITY" => LoanKind::Annuity,
                "DIFFERENTIATED" => LoanKind::Differentiated,
                _ => return Err(ServiceError::Invalid("jadval turi noto'g'ri")),
            };
            let r = payoff::calculator(
                k,
                amount(ctx, &principal)?,
                percent_to_bp(&annual_percent)?,
                months,
                zero_or(ctx, &extra)?,
            )?;
            Ok(CalculatorDto {
                baseline: amort_dto(&r.baseline),
                accelerated: amort_dto(&r.accelerated),
                months_saved: r.months_saved,
                interest_saved: m(r.interest_saved),
            })
        })
    })
}

// ---------------------------------------------------------------- to'lovchilar

#[derive(Debug, Serialize, Type)]
pub struct ContributorDto {
    pub member_id: String,
    pub name: String,
    pub monthly_share: Option<MoneyDto>,
    pub paid: MoneyDto,
}

#[tauri::command]
#[specta::specta]
pub fn list_contributors(
    debt_id: String,
    state: State<'_, AppSession>,
) -> Result<Vec<ContributorDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            Ok(contributors::list(db.conn(), env, ctx, &debt_id)?
                .into_iter()
                .map(|c| ContributorDto {
                    member_id: c.member_id,
                    name: c.name,
                    monthly_share: c.monthly_share.map(m),
                    paid: m(c.paid),
                })
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_contributor_share(
    debt_id: String,
    member_id: String,
    share: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            contributors::set_share(db, env, ctx, &debt_id, &member_id, amount(ctx, &share)?)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_contributor(
    debt_id: String,
    member_id: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| contributors::remove(db, env, ctx, &debt_id, &member_id))
    })
}

// ---------------------------------------------------------------- sotiladigan buyumlar

#[derive(Debug, Serialize, Type)]
pub struct SellableDto {
    pub id: String,
    pub name: String,
    pub estimated_price: MoneyDto,
    pub unused_since: Option<String>,
    /// `LISTED` | `SOLD`.
    pub status: String,
    pub sold_amount: Option<MoneyDto>,
    pub sold: bool,
}

#[tauri::command]
#[specta::specta]
pub fn list_sellables(state: State<'_, AppSession>) -> Result<Vec<SellableDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(sellables::list(db.conn(), ctx)?
                .into_iter()
                .map(|i| SellableDto {
                    id: i.meta.id,
                    name: i.name,
                    estimated_price: m(i.estimated_price),
                    unused_since: i.unused_since.map(ds),
                    status: i.status.as_str().to_owned(),
                    sold_amount: i.sold_amount.map(m),
                    sold: i.status == SellStatus::Sold,
                })
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_sellable(
    name: String,
    price: String,
    unused_since: Option<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let since = unused_since
                .as_deref()
                .filter(|t| !t.trim().is_empty())
                .map(|t| {
                    date_from_str(t)
                        .map_err(|_| ServiceError::Invalid("sana YYYY-MM-DD ko'rinishida bo'lsin"))
                })
                .transpose()?;
            sellables::add(db, env, ctx, &name, amount(ctx, &price)?, since)?;
            Ok(())
        })
    })
}

/// Sotildi: tushum `debt_id` qarziga (qoldiqdan oshmagan qismi) qo'shimcha to'lov bo'ladi.
/// To'langan summani qaytaradi.
#[tauri::command]
#[specta::specta]
pub fn sell_item(
    id: String,
    sold_for: String,
    debt_id: Option<String>,
    state: State<'_, AppSession>,
) -> Result<MoneyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let paid = sellables::sell(
                db,
                env,
                ctx,
                &id,
                amount(ctx, &sold_for)?,
                debt_id.as_deref(),
            )?;
            Ok(m(paid))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_sellable(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| sellables::remove(db, env, ctx, &id))
    })
}
