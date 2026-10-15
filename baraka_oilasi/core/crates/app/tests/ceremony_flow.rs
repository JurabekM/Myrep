#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U10: marosim rejalovchisi — stsenariylar, qarzsiz o'tkazish muhokamasi, tasdiqlash qulfi.

use std::sync::Arc;

use baraka_app::*;
use chrono::{DateTime, Utc};

fn app() -> (App, String, Vec<MemberDto>) {
    let clock = Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339("2026-10-15T09:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    ));
    let app = App::open_in_memory(
        &DbKey::from_bytes([6; 32]),
        "dev-desktop",
        clock,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let member = |n: &str, r: &str| NewMemberInput {
        display_name: n.into(),
        role: r.into(),
    };
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Karim akaning oilasi".into(),
            device_name: "Kompyuter".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![
                member("Karim", "ADULT"),
                member("Gulnora", "ADULT"),
                member("Sanjar", "CHILD"),
            ],
        })
        .unwrap();
    let uy = h.spaces[0].id.clone();
    (app, uy, h.members)
}

fn line(title: &str, kind: &str, amount: &str, source: &str) -> NewCeremonyLineInput {
    NewCeremonyLineInput {
        title: title.into(),
        kind: kind.into(),
        amount: amount.into(),
        source: source.into(),
    }
}

fn scenario(name: &str, guests: i32) -> ScenarioInput {
    ScenarioInput {
        name: name.into(),
        guests,
        copy_from: None,
    }
}

/// Vektor `cer-001-karim` bilan bir xil uchta stsenariy.
fn karim(app: &App, uy: &str) -> CeremonyDto {
    let c = app
        .create_ceremony(
            uy,
            NewCeremonyInput {
                kind: "TOY".into(),
                title: "Sanjarning toʻyi".into(),
                planned_on: Some("20.05.2027".into()),
                scenario_name: "3 kunlik, 200 kishi".into(),
                guests: 200,
            },
        )
        .unwrap();
    let s1 = c.scenarios[0].id.clone();
    for l in [
        line("Osh va dasturxon", "PER_GUEST", "250 000", "SAVINGS"),
        line("Sarpo", "ONE_OFF", "15 000 000", "FAMILY"),
        line("Toʻyonadan", "ONE_OFF", "8 000 000", "EXPECTED_GIFTS"),
        line("Xonanda va zal", "ONE_OFF", "20 000 000", "DEBT"),
    ] {
        app.add_ceremony_line(uy, &c.id, &s1, l).unwrap();
    }
    let c = app
        .add_scenario(uy, &c.id, scenario("1 kunlik, 100 kishi", 100))
        .unwrap();
    let s2 = c.scenarios[1].id.clone();
    for l in [
        line("Osh va dasturxon", "PER_GUEST", "250 000", "SAVINGS"),
        line("Sarpo", "ONE_OFF", "6 000 000", "FAMILY"),
        line("Toʻyonadan", "ONE_OFF", "4 000 000", "EXPECTED_GIFTS"),
    ] {
        app.add_ceremony_line(uy, &c.id, &s2, l).unwrap();
    }
    let c = app
        .add_scenario(uy, &c.id, scenario("Oʻrtacha, 150 kishi", 150))
        .unwrap();
    let s3 = c.scenarios[2].id.clone();
    for l in [
        line("Osh va dasturxon", "PER_GUEST", "250 000", "SAVINGS"),
        line("Sarpo", "ONE_OFF", "10 000 000", "FAMILY"),
        line("Xonanda", "ONE_OFF", "5 000 000", "DEBT"),
    ] {
        app.add_ceremony_line(uy, &c.id, &s3, l).unwrap();
    }
    app.update_ceremony(
        uy,
        &c.id,
        CeremonyUpdateInput {
            title: "Sanjarning toʻyi".into(),
            planned_on: Some("20.05.2027".into()),
            monthly_capacity: Some("2 400 000".into()),
        },
    )
    .unwrap()
}

#[test]
fn scenarios_match_vectors_and_u9_simulator() {
    let (app, uy, _) = app();
    app.add_goal(
        &uy,
        NewGoalInput {
            title: "Kontrakt".into(),
            target: "12 000 000".into(),
            currency: "UZS".into(),
        },
    )
    .unwrap();
    let c = karim(&app, &uy);
    assert_eq!(c.capacity_source, "MANUAL");
    let [a, b, m] = [&c.scenarios[0], &c.scenarios[1], &c.scenarios[2]];
    assert_eq!(a.total.minor, "9300000000");
    assert_eq!(a.by_source.debt.minor, "2000000000");
    assert_eq!(
        (a.payoff_months, a.payoff_date.as_deref()),
        (Some(9), Some("2028-01-01"))
    );
    assert_eq!(b.saved_vs_max.minor, "5800000000");
    assert!(!b.has_debt && b.payoff_months == Some(0));
    assert_eq!(b.goal_equivalents[0].percent, "483,33");
    assert_eq!(m.payoff_months, Some(3));
    assert!(c.gifts_warning);
    assert_eq!(
        app.add_scenario(&uy, &c.id, scenario("4-chi", 10))
            .unwrap_err()
            .code,
        "TOO_MANY_SCENARIOS"
    );
    // Ajratma 0 — qarz yopilmaydi.
    let c0 = app
        .update_ceremony(
            &uy,
            &c.id,
            CeremonyUpdateInput {
                title: c.title.clone(),
                planned_on: c.planned_on.clone(),
                monthly_capacity: Some("0".into()),
            },
        )
        .unwrap();
    assert!(c0.scenarios[0].not_repayable);
    let pdf = app.ceremony_estimate_pdf(&uy, &c.id).unwrap();
    assert!(pdf.starts_with(b"%PDF"));
}

