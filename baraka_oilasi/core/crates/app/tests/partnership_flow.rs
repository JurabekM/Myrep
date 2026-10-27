#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U11: sheriklik — qoidalar, kafolatli daromad taqiqi, versiya va imzolar, darvoza faqat
//! kapital kirituvchiga, kapital qabul qilishda oilaviy rozilik, buyout, shartnoma PDF'i.

use std::sync::Arc;

use baraka_agreements::{Answer, Arbiter, Custody, Duty, ExitClause, Stroke, Term};
use baraka_app::*;
use chrono::{DateTime, Utc};

fn app() -> (App, String, Vec<MemberDto>) {
    let clock = Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339("2026-10-15T09:00:00+05:00")
            .unwrap()
            .with_timezone(&Utc),
    ));
    let app = App::open_in_memory(
        &DbKey::from_bytes([7; 32]),
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
            income_rhythm: None,
            debts_declared: false,
            household_name: "Feruzaning oilasi".into(),
            device_name: "Kompyuter".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![
                member("Feruza", "ADULT"),
                member("Bobur", "ADULT"),
                member("Zarina", "CHILD"),
            ],
        })
        .unwrap();
    let uy = h.spaces[0].id.clone();
    (app, uy, h.members)
}

fn answered<T>(value: T) -> Answer<T> {
    Answer::Answered { value }
}

fn capital(kind: &str, description: &str, amount: &str) -> CapitalItemInput {
    CapitalItemInput {
        kind: kind.into(),
        description: description.into(),
        amount: amount.into(),
    }
}

/// Dilshod Tursunov tikuv uskunasi va mato puli beradi, Feruza (shu oila) tikadi — mudoraba 50/50.
fn mudaraba(me_is_worker: bool) -> PartnershipInput {
    PartnershipInput {
        kind: "MUDARABA".into(),
        title: "Tikuvchilik ustaxonasi".into(),
        parties: vec![
            PartnerInput {
                id: "P1".into(),
                full_name: "Dilshod Tursunov".into(),
                role: "CAPITAL_PROVIDER".into(),
                profit_share_bp: 5000,
                is_me: !me_is_worker,
                capital: vec![
                    capital("EQUIPMENT", "Tikuv mashinasi (2 ta)", "24 000 000"),
                    capital("MONEY", "Mato uchun", "6 000 000"),
                ],
            },
            PartnerInput {
                id: "P2".into(),
                full_name: "Feruza Karimova".into(),
                role: "WORKER".into(),
                profit_share_bp: 5000,
                is_me: me_is_worker,
                capital: vec![],
            },
        ],
        fixed_return: None,
        duties: answered(vec![Duty {
            id: String::new(),
            title: "Buyurtmalarni tikish va topshirish".into(),
            owner_party_id: Some("P2".into()),
            breach_clause: Some("1 kun ichida xabar beradi va oʻrniga yechim topadi".into()),
        }]),
        negligence_clause: Some("Uskunani boshqa ishga berish".into()),
        custody: answered(Custody {
            location: "Alohida karta".into(),
            keeper_party_id: "P2".into(),
            review_every_days: 30,
            keeper_device_id: None,
        }),
        exit_clause: answered(ExitClause {
            notice_days: 30,
            valuation_method: "Bozor narxi, ikki tomon kelishuvi bilan".into(),
            payout_terms: "3 oy ichida".into(),
            asset_split: None,
        }),
        arbiter: answered(Arbiter {
            full_name: "Mahalla oqsoqoli Hamid aka".into(),
            role: Some("qoʻshni".into()),
            party_id: None,
        }),
        term: answered(Term {
            effective_from: "01.11.2026".into(),
            duration_months: Some(12),
            review_date: "01.11.2027".into(),
        }),
        witnesses: vec!["Dilnoza opa".into()],
        buyout: Some(BuyoutTermsInput {
            seller_party_id: "P1".into(),
            buyer_party_id: "P2".into(),
            units: 10,
            units_per_period: 1,
            period_months: 1,
            start: "30.11.2026".into(),
            expected_profit: Some("8 000 000".into()),
        }),
    }
}

fn sig() -> Vec<Stroke> {
    vec![Stroke(vec![[100, 300], [300, 120], [500, 280], [700, 100]])]
}

