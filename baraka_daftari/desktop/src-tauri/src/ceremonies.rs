//! D11 commandlari: marosim rejalovchisi (byudjet qatorlari, muhokama, solishtirish, smeta PDF).

use domain::{date_from_str, date_to_string, CeremonyKind, CeremonyStatus, FundingSource};
use money::{parse_amount, Locale, Money};
use serde::Serialize;
use services::{
    ceremonies::{self, NewLine, PlanView, ScenarioView},
    Ctx, ServiceError,
};
use specta::Type;
use tauri::{AppHandle, State};
use tauri_plugin_dialog::DialogExt;

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

fn ds(d: domain::Date) -> String {
    date_to_string(d).unwrap_or_default()
}

fn opt_date(text: Option<&str>) -> Result<Option<domain::Date>, ServiceError> {
    text.filter(|t| !t.trim().is_empty())
        .map(|t| {
            date_from_str(t)
                .map_err(|_| ServiceError::Invalid("sana YYYY-MM-DD ko'rinishida bo'lsin"))
        })
        .transpose()
}

fn funding(text: &str) -> Result<FundingSource, ServiceError> {
    FundingSource::parse(text).ok_or(ServiceError::Invalid("moliyalash manbasini tanlang"))
}

#[derive(Debug, Serialize, Type)]
pub struct CeremonyLineDto {
    pub id: String,
    pub name: String,
    pub qty: u32,
    pub unit_price: MoneyDto,
    pub total: MoneyDto,
    /// `SAVINGS` | `FAMILY` | `EXPECTED_GIFTS` | `DEBT`.
    pub funding: String,
}

#[derive(Debug, Serialize, Type)]
pub struct CeremonyTotalsDto {
    pub total: MoneyDto,
    pub savings: MoneyDto,
    pub family: MoneyDto,
    pub expected_gifts: MoneyDto,
    pub debt: MoneyDto,
    pub debt_bp: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct CeremonyDto {
    pub id: String,
    pub name: String,
    /// `WEDDING` | `BESHIK` | `SUNNAT` | `MARAKA` | `OTHER`.
    pub kind: String,
    pub date: Option<String>,
    /// `DRAFT` | `CONFIRMED`.
    pub status: String,
    pub discussed: bool,
    pub discussion_note: Option<String>,
    pub lines: Vec<CeremonyLineDto>,
    pub totals: CeremonyTotalsDto,
    /// Hozir tasdiqlab bo'lmasa sababi: `DISCUSSION_REQUIRED` | `DATE_REQUIRED`.
    pub confirm_blocker: Option<String>,
}

fn dto(v: &PlanView) -> CeremonyDto {
    let t = &v.totals;
    CeremonyDto {
        id: v.plan.meta.id.clone(),
        name: v.plan.name.clone(),
        kind: v.plan.kind.as_str().to_owned(),
        date: v.plan.date.map(ds),
        status: v.plan.status.as_str().to_owned(),
        discussed: v.plan.discussed,
        discussion_note: v.plan.discussion_note.clone(),
        lines: v
            .lines
            .iter()
            .map(|l| CeremonyLineDto {
                id: l.line.meta.id.clone(),
                name: l.line.name.clone(),
                qty: l.line.qty,
                unit_price: m(l.line.unit_price),
                total: m(l.total),
                funding: l.line.funding.as_str().to_owned(),
            })
            .collect(),
        totals: CeremonyTotalsDto {
            total: m(t.total),
            savings: m(t.savings),
            family: m(t.family),
            expected_gifts: m(t.expected_gifts),
            debt: m(t.debt),
            debt_bp: t.debt_bp,
        },
        confirm_blocker: v.confirm_blocker.map(str::to_owned),
    }
}

#[tauri::command]
#[specta::specta]
pub fn list_ceremonies(state: State<'_, AppSession>) -> Result<Vec<CeremonyDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| Ok(ceremonies::list(db.conn(), ctx)?.iter().map(dto).collect()))
    })
}

