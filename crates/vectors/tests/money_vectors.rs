//! Pul vektorlari runner'i: `spec/test-vectors` dagi suite'larni `baraka-money` ga qarshi tekshiradi.
//!
//! Har bir case'da natija JSON ko'rinishiga keltiriladi va `expected` bilan TO'LIQ solishtiriladi
//! (DESKTOP_PROMPT.md 5.2). Xato holatlari `{"error": "KOD"}` ko'rinishida, kod — `MoneyError::code()`.
#![allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]

use money::{Currency, FxRate, Locale, Money, allocate, convert, format_money, percent_of};
use serde_json::{Value, json};
use time::{Date, Month};
use vectors::{
    Case, Suite, int_field, load_suite, opt_str_field, str_field, suite_names, u64_array_field,
};

/// Runner yozilgan suite'lar. Yangi vektor fayli qo'shilsa, shu ro'yxatga ham qo'shilishi shart:
/// `har_bir_vektor_fayli_runner_bilan_qoplangan` testi buni talab qiladi.
const COVERED_SUITES: &[&str] = &[
    "allocate",
    "emergency_target",
    "fx_convert",
    "income_share",
    "money_format",
    "money_parse",
    "percent_of",
    "personal_inflation",
    "readiness_gate",
    "savings_rescue",
    "streak",
    "unexplained_gap",
];

/// Kurs sanasi (vektorlarda sana yo'q; konstruktor talab qiladi).
fn snapshot_date() -> Date {
    Date::from_calendar_date(2026, Month::October, 14).expect("to'g'ri sana")
}

fn currency_of(object: &Value, key: &str) -> Currency {
    Currency::from_iso(str_field(object, key).expect("valyuta maydoni")).expect("ma'lum valyuta")
}

/// Case natijasini `expected` bilan solishtiradi; farq bo'lsa ro'yxatga yozadi.
fn check(case: &Case, actual: Value, failures: &mut Vec<String>) {
    if actual != case.expected {
        failures.push(format!(
            "{}: kutilgan {} — olingan {}",
            case.id, case.expected, actual
        ));
    }
}

/// Suite yakuni: bo'sh suite yo'q va hech bir case muvaffaqiyatsiz emas.
fn finish(suite: &Suite, failures: &[String]) {
    assert!(!suite.cases.is_empty(), "{}: vektorlar yo'q", suite.suite);
    assert!(
        failures.is_empty(),
        "{}: {} ta vektor muvaffaqiyatsiz\n{}",
        suite.suite,
        failures.len(),
        failures.join("\n")
    );
}

#[test]
fn har_bir_vektor_fayli_runner_bilan_qoplangan() {
    let files = suite_names().expect("vektor papkasini o'qish");
    let mut covered: Vec<String> = COVERED_SUITES
        .iter()
        .map(|name| (*name).to_owned())
        .collect();
    covered.sort();
    assert_eq!(
        files, covered,
        "spec/test-vectors dagi fayllar va runner'lar mos emas"
    );
}