#[test]
fn debt_scenario_cannot_be_confirmed_without_family_discussion() {
    let (app, uy, members) = app();
    let c = karim(&app, &uy);
    let id = c.id.clone();
    let (karim_id, gulnora_id, sanjar_id) = (
        members[0].id.clone(),
        members[1].id.clone(),
        members[2].id.clone(),
    );
    assert_eq!(c.confirm_blocker.as_deref(), Some("DISCUSSION_REQUIRED"));
    assert!(c.discussion.required);
    assert_eq!(
        app.confirm_ceremony(&uy, &id).unwrap_err().code,
        "DISCUSSION_REQUIRED"
    );
    assert_eq!(
        app.agree_discussion(&uy, &id, &karim_id).unwrap_err().code,
        "DISCUSSION_EMPTY"
    );
    app.save_discussion(
        &uy,
        &id,
        vec![DiscussionAnswerDto {
            key: "guests".into(),
            note: "200 dan 150 ga tushirsa boʻladi".into(),
        }],
    )
    .unwrap();
    let c = app.agree_discussion(&uy, &id, &karim_id).unwrap();
    assert_eq!(c.status, "DRAFT");
    assert_eq!(
        app.agree_discussion(&uy, &id, &sanjar_id).unwrap_err().code,
        "NOT_ADULT_MEMBER"
    );
    let c = app.agree_discussion(&uy, &id, &gulnora_id).unwrap();
    assert_eq!(c.status, "DISCUSSED");
    assert!(c.can_confirm);

    // Muhokamadan keyin reja o'zgarsa — roziliklar bekor, yana qoralama.
    let s1 = c.scenarios[0].id.clone();
    let c = app
        .add_ceremony_line(
            &uy,
            &id,
            &s1,
            line("Mashina", "ONE_OFF", "3 000 000", "DEBT"),
        )
        .unwrap();
    assert_eq!(c.status, "DRAFT");
    assert!(c.discussion.adults.iter().all(|a| a.agreed_on.is_none()));
    assert_eq!(
        c.discussion.answers[0].note,
        "200 dan 150 ga tushirsa boʻladi"
    );

    app.agree_discussion(&uy, &id, &karim_id).unwrap();
    app.agree_discussion(&uy, &id, &gulnora_id).unwrap();
    let c = app.confirm_ceremony(&uy, &id).unwrap();
    assert_eq!(c.status, "CONFIRMED");
    assert_eq!(
        app.add_ceremony_line(&uy, &id, &s1, line("x", "ONE_OFF", "1", "SAVINGS"))
            .unwrap_err()
            .code,
        "CEREMONY_LOCKED"
    );
    let c = app.reopen_ceremony(&uy, &id).unwrap();
    assert_eq!(c.status, "DRAFT");

    // Qarzsiz stsenariy muhokamasiz tasdiqlanadi.
    let s2 = c.scenarios[1].id.clone();
    let c = app.select_scenario(&uy, &id, &s2).unwrap();
    assert!(!c.discussion.required && c.can_confirm);
    assert_eq!(app.confirm_ceremony(&uy, &id).unwrap().status, "CONFIRMED");
    assert_eq!(
        app.ceremonies(&uy).unwrap()[0]
            .total
            .as_ref()
            .unwrap()
            .minor,
        "3500000000"
    );
}

#[test]
fn gifts_go_to_young_family_goal() {
    let (app, uy, _) = app();
    let g = app
        .add_goal(
            &uy,
            NewGoalInput {
                title: "Yosh oila uchun uy".into(),
                target: "20 000 000".into(),
                currency: "UZS".into(),
            },
        )
        .unwrap();
    let g = app
        .add_goal_contribution(
            &uy,
            &g.id,
            NewGoalContributionInput {
                contributor: "Hasan aka".into(),
                amount: "1 500 000".into(),
                given_on: None,
            },
        )
        .unwrap();
    assert_eq!(g.collected.minor, "150000000");
    assert_eq!(g.collected_percent, "7,5");
    assert_eq!(g.contributions[0].given_on, "2026-10-15");
}
