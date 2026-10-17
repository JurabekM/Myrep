//! D8A vektorlari: jurnal xesh-zanjiri (`journal_chain`) va kelishuv to'liqligi (`agreement_completeness`).
//! Mobil bilan umumiy fayllar — `spec/test-vectors/SHA256SUMS` manifestida.
#![allow(clippy::expect_used, clippy::unwrap_used, clippy::panic)]

use std::collections::BTreeMap;

use domain::agreement::{
    AgreementAnswers, AgreementType, Arbiter, Contribution, Custody, Duty, ExitClause, Party,
    ProfitRule, Term, completeness,
};
use domain::journal::{JournalEntry, JournalKind, chain_hashes, verify_chain};
use money::{Currency, Money};
use serde_json::{Value, json};
use time::{Date, Month};
use vectors::{Case, Suite, int_field, load_suite, opt_str_field, str_field};

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

/// `{"minor": "300000000", "currency": "UZS"}` yoki `null`.
fn money_or_none(value: &Value) -> Option<Money> {
    if value.is_null() {
        return None;
    }
    let minor = str_field(value, "minor")
        .expect("minor")
        .parse::<i64>()
        .expect("butun son");
    Some(Money::new(minor, currency_of(value, "currency")))
}

/// `YYYY-MM-DD` → sana.
fn date_of(text: &str) -> Date {
    let mut parts = text.split('-');
    let year: i32 = parts.next().expect("yil").parse().expect("yil raqami");
    let month: u8 = parts.next().expect("oy").parse().expect("oy raqami");
    let day: u8 = parts.next().expect("kun").parse().expect("kun raqami");
    Date::from_calendar_date(year, Month::try_from(month).expect("oy"), day).expect("sana")
}

fn kind_of(code: &str) -> JournalKind {
    JournalKind::from_code(code).expect("jurnal turi")
}

fn entries_of(input: &Value) -> Vec<JournalEntry> {
    input["entries"]
        .as_array()
        .expect("entries massivi")
        .iter()
        .map(|item| {
            let amount = money_or_none(&item["amount"]).expect("summa");
            JournalEntry {
                id: str_field(item, "id").expect("id").to_owned(),
                agreement_id: str_field(item, "agreementId")
                    .expect("agreementId")
                    .to_owned(),
                kind: kind_of(str_field(item, "kind").expect("kind")),
                party_id: str_field(item, "partyId").expect("partyId").to_owned(),
                amount,
                date: date_of(str_field(item, "date").expect("date")),
                note: opt_str_field(item, "note").map(str::to_owned),
            }
        })
        .collect()
}

#[test]
fn journal_chain_vektorlari() {
    let suite = load_suite("journal_chain").expect("journal_chain.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let actual = if let Some(base_id) = opt_str_field(&case.input, "base") {
            // Buzilgan zanjir: asosiy zanjirning xeshlari saqlanadi, bitta yozuv o'zgartiriladi.
            let base = suite
                .cases
                .iter()
                .find(|candidate| candidate.id == base_id)
                .expect("base case");
            let entries = entries_of(&base.input);
            let stored = chain_hashes(&entries);
            let tamper = &case.input["tamper"];
            let index =
                usize::try_from(int_field(tamper, "index").expect("index")).expect("indeks");
            let mut tampered = entries.clone();
            let amount = tampered[index].amount;
            let new_minor = str_field(tamper, "amountMinor")
                .expect("amountMinor")
                .parse::<i64>()
                .expect("butun son");
            tampered[index].amount = Money::new(new_minor, amount.currency());
            match verify_chain(&tampered, &stored) {
                Ok(()) => json!({ "firstBroken": Value::Null }),
                Err(broken) => json!({ "firstBroken": broken.first_broken }),
            }
        } else {
            let entries = entries_of(&case.input);
            json!({ "hashes": chain_hashes(&entries) })
        };
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}

