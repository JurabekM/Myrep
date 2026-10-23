#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U12: sheriklik kassa daftari — yozuvlar va ilovalar, davrni yopish (buyout ayirmasi bilan),
//! yopilgan davr o'zgarmasligi, tuzatish, zararni keyingi foydadan tiklash (OQ-D1), faqat hisob
//! yurituvchi yozadi, xonadonga faqat ulush tushadi; «Hunardan ishga» va taklif tekshiruvi.

use std::sync::Arc;

use baraka_agreements::{Answer, Arbiter, Custody, Duty, ExitClause, Stroke, Term};
use baraka_app::*;
use chrono::{DateTime, Utc};

fn at(ts: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(ts)
        .unwrap()
        .with_timezone(&Utc)
}

fn app() -> (App, Arc<FixedClock>, String, Vec<MemberDto>) {
    let clock = Arc::new(FixedClock::new(at("2026-12-02T09:00:00+05:00")));
    let app = App::open_in_memory(
        &DbKey::from_bytes([7; 32]),
        "dev-desktop",
        clock.clone(),
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
            household_name: "Nilufarning oilasi".into(),
            device_name: "Kompyuter".into(),
            platform: "linux".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into()],
            members: vec![member("Nilufar", "ADULT"), member("Rustam", "ADULT")],
        })
        .unwrap();
    let uy = h.spaces[0].id.clone();
    (app, clock, uy, h.members)
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

