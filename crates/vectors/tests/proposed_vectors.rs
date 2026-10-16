//! Desktop taklif vektorlari (`spec/test-vectors/proposed/`): mobil tasdiqlaguncha «PROPOSED».
//! Bu yerda to'liq jadval emas, birinchi va oxirgi qator solishtiriladi (fayl ixcham qolsin).
#![allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]

use domain::amortization::{AmortRow, differentiated_schedule, fixed_markup_schedule};
use money::{Currency, Money};
use serde_json::{Value, json};
use vectors::{int_field, load_proposed_suite, str_field};

fn minor_of(object: &Value, key: &str) -> i64 {
    str_field(object, key)
        .expect("summa")
        .parse::<i64>()
        .expect("butun son")
}

fn row_json(row: &AmortRow) -> Value {
    json!({
        "month": row.month,
        "interest": row.interest.minor().to_string(),
        "principal": row.principal.minor().to_string(),
        "extra": row.extra.minor().to_string(),
        "balance": row.balance.minor().to_string(),
    })
}

#[test]
fn amortization_extended_taklif_vektorlari() {
    let suite = load_proposed_suite("amortization_extended").expect("amortization_extended.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency =
            Currency::from_iso(str_field(input, "currency").expect("valyuta")).expect("valyuta");
        let principal = Money::new(minor_of(input, "principal"), currency);
        let term = int_field(input, "termMonths").expect("termMonths");
        let schedule = match str_field(input, "type").expect("type") {
            "DIFFERENTIATED" => differentiated_schedule(
                principal,
                int_field(input, "annualBp").expect("annualBp"),
                term,
                Money::new(minor_of(input, "extraPerMonth"), currency),
            ),
            "FIXED_MARKUP" => fixed_markup_schedule(
                principal,
                Money::new(minor_of(input, "markup"), currency),
                term,
            ),
            other => panic!("noma'lum tur: {other}"),
        }
        .expect("jadval");
        let actual = json!({
            "months": schedule.months,
            "totalInterest": schedule.total_interest.minor().to_string(),
            "first": schedule.rows.first().map(row_json),
            "last": schedule.rows.last().map(row_json),
        });
        if actual != case.expected {
            failures.push(format!(
                "{}: kutilgan {} — olingan {}",
                case.id, case.expected, actual
            ));
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}

#[test]
fn payoff_strategy_taklif_vektorlari() {
    use domain::loans::{OpenLoan, PayoffStrategy, payoff_order};
    let suite = load_proposed_suite("payoff_strategy").expect("payoff_strategy.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency =
            Currency::from_iso(str_field(input, "currency").expect("valyuta")).expect("valyuta");
        let strategy = PayoffStrategy::from_code(str_field(input, "strategy").expect("strategy"))
            .expect("strategiya");
        let loans: Vec<OpenLoan> = input["loans"]
            .as_array()
            .expect("loans")
            .iter()
            .map(|loan| OpenLoan {
                outstanding: Money::new(minor_of(loan, "outstanding"), currency),
                installment: Money::new(minor_of(loan, "installment"), currency),
                has_markup: loan["hasMarkup"].as_bool().unwrap_or(false),
            })
            .collect();
        let result = payoff_order(
            strategy,
            &loans,
            Money::new(minor_of(input, "extra"), currency),
        )
        .expect("tartib");
        let mut months = vec![0_u32; loans.len()];
        for step in &result.order {
            months[step.index] = step.months_to_clear;
        }
        let actual = json!({
            "order": result.order.iter().map(|s| s.index).collect::<Vec<_>>(),
            "monthsToClear": months,
            "totalMonths": result.total_months,
        });
        if actual != case.expected {
            failures.push(format!(
                "{}: kutilgan {} — olingan {}",
                case.id, case.expected, actual
            ));
        }
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}
