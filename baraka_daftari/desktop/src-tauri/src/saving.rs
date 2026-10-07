//! D7 commandlari: obunalar, konvertlar, qutqarilgan pul, CSV import. Fayl tanlash va o'qish faqat Rust
//! tomonida (OS dialogi orqali); frontend faylga tegmaydi, faqat ko'rik va natijani oladi.

use std::{collections::HashMap, sync::Mutex};

use domain::{date_from_str, date_to_string, BillingPeriod, Necessity, SavingsRescue};
use money::{format_money, parse_amount, Locale, Money};
use serde::{Deserialize, Serialize};
use services::{
    csv_import::{self, DateFormat, Mapping, SignRule, Table},
    envelopes, local_date, rescue, subscriptions, Ctx, ServiceError,
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

fn u32_of(n: usize) -> u32 {
    u32::try_from(n).unwrap_or(u32::MAX)
}

fn bp32(v: i64) -> u32 {
    u32::try_from(v.max(0)).unwrap_or(u32::MAX)
}

// ---------------------------------------------------------------- obunalar

#[derive(Debug, Serialize, Type)]
pub struct SubscriptionDto {
    pub id: String,
    pub name: String,
    pub amount: MoneyDto,
    /// `WEEKLY` | `MONTHLY` | `QUARTERLY` | `YEARLY`.
    pub period: String,
    pub monthly: MoneyDto,
    pub yearly: MoneyDto,
    pub started_on: String,
    pub last_used_on: Option<String>,
    pub cancelled_on: Option<String>,
    /// «Kerakmi?» javobi; `None` — javob berilmagan.
    pub needed: Option<bool>,
    pub active: bool,
    pub forgotten: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct SubscriptionsDto {
    pub items: Vec<SubscriptionDto>,
    pub monthly_total: MoneyDto,
    pub yearly_total: MoneyDto,
}

#[tauri::command]
#[specta::specta]
pub fn list_subscriptions(state: State<'_, AppSession>) -> Result<SubscriptionsDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let today = local_date(env.clock.now());
            let totals = subscriptions::totals(db.conn(), ctx, today)?;
            let items = subscriptions::list(db.conn(), ctx, today)?
                .into_iter()
                .map(|v| SubscriptionDto {
                    id: v.sub.meta.id,
                    name: v.sub.name,
                    amount: m(v.sub.amount),
                    period: v.sub.period.as_str().to_owned(),
                    monthly: m(v.cost.monthly),
                    yearly: m(v.cost.yearly),
                    started_on: ds(v.sub.started_on),
                    last_used_on: v.sub.last_used_on.map(ds),
                    cancelled_on: v.sub.cancelled_on.map(ds),
                    needed: v.sub.needed,
                    active: v.active,
                    forgotten: v.forgotten,
                })
                .collect();
            Ok(SubscriptionsDto {
                items,
                monthly_total: m(totals.monthly),
                yearly_total: m(totals.yearly),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_subscription(
    name: String,
    amount_text: String,
    period: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let period = BillingPeriod::parse(&period)
                .ok_or(ServiceError::Invalid("davriylikni tanlang"))?;
            subscriptions::add(
                db,
                env,
                ctx,
                &name,
                amount(ctx, &amount_text)?,
                period,
                None,
            )?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn mark_subscription_used(
    id: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| subscriptions::mark_used(db, env, ctx, &id))
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_subscription_needed(
    id: String,
    needed: Option<bool>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| subscriptions::set_needed(db, env, ctx, &id, needed))
    })
}

/// Bekor qiladi; qutqarilgan summa (bir oylik narx) qaytadi (bepul obunada `None`).
#[tauri::command]
#[specta::specta]
pub fn cancel_subscription(
    id: String,
    state: State<'_, AppSession>,
) -> Result<Option<MoneyDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| Ok(subscriptions::cancel(db, env, ctx, &id)?.map(|r| m(r.amount))))
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_subscription(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| subscriptions::remove(db, env, ctx, &id))
    })
}

