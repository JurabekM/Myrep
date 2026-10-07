//! D8 commandlari (3-qonun): qorovul pul, tayyorgarlik darvozasi, narx daftari, «sichqon kemirgani».

use domain::{date_from_str, date_to_string};
use money::{parse_amount, Locale, Money};
use serde::Serialize;
use services::{guard, prices, Ctx, ServiceError};
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

fn amount(ctx: &Ctx, text: &str) -> Result<Money, ServiceError> {
    Ok(parse_amount(text, ctx.currency)?)
}

fn ds(d: domain::Date) -> String {
    date_to_string(d).unwrap_or_default()
}

fn bp_i32(v: i64) -> i32 {
    i32::try_from(v).unwrap_or(if v < 0 { i32::MIN } else { i32::MAX })
}

fn u32_of(n: usize) -> u32 {
    u32::try_from(n).unwrap_or(u32::MAX)
}

// ---------------------------------------------------------------- qorovul va darvoza

#[derive(Debug, Serialize, Type)]
pub struct GuardDto {
    pub monthly_need: MoneyDto,
    pub target: MoneyDto,
    pub milestone: MoneyDto,
    pub balance: MoneyDto,
    pub growing_balance: MoneyDto,
    pub gap: MoneyDto,
    /// Necha oylik zaxira ×100 (140 = 1,4 oy).
    pub months_x100: u32,
    pub milestone_reached: bool,
    pub full_reached: bool,
    pub basis_months: u32,
}

#[tauri::command]
#[specta::specta]
pub fn guard_overview(state: State<'_, AppSession>) -> Result<GuardDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let o = guard::overview(db.conn(), env, ctx)?;
            Ok(GuardDto {
                monthly_need: m(o.monthly_need),
                target: m(o.target),
                milestone: m(o.milestone),
                balance: m(o.balance),
                growing_balance: m(o.growing_balance),
                gap: m(o.gap),
                months_x100: o.months_x100,
                milestone_reached: o.milestone_reached,
                full_reached: o.full_reached,
                basis_months: u32_of(o.basis_months),
            })
        })
    })
}

#[derive(Debug, Serialize, Type)]
pub struct GateDto {
    pub rules_open: bool,
    pub bypassed: bool,
    pub open: bool,
    /// `GUARD_BELOW_TARGET` | `INTEREST_DEBT_NO_PLAN`.
    pub reasons: Vec<String>,
    pub months_x100: u32,
    pub required_x100: u32,
    pub has_interest_debt: bool,
    pub has_debt_plan: bool,
}

#[tauri::command]
#[specta::specta]
pub fn gate_status(state: State<'_, AppSession>) -> Result<GateDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let g = guard::gate(db.conn(), env, ctx)?;
            Ok(GateDto {
                rules_open: g.rules_open,
                bypassed: g.bypassed,
                open: g.open,
                reasons: g.reasons.iter().map(|r| r.code().to_owned()).collect(),
                months_x100: g.months_x100,
                required_x100: g.required_x100,
                has_interest_debt: g.has_interest_debt,
                has_debt_plan: g.has_debt_plan,
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_debt_declaration(
    has_interest_debt: bool,
    has_debt_plan: bool,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            guard::set_debt_declaration(db, env, ctx, has_interest_debt, has_debt_plan)
        })
    })
}

/// Qulfni ongli chetlab o'tish: tasdiq UI'da so'raladi, `confirmed` Rustda tekshiriladi.
#[tauri::command]
#[specta::specta]
pub fn bypass_gate(confirmed: bool, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| guard::bypass(db, env, ctx, confirmed))
    })
}

#[tauri::command]
#[specta::specta]
pub fn revoke_gate_bypass(state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| s.run(guard::revoke_bypass))
}

// ---------------------------------------------------------------- narx daftari

#[derive(Debug, Serialize, Type)]
pub struct PricePointDto {
    pub id: String,
    pub price: MoneyDto,
    pub observed_on: String,
    pub place: Option<String>,
}