fn sign_all(app: &App, uy: &str, p: &PartnershipDto) -> PartnershipDto {
    let mut last = p.clone();
    for s in &p.signers {
        last = app
            .sign_partnership(
                uy,
                &p.id,
                SignInput {
                    signer_key: s.key.clone(),
                    strokes: sig(),
                },
            )
            .unwrap();
    }
    last
}

#[test]
fn contract_rules_buyout_and_guaranteed_return() {
    let (app, uy, _) = app();
    let p = app.create_partnership(&uy, mudaraba(true)).unwrap();
    assert_eq!(p.check.answered, 9);
    assert!(p.check.can_sign, "{:?}", p.check);
    assert_eq!(p.check.errors, Vec::<String>::new());
    assert_eq!(p.capital_total.minor, "3000000000");
    assert_eq!(p.parties[0].loss_share.as_deref(), Some("100%"));
    assert_eq!(p.parties[1].loss_share.as_deref(), Some("0%"));
    // Buyout — vektor `buy-001-feruza` bilan bir xil.
    let b = p.buyout.as_ref().unwrap();
    assert_eq!(b.rows.len(), 10);
    assert_eq!(b.end_date.as_deref(), Some("30.08.2027"));
    assert_eq!(b.rows[1].date, "30.12.2026");
    assert_eq!(b.rows[0].payment.minor, "300000000");
    assert_eq!(b.buyer_profit.as_ref().unwrap().minor, "400000000");
    assert_eq!(b.rows[9].buyer_percent, "100%");
    assert!(b.rows.iter().all(|r| !r.exceeds_share));
    assert_eq!(p.template_review, "PENDING");

    // 9-savol javobsiz: bu `missing` da, muddat qoidasi takrorlanmaydi va zarar ulushlari ko'rinadi.
    let mut no_term = mudaraba(true);
    no_term.term = Answer::Unanswered;
    let d = app.create_partnership(&uy, no_term.clone()).unwrap();
    assert_eq!(d.check.missing, [9]);
    assert!(!d.check.errors.iter().any(|e| e == "TERM_REQUIRED"));
    assert_eq!(d.parties[0].loss_share.as_deref(), Some("100%"));
    // «Tegishli emas» deyilsa — muddat qoidasi ishlaydi (sheriklikda muddat majburiy).
    no_term.term = Answer::NotApplicable {
        reason: "muddatsiz".into(),
    };
    let d = app.update_partnership(&uy, &d.id, no_term).unwrap();
    assert!(d.check.errors.iter().any(|e| e == "TERM_REQUIRED"));
    app.delete_partnership(&uy, &d.id).unwrap();

    // Kafolatli daromad — domen darajasida rad etiladi, saqlashga ham yo'l yo'q.
    let mut fixed = mudaraba(true);
    fixed.fixed_return = Some("2 000 000".into());
    let e = app.create_partnership(&uy, fixed).unwrap_err();
    assert_eq!(
        (e.code.as_str(), e.field.as_deref()),
        ("GUARANTEED_RETURN_FORBIDDEN", Some("fixedReturn"))
    );
    assert_eq!(app.partnerships(&uy).unwrap().len(), 1);

    // Qoidaga zid shartlar saqlanadi (usta), lekin imzolash yopiq.
    let mut bad = mudaraba(true);
    bad.parties[0].profit_share_bp = 6000;
    bad.parties[1].capital = vec![capital("MONEY", "naqd", "1 000 000")];
    bad.duties = answered(vec![Duty {
        id: "d1".into(),
        title: "Hamma ishlaydi".into(),
        owner_party_id: Some("hamma".into()),
        breach_clause: None,
    }]);
    let p2 = app.update_partnership(&uy, &p.id, bad).unwrap();
    assert!(!p2.check.can_sign);
    for code in [
        "PROFIT_SHARES_NOT_100",
        "MUDARABA_WORKER_CAPITAL",
        "DUTY_WITHOUT_OWNER",
        "BREACH_CLAUSE_REQUIRED",
    ] {
        assert!(p2.check.errors.iter().any(|x| x == code), "{code}");
    }
    let e = app
        .sign_partnership(
            &uy,
            &p.id,
            SignInput {
                signer_key: "party:P1".into(),
                strokes: sig(),
            },
        )
        .unwrap_err();
    assert_eq!(e.code, "SIGN_BLOCKED");
    // Bo'sh imzo qabul qilinmaydi.
    let ok = app.update_partnership(&uy, &p.id, mudaraba(true)).unwrap();
    let e = app
        .sign_partnership(
            &uy,
            &ok.id,
            SignInput {
                signer_key: "party:P1".into(),
                strokes: vec![Stroke(vec![[1, 1]])],
            },
        )
        .unwrap_err();
    assert_eq!(e.code, "SIGNATURE_EMPTY");
    let pdf = app.partnership_pdf(&uy, &p.id).unwrap();
    assert!(pdf.starts_with(b"%PDF"));
}