// ---------------------------------------------------------------- konvertlar

#[derive(Debug, Serialize, Type)]
pub struct EnvelopeDto {
    pub id: String,
    pub name: String,
    pub limit: MoneyDto,
    pub spent: MoneyDto,
    /// Qoldiq (manfiy bo'lishi mumkin).
    pub remaining: MoneyDto,
    /// Jismoniy konvertga hozir solinadigan naqd.
    pub cash_to_fill: MoneyDto,
    /// `OK` | `NEAR` | `OVER`.
    pub state: String,
    pub used_bp: u32,
    pub week_start: String,
    /// Shu hafta yopilgan bo'lsa: kiritilgan naqd qoldiq va farq.
    pub closed_leftover: Option<MoneyDto>,
    pub closed_difference: Option<MoneyDto>,
}

#[tauri::command]
#[specta::specta]
pub fn list_envelopes(state: State<'_, AppSession>) -> Result<Vec<EnvelopeDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let today = local_date(env.clock.now());
            Ok(envelopes::status(db.conn(), ctx, today)?
                .into_iter()
                .map(|v| EnvelopeDto {
                    id: v.envelope.meta.id,
                    name: v.envelope.name,
                    limit: m(v.envelope.weekly_limit),
                    spent: m(v.spent),
                    remaining: m(v.status.remaining),
                    cash_to_fill: m(v.cash_to_fill),
                    state: match v.status.state {
                        domain::HavasState::Ok => "OK",
                        domain::HavasState::Near => "NEAR",
                        domain::HavasState::Over => "OVER",
                    }
                    .to_owned(),
                    used_bp: bp32(v.status.used_bp),
                    week_start: ds(v.week_start),
                    closed_leftover: v.closed.as_ref().map(|p| m(p.leftover_cash)),
                    closed_difference: v.closed.as_ref().map(|p| m(p.difference)),
                })
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_envelope(
    name: String,
    limit_text: String,
    category_id: Option<String>,
    necessity: Option<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let nec = necessity
                .as_deref()
                .map(|t| Necessity::parse(t).ok_or(ServiceError::Invalid("toifani tanlang")))
                .transpose()?;
            envelopes::add(
                db,
                env,
                ctx,
                &name,
                amount(ctx, &limit_text)?,
                category_id,
                nec,
            )?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_envelope_active(
    id: String,
    active: bool,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| envelopes::set_active(db, env, ctx, &id, active))
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_envelope(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| envelopes::remove(db, env, ctx, &id))
    })
}

/// Haftani yopadi: hafta oxiridagi naqd qoldiq kiritiladi; farq (kam/ortiq naqd) qaytadi.
#[tauri::command]
#[specta::specta]
pub fn close_envelope_week(
    id: String,
    leftover_text: String,
    state: State<'_, AppSession>,
) -> Result<MoneyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let today = local_date(env.clock.now());
            let p = envelopes::close_week(db, env, ctx, &id, today, amount(ctx, &leftover_text)?)?;
            Ok(m(p.difference))
        })
    })
}

// ---------------------------------------------------------------- qutqarilgan pul

