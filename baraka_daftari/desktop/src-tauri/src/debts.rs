//! D9 commandlari (4-qonun): qarz inventari, berilgan qarzlar (foizsiz), maqsadlar, tilxat PDF.
//! Commandlar yupqa: matnni parse qiladi → `services` → tayyor formatlangan DTO.

use domain::{
    date_from_str, date_to_string, BorrowAlternative, BorrowNeed, CreditorType, ReceiptKind,
    ScheduleKind,
};
use money::{format_money, parse_amount, Locale, Money};
use serde::{Deserialize, Serialize};
use services::{
    debts::{self, DebtView, NewDebt, ScheduleInput},
    goals, receipts, receivables, Ctx, ServiceError,
};
use specta::Type;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

use crate::{
    commands::{with_session, AppSession, CommandError},
    dto::MoneyDto,
};

const LOCALE: Locale = Locale::Uz;

fn m(v: Money) -> MoneyDto {
    MoneyDto::from_money(v, LOCALE)
}

fn amount(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    Ok(parse_amount(text, ctx.currency)?)
}

fn ds(d: domain::Date) -> String {
    date_to_string(d).unwrap_or_default()
}

fn pd(text: &str) -> Result<domain::Date, ServiceError> {
    date_from_str(text).map_err(|_| ServiceError::Invalid("sana YYYY-MM-DD ko'rinishida bo'lsin"))
}

fn opt_date(text: Option<&str>) -> Result<Option<domain::Date>, ServiceError> {
    text.filter(|t| !t.trim().is_empty()).map(pd).transpose()
}

fn u32_of(n: usize) -> u32 {
    u32::try_from(n).unwrap_or(u32::MAX)
}

// ---------------------------------------------------------------- DTO'lar