/// Sobir Qodirov tikuv uskunasi va mato puli beradi, Nilufar (shu oila) tikadi — mudoraba 50/50.
fn mudaraba(me_is_worker: bool) -> PartnershipInput {
    PartnershipInput {
        kind: "MUDARABA".into(),
        title: "Tikuvchilik ustaxonasi".into(),
        parties: vec![
            PartnerInput {
                id: "P1".into(),
                full_name: "Sobir Qodirov".into(),
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
                full_name: "Nilufar Karimova".into(),
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

/// Nilufar (shu oila) — mehnat egasi va hisob yurituvchi; shartnoma imzolanib, faollashtirilgan.
fn active(app: &App, uy: &str, members: &[MemberDto], input: PartnershipInput) -> PartnershipDto {
    let p = app.create_partnership(uy, input).unwrap();
    let p = sign_all(app, uy, &p);
    app.acknowledge_not_debt(uy, &p.id).unwrap();
    for m in members {
        app.consent_partnership(uy, &p.id, &m.id).unwrap();
    }
    app.activate_partnership(uy, &p.id).unwrap()
}

fn entry(
    kind: &str,
    cat: Option<&str>,
    amount: &str,
    on: &str,
    note: Option<&str>,
) -> VentureEntryInput {
    VentureEntryInput {
        kind: kind.into(),
        category: cat.map(Into::into),
        amount: amount.into(),
        occurred_on: on.into(),
        note: note.map(Into::into),
        corrects_entry_id: None,
        attachments: Vec::new(),
    }
}

fn png() -> Vec<u8> {
    let mut b = vec![0x89, b'P', b'N', b'G', 0x0D, 0x0A, 0x1A, 0x0A];
    b.extend_from_slice(b"chek-rasmi");
    b
}

fn close(end: &str) -> ClosePeriodInput {
    ClosePeriodInput {
        end_on: end.into(),
        negligence: None,
        buyout_prices: Vec::new(),
        channel: "CARD".into(),
    }
}

#[test]
fn ledger_close_buyout_and_immutability() {
    let (app, _clock, uy, members) = app();
    let p = active(&app, &uy, &members, mudaraba(true));
    let l = app.venture_ledger(&uy, &p.id).unwrap();
    assert!(l.writable, "{:?}", l.read_only_reason);
    assert_eq!(
        (l.start_on.as_str(), l.open.from.as_str()),
        ("2026-11-01", "2026-11-01")
    );
    assert_eq!(l.balances[0].capital.minor, "3000000000");
    assert_eq!(l.keeper_name.as_deref(), Some("Nilufar Karimova"));

    let mut order = entry(
        "INCOME",
        Some("ORDER"),
        "12 000 000",
        "05.11.2026",
        Some("Toʻy koʻylaklari"),
    );
    order.attachments.push(AttachmentInput {
        file_name: "chek.png".into(),
        bytes: png(),
    });
    let l = app.add_venture_entry(&uy, &p.id, order).unwrap();
    assert_eq!(l.entries[0].attachments[0].mime, "image/png");
    let att = l.entries[0].attachments[0].id.clone();
    for e in [
        entry("INCOME", Some("ORDER"), "3 000 000", "20.11.2026", None),
        entry(
            "EXPENSE",
            Some("MATERIAL"),
            "5 000 000",
            "09.11.2026",
            Some("Mato va ip"),
        ),
        entry(
            "EXPENSE",
            Some("WAGE"),
            "2 000 000",
            "30.11.2026",
            Some("Zamira"),
        ),
    ] {
        app.add_venture_entry(&uy, &p.id, e).unwrap();
    }
    let err = |e: VentureEntryInput| app.add_venture_entry(&uy, &p.id, e).unwrap_err().code;
    assert_eq!(
        err(entry("FORCE_MAJEURE", None, "1 000", "10.11.2026", None)),
        "REQUIRED"
    );
    assert_eq!(
        err(entry("INCOME", None, "1 000", "10.12.2026", None)),
        "FUTURE_DATE"
    );
    assert_eq!(
        err(entry("INCOME", None, "1 000", "31.10.2026", None)),
        "BEFORE_START"
    );
    assert_eq!(
        err(entry("EXPENSE", Some("PIZZA"), "1 000", "10.11.2026", None)),
        "INVALID_CATEGORY"
    );
    let mut txt = entry("EXPENSE", None, "1 000", "10.11.2026", None);
    txt.attachments.push(AttachmentInput {
        file_name: "a.txt".into(),
        bytes: b"salom".to_vec(),
    });
    assert_eq!(err(txt), "ATTACHMENT_TYPE_NOT_ALLOWED");

    // Oldindan ko'rish = vektor vp-006 mantig'i: 8 mln foyda, 4 + 4; buyout 1-bosqich (3 mln)
    // xaridor ulushidan ayriladi; kapital 27 / 3 mln.
    let pre = app
        .venture_period_preview(&uy, &p.id, close("30.11.2026"))
        .unwrap();
    assert_eq!(pre.result.minor, "800000000");
    assert_eq!(pre.entries, 4);
    assert_eq!(pre.parties[0].share.minor, "400000000");
    assert_eq!(pre.parties[1].payout.minor, "100000000");
    assert_eq!(pre.parties[0].payout.minor, "700000000");
    assert_eq!(pre.buyout.as_ref().unwrap().paid, [1]);
    assert_eq!(pre.parties[0].capital_after.minor, "2700000000");
    assert_eq!(pre.parties[1].capital_after.minor, "300000000");
    assert_eq!(pre.my_income.minor, "100000000");
    assert!(app.venture_ledger(&uy, &p.id).unwrap().periods.is_empty());

    let l = app
        .close_venture_period(&uy, &p.id, close("30.11.2026"))
        .unwrap();
    assert_eq!(l.periods.len(), 1);
    assert_eq!(l.open.from, "2026-12-01");
    assert_eq!(l.buyout.as_ref().unwrap().paid, 1);
    assert_eq!(l.balances[1].capital.minor, "300000000");
    assert!(l.chain_ok);
    assert!(l.entries.iter().all(|e| e.period_no == Some(1)));
    // Xonadonga faqat ulush tushdi (buyout ayrilgandan keyin 1 mln).
    let nov = app.monthly_summary(&uy, Some("2026-11-15"), None).unwrap();
    assert_eq!(nov.income.minor, "100000000");

    // Yopilgan davr o'zgarmaydi: uning ichidagi sanaga yozuv qo'shilmaydi.
    assert_eq!(
        err(entry("INCOME", None, "1 000", "30.11.2026", None)),
        "PERIOD_CLOSED"
    );
    assert_eq!(
        app.close_venture_period(&uy, &p.id, close("30.11.2026"))
            .unwrap_err()
            .code,
        "INVALID_PERIOD_END"
    );
    // Xato faqat tuzatuvchi yozuv bilan: 12 mln buyurtma aslida 11 mln edi.
    let target = l
        .entries
        .iter()
        .find(|e| e.amount.minor == "1200000000")
        .unwrap()
        .id
        .clone();
    let mut fix = entry(
        "CORRECTION",
        None,
        "11 000 000",
        "01.12.2026",
        Some("Chekda 11 mln"),
    );
    fix.corrects_entry_id = Some(target.clone());
    let l = app.add_venture_entry(&uy, &p.id, fix.clone()).unwrap();
    assert_eq!(l.entries[0].effect.minor, "-100000000");
    assert_eq!(l.entries[0].period_no, None);
    assert!(l.entries.iter().find(|e| e.id == target).unwrap().corrected);
    assert_eq!(l.open.result.minor, "-100000000");
    assert_eq!(err(fix), "NOTHING_TO_CORRECT");

    // Ochiq davr bor ekan, sheriklikni yopib bo'lmaydi.
    assert_eq!(
        app.close_partnership(&uy, &p.id).unwrap_err().code,
        "OPEN_PERIOD_NOT_CLOSED"
    );
    let pdf = app
        .venture_period_pdf(&uy, &p.id, l.periods[0].id.as_deref().unwrap())
        .unwrap();
    assert!(pdf.starts_with(b"%PDF-"));
    let a = app.venture_attachment(&uy, &p.id, &att).unwrap();
    assert_eq!((a.mime.as_str(), a.bytes), ("image/png", png()));
    assert!(app.verify_journal(&uy, &p.agreement_id).unwrap().ok);
}

#[test]
fn loss_is_recovered_from_next_profit_and_only_keeper_writes() {
    let (app, clock, uy, members) = app();
    let mut input = mudaraba(true);
    input.buyout = None;
    let p = active(&app, &uy, &members, input);
    // 1-davr: zarar 2 mln — kapital egasida; xonadonga hech narsa tushmaydi.
    app.add_venture_entry(
        &uy,
        &p.id,
        entry(
            "FORCE_MAJEURE",
            None,
            "2 000 000",
            "15.11.2026",
            Some("Omborni suv bosdi"),
        ),
    )
    .unwrap();
    let l = app
        .close_venture_period(&uy, &p.id, close("30.11.2026"))
        .unwrap();
    let p1 = &l.periods[0];
    assert_eq!(p1.parties[0].share.minor, "-200000000");
    assert_eq!(p1.parties[1].share.minor, "0");
    assert_eq!(l.balances[0].carried_loss.minor, "200000000");
    assert_eq!(l.balances[0].capital.minor, "2800000000");
    // 2-davr: foyda 3 mln — avval 2 mln kapitalga, qolgan 1 mln 50/50 (OQ-D1 misoli).
    clock.set(at("2027-01-02T09:00:00+05:00"));
    app.add_venture_entry(
        &uy,
        &p.id,
        entry("INCOME", Some("ORDER"), "3 000 000", "10.12.2026", None),
    )
    .unwrap();
    let l = app
        .close_venture_period(&uy, &p.id, close("31.12.2026"))
        .unwrap();
    let p2 = &l.periods[0];
    assert_eq!(p2.no, 2);
    assert_eq!(p2.recovered.minor, "200000000");
    assert_eq!(p2.parties[0].share.minor, "50000000");
    assert_eq!(p2.parties[1].payout.minor, "50000000");
    assert_eq!(l.balances[0].carried_loss.minor, "0");
    assert_eq!(l.balances[0].capital.minor, "3000000000");
    // Beparvolik faqat zararda va izoh bilan.
    app.add_venture_entry(
        &uy,
        &p.id,
        entry("EXPENSE", None, "1 000 000", "02.01.2027", None),
    )
    .unwrap();
    let mut neg = close("02.01.2027");
    neg.negligence = Some(NegligenceInput {
        party_id: "P2".into(),
        note: "Mato boshqa ishga ishlatildi".into(),
    });
    let pre = app.venture_period_preview(&uy, &p.id, neg).unwrap();
    assert_eq!(pre.parties[1].liability.minor, "100000000");
    assert_eq!(pre.parties[0].capital_after.minor, "3000000000");

    // Hisobni boshqa tomon yuritsa — bu qurilmada daftar faqat o'qish uchun.
    let mut other = mudaraba(true);
    other.title = "Ikkinchi".into();
    other.buyout = None;
    if let Answer::Answered { value } = &mut other.custody {
        value.keeper_party_id = "P1".into();
    }
    let q = active(&app, &uy, &members, other);
    let l = app.venture_ledger(&uy, &q.id).unwrap();
    assert_eq!(l.read_only_reason.as_deref(), Some("NOT_KEEPER"));
    assert_eq!(
        app.add_venture_entry(
            &uy,
            &q.id,
            entry("INCOME", None, "1 000", "05.12.2026", None)
        )
        .unwrap_err()
        .code,
        "NOT_KEEPER"
    );
}

#[test]
fn ideas_payback_draft_and_offer_check() {
    let (app, _clock, uy, members) = app();
    let skills = app
        .add_skill(
            &uy,
            SkillInput {
                member_id: Some(members[0].id.clone()),
                title: "Tikuvchilik".into(),
                note: None,
            },
        )
        .unwrap();
    assert_eq!(skills[0].member_name.as_deref(), Some("Nilufar"));
    let line = |t: &str, a: &str| CapexLineInput {
        title: t.into(),
        amount: a.into(),
    };
    let sc = |n: &str, i: &str, e: &str| IdeaScenarioInput {
        name: n.into(),
        income: i.into(),
        expense: e.into(),
    };
    let input = VentureIdeaInput {
        title: "Uyda tikuv".into(),
        skill_id: Some(skills[0].id.clone()),
        capex: vec![
            line("Overlok", "5 000 000"),
            line("Bichish stoli", "1 500 000"),
            line("2 oʻram mato", "1 500 000"),
        ],
        scenarios: vec![
            sc("PESSIMISTIC", "4 000 000", "3 000 000"),
            sc("BASE", "6 000 000", "3 500 000"),
            sc("OPTIMISTIC", "8 000 000", "4 000 000"),
        ],
        worker_share_bp: Some(5000),
    };
    let idea = app.create_venture_idea(&uy, input.clone()).unwrap();
    // Vektorlar idea-001/002: CAPEX 8 mln → 8 / 4 / 2 oy; kapital egasi uchun 16 / 7 / 4 oy.
    assert_eq!(idea.capex.minor, "800000000");
    let pay: Vec<Option<u32>> = idea.scenarios.iter().map(|s| s.payback_months).collect();
    assert_eq!(pay, [Some(8), Some(4), Some(2)]);
    let inv: Vec<Option<u32>> = idea
        .scenarios
        .iter()
        .map(|s| s.investor_payback_months)
        .collect();
    assert_eq!(inv, [Some(16), Some(7), Some(4)]);
    assert_eq!(idea.skill_title.as_deref(), Some("Tikuvchilik"));
    let mut bad = input.clone();
    bad.scenarios.pop();
    assert_eq!(
        app.create_venture_idea(&uy, bad).unwrap_err().code,
        "INVALID_SCENARIOS"
    );

    let draft = app
        .draft_partnership_from_idea(
            &uy,
            &idea.id,
            IdeaDraftInput {
                capital_provider_name: "Sobir Qodirov".into(),
                my_name: "Nilufar Karimova".into(),
            },
        )
        .unwrap();
    assert_eq!(draft.status, "DRAFT");
    assert_eq!(draft.capital_total.minor, "800000000");
    assert_eq!(draft.parties[1].profit_share_bp, 5000);
    assert!(draft.parties[1].is_me);
    let ideas = app.venture_ideas(&uy).unwrap();
    assert_eq!(ideas[0].partnership_id.as_deref(), Some(draft.id.as_str()));
    assert_eq!(
        app.draft_partnership_from_idea(
            &uy,
            &idea.id,
            IdeaDraftInput {
                capital_provider_name: "x".into(),
                my_name: "y".into()
            }
        )
        .unwrap_err()
        .code,
        "ALREADY_DRAFTED"
    );

    let ask = |g: &str, l: &str, r: &str, rc: &str, u: &str, w: &str| OfferAnswersInput {
        guaranteed: g.into(),
        loss_shared: l.into(),
        real_activity: r.into(),
        recruitment: rc.into(),
        urgency: u.into(),
        written: w.into(),
        licensed: "YES".into(),
        inspection: "YES".into(),
        exit_easy: "YES".into(),
    };
    let ok = app
        .check_offer(ask("NO", "YES", "YES", "NO", "NO", "YES"))
        .unwrap();
    assert_eq!((ok.verdict.as_str(), ok.flags.len()), ("GREEN", 0));
    let pyramid = app
        .check_offer(ask("YES", "NO", "NO", "YES", "YES", "NO"))
        .unwrap();
    assert_eq!(pyramid.verdict, "RED");
    assert_eq!(pyramid.flags[0].code, "GUARANTEED_PROFIT");
    // «Besh xavf belgisi»: kafolat, yangi odam, ish yo'q, shoshirish — to'rt belgi.
    assert_eq!(pyramid.signs, 4);
    assert_eq!(pyramid.flags.last().unwrap().code, "TWO_SIGNS");
    let unsure = app
        .check_offer(ask("UNKNOWN", "YES", "YES", "NO", "NO", "YES"))
        .unwrap();
    assert_eq!(unsure.verdict, "YELLOW");
    assert_eq!(
        app.check_offer(ask("MAYBE", "YES", "YES", "NO", "NO", "YES"))
            .unwrap_err()
            .code,
        "INVALID_ANSWER"
    );
}