#[derive(Debug, Serialize, Type)]
pub struct RescueItemDto {
    pub id: String,
    /// `HAVAS_DROP` | `SUBSCRIPTION`.
    pub kind: String,
    pub amount: MoneyDto,
    pub note: Option<String>,
    pub transferred: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct RescueDto {
    /// Tugagan oxirgi hafta (jumasi).
    pub week: String,
    pub baseline: MoneyDto,
    pub current: MoneyDto,
    pub rescued: MoneyDto,
    pub claimed: bool,
    /// Hali «Kelajagim»ga o'tkazilmagan jami.
    pub available: MoneyDto,
    pub items: Vec<RescueItemDto>,
}

fn item(r: &SavingsRescue) -> RescueItemDto {
    RescueItemDto {
        id: r.meta.id.clone(),
        kind: r.kind.as_str().to_owned(),
        amount: m(r.amount),
        note: r.note.clone(),
        transferred: r.transferred_at.is_some(),
    }
}

/// Haftalik hisobot; kerak bo'lsa tugagan haftaning qutqarilgan pulini yozadi.
#[tauri::command]
#[specta::specta]
pub fn rescue_report(state: State<'_, AppSession>) -> Result<RescueDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            rescue::claim_week(db, env, ctx)?;
            let today = local_date(env.clock.now());
            let r = rescue::weekly_report(db.conn(), ctx, today)?;
            Ok(RescueDto {
                week: ds(r.week),
                baseline: m(r.baseline),
                current: m(r.current),
                rescued: m(r.rescued),
                claimed: r.claimed.is_some(),
                available: m(rescue::available(db.conn(), ctx)?),
                items: rescue::list(db.conn(), ctx)?
                    .iter()
                    .rev()
                    .map(item)
                    .collect(),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn transfer_rescue(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| rescue::transfer(db, env, ctx, &id))
    })
}

/// Bir bosishda hammasini «Kelajagim»ga o'tkazadi; o'tkazilgan jami.
#[tauri::command]
#[specta::specta]
pub fn transfer_all_rescue(state: State<'_, AppSession>) -> Result<MoneyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| Ok(m(rescue::transfer_all(db, env, ctx)?)))
    })
}

// ---------------------------------------------------------------- CSV import

/// Yuklangan fayl jadvali Rust xotirasida turadi (faylning o'zi frontendga berilmaydi).
#[derive(Default)]
pub struct ImportStore(Mutex<HashMap<String, Table>>);

#[derive(Debug, Serialize, Type)]
pub struct CsvPreviewDto {
    pub token: String,
    pub headers: Vec<String>,
    pub rows: Vec<Vec<String>>,
    pub total_rows: u32,
    pub delimiter: String,
}

#[derive(Debug, Deserialize, Type)]
pub struct CsvMappingInput {
    pub date_col: u32,
    pub amount_col: u32,
    pub note_col: Option<u32>,
    /// `ISO` | `DMY_DOTS` | `DMY_SLASHES` | `YMD_SLASHES`.
    pub date_format: String,
    /// `NEGATIVE_ARE_EXPENSES` | `POSITIVE_ARE_EXPENSES` | `ABSOLUTE_ALL`.
    pub sign: String,
}

#[derive(Debug, Serialize, Type)]
pub struct CsvRowError {
    pub line: u32,
    pub reason: String,
}

#[derive(Debug, Serialize, Type)]
pub struct CsvResultDto {
    pub imported: u32,
    pub duplicates: u32,
    pub skipped_sign: u32,
    /// Birinchi 50 ta xato qator.
    pub errors: Vec<CsvRowError>,
    pub error_count: u32,
}

fn mapping(input: &CsvMappingInput) -> Result<Mapping, ServiceError> {
    Ok(Mapping {
        date_col: input.date_col as usize,
        amount_col: input.amount_col as usize,
        note_col: input.note_col.map(|c| c as usize),
        date_format: DateFormat::parse(&input.date_format)
            .ok_or(ServiceError::Invalid("sana formatini tanlang"))?,
        sign: SignRule::parse(&input.sign)
            .ok_or(ServiceError::Invalid("ishora qoidasini tanlang"))?,
    })
}

fn errors_dto(errors: &[services::csv_import::RowError]) -> Vec<CsvRowError> {
    errors
        .iter()
        .take(50)
        .map(|e| CsvRowError {
            line: u32_of(e.line),
            reason: e.reason.to_owned(),
        })
        .collect()
}