#[derive(Debug, Serialize, Type)]
pub struct DebtCostDto {
    pub total: MoneyDto,
    pub excess: MoneyDto,
    /// Ortiqcha ulushi jamiga nisbatan, bazis punkt.
    pub excess_bp: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct InstalmentDto {
    pub due_on: String,
    pub amount: MoneyDto,
}

#[derive(Debug, Serialize, Type)]
pub struct BorrowCheckDto {
    /// `NEED` | `LUXURY`.
    pub need: String,
    /// `NONE` | `GUARD` | `RELATIVE` | `SELL_ITEM`.
    pub alternative: String,
    pub burden_bp: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct EquivalenceDto {
    pub goal_name: String,
    pub goal_target: MoneyDto,
    /// Necha marta (1/1000 aniqlikda, matn).
    pub times_milli: String,
}

#[derive(Debug, Serialize, Type)]
pub struct DebtDto {
    pub id: String,
    pub creditor: String,
    /// `BANK` | `SHOP` | `RELATIVE` | `FRIEND` | `OTHER`.
    pub creditor_type: String,
    pub reason: Option<String>,
    pub principal: MoneyDto,
    /// `ANNUITY` | `DIFFERENTIATED` | `FIXED_MARKUP` | `MANUAL`.
    pub schedule_kind: String,
    pub monthly: MoneyDto,
    pub due_date: String,
    pub borrowed_on: String,
    pub early_terms: Option<String>,
    pub closed_on: Option<String>,
    pub active: bool,
    pub paid: MoneyDto,
    pub total_scheduled: MoneyDto,
    pub remaining: MoneyDto,
    pub markup: MoneyDto,
    pub has_markup: bool,
    pub cost: DebtCostDto,
    pub next_due: Option<InstalmentDto>,
    pub overdue: bool,
    pub instalments: Vec<InstalmentDto>,
    pub check: Option<BorrowCheckDto>,
    /// Imkoniyat narxi: ortiqcha to'lov maqsadlarga necha marta teng.
    pub equivalences: Vec<EquivalenceDto>,
}

fn debt_dto(v: &DebtView, eq: Vec<services::goals::Equivalence>) -> DebtDto {
    let d = &v.debt;
    DebtDto {
        id: d.meta.id.clone(),
        creditor: d.creditor.clone(),
        creditor_type: d.creditor_type.as_str().to_owned(),
        reason: d.reason.clone(),
        principal: m(d.principal),
        schedule_kind: d.schedule_kind.as_str().to_owned(),
        monthly: m(d.monthly_payment),
        due_date: ds(d.due_date),
        borrowed_on: ds(d.borrowed_on),
        early_terms: d.early_repayment_terms.clone(),
        closed_on: d.closed_on.map(ds),
        active: v.active(),
        paid: m(v.paid),
        total_scheduled: m(v.total_scheduled),
        remaining: m(v.remaining),
        markup: m(v.markup),
        has_markup: v.has_markup(),
        cost: DebtCostDto {
            total: m(v.cost.total),
            excess: m(v.cost.excess),
            excess_bp: v.cost.excess_bp,
        },
        next_due: v.next_due.map(|(due, a)| InstalmentDto {
            due_on: ds(due),
            amount: m(a),
        }),
        overdue: v.overdue,
        instalments: v
            .instalments
            .iter()
            .map(|i| InstalmentDto {
                due_on: ds(i.due_on),
                amount: m(i.amount),
            })
            .collect(),
        check: d.check.map(|c| BorrowCheckDto {
            need: c.need.as_str().to_owned(),
            alternative: c.alternative.as_str().to_owned(),
            burden_bp: c.burden_bp,
        }),
        equivalences: eq
            .into_iter()
            .map(|e| EquivalenceDto {
                goal_name: e.goal_name,
                goal_target: m(e.goal_target),
                times_milli: e.times_milli.to_string(),
            })
            .collect(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct DebtOverviewDto {
    pub active_count: u32,
    pub total_remaining: MoneyDto,
    pub nasiya_remaining: MoneyDto,
    pub monthly_load: MoneyDto,
    /// Daromadga nisbatan oylik yuk (bp); daromad bo'lmasa `None`.
    pub burden_bp: Option<u32>,
    pub excess_total: MoneyDto,
    pub has_markup_debt: bool,
    pub any_overdue: bool,
    pub receivables_outstanding: MoneyDto,
}

#[derive(Debug, Deserialize, Type)]
pub struct FixedInput {
    pub markup: String,
    pub months: u32,
    pub first_due: String,
}

#[derive(Debug, Deserialize, Type)]
pub struct RowInput {
    pub due: String,
    pub amount: String,
}

#[derive(Debug, Deserialize, Type)]
pub struct CheckInput {
    /// `NEED` | `LUXURY`.
    pub need: String,
    /// `NONE` | `GUARD` | `RELATIVE` | `SELL_ITEM`.
    pub alternative: String,
}

#[derive(Debug, Deserialize, Type)]
pub struct DebtInput {
    pub creditor: String,
    pub creditor_type: String,
    pub reason: Option<String>,
    pub principal: String,
    pub schedule_kind: String,
    /// `FIXED_MARKUP` uchun.
    pub fixed: Option<FixedInput>,
    /// Boshqa turlar uchun jadval qatorlari.
    pub rows: Vec<RowInput>,
    pub borrowed_on: Option<String>,
    pub early_terms: Option<String>,
    pub check: Option<CheckInput>,
}

fn new_debt(ctx: &Ctx, i: &DebtInput) -> Result<NewDebt, ServiceError> {
    let creditor_type = CreditorType::parse(&i.creditor_type)
        .ok_or(ServiceError::Invalid("kreditor turini tanlang"))?;
    let schedule_kind = ScheduleKind::parse(&i.schedule_kind)
        .ok_or(ServiceError::Invalid("jadval turini tanlang"))?;
    let schedule = match &i.fixed {
        Some(f) => ScheduleInput::FixedMarkup {
            markup: amount(ctx, &f.markup)?,
            months: f.months,
            first_due: pd(&f.first_due)?,
        },
        None => ScheduleInput::Rows(
            i.rows
                .iter()
                .map(|r| Ok((pd(&r.due)?, amount(ctx, &r.amount)?)))
                .collect::<Result<Vec<_>, ServiceError>>()?,
        ),
    };
    let check = i
        .check
        .as_ref()
        .map(|c| {
            Ok::<_, ServiceError>((
                BorrowNeed::parse(&c.need).ok_or(ServiceError::Invalid("zarurat/hashamat"))?,
                BorrowAlternative::parse(&c.alternative)
                    .ok_or(ServiceError::Invalid("muqobilni tanlang"))?,
            ))
        })
        .transpose()?;
    Ok(NewDebt {
        creditor: i.creditor.clone(),
        creditor_type,
        reason: i.reason.clone(),
        principal: amount(ctx, &i.principal)?,
        schedule_kind,
        schedule,
        borrowed_on: opt_date(i.borrowed_on.as_deref())?,
        early_repayment_terms: i.early_terms.clone(),
        check,
    })
}

// ---------------------------------------------------------------- qarzlar

#[tauri::command]
#[specta::specta]
pub fn debt_overview(state: State<'_, AppSession>) -> Result<DebtOverviewDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let o = debts::overview(db.conn(), env, ctx)?;
            Ok(DebtOverviewDto {
                active_count: u32_of(o.active_count),
                total_remaining: m(o.total_remaining),
                nasiya_remaining: m(o.nasiya_remaining),
                monthly_load: m(o.monthly_load),
                burden_bp: o.burden_bp,
                excess_total: m(o.excess_total),
                has_markup_debt: o.has_markup_debt,
                any_overdue: o.any_overdue,
                receivables_outstanding: m(receivables::outstanding_total(db.conn(), env, ctx)?),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn list_debts(state: State<'_, AppSession>) -> Result<Vec<DebtDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            debts::list(db.conn(), env, ctx)?
                .iter()
                .map(|v| {
                    let eq = goals::equivalences(db.conn(), ctx, v.cost.excess)?;
                    Ok(debt_dto(v, eq))
                })
                .collect()
        })
    })
}

/// Friction ekrani uchun: yangi qarzdan keyingi oylik yuk (bp); daromad ma'lum bo'lmasa `None`.
#[tauri::command]
#[specta::specta]
pub fn debt_burden_preview(
    input: DebtInput,
    state: State<'_, AppSession>,
) -> Result<Option<u32>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| debts::burden_preview(db.conn(), env, ctx, &new_debt(ctx, &input)?))
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_debt(input: DebtInput, state: State<'_, AppSession>) -> Result<DebtDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let new = new_debt(ctx, &input)?;
            let v = debts::add(db, env, ctx, new)?;
            let eq = goals::equivalences(db.conn(), ctx, v.cost.excess)?;
            Ok(debt_dto(&v, eq))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn pay_debt(
    id: String,
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<DebtDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let v = debts::pay(db, env, ctx, &id, amount(ctx, &amount_text)?, None, None)?;
            let eq = goals::equivalences(db.conn(), ctx, v.cost.excess)?;
            Ok(debt_dto(&v, eq))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_debt_early_terms(
    id: String,
    terms: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| debts::set_early_terms(db, env, ctx, &id, &terms))
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_debt(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| debts::remove(db, env, ctx, &id))
    })
}

// ---------------------------------------------------------------- berilgan qarzlar

#[derive(Debug, Serialize, Type)]
pub struct ReceivableDto {
    pub id: String,
    pub debtor: String,
    pub amount: MoneyDto,
    pub returned: MoneyDto,
    pub outstanding: MoneyDto,
    pub given_on: String,
    pub due_on: Option<String>,
    pub note: Option<String>,
    /// Muddat keldi: xushmuomala eslatma.
    pub due: bool,
}

#[derive(Debug, Deserialize, Type)]
pub struct ReceivableInput {
    pub debtor: String,
    pub amount: String,
    pub given_on: Option<String>,
    pub due_on: Option<String>,
    pub note: Option<String>,
}

#[tauri::command]
#[specta::specta]
pub fn list_receivables(state: State<'_, AppSession>) -> Result<Vec<ReceivableDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            Ok(receivables::list(db.conn(), env, ctx)?
                .into_iter()
                .map(|v| ReceivableDto {
                    id: v.item.meta.id.clone(),
                    debtor: v.item.debtor.clone(),
                    amount: m(v.item.amount),
                    returned: m(v.item.returned),
                    outstanding: m(v.outstanding),
                    given_on: ds(v.item.given_on),
                    due_on: v.item.due_on.map(ds),
                    note: v.item.note.clone(),
                    due: v.due,
                })
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_receivable(
    input: ReceivableInput,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            receivables::add(
                db,
                env,
                ctx,
                receivables::NewReceivable {
                    debtor: &input.debtor,
                    amount: amount(ctx, &input.amount)?,
                    given_on: opt_date(input.given_on.as_deref())?,
                    due_on: opt_date(input.due_on.as_deref())?,
                    note: input.note.as_deref(),
                },
            )?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn return_receivable(
    id: String,
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            receivables::record_return(db, env, ctx, &id, amount(ctx, &amount_text)?)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_receivable(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| receivables::remove(db, env, ctx, &id))
    })
}

// ---------------------------------------------------------------- maqsadlar

#[derive(Debug, Serialize, Type)]
pub struct GoalDto {
    pub id: String,
    pub name: String,
    pub target: MoneyDto,
    pub saved: MoneyDto,
    pub due_on: Option<String>,
}

#[tauri::command]
#[specta::specta]
pub fn list_goals(state: State<'_, AppSession>) -> Result<Vec<GoalDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(goals::list(db.conn(), ctx)?
                .into_iter()
                .map(|g| GoalDto {
                    id: g.meta.id,
                    name: g.name,
                    target: m(g.target),
                    saved: m(g.saved),
                    due_on: g.due_on.map(ds),
                })
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_goal(
    name: String,
    target: String,
    due_on: Option<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            goals::add(
                db,
                env,
                ctx,
                &name,
                amount(ctx, &target)?,
                opt_date(due_on.as_deref())?,
            )?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn contribute_goal(
    id: String,
    amount_text: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            goals::contribute(db, env, ctx, &id, amount(ctx, &amount_text)?)?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_goal(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| goals::remove(db, env, ctx, &id))
    })
}

// ---------------------------------------------------------------- tilxat

#[derive(Debug, Serialize, Type)]
pub struct ReceiptDto {
    pub lender: String,
    pub borrower: String,
    pub amount: MoneyDto,
    pub given_on: String,
    pub due_on: Option<String>,
    pub has_markup: bool,
    pub witnesses: Vec<String>,
    pub confirmed_by_counterparty: bool,
}

fn kind_of(text: &str) -> Result<ReceiptKind, ServiceError> {
    ReceiptKind::parse(text).ok_or(ServiceError::Invalid("tilxat turi noto'g'ri"))
}

/// `kind`: `DEBT` | `RECEIVABLE`.
#[tauri::command]
#[specta::specta]
pub fn receipt_details(
    kind: String,
    id: String,
    state: State<'_, AppSession>,
) -> Result<ReceiptDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let d = receipts::data(db.conn(), env, ctx, kind_of(&kind)?, &id)?;
            Ok(ReceiptDto {
                lender: d.lender,
                borrower: d.borrower,
                amount: m(d.amount),
                given_on: ds(d.given_on),
                due_on: d.due_on.map(ds),
                has_markup: d.has_markup,
                witnesses: d.witnesses,
                confirmed_by_counterparty: d.confirmed_by_counterparty,
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn save_receipt_details(
    kind: String,
    id: String,
    witnesses: Vec<String>,
    confirmed: bool,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            receipts::save_details(db, env, ctx, kind_of(&kind)?, &id, &witnesses, confirmed)
        })
    })
}