fn point_dto(p: &domain::PricePoint) -> PricePointDto {
    PricePointDto {
        id: p.meta.id.clone(),
        price: m(p.price),
        observed_on: ds(p.observed_on),
        place: p.place.clone(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct PriceItemDto {
    pub id: String,
    pub name: String,
    pub unit: String,
    pub weight_bp: u32,
    pub active: bool,
    pub first: Option<PricePointDto>,
    pub last: Option<PricePointDto>,
    pub points: u32,
    /// Birinchi → oxirgi narx o'zgarishi, bazis punkt (6250 = +62,5%).
    pub change_bp: Option<i32>,
}

#[tauri::command]
#[specta::specta]
pub fn list_price_items(state: State<'_, AppSession>) -> Result<Vec<PriceItemDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(prices::items(db.conn(), ctx)?
                .into_iter()
                .map(|v| PriceItemDto {
                    id: v.item.meta.id.clone(),
                    name: v.item.name.clone(),
                    unit: v.item.unit.clone(),
                    weight_bp: v.item.weight_bp,
                    active: v.item.active,
                    first: v.first.as_ref().map(point_dto),
                    last: v.last.as_ref().map(point_dto),
                    points: u32_of(v.points),
                    change_bp: v.change_bp.map(bp_i32),
                })
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn add_price_item(
    name: String,
    unit: String,
    weight_bp: u32,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            prices::add_item(db, env, ctx, &name, &unit, weight_bp)?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_price_item(
    id: String,
    weight_bp: u32,
    active: bool,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| prices::set_item(db, env, ctx, &id, weight_bp, active))
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_price_item(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| prices::remove_item(db, env, ctx, &id))
    })
}

/// `date` — `YYYY-MM-DD`; `None` — bugun.
#[tauri::command]
#[specta::specta]
pub fn add_price(
    item_id: String,
    price: String,
    date: Option<String>,
    place: Option<String>,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let observed = date
                .as_deref()
                .map(|d| {
                    date_from_str(d).map_err(|_| ServiceError::Invalid("sana YYYY-MM-DD bo'lsin"))
                })
                .transpose()?;
            prices::add_price(
                db,
                env,
                ctx,
                &item_id,
                amount(ctx, &price)?,
                observed,
                place.as_deref(),
            )?;
            Ok(())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn price_history(
    item_id: String,
    state: State<'_, AppSession>,
) -> Result<Vec<PricePointDto>, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            Ok(prices::history(db.conn(), ctx, &item_id)?
                .iter()
                .map(point_dto)
                .collect())
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn remove_price(id: String, state: State<'_, AppSession>) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| prices::remove_price(db, env, ctx, &id))
    })
}

#[derive(Debug, Serialize, Type)]
pub struct InflationItemDto {
    pub name: String,
    pub change_bp: i32,
    pub weight_bp: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct InflationDto {
    pub index_bp: i32,
    pub items: Vec<InflationItemDto>,
    pub span_days: i32,
}

#[derive(Debug, Serialize, Type)]
pub struct PriceBookDto {
    /// `None` — ma'lumot yetarli emas (kamida 2 ta narxli mahsulot kerak).
    pub inflation: Option<InflationDto>,
    pub streak_weeks: u32,
    pub best_streak_weeks: u32,
    /// Shu haftada narx kiritilganmi (haftalik eslatma).
    pub logged_this_week: bool,
}

#[tauri::command]
#[specta::specta]
pub fn price_book(state: State<'_, AppSession>) -> Result<PriceBookDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let st = prices::streak(db.conn(), env, ctx)?;
            Ok(PriceBookDto {
                inflation: prices::inflation(db.conn(), ctx)?.map(|i| InflationDto {
                    index_bp: bp_i32(i.index_bp),
                    items: i
                        .per_item
                        .into_iter()
                        .map(|(name, change_bp, weight_bp)| InflationItemDto {
                            name,
                            change_bp: bp_i32(change_bp),
                            weight_bp,
                        })
                        .collect(),
                    span_days: i32::try_from(i.span_days).unwrap_or(i32::MAX),
                }),
                streak_weeks: st.current_weeks,
                best_streak_weeks: st.best_weeks,
                logged_this_week: prices::logged_this_week(db.conn(), env, ctx)?,
            })
        })
    })
}

