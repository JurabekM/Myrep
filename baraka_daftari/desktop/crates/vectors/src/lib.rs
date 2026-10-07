//! `spec/test-vectors/*.json` oltin vektorlarini yuklaydi va `money` crate'ga qarshi ishga tushiradi.
//! Pul qiymatlari JSON'da string (minor birlikda) ko'rinishida.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

use std::{fs, path::Path};

use money::{
    allocate, format_money, parse_amount, parse_signed_amount, percent_of, Currency, FxRate,
    Locale, Money, MoneyError,
};
use serde::Deserialize;
use serde_json::Value;

#[derive(Debug, thiserror::Error)]
pub enum VectorError {
    #[error("fayl o'qilmadi: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON noto'g'ri ({file}): {source}")]
    Json {
        file: String,
        source: serde_json::Error,
    },
    #[error("noma'lum suite: {0}")]
    UnknownSuite(String),
}

#[derive(Debug, Deserialize)]
struct Suite {
    suite: String,
    cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
struct Case {
    id: String,
    input: Value,
    expected: Value,
}

#[derive(Debug, Default)]
pub struct Report {
    pub passed: usize,
    pub failures: Vec<String>,
}

impl Report {
    #[must_use]
    pub fn is_green(&self) -> bool {
        self.failures.is_empty()
    }
}

/// Katalogdagi barcha `*.json` suite'larni ishga tushiradi (fayl nomi bo'yicha tartiblangan).
///
/// # Errors
/// Fayl o'qilmasa, JSON noto'g'ri bo'lsa yoki suite noma'lum bo'lsa.
pub fn run_dir(dir: &Path) -> Result<Report, VectorError> {
    let mut files: Vec<_> = fs::read_dir(dir)?
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|e| e == "json"))
        .collect();
    files.sort();

    let mut report = Report::default();
    for path in files {
        let text = fs::read_to_string(&path)?;
        let suite: Suite = serde_json::from_str(&text).map_err(|source| VectorError::Json {
            file: path.display().to_string(),
            source,
        })?;
        let runner = runner_for(&suite.suite)?;
        for case in suite.cases {
            match runner(&case.input) {
                Ok(actual) if actual == case.expected => report.passed += 1,
                Ok(actual) => report.failures.push(format!(
                    "{}/{}: kutilgan {}, olingan {actual}",
                    suite.suite, case.id, case.expected
                )),
                Err(msg) => report
                    .failures
                    .push(format!("{}/{}: {msg}", suite.suite, case.id)),
            }
        }
    }
    Ok(report)
}

type Runner = fn(&Value) -> Result<Value, String>;

fn runner_for(suite: &str) -> Result<Runner, VectorError> {
    match suite {
        "allocate" => Ok(run_allocate),
        "percent_of" => Ok(run_percent_of),
        "fx_convert" => Ok(run_fx_convert),
        "money_format" => Ok(run_money_format),
        "money_parse" => Ok(run_money_parse),
        "unexplained_gap" => Ok(run_unexplained_gap),
        "streak" => Ok(run_streak),
        "share_suggestion" => Ok(run_share_suggestion),
        "chapter_unlock" => Ok(run_chapter_unlock),
        "havas_status" => Ok(run_havas_status),
        "habit_projection" => Ok(run_habit_projection),
        "rescued_money" => Ok(run_rescued_money),
        "subscription_cost" => Ok(run_subscription_cost),
        "forgotten_subscription" => Ok(run_forgotten_subscription),
        "envelope" => Ok(run_envelope),
        "money_parse_signed" => Ok(run_money_parse_signed),
        "emergency_target" => Ok(run_emergency_target),
        "guard_months" => Ok(run_guard_months),
        "personal_inflation" => Ok(run_personal_inflation),
        "readiness_gate" => Ok(run_readiness_gate),
        "allocation_priority" => Ok(run_allocation_priority),
        "purchasing_power" => Ok(run_purchasing_power),
        other => Err(VectorError::UnknownSuite(other.to_owned())),
    }
}

fn str_field<'a>(v: &'a Value, key: &str) -> Result<&'a str, String> {
    v.get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("`{key}` string bo'lishi kerak"))
}

fn int_field(v: &Value, key: &str) -> Result<u64, String> {
    v.get(key)
        .and_then(Value::as_u64)
        .ok_or_else(|| format!("`{key}` butun son bo'lishi kerak"))
}

fn parse_minor(s: &str) -> Result<i64, String> {
    s.parse::<i64>()
        .map_err(|e| format!("`{s}` summa emas: {e}"))
}

