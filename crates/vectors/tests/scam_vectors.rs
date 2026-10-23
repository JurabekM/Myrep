//! 7-qonun vektorlari (SPEC 2G, DESKTOP_PROMPT 5-bo'lim): besh xavf belgisi, va'da qilingan foyda, piramida,
//! «oilaviy zaxira». Mobil bilan umumiy fayllar — `SHA256SUMS` manifestida.
#![allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]

use domain::offer_check::{Answer, OfferAnswers, Question, offer_check};
use domain::scam_math::{lump_sum_split, promised_return, pyramid_levels};
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

#[test]
fn scam_signals_vektorlari() {
    let suite = load_suite("scam_signals").expect("scam_signals.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let answers_json = &case.input["answers"];
        let mut answers = OfferAnswers::UNKNOWN;
        for question in Question::ALL {
            let code = answers_json
                .get(question.code())
                .and_then(Value::as_str)
                .unwrap_or("UNKNOWN");
            answers.set(question, Answer::from_code(code));
        }
        let report = offer_check(&answers);
        let actual = json!({
            "signs": report.signs.iter().map(|s| s.code()).collect::<Vec<_>>(),
            "level": report.level.code(),
            "verdict": report.verdict.code(),
            "categories": report.categories.iter().map(|c| c.code()).collect::<Vec<_>>(),
        });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn promised_return_vektorlari() {
    let suite = load_suite("promised_return").expect("promised_return.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let monthly =
            u32::try_from(int_field(&case.input, "monthlyBp").expect("monthlyBp")).unwrap();
        let months = u32::try_from(int_field(&case.input, "months").expect("months")).unwrap();
        let result = promised_return(monthly, months).expect("hisob");
        let actual = json!({
            "simpleMultipleBp": result.simple_multiple_bp,
            "compoundMultipleBp": result.compound_multiple_bp,
        });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn pyramid_levels_vektorlari() {
    let suite = load_suite("pyramid_levels").expect("pyramid_levels.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let k = u64::try_from(int_field(&case.input, "recruitsPerPerson").expect("k")).unwrap();
        let n = u64::try_from(int_field(&case.input, "population").expect("N")).unwrap();
        let model = pyramid_levels(k, n).expect("model");
        let actual = json!({
            "levels": model.levels,
            "participants": model.participants,
            "lastLevel": model.last_level,
            "lastLevelShareBp": model.last_level_share_bp,
            "lastLevelFull": model.last_level_full,
        });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

#[test]
fn lump_sum_split_vektorlari() {
    let suite = load_suite("lump_sum_split").expect("lump_sum_split.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let currency = Currency::from_iso(str_field(&case.input, "currency").expect("valyuta"))
            .expect("ma'lum");
        let minor = |key: &str| -> i64 {
            str_field(&case.input, key)
                .expect("summa")
                .parse::<i64>()
                .expect("butun son")
        };
        let split = lump_sum_split(
            Money::new(minor("amount"), currency),
            Money::new(minor("reserveMissing"), currency),
        )
        .expect("taqsimot");
        let actual = json!({
            "toReserve": split.to_reserve.minor().to_string(),
            "toInvest": split.to_invest.minor().to_string(),
        });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}