#[test]
fn new_version_asks_for_signatures_again() {
    let (app, uy, _) = app();
    let p = app.create_partnership(&uy, mudaraba(true)).unwrap();
    assert_eq!(
        p.signers.iter().map(|s| s.key.as_str()).collect::<Vec<_>>(),
        ["party:P1", "party:P2", "witness:0", "arbiter"]
    );
    let first = app
        .sign_partnership(
            &uy,
            &p.id,
            SignInput {
                signer_key: "party:P1".into(),
                strokes: sig(),
            },
        )
        .unwrap();
    assert_eq!((first.version, first.status.as_str()), (Some(1), "DRAFT"));
    assert_eq!(
        app.sign_partnership(
            &uy,
            &p.id,
            SignInput {
                signer_key: "party:P1".into(),
                strokes: sig(),
            },
        )
        .unwrap_err()
        .code,
        "ALREADY_SIGNED"
    );
    let signed = sign_all(
        &app,
        &uy,
        &PartnershipDto {
            signers: first.signers[1..].to_vec(),
            ..first
        },
    );
    assert_eq!(signed.status, "SIGNED");
    assert_eq!(signed.signed_version, Some(1));
    assert!(signed.all_signed);
    assert!(signed.signers.iter().all(|s| s.svg.is_some()));

    // Matn o'zgardi: qoralamaga qaytadi, imzolar qayta so'raladi, eski versiya dalil sifatida qoladi.
    let mut changed = mudaraba(true);
    changed.parties[0].profit_share_bp = 4000;
    changed.parties[1].profit_share_bp = 6000;
    let p2 = app.update_partnership(&uy, &p.id, changed.clone()).unwrap();
    assert_eq!(p2.status, "DRAFT");
    assert_eq!((p2.version, p2.signed_version), (None, None));
    assert!(p2.signers.iter().all(|s| s.signed_at.is_none()));
    assert!(!p2.all_signed);
    let p3 = sign_all(&app, &uy, &p2);
    assert_eq!((p3.version, p3.signed_version), (Some(2), Some(2)));
    assert_eq!(
        p3.history
            .iter()
            .map(|h| (h.no, h.signed, h.required, h.in_force))
            .collect::<Vec<_>>(),
        [(1, 4, 4, false), (2, 4, 4, true)]
    );
    // Hech narsa o'zgarmasa, versiya ham o'zgarmaydi.
    let same = app.update_partnership(&uy, &p.id, changed).unwrap();
    assert_eq!((same.status.as_str(), same.version), ("SIGNED", Some(2)));
    assert_eq!(
        app.delete_partnership(&uy, &p.id).unwrap_err().code,
        "PARTNERSHIP_HAS_SIGNATURES"
    );
}