fn parse_currency(v: &Value, key: &str) -> Result<Currency, String> {
    Currency::from_code(str_field(v, key)?).map_err(|e| e.to_string())
}

fn parse_money(v: &Value, amount_key: &str, currency_key: &str) -> Result<Money, String> {
    Ok(Money::new(
        parse_minor(str_field(v, amount_key)?)?,
        parse_currency(v, currency_key)?,
    ))
}

fn money_json(m: Money) -> Value {
    serde_json::json!({ "minor": m.minor().to_string(), "currency": m.currency().code() })
}

fn error_code(e: &MoneyError) -> &'static str {
    match e {
        MoneyError::CurrencyMismatch { .. } => "CURRENCY_MISMATCH",
        MoneyError::Overflow => "OVERFLOW",
        MoneyError::InvalidRatios => "INVALID_RATIOS",
        MoneyError::InvalidBasisPoints => "INVALID_BASIS_POINTS",
        MoneyError::InvalidRate => "INVALID_RATE",
        MoneyError::UnknownCurrency(_) => "UNKNOWN_CURRENCY",
        MoneyError::Parse(_) => "PARSE",
    }
}

fn error_json(e: &MoneyError) -> Value {
    serde_json::json!({ "error": error_code(e) })
}

fn run_allocate(input: &Value) -> Result<Value, String> {
    let total = parse_money(input, "total", "currency")?;
    let ratios: Vec<u64> = input
        .get("ratios")
        .and_then(Value::as_array)
        .ok_or("`ratios` massiv bo'lishi kerak")?
        .iter()
        .map(|r| {
            r.as_u64()
                .ok_or_else(|| "nisbat butun son bo'lishi kerak".to_owned())
        })
        .collect::<Result<_, _>>()?;
    Ok(match allocate(total, &ratios) {
        Ok(parts) => {
            serde_json::json!({ "parts": parts.iter().map(|m| m.minor().to_string()).collect::<Vec<_>>() })
        }
        Err(e) => error_json(&e),
    })
}

fn run_percent_of(input: &Value) -> Result<Value, String> {
    let amount = parse_money(input, "amount", "currency")?;
    let bp = u32::try_from(int_field(input, "bp")?).map_err(|e| e.to_string())?;
    Ok(match percent_of(amount, bp) {
        Ok(m) => serde_json::json!({ "minor": m.minor().to_string() }),
        Err(e) => error_json(&e),
    })
}

fn run_fx_convert(input: &Value) -> Result<Value, String> {
    let amount = parse_money(input, "amount", "currency")?;
    let rate = FxRate {
        from: parse_currency(input, "from")?,
        to: parse_currency(input, "to")?,
        rate_num: parse_minor(str_field(input, "rate_num")?)?,
        rate_den: parse_minor(str_field(input, "rate_den")?)?,
        date: "vector".into(),
        source: "vector".into(),
    };
    Ok(match rate.convert(amount) {
        Ok(m) => money_json(m),
        Err(e) => error_json(&e),
    })
}

fn run_money_format(input: &Value) -> Result<Value, String> {
    let amount = parse_money(input, "minor", "currency")?;
    let locale = match str_field(input, "locale")? {
        "uz" => Locale::Uz,
        "ru" => Locale::Ru,
        other => return Err(format!("noma'lum locale `{other}`")),
    };
    Ok(serde_json::json!({ "text": format_money(amount, locale) }))
}

fn run_unexplained_gap(input: &Value) -> Result<Value, String> {
    let m = |key| parse_money(input, key, "currency");
    let (income, obligations, expenses, savings) = (
        m("income")?,
        m("obligations")?,
        m("expenses")?,
        m("savings")?,
    );
    let result = domain::month_result(income, obligations, expenses).map_err(|e| e.to_string())?;
    let gap = domain::unexplained_gap(income, obligations, expenses, savings)
        .map_err(|e| e.to_string())?;
    Ok(serde_json::json!({
        "month_result": result.minor().to_string(),
        "unexplained": gap.minor().to_string(),
    }))
}

fn parse_weekday(s: &str) -> Result<time::Weekday, String> {
    use time::Weekday::{Friday, Monday, Saturday, Sunday, Thursday, Tuesday, Wednesday};
    Ok(match s {
        "MONDAY" => Monday,
        "TUESDAY" => Tuesday,
        "WEDNESDAY" => Wednesday,
        "THURSDAY" => Thursday,
        "FRIDAY" => Friday,
        "SATURDAY" => Saturday,
        "SUNDAY" => Sunday,
        other => return Err(format!("noma'lum hafta kuni `{other}`")),
    })
}

