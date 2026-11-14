//! D8 vektorlari: zaxira maqsadi, shaxsiy inflyatsiya, tayyorgarlik darvozasi, mobil bilan umumiy fayllar manifesti.
//!
//! Mobil ilova bilan umumiy vektorlar `spec/test-vectors/SHA256SUMS` da xeshlari bilan qayd etilgan:
//! nusxa bitta bayt farq qilsa, test yiqiladi (DESKTOP_PROMPT.md 5.4).
#![allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]

use money::{Currency, Money};
use serde_json::{Value, json};
use vectors::{Case, Suite, int_field, load_suite, str_field};

/// Case natijasini `expected` bilan TO'LIQ solishtiradi.
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

fn currency_of(object: &Value, key: &str) -> Currency {
    Currency::from_iso(str_field(object, key).expect("valyuta maydoni")).expect("ma'lum valyuta")
}

/// Satr ko'rinishidagi minor qiymat (`"520000000"`).
fn minor_text(object: &Value, key: &str) -> i64 {
    str_field(object, key)
        .expect("summa maydoni")
        .parse::<i64>()
        .expect("butun son")
}

#[test]
fn emergency_target_vektorlari() {
    use domain::emergency::emergency_target;

    let suite = load_suite("emergency_target").expect("emergency_target.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency = currency_of(input, "currency");
        let months: Vec<Money> = input["months"]
            .as_array()
            .expect("months massivi")
            .iter()
            .map(|value| {
                Money::new(
                    value
                        .as_str()
                        .expect("summa satri")
                        .parse::<i64>()
                        .expect("butun son"),
                    currency,
                )
            })
            .collect();
        let n = int_field(input, "n").expect("n");
        let actual = match emergency_target(currency, &months, n) {
            Ok(target) => json!({ "target": target.map(|money| money.minor().to_string()) }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn personal_inflation_vektorlari() {
    use domain::inflation::{PriceChange, personal_index};

    let suite = load_suite("personal_inflation").expect("personal_inflation.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let currency = currency_of(input, "currency");
        let items: Vec<PriceChange> = input["items"]
            .as_array()
            .expect("items massivi")
            .iter()
            .map(|item| PriceChange {
                name: str_field(item, "name").expect("nomi").to_owned(),
                from: Money::new(minor_text(item, "from"), currency),
                to: Money::new(minor_text(item, "to"), currency),
                weight_bp: int_field(item, "weightBp").expect("weightBp"),
            })
            .collect();
        let actual = match personal_index(&items) {
            Ok(index) => json!({ "items": index.item_bps, "index": index.index_bp }),
            Err(error) => json!({ "error": error.code() }),
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn readiness_gate_vektorlari() {
    use domain::readiness::readiness_gate;

    let suite = load_suite("readiness_gate").expect("readiness_gate.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let input = &case.input;
        let result = readiness_gate(
            int_field(input, "reserveMonthsTenths").expect("reserveMonthsTenths"),
            input["hasInterestDebt"].as_bool().expect("hasInterestDebt"),
            input["hasRecoveryPlan"].as_bool().expect("hasRecoveryPlan"),
        );
        let reasons: Vec<&str> = result.reasons.iter().map(|reason| reason.code()).collect();
        let actual = json!({ "state": result.state.code(), "reasons": reasons });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn mobil_bilan_umumiy_vektorlar_manifestga_mos() {
    use sha2::{Digest, Sha256};

    let dir = vectors::vectors_dir();
    let manifest = std::fs::read_to_string(dir.join("SHA256SUMS")).expect("SHA256SUMS");
    let mut checked = 0;
    for line in manifest.lines().filter(|line| !line.trim().is_empty()) {
        let (expected, name) = line
            .split_once("  ")
            .expect("sha256sum formati: «xesh  fayl»");
        let bytes = std::fs::read(dir.join(name)).expect("manifestdagi fayl");
        let actual = format!("{:x}", Sha256::digest(&bytes));
        assert_eq!(actual, expected, "{name}: xesh mos emas (nusxa o'zgargan)");
        checked += 1;
    }
    assert!(checked >= 3, "manifestda kamida 3 ta fayl bo'lishi kerak");
}