/// Javoblar JSON'ini domen tuzilmasiga o'giradi. Yo'q bo'limlar bo'sh qiymat bo'ladi —
/// to'liqlikni `completeness` aniqlaydi, parser emas.
fn parse_answers(answers: &Value) -> AgreementAnswers {
    let parties = answers["parties"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|item| Party {
            id: str_field(item, "id").expect("id").to_owned(),
            name: str_field(item, "name").expect("name").to_owned(),
            role: str_field(item, "role").expect("role").to_owned(),
            relation: opt_str_field(item, "relation").unwrap_or("").to_owned(),
            is_me: item["isMe"].as_bool().unwrap_or(false),
        })
        .collect();
    let contributions = answers["contributions"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|item| Contribution {
            party_id: str_field(item, "partyId").expect("partyId").to_owned(),
            kind: str_field(item, "kind").expect("kind").to_owned(),
            amount: money_or_none(&item["amount"]),
            description: opt_str_field(item, "description").unwrap_or("").to_owned(),
        })
        .collect();
    let duties = answers["duties"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|item| Duty {
            id: opt_str_field(item, "id").unwrap_or("").to_owned(),
            title: opt_str_field(item, "title").unwrap_or("").to_owned(),
            owner_party_id: opt_str_field(item, "ownerPartyId").map(str::to_owned),
            breach_clause: opt_str_field(item, "breachClause").unwrap_or("").to_owned(),
        })
        .collect();

    let profit_json = &answers["profit"];
    let mut shares = BTreeMap::new();
    for (party, bp) in profit_json["shares"].as_object().into_iter().flatten() {
        shares.insert(party.clone(), bp.as_i64().expect("ulush bp"));
    }
    let profit = ProfitRule {
        shares,
        fixed_amount: money_or_none(&profit_json["fixedAmount"]),
        text: opt_str_field(profit_json, "text").unwrap_or("").to_owned(),
    };

    let custody_json = &answers["custody"];
    let custody = Custody {
        location: opt_str_field(custody_json, "where")
            .unwrap_or("")
            .to_owned(),
        keeper_party_id: opt_str_field(custody_json, "keeperPartyId").map(str::to_owned),
        keeper_device_id: opt_str_field(custody_json, "keeperDeviceId").map(str::to_owned),
        review_every_days: int_field(custody_json, "reviewEveryDays").unwrap_or(0),
    };

    let exit_json = &answers["exit"];
    let exit = ExitClause {
        notice_days: int_field(exit_json, "noticeDays").unwrap_or(0),
        valuation: opt_str_field(exit_json, "valuation")
            .unwrap_or("")
            .to_owned(),
        payout: opt_str_field(exit_json, "payout").unwrap_or("").to_owned(),
        assets: opt_str_field(exit_json, "assets").unwrap_or("").to_owned(),
    };

    let arbiter = if answers["arbiter"].is_null() {
        None
    } else {
        Some(Arbiter {
            name: opt_str_field(&answers["arbiter"], "name")
                .unwrap_or("")
                .to_owned(),
            role: opt_str_field(&answers["arbiter"], "role")
                .unwrap_or("")
                .to_owned(),
        })
    };

    let term_json = &answers["term"];
    let term = Term {
        term_months: int_field(term_json, "termMonths").unwrap_or(0),
        review_date: opt_str_field(term_json, "reviewDate").map(date_of),
    };

    // «Tegishli emas» holatlari: faqat `notApplicable` bo'lsa, sabab olinadi.
    let not_applicable = |key: &str| -> Option<String> {
        let status = &answers["status"][key];
        if status["state"].as_str() == Some("notApplicable") {
            Some(opt_str_field(status, "reason").unwrap_or("").to_owned())
        } else {
            None
        }
    };

    AgreementAnswers {
        profit_not_applicable: not_applicable("profitRule"),
        loss_not_applicable: not_applicable("lossRule"),
        exit_not_applicable: not_applicable("exitClause"),
        parties,
        contributions,
        duties,
        profit,
        loss_text: opt_str_field(answers, "lossText").unwrap_or("").to_owned(),
        custody,
        exit,
        arbiter,
        term,
    }
}

#[test]
fn agreement_completeness_vektorlari() {
    let suite = load_suite("agreement_completeness").expect("agreement_completeness.json");
    let mut failures = Vec::new();
    for case in &suite.cases {
        let kind = AgreementType::from_code(str_field(&case.input, "type").expect("type"))
            .expect("kelishuv turi");
        let has_schedule = case.input["hasSchedule"].as_bool().unwrap_or(false);
        let answers = parse_answers(&case.input["answers"]);
        let result = completeness(kind, &answers, has_schedule);
        let actual = json!({
            "complete": result.complete,
            "missing": result.missing,
            "errors": result.errors,
        });
        check(case, actual, &mut failures);
    }
    finish(&suite, &failures);
}