fn run_streak(input: &Value) -> Result<Value, String> {
    let dates = input
        .get("dates")
        .and_then(Value::as_array)
        .ok_or("`dates` massiv bo'lishi kerak")?
        .iter()
        .map(|d| {
            d.as_str()
                .ok_or_else(|| "sana string bo'lishi kerak".to_owned())
                .and_then(|s| domain::date_from_str(s).map_err(|e| e.to_string()))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let today = domain::date_from_str(str_field(input, "today")?).map_err(|e| e.to_string())?;
    let anchor = parse_weekday(str_field(input, "anchor")?)?;
    let s = domain::compute_streak(&dates, today, anchor);
    Ok(serde_json::json!({
        "current_weeks": s.current_weeks,
        "best_weeks": s.best_weeks,
        "saved_days": s.saved_days,
    }))
}

fn run_share_suggestion(input: &Value) -> Result<Value, String> {
    let income = parse_money(input, "income", "currency")?;
    let allocated = parse_money(input, "allocated_this_month", "currency")?;
    let rule = input.get("rule").ok_or("`rule` kerak")?;
    let value = parse_minor(str_field(rule, "value")?)?;
    let rule = match str_field(rule, "kind")? {
        "PERCENT" => domain::ShareRule::Percent {
            bp: u32::try_from(value).map_err(|e| e.to_string())?,
        },
        "MONTHLY_FIXED" => domain::ShareRule::MonthlyFixed {
            target: Money::new(value, income.currency()),
        },
        other => return Err(format!("noma'lum qoida `{other}`")),
    };
    Ok(match domain::suggest_share(rule, income, allocated) {
        Ok(m) => serde_json::json!({ "minor": m.minor().to_string() }),
        Err(e) => error_json(&e),
    })
}

fn run_money_parse(input: &Value) -> Result<Value, String> {
    let currency = parse_currency(input, "currency")?;
    Ok(match parse_amount(str_field(input, "text")?, currency) {
        Ok(m) => serde_json::json!({ "minor": m.minor().to_string() }),
        Err(e) => error_json(&e),
    })
}

fn u32_field(v: &Value, key: &str) -> Result<u32, String> {
    u32::try_from(int_field(v, key)?).map_err(|e| e.to_string())
}

fn run_chapter_unlock(input: &Value) -> Result<Value, String> {
    let p = input.get("policy").ok_or("`policy` kerak")?;
    let policy = content::UnlockPolicy::new(
        u32_field(p, "window_weeks")?,
        u32_field(p, "min_satisfied_weeks")?,
        u32_field(p, "min_tasks_per_week")?,
    )
    .map_err(|e| e.to_string())?;
    let opened =
        domain::date_from_str(str_field(input, "opened_week")?).map_err(|e| e.to_string())?;
    let today = domain::date_from_str(str_field(input, "today")?).map_err(|e| e.to_string())?;
    let anchor = parse_weekday(str_field(input, "anchor")?)?;
    let results = input
        .get("results")
        .and_then(Value::as_array)
        .ok_or("`results` massiv bo'lishi kerak")?
        .iter()
        .map(|r| {
            Ok(content::WeekResult {
                week_start: domain::date_from_str(str_field(r, "week_start")?)
                    .map_err(|e| e.to_string())?,
                completed_tasks: u32_field(r, "completed_tasks")?,
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    Ok(
        match content::decide(policy, opened, today, anchor, &results) {
            content::UnlockDecision::Unlocked => serde_json::json!({ "decision": "UNLOCKED" }),
            content::UnlockDecision::Locked {
                satisfied_weeks,
                needed_weeks,
                weeks_in_window,
            } => {
                serde_json::json!({
                    "decision": "LOCKED",
                    "satisfied_weeks": satisfied_weeks,
                    "needed_weeks": needed_weeks,
                    "weeks_in_window": weeks_in_window,
                })
            }
        },
    )
}

fn havas_error_code(e: &domain::HavasError) -> &'static str {
    match e {
        domain::HavasError::InvalidLimit => "INVALID_LIMIT",
        domain::HavasError::InvalidAmount => "INVALID_AMOUNT",
        domain::HavasError::Money(m) => error_code(m),
    }
}

fn run_havas_status(input: &Value) -> Result<Value, String> {
    let spent = parse_money(input, "spent", "currency")?;
    let limit = parse_money(input, "limit", "currency")?;
    Ok(match domain::havas_status(spent, limit) {
        Ok(s) => serde_json::json!({
            "state": match s.state {
                domain::HavasState::Ok => "OK",
                domain::HavasState::Near => "NEAR",
                domain::HavasState::Over => "OVER",
            },
            "used_bp": s.used_bp,
        }),
        Err(e) => serde_json::json!({ "error": havas_error_code(&e) }),
    })
}

fn run_habit_projection(input: &Value) -> Result<Value, String> {
    let total = parse_money(input, "total", "currency")?;
    let days = u32_field(input, "window_days")?;
    Ok(match domain::habit_projection(total, days) {
        Ok(p) => serde_json::json!({
            "week": p.week.minor().to_string(),
            "month": p.month.minor().to_string(),
            "year": p.year.minor().to_string(),
        }),
        Err(e) => serde_json::json!({ "error": havas_error_code(&e) }),
    })
}

fn run_rescued_money(input: &Value) -> Result<Value, String> {
    let baseline = parse_money(input, "baseline", "currency")?;
    let current = parse_money(input, "current", "currency")?;
    Ok(match domain::rescued_money(baseline, current) {
        Ok(m) => serde_json::json!({ "rescued": m.minor().to_string() }),
        Err(e) => serde_json::json!({ "error": havas_error_code(&e) }),
    })
}

fn run_subscription_cost(input: &Value) -> Result<Value, String> {
    let amount = parse_money(input, "amount", "currency")?;
    let period =
        domain::BillingPeriod::parse(str_field(input, "period")?).ok_or("noma'lum davriylik")?;
    Ok(match domain::subscription_cost(amount, period) {
        Ok(c) => serde_json::json!({
            "monthly": c.monthly.minor().to_string(),
            "yearly": c.yearly.minor().to_string(),
        }),
        Err(e) => serde_json::json!({ "error": havas_error_code(&e) }),
    })
}

fn run_forgotten_subscription(input: &Value) -> Result<Value, String> {
    let date = |key: &str| -> Result<domain::Date, String> {
        domain::date_from_str(str_field(input, key)?).map_err(|e| e.to_string())
    };
    let last = match input.get("last_used_on") {
        Some(Value::String(s)) => Some(domain::date_from_str(s).map_err(|e| e.to_string())?),
        _ => None,
    };
    let days = i64::try_from(int_field(input, "threshold_days")?).map_err(|e| e.to_string())?;
    Ok(serde_json::json!({
        "forgotten": domain::is_forgotten(last, date("started_on")?, date("today")?, days)
    }))
}

fn run_envelope(input: &Value) -> Result<Value, String> {
    let limit = parse_money(input, "limit", "currency")?;
    let spent = parse_money(input, "spent", "currency")?;
    let status = match domain::envelope_status(limit, spent) {
        Ok(s) => s,
        Err(e) => return Ok(serde_json::json!({ "error": havas_error_code(&e) })),
    };
    let fill = domain::cash_to_fill(limit, spent).map_err(|e| e.to_string())?;
    let mut out = serde_json::json!({
        "remaining": status.remaining.minor().to_string(),
        "state": match status.state {
            domain::HavasState::Ok => "OK",
            domain::HavasState::Near => "NEAR",
            domain::HavasState::Over => "OVER",
        },
        "used_bp": status.used_bp,
        "cash_to_fill": fill.minor().to_string(),
    });
    if input.get("leftover_cash").is_some() {
        let left = parse_money(input, "leftover_cash", "currency")?;
        let diff = domain::closing_difference(limit, spent, left).map_err(|e| e.to_string())?;
        out["difference"] = Value::String(diff.minor().to_string());
    }
    Ok(out)
}

fn run_money_parse_signed(input: &Value) -> Result<Value, String> {
    let currency = parse_currency(input, "currency")?;
    Ok(
        match parse_signed_amount(str_field(input, "text")?, currency) {
            Ok((negative, m)) => {
                serde_json::json!({ "negative": negative, "minor": m.minor().to_string() })
            }
            Err(e) => error_json(&e),
        },
    )
}

fn guard_error_code(e: &domain::GuardError) -> &'static str {
    match e {
        domain::GuardError::NoWeights => "NO_WEIGHTS",
        domain::GuardError::InvalidPrice => "INVALID_PRICE",
        domain::GuardError::InvalidAmount => "INVALID_AMOUNT",
        domain::GuardError::Money(m) => error_code(m),
    }
}

fn guard_error(e: &domain::GuardError) -> Value {
    serde_json::json!({ "error": guard_error_code(e) })
}

fn run_emergency_target(input: &Value) -> Result<Value, String> {
    let currency = parse_currency(input, "currency")?;
    let months = input
        .get("months")
        .and_then(Value::as_array)
        .ok_or("months massivi kerak")?
        .iter()
        .map(|v| {
            v.as_str()
                .ok_or_else(|| "oy summasi matn bo'lishi kerak".to_owned())
                .and_then(parse_minor)
                .map(|m| Money::new(m, currency))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let n = u32_field(input, "target_months")?;
    Ok(match domain::emergency_target(&months, n, currency) {
        Ok(t) => serde_json::json!({ "target": t.minor().to_string() }),
        Err(e) => guard_error(&e),
    })
}

fn run_guard_months(input: &Value) -> Result<Value, String> {
    let balance = parse_money(input, "balance", "currency")?;
    let target = parse_money(input, "target", "currency")?;
    let n = u32_field(input, "target_months")?;
    Ok(match domain::guard_months_x100(balance, target, n) {
        Ok(m) => serde_json::json!({ "months_x100": m }),
        Err(e) => guard_error(&e),
    })
}

fn run_personal_inflation(input: &Value) -> Result<Value, String> {
    let currency = parse_currency(input, "currency")?;
    let lines = input
        .get("items")
        .and_then(Value::as_array)
        .ok_or("items massivi kerak")?
        .iter()
        .map(|v| {
            Ok(domain::BasketLine {
                weight_bp: u32_field(v, "weight_bp")?,
                first: Money::new(parse_minor(str_field(v, "first")?)?, currency),
                last: Money::new(parse_minor(str_field(v, "last")?)?, currency),
            })
        })
        .collect::<Result<Vec<_>, String>>()?;
    Ok(match domain::personal_inflation(&lines) {
        Ok(i) => serde_json::json!({ "per_item_bp": i.per_item_bp, "index_bp": i.index_bp }),
        Err(e) => guard_error(&e),
    })
}

fn run_readiness_gate(input: &Value) -> Result<Value, String> {
    let flag = |key: &str| {
        input
            .get(key)
            .and_then(Value::as_bool)
            .ok_or_else(|| format!("{key} (bool) kerak"))
    };
    let g = domain::readiness_gate(
        u32_field(input, "guard_months_x100")?,
        flag("has_interest_debt")?,
        flag("has_debt_plan")?,
        u32_field(input, "required_x100")?,
    );
    Ok(serde_json::json!({
        "status": if g.open { "OPEN" } else { "LOCKED" },
        "reasons": g.reasons.iter().map(|r| r.code()).collect::<Vec<_>>(),
    }))
}

fn run_allocation_priority(input: &Value) -> Result<Value, String> {
    let share = parse_money(input, "share", "currency")?;
    let balance = parse_money(input, "guard_balance", "currency")?;
    let target = parse_money(input, "guard_target", "currency")?;
    let open = input
        .get("gate_open")
        .and_then(Value::as_bool)
        .ok_or("gate_open (bool) kerak")?;
    Ok(
        match domain::split_allocation(share, balance, target, open) {
            Ok((g, r)) => serde_json::json!({
                "guard": g.minor().to_string(),
                "growing": r.minor().to_string(),
            }),
            Err(e) => guard_error(&e),
        },
    )
}

fn run_purchasing_power(input: &Value) -> Result<Value, String> {
    let amount = parse_money(input, "amount", "currency")?;
    match str_field(input, "op")? {
        "real_value" | "future_price" => {
            let bp = u32_field(input, "annual_bp")?;
            let years = u32_field(input, "years")?;
            let res = if str_field(input, "op")? == "real_value" {
                domain::real_value(amount, bp, years)
            } else {
                domain::future_price(amount, bp, years)
            };
            Ok(match res {
                Ok(m) => serde_json::json!({ "amount": m.minor().to_string() }),
                Err(e) => guard_error(&e),
            })
        }
        "quantity_milli" => {
            let price = Money::new(
                parse_minor(str_field(input, "unit_price")?)?,
                amount.currency(),
            );
            Ok(match domain::quantity_milli(amount, price) {
                Ok(q) => serde_json::json!({ "milli": q }),
                Err(e) => guard_error(&e),
            })
        }
        other => Err(format!("noma'lum op: {other}")),
    }
}
