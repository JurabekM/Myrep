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
const COVERED_SUITES: &[&str] = &["allocate", "fx_convert", "money_format", "percent_of"];

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