#[tauri::command]
#[specta::specta]
pub fn create_ceremony(
    name: String,
    kind: String,
    date: Option<String>,
    state: State<'_, AppSession>,
) -> Result<CeremonyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let k = CeremonyKind::parse(&kind)
                .ok_or(ServiceError::Invalid("marosim turini tanlang"))?;
            let v = ceremonies::create(db, env, ctx, &name, k, opt_date(date.as_deref())?)?;
            Ok(dto(&v))
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_ceremony_date(
    id: String,
    date: Option<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| ceremonies::set_date(db, env, ctx, &id, opt_date(date.as_deref())?))
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_ceremony_line(
    plan_id: String,
    name: String,
    qty: u32,
    unit_price: String,
    funding_source: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            ceremonies::add_line(
                db,
                env,
                ctx,
                NewLine {
                    plan_id: &plan_id,
                    name: &name,
                    qty,
                    unit_price: amount(ctx, &unit_price)?,
                    funding: funding(&funding_source)?,
                },
            )
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn update_ceremony_line(
    line_id: String,
    qty: u32,
    unit_price: String,
    funding_source: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            ceremonies::update_line(
                db,
                env,
                ctx,
                &line_id,
                qty,
                amount(ctx, &unit_price)?,
                funding(&funding_source)?,
            )
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_ceremony_line(
    line_id: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| ceremonies::remove_line(db, env, ctx, &line_id))
    })
}

#[tauri::command]
#[specta::specta]
pub fn record_ceremony_discussion(
    id: String,
    note: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| ceremonies::record_discussion(db, env, ctx, &id, &note))
    })
}

/// `status`: `DRAFT` | `CONFIRMED`.
#[tauri::command]
#[specta::specta]
pub fn set_ceremony_status(
    id: String,
    status: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let st =
                CeremonyStatus::parse(&status).ok_or(ServiceError::Invalid("holat noto'g'ri"))?;
            ceremonies::set_status(db, env, ctx, &id, st)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_ceremony(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| ceremonies::remove(db, env, ctx, &id))
    })
}

#[derive(Debug, Serialize, Type)]
pub struct AlternativeDto {
    pub goal_name: String,
    pub goal_target: MoneyDto,
    /// Necha marta (1/1000 aniqlikda, matn).
    pub times_milli: String,
}

#[derive(Debug, Serialize, Type)]
pub struct ScenarioDto {
    pub plan: CeremonyDto,
    pub cheaper_than_max: MoneyDto,
    /// Qarzni qaytarish muddati (oy); imkoniyat berilmagan yoki sig'masa `None`.
    pub repay_months: Option<u32>,
    pub repay_too_long: bool,
    pub alternatives: Vec<AlternativeDto>,
}

fn scenario_dto(s: &ScenarioView) -> ScenarioDto {
    ScenarioDto {
        plan: dto(&s.view),
        cheaper_than_max: m(s.cheaper_than_max),
        repay_months: s.repay_months,
        repay_too_long: s.repay_too_long,
        alternatives: s
            .alternatives
            .iter()
            .map(|a| AlternativeDto {
                goal_name: a.goal_name.clone(),
                goal_target: m(a.goal_target),
                times_milli: a.times_milli.to_string(),
            })
            .collect(),
    }
}

/// 2–3 stsenariyni solishtiradi. `capacity` — oylik to'lov imkoniyati (bo'sh — hisoblanmaydi);
/// `annual_percent` — qarz foizi (bo'sh — 0, qarzi hasana).
#[tauri::command]
#[specta::specta]
pub fn compare_ceremonies(
    ids: Vec<String>,
    capacity: String,
    annual_percent: String,
    state: State<'_, AppSession>,
) -> Result<Vec<ScenarioDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            let cap = if capacity.trim().is_empty() {
                None
            } else {
                Some(amount(ctx, &capacity)?)
            };
            let bp = if annual_percent.trim().is_empty() {
                0
            } else {
                percent_to_bp(&annual_percent)?
            };
            Ok(ceremonies::compare(db.conn(), ctx, &ids, cap, bp)?
                .iter()
                .map(scenario_dto)
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn open_gift_goal(
    plan_id: String,
    target: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            ceremonies::open_gift_goal(db, env, ctx, &plan_id, amount(ctx, &target)?)
        })
    })
}

/// Smetani OS «saqlash» oynasi orqali PDF qilib yozadi; bekor qilinsa `None`.
#[tauri::command]
#[specta::specta]
pub async fn export_ceremony_pdf(
    plan_id: String,
    app: AppHandle,
    state: State<'_, AppSession>,
) -> Result<Option<String>, CommandError> {
    let bytes = with_session(&state, |s| {
        s.run(|db, _, ctx| ceremonies::budget_pdf(db.conn(), ctx, &plan_id))
    })?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("PDF", &["pdf"])
        .set_file_name("marosim-smetasi.pdf")
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