/// OS dialogida CSV tanlanadi; Rust o'qiydi va ko'rik qaytaradi. Bekor qilinsa `None`.
#[tauri::command]
#[specta::specta]
pub async fn csv_open(
    app: AppHandle,
    state: State<'_, AppSession>,
    store: State<'_, ImportStore>,
) -> Result<Option<CsvPreviewDto>, CommandError> {
    // Qulf holatida import mumkin emas.
    with_session(&state, |s| s.run(|_, _, _| Ok(())))?;
    let Some(file) = app
        .dialog()
        .file()
        .add_filter("CSV", &["csv", "txt"])
        .blocking_pick_file()
    else {
        return Ok(None);
    };
    let path = file.into_path().map_err(|_| CommandError::Internal {
        message: "fayl yo'li noto'g'ri".into(),
    })?;
    let too_big = std::fs::metadata(&path)
        .map_err(|_| CommandError::Internal {
            message: "faylni o'qib bo'lmadi".into(),
        })?
        .len()
        > csv_import::MAX_BYTES as u64;
    if too_big {
        return Err(ServiceError::Invalid("fayl juda katta (5 MB gacha)").into());
    }
    let bytes = std::fs::read(&path).map_err(|_| CommandError::Internal {
        message: "faylni o'qib bo'lmadi".into(),
    })?;
    let table = csv_import::parse_table(&bytes).map_err(CommandError::from)?;
    let token = domain::IdGen::new_id(&domain::UuidV7Gen);
    let preview = CsvPreviewDto {
        token: token.clone(),
        headers: table.headers.clone(),
        rows: csv_import::preview(&table),
        total_rows: u32_of(table.rows.len()),
        delimiter: table.delimiter.to_string(),
    };
    let mut guard = store
        .0
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    guard.clear(); // bir vaqtda bitta import
    guard.insert(token, table);
    Ok(Some(preview))
}

fn table_of(store: &ImportStore, token: &str) -> Result<Table, ServiceError> {
    store
        .0
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
        .get(token)
        .cloned()
        .ok_or(ServiceError::Invalid("fayl topilmadi: qaytadan tanlang"))
}

/// Xaritalashni sinash: nima import qilinishini ko'rsatadi, hech narsa yozmaydi.
#[tauri::command]
#[specta::specta]
pub fn csv_dry_run(
    token: String,
    input: CsvMappingInput,
    state: State<'_, AppSession>,
    store: State<'_, ImportStore>,
) -> Result<CsvResultDto, CommandError> {
    with_session(&state, |s| {
        s.run(|_, env, ctx| {
            let parsed = csv_import::parse_rows(
                &table_of(&store, &token)?,
                &mapping(&input)?,
                ctx.currency,
                local_date(env.clock.now()),
            );
            Ok(CsvResultDto {
                imported: u32_of(parsed.rows.len()),
                duplicates: 0,
                skipped_sign: u32_of(parsed.skipped_sign),
                errors: errors_dto(&parsed.errors),
                error_count: u32_of(parsed.errors.len()),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn csv_import(
    token: String,
    input: CsvMappingInput,
    default_category_id: String,
    state: State<'_, AppSession>,
    store: State<'_, ImportStore>,
) -> Result<CsvResultDto, CommandError> {
    let result = with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let parsed = csv_import::parse_rows(
                &table_of(&store, &token)?,
                &mapping(&input)?,
                ctx.currency,
                local_date(env.clock.now()),
            );
            let out = csv_import::import(db, env, ctx, parsed, &default_category_id)?;
            Ok(CsvResultDto {
                imported: u32_of(out.imported),
                duplicates: u32_of(out.duplicates),
                skipped_sign: u32_of(out.skipped_sign),
                errors: errors_dto(&out.errors),
                error_count: u32_of(out.errors.len()),
            })
        })
    })?;
    store
        .0
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
        .remove(&token);
    Ok(result)
}

// Ishlatilmaydigan importlar uchun yagona joy.
const _: fn() = || {
    let _ = (date_from_str, format_money);
};