#[test]
fn receiving_capital_needs_family_consent_not_gate() {
    let (app, uy, members) = app();
    let p = app.create_partnership(&uy, mudaraba(true)).unwrap();
    assert!(p.me_receives_capital && !p.me_provides_capital);
    assert!(
        p.gate.is_none(),
        "darvoza kapital qabul qiluvchiga qo'llanmaydi"
    );
    assert_eq!(p.activate_blocker.as_deref(), Some("NOT_SIGNED"));
    assert_eq!(
        app.activate_partnership(&uy, &p.id).unwrap_err().code,
        "NOT_SIGNED"
    );
    let p = sign_all(&app, &uy, &p);
    assert_eq!(p.activate_blocker.as_deref(), Some("NOT_DEBT_ACK_REQUIRED"));
    let p = app.acknowledge_not_debt(&uy, &p.id).unwrap();
    assert_eq!(
        p.activate_blocker.as_deref(),
        Some("FAMILY_CONSENT_REQUIRED")
    );
    assert_eq!(
        app.consent_partnership(&uy, &p.id, &members[2].id)
            .unwrap_err()
            .code,
        "NOT_ADULT_MEMBER"
    );
    app.consent_partnership(&uy, &p.id, &members[0].id).unwrap();
    let p = app.consent_partnership(&uy, &p.id, &members[1].id).unwrap();
    assert!(p.consent.as_ref().unwrap().complete && p.can_activate);
    let p = app.activate_partnership(&uy, &p.id).unwrap();
    assert_eq!(p.status, "ACTIVE");
    // Kapital hissalari jurnalga shartnoma xeshi bilan yozildi.
    let j = app.journal(&uy, &p.agreement_id).unwrap();
    assert_eq!(j.len(), 2);
    assert!(j
        .iter()
        .all(|e| e.kind == "CONTRIBUTION" && e.date == "2026-11-01"));
    assert!(app.verify_journal(&uy, &p.agreement_id).unwrap().ok);

    // Faol sheriklikka o'zgartirish: yangi versiya imzolanmaguncha eski versiya kuchda.
    let mut amend = mudaraba(true);
    amend.witnesses.push("Mohira opa".into());
    let a = app.update_partnership(&uy, &p.id, amend).unwrap();
    assert_eq!((a.status.as_str(), a.signed_version), ("ACTIVE", Some(1)));
    assert!(a.amendment_pending);
    let a = sign_all(&app, &uy, &a);
    assert_eq!((a.signed_version, a.amendment_pending), (Some(2), false));
    let mut other = mudaraba(true);
    other.kind = "MUSHARAKA".into();
    assert_eq!(
        app.update_partnership(&uy, &p.id, other).unwrap_err().code,
        "KIND_LOCKED"
    );
    let c = app.close_partnership(&uy, &p.id).unwrap();
    assert_eq!(c.status, "CLOSED");
}

#[test]
fn gate_applies_only_to_capital_provider() {
    let (app, uy, _) = app();
    let p = app.create_partnership(&uy, mudaraba(false)).unwrap();
    assert!(p.me_provides_capital && !p.me_receives_capital);
    assert!(p.consent.is_none());
    let g = p.gate.as_ref().unwrap();
    assert!(!g.open);
    assert_eq!(g.reasons, ["EMERGENCY_FUND_BELOW_TARGET"]);
    assert_eq!(g.coverage_months, None);
    let p = sign_all(&app, &uy, &p);
    assert_eq!(p.activate_blocker.as_deref(), Some("GATE_CLOSED"));
    assert_eq!(
        app.activate_partnership(&uy, &p.id).unwrap_err().code,
        "GATE_CLOSED"
    );

    // Uch oy zarur xarajat 5 mln dan, zaxira pul 20 mln — 4 oy, hali yopiq.
    let cat = app.categories(&uy).unwrap()[0].id.clone();
    for d in ["2026-07-10", "2026-08-10", "2026-09-10"] {
        app.record_expense(
            &uy,
            NewExpenseInput {
                amount: "5 000 000".into(),
                category_id: cat.clone(),
                channel: "CASH".into(),
                member_id: None,
                occurred_on: Some(d.into()),
                necessity: Some("ZARUR".into()),
                obligation_id: None,
                is_gift: false,
                is_ostentation: false,
                funded_by_debt: false,
                note: None,
            },
        )
        .unwrap();
    }
    app.record_initial_balance(&uy, "20 000 000").unwrap();
    let g = app.readiness_gate(&uy).unwrap();
    assert_eq!((g.open, g.coverage_months.as_deref()), (false, Some("4")));
    assert_eq!(g.monthly_essentials.unwrap().minor, "500000000");
    app.deposit_to_vault(&uy, "10 000 000", None).unwrap();
    let g = app.readiness_gate(&uy).unwrap();
    assert!(g.open, "{g:?}");
    let p = app.activate_partnership(&uy, &p.id).unwrap();
    assert_eq!(p.status, "ACTIVE");
}
