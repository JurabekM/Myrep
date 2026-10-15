//! D10 vektorlari: amortizatsiya jadvali (`amortization`) va 70/20/10 taqsimoti (`debt_recovery_split`).
#![allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]

use domain::amortization::annuity_schedule;
use domain::recovery::recovery_split;
use money::{Currency, Money};
use serde_json::{Value, json};
use vectors::{Case, Suite, int_field, load_suite, str_field};

fn check(case: &Case, actual: Value, failures: &mut Vec<String>) {
    if actual != case.expected {
        failures.push(format!(
            "{}: kutilgan {} — olingan {}",
            case.id, case.expected, actual
        ));
    }
}

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

fn currency_of(object: &Value, key: &str) -> Currency {
    Currency::from_iso(str_field(object, key).expect("valyuta")).expect("ma'lum valyuta")
}

fn minor_of(object: &Value, key: &str) -> i64 {
    str_field(object, key)
        .expect("summa")
        .parse::<i64>()
        .expect("butun son")
}

#[test]
fn amortization_vektorlari() {
    let suite = load_suite("amortization").expect("amortization.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency = currency_of(input, "currency");
        let principal = Money::new(minor_of(input, "principal"), currency);
        let extra = Money::new(minor_of(input, "extraPerMonth"), currency);
        let schedule = annuity_schedule(
            principal,
            int_field(input, "annualBp").expect("annualBp"),
            int_field(input, "termMonths").expect("termMonths"),
            extra,
        )
        .expect("jadval");
        let rows: Vec<Value> = schedule
            .rows
            .iter()
            .map(|row| {
                json!({
                    "month": row.month,
                    "interest": row.interest.minor().to_string(),
                    "principal": row.principal.minor().to_string(),
                    "extra": row.extra.minor().to_string(),
                    "balance": row.balance.minor().to_string(),
                })
            })
            .collect();
        let actual = json!({
            "payment": schedule.payment.minor().to_string(),
            "months": schedule.months,
            "totalInterest": schedule.total_interest.minor().to_string(),
            "schedule": rows,
        });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn debt_recovery_split_vektorlari() {
    let suite = load_suite("debt_recovery_split").expect("debt_recovery_split.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency = currency_of(input, "currency");
        let income = Money::new(minor_of(input, "income"), currency);
        let split_values: Vec<u64> = input["split"]
            .as_array()
            .expect("split massivi")
            .iter()
            .map(|value| value.as_u64().expect("bp"))
            .collect();
        let split: [u64; 3] = split_values.try_into().expect("uch ulush");
        let actual = match recovery_split(income, split) {
            Ok(parts) => json!({
                "parts": parts.iter().map(|part| part.minor().to_string()).collect::<Vec<_>>(),
            }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}