// ---------------------------------------------------------------- sichqon kemirgani

#[derive(Debug, Serialize, Type)]
pub struct ItemExampleDto {
    pub name: String,
    pub unit: String,
    pub price_today: MoneyDto,
    pub price_future: MoneyDto,
    /// Birlikning 1/1000 ulushlarida (kg uchun gramm).
    pub quantity_now_milli: String,
    pub quantity_future_milli: String,
}

#[derive(Debug, Serialize, Type)]
pub struct PurchasingDto {
    pub nominal: MoneyDto,
    pub real: MoneyDto,
    pub years: u32,
    pub annual_bp: u32,
    pub example: Option<ItemExampleDto>,
}

/// `annual_percent` — foydalanuvchi kiritgan taxminiy yillik narx o'sishi (masalan, `12,5`).
#[tauri::command]
#[specta::specta]
pub fn purchasing_power(
    annual_percent: String,
    years: u32,
    item_id: Option<String>,
    state: State<'_, AppSession>,
) -> Result<PurchasingDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, _, ctx| {
            let bp = percent_to_bp(&annual_percent)?;
            let p = prices::purchasing(db.conn(), ctx, bp, years, item_id.as_deref())?;
            Ok(PurchasingDto {
                nominal: m(p.nominal),
                real: m(p.real),
                years: p.years,
                annual_bp: p.annual_bp,
                example: p.example.map(|e| ItemExampleDto {
                    name: e.name,
                    unit: e.unit,
                    price_today: m(e.price_today),
                    price_future: m(e.price_future),
                    quantity_now_milli: e.quantity_now_milli.to_string(),
                    quantity_future_milli: e.quantity_future_milli.to_string(),
                }),
            })
        })
    })
}

/// «12,5» → 1250 bp. Faqat butun va bir-ikki xonali kasr; manfiy yoki 1000% dan katta emas.
fn percent_to_bp(text: &str) -> Result<u32, ServiceError> {
    let t = text.trim().replace(',', ".");
    let bad = ServiceError::Invalid("foiz noto'g'ri (masalan, 12,5)");
    let (int, frac) = t.split_once('.').unwrap_or((&t, ""));
    if int.is_empty() || frac.len() > 2 || !int.bytes().all(|b| b.is_ascii_digit()) {
        return Err(bad);
    }
    if !frac.bytes().all(|b| b.is_ascii_digit()) {
        return Err(bad);
    }
    let int: u32 = int
        .parse()
        .map_err(|_| ServiceError::Invalid("foiz noto'g'ri"))?;
    let frac_bp = match frac.len() {
        0 => 0,
        1 => {
            frac.parse::<u32>()
                .map_err(|_| ServiceError::Invalid("foiz noto'g'ri"))?
                * 10
        }
        _ => frac
            .parse::<u32>()
            .map_err(|_| ServiceError::Invalid("foiz noto'g'ri"))?,
    };
    let bp = int
        .checked_mul(100)
        .and_then(|v| v.checked_add(frac_bp))
        .ok_or(ServiceError::Invalid("foiz juda katta"))?;
    if bp > 100_000 {
        return Err(ServiceError::Invalid("foiz juda katta"));
    }
    Ok(bp)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_percent_to_basis_points() {
        assert_eq!(percent_to_bp("12,5").unwrap(), 1250);
        assert_eq!(percent_to_bp(" 7.25 ").unwrap(), 725);
        assert_eq!(percent_to_bp("15").unwrap(), 1500);
        assert_eq!(percent_to_bp("0").unwrap(), 0);
        for bad in ["", "-1", "1.234", "abc", "1e2", ".5", "1000.01", "5%"] {
            assert!(percent_to_bp(bad).is_err(), "{bad}");
        }
    }
}