/// Tilxat PDF'ini OS «saqlash» oynasi orqali yozadi. Imzolar: PNG baytlari (sichqoncha/pero) yoki
/// `None` — chop etib qo'lda imzolash. Foydalanuvchi bekor qilsa `None` qaytadi.
#[tauri::command]
#[specta::specta]
pub async fn export_receipt_pdf(
    kind: String,
    id: String,
    lender_signature: Option<Vec<u8>>,
    borrower_signature: Option<Vec<u8>>,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let sig = receipts::ReceiptSignatures {
        lender_png: lender_signature,
        borrower_png: borrower_signature,
    };
    let bytes = with_session(&state, |s| {
        s.run(|db, env, ctx| receipts::pdf(db.conn(), env, ctx, kind_of(&kind)?, &id, &sig))
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name("qarz-tilxati.pdf")
        .blocking_save_file()
    else {
        return Ok(None);
    };
    let mut path = file.into_path().map_err(|_| CommandError::Internal {
        message: "fayl yo'li noto'g'ri".into(),
    })?;
    if path
        .extension()
        .is_none_or(|e| !e.eq_ignore_ascii_case("pdf"))
    {
        path.set_extension("pdf");
    }
    std::fs::write(&path, bytes).map_err(|_| CommandError::Internal {
        message: "faylni yozib bo'lmadi".into(),
    })?;
    Ok(path.file_name().map(|n| n.to_string_lossy().into_owned()))
}

// Ishlatilmaydigan import ogohlantirishini oldini olish uchun (formatlash `MoneyDto` ichida).
const _: fn() = || {
    let _ = format_money;
};