#[test]
fn allocate_vektorlari() {
    let suite = load_suite("allocate").expect("allocate.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let total = Money::new(
            int_field(&case.input, "total").expect("total"),
            currency_of(&case.input, "currency"),
        );
        let ratios = u64_array_field(&case.input, "ratios").expect("ratios");
        let actual = match allocate(total, &ratios) {
            Ok(parts) => json!({
                "parts": parts.iter().map(|part| part.minor().to_string()).collect::<Vec<String>>()
            }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn percent_of_vektorlari() {
    let suite = load_suite("percent_of").expect("percent_of.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let amount = Money::new(
            int_field(&case.input, "amount").expect("amount"),
            currency_of(&case.input, "currency"),
        );
        let bp = int_field(&case.input, "bp").expect("bp");
        let actual = match percent_of(amount, bp) {
            Ok(result) => json!({ "result": result.minor().to_string() }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn fx_convert_vektorlari() {
    let suite = load_suite("fx_convert").expect("fx_convert.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let amount_currency = currency_of(input, "from");
        let target = currency_of(input, "to");
        // rateFrom berilmasa, kurs manbasi summa valyutasi bilan bir xil deb olinadi.
        let rate_from = opt_str_field(input, "rateFrom").map_or(amount_currency, |code| {
            Currency::from_iso(code).expect("rateFrom")
        });
        let amount = Money::new(int_field(input, "amount").expect("amount"), amount_currency);
        let rate = FxRate::new(
            rate_from,
            target,
            int_field(input, "rateNum").expect("rateNum"),
            int_field(input, "rateDen").expect("rateDen"),
            snapshot_date(),
            "vector",
        );
        let actual = match rate.map(|rate| convert(amount, &rate)) {
            Ok(Ok(result)) => json!({ "result": result.minor().to_string() }),
            Ok(Err(error)) | Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn money_format_vektorlari() {
    let suite = load_suite("money_format").expect("money_format.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let amount = Money::new(
            int_field(input, "amount").expect("amount"),
            currency_of(input, "currency"),
        );
        let locale = match str_field(input, "locale").expect("locale") {
            "uz" => Locale::Uz,
            "ru" => Locale::Ru,
            other => panic!("noma'lum lokal: {other}"),
        };
        check(
            case,
            json!({ "text": format_money(amount, locale) }),
            &mut failures,
        );
    }
    finish(&suite, &failures);
}

/// Minor birlik maydoni (satr ko'rinishida, masalan `"800000000"`). Maydon yo'q bo'lsa — `None`.
fn minor_field(object: &Value, key: &str) -> Option<i64> {
    opt_str_field(object, key).map(|text| text.parse::<i64>().expect("minor birlik butun son"))
}

/// `YYYY-MM-DD` sanasini o'qiydi (vektorlardagi kalendar sanasi).
fn parse_date(text: &str) -> Date {
    let parts: Vec<&str> = text.split('-').collect();
    let year: i32 = parts[0].parse().expect("yil");
    let month_number: u8 = parts[1].parse().expect("oy");
    let day: u8 = parts[2].parse().expect("kun");
    Date::from_calendar_date(year, Month::try_from(month_number).expect("oy 1..12"), day)
        .expect("to'g'ri sana")
}

#[test]
fn money_parse_vektorlari() {
    let suite = load_suite("money_parse").expect("money_parse.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let text = str_field(&case.input, "text").expect("text");
        let currency = currency_of(&case.input, "currency");
        let actual = match money::parse_amount(text, currency) {
            Ok(value) => json!({ "minor": value.minor().to_string() }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn income_share_vektorlari() {
    use domain::{ShareRule, ShareTarget, suggest_share};

    let suite = load_suite("income_share").expect("income_share.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency = currency_of(input, "currency");
        let income = Money::new(minor_field(input, "income").expect("income"), currency);
        let target = match str_field(input, "mode").expect("mode") {
            "PERCENT" => ShareTarget::Percent(int_field(input, "basis_points").expect("bp")),
            _ => ShareTarget::Fixed(Money::new(
                minor_field(input, "monthly_target").expect("monthly_target"),
                currency,
            )),
        };
        let saved = Money::new(
            minor_field(input, "saved_this_month").unwrap_or(0),
            currency,
        );
        let rule = ShareRule {
            target,
            progressive: false,
            progression_offered_on: None,
        };
        let actual = match suggest_share(income, &rule, saved) {
            Ok(share) => json!({ "share": share.map(|value| value.minor().to_string()) }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn streak_vektorlari() {
    use domain::{habit_stats, streak_since};

    let suite = load_suite("streak").expect("streak.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let dates: Vec<Date> = input["saving_dates"]
            .as_array()
            .expect("saving_dates massiv")
            .iter()
            .map(|value| parse_date(value.as_str().expect("sana matni")))
            .collect();
        let today = parse_date(str_field(input, "today").expect("today"));
        let since = opt_str_field(input, "since").map(parse_date);
        let actual = match habit_stats(&dates, today) {
            Some(stats) => json!({
                "current_streak_weeks": stats.current_streak_weeks,
                "total_weeks": stats.total_weeks,
                "this_week_done": stats.this_week_done,
                "since_streak_weeks": streak_since(&dates, today, since),
            }),
            None => json!({ "error": "CALENDAR" }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn unexplained_gap_vektorlari() {
    use domain::ledger::unexplained_gap;

    let suite = load_suite("unexplained_gap").expect("unexplained_gap.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency = currency_of(input, "currency");
        let amount =
            |key: &str| Money::new(minor_field(input, key).expect("minor maydon"), currency);
        let actual = match unexplained_gap(
            amount("income"),
            amount("obligations"),
            amount("expenses"),
            amount("savings"),
        ) {
            Ok(gap) => json!({ "gap": gap.minor().to_string() }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn savings_rescue_vektorlari() {
    use domain::calendar::DateRange;
    use domain::rescue::{RescueKind, compute_rescue, subscription_savings};
    use money::{Currency, Money};

    let suite = load_suite("savings_rescue").expect("savings_rescue.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency =
            Currency::from_iso(str_field(input, "currency").expect("currency")).expect("valyuta");
        let actual = match str_field(input, "op").expect("op") {
            "compute" => {
                let baseline = input["baselineHavasMinor"].as_i64().map(|minor| {
                    (
                        Money::new(minor, currency),
                        input["baselineDays"].as_i64().expect("baselineDays"),
                    )
                });
                let result = compute_rescue(
                    currency,
                    input["elapsedDays"].as_i64().expect("elapsedDays"),
                    Money::new(
                        input["currentHavasMinor"]
                            .as_i64()
                            .expect("currentHavasMinor"),
                        currency,
                    ),
                    baseline,
                    Money::new(
                        input["subscriptionsMinor"]
                            .as_i64()
                            .expect("subscriptionsMinor"),
                        currency,
                    ),
                    Money::new(
                        input["envelopesMinor"].as_i64().expect("envelopesMinor"),
                        currency,
                    ),
                    Money::new(
                        input["transferredMinor"]
                            .as_i64()
                            .expect("transferredMinor"),
                        currency,
                    ),
                );
                match result {
                    Ok(breakdown) => {
                        let available = breakdown.available().expect("qoldiq");
                        let total = breakdown.total().expect("jami");
                        json!({
                            "havas_delta_minor": breakdown.havas_delta.minor(),
                            "havas_shown_minor": breakdown.havas_shown().minor(),
                            "total_minor": total.minor(),
                            "available_minor": available.minor(),
                            "spent_more": breakdown.spent_more(),
                            "has_baseline": breakdown.has_baseline,
                        })
                    }
                    Err(error) => json!({ "error": error.code() }),
                }
            }
            "subscription" => {
                let cancelled: Vec<(Money, Date)> = input["cancelled"]
                    .as_array()
                    .expect("cancelled massiv")
                    .iter()
                    .map(|item| {
                        (
                            Money::new(
                                item["monthlyMinor"].as_i64().expect("monthlyMinor"),
                                currency,
                            ),
                            parse_date(str_field(item, "on").expect("on")),
                        )
                    })
                    .collect();
                let period = DateRange {
                    start: parse_date(str_field(input, "periodStart").expect("periodStart")),
                    end: parse_date(str_field(input, "periodEnd").expect("periodEnd")),
                };
                let today = parse_date(str_field(input, "today").expect("today"));
                match subscription_savings(currency, &cancelled, period, today) {
                    Ok(savings) => json!({ "savings_minor": savings.minor() }),
                    Err(error) => json!({ "error": error.code() }),
                }
            }
            other => panic!("noma'lum operatsiya: {other}"),
        };
        let _ = RescueKind::Transfer;
        check(case, actual, &mut failures);
    }
    assert!(
        failures.is_empty(),
        "xatolar:
{}",
        failures.join(
            "
"
        )
    );
}
