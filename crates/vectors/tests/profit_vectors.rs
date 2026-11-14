//! D12/D13A vektorlari: sheriklik foyda-zarar taqsimoti (`profit_distribution`) va «katta foyda» (`profit_spike`).
#![allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]

use domain::partnership::{PartnerInput, PartnershipKind, distribute};
use domain::profit_spike::{SpikeInput, profit_spike_alert};
use money::{Currency, Money};
use serde_json::{Value, json};
use vectors::{Case, Suite, load_suite, opt_str_field, str_field};

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

fn minor_text(object: &Value, key: &str) -> i64 {
    str_field(object, key)
        .expect("summa")
        .parse::<i64>()
        .expect("butun son")
}

#[test]
fn profit_distribution_vektorlari() {
    let suite = load_suite("profit_distribution").expect("profit_distribution.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency =
            Currency::from_iso(str_field(input, "currency").expect("valyuta")).expect("valyuta");
        let kind = match str_field(input, "type").expect("type") {
            "MUDARABA" => PartnershipKind::Mudaraba,
            "MUSHARAKA" => PartnershipKind::Musharaka,
            other => panic!("noma'lum tur: {other}"),
        };
        let net = Money::new(minor_text(input, "net"), currency);
        let parties: Vec<PartnerInput> = input["parties"]
            .as_array()
            .expect("parties")
            .iter()
            .map(|party| PartnerInput {
                share_bp: party["shareBp"].as_u64().unwrap_or(0),
                capital: Money::new(minor_text(party, "capital"), currency),
                fixed_return: opt_str_field(party, "fixedReturn")
                    .map(|text| Money::new(text.parse::<i64>().expect("kafolat"), currency)),
                is_capital_provider: opt_str_field(party, "role") == Some("CAPITAL_PROVIDER"),
            })
            .collect();
        let actual = match distribute(kind, net, &parties) {
            Ok(shares) => json!({
                "shares": shares.iter().map(|share| share.minor().to_string()).collect::<Vec<_>>(),
            }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn profit_spike_vektorlari() {
    let suite = load_suite("profit_spike").expect("profit_spike.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let plan = opt_str_field(input, "plan").map(|text| text.parse::<i64>().expect("reja"));
        let last_three = input["last3"].as_array().map(|items| {
            let values: Vec<i64> = items
                .iter()
                .map(|item| item.as_str().expect("davr").parse::<i64>().expect("summa"))
                .collect();
            [values[0], values[1], values[2]]
        });
        let actual = json!({
            "alert": profit_spike_alert(SpikeInput {
                plan,
                last_three,
                actual: minor_text(input, "actual"),
            }),
        });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}
