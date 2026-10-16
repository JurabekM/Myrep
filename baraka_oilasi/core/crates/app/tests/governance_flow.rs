#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U13: 6-qonun ijrosi — vazifa hodisasi va «bajarilmasa» bandi, ochiq hisob ko'rigi bayonnomasi
//! (zanjir boshi; keyin o'zgartirilgan yozuv aniqlanadi), «katta foyda»da qayta o'qish, nizo
//! taqsimotni bloklaydi, hakam qarori va ish papkasi, yillik yangilash eslatmasi ilova qayta
//! ochilganda ham saqlanadi, oilaviy kelishuvlar va kelishuvlar markazi.

use std::path::Path;
use std::sync::Arc;

use baraka_agreements::{Answer, Arbiter, Custody, Duty, ExitClause, Stroke, Term};
use baraka_app::*;
use baraka_storage::repo::journal;
use baraka_storage::{Database, SpaceScope};
use chrono::{DateTime, Utc};

const KEY: [u8; 32] = [9; 32];

fn at(ts: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(ts)
        .unwrap()
        .with_timezone(&Utc)
}

struct Env {
    app: App,
    clock: Arc<FixedClock>,
    ids: Arc<SequentialIdGen>,
    uy: String,
    household: String,
    members: Vec<MemberDto>,
}

fn open(path: Option<&Path>, clock: Arc<FixedClock>, ids: Arc<SequentialIdGen>) -> App {
    let key = DbKey::from_bytes(KEY);
    match path {
        Some(p) => App::open(p, &key, "dev-desktop", clock, ids),
        None => App::open_in_memory(&key, "dev-desktop", clock, ids),
    }
    .unwrap()
}

fn env(path: Option<&Path>) -> Env {
    let clock = Arc::new(FixedClock::new(at("2026-12-02T09:00:00+05:00")));
    let ids = Arc::new(SequentialIdGen::default());
    let app = open(path, clock.clone(), ids.clone());
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
            members: vec![
                member("Nilufar", "ADULT"),
                member("Rustam", "ADULT"),
                member("Madina", "CHILD"),
            ],
        })
        .unwrap();
    let uy = h.spaces[0].id.clone();
    let adults = h
        .members
        .iter()
        .filter(|m| m.role == "ADULT")
        .cloned()
        .collect();
    Env {
        app,
        clock,
        ids,
        uy,
        household: h.id,
        members: adults,
    }
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

/// Sobir hoji tikuv uskunasi va mato puli beradi, Nilufar (shu oila) tikadi — mudoraba 50/50.
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

fn close(end: &str) -> ClosePeriodInput {
    ClosePeriodInput {
        end_on: end.into(),
        negligence: None,
        buyout_prices: Vec::new(),
        channel: "CARD".into(),
    }
}

fn ack(party: &str, verdict: &str, note: Option<&str>) -> ReviewAckInput {
    ReviewAckInput {
        party_id: party.into(),
        verdict: verdict.into(),
        note: note.map(Into::into),
    }
}

fn scope(e: &Env) -> SpaceScope {
    SpaceScope {
        household_id: e.household.clone(),
        space_id: e.uy.clone(),
    }
}

/// Jurnaldagi birinchi `REVENUE` yozuvi summasini o'zgartiradi (triggerni o'chirib — «buzg'unchi»).
/// `forge` bo'lsa, butun zanjir xeshlari ham qayta hisoblanadi (izsiz soxtalashtirish urinishi).
fn tamper(path: &Path, s: &SpaceScope, agreement_id: &str, forge: bool) {
    let db = Database::open(path, &DbKey::from_bytes(KEY)).unwrap();
    let mut list = db.read(|c| journal::list(c, s, agreement_id)).unwrap();
    let i = list
        .iter()
        .position(|x| x.entry.kind.as_str() == "REVENUE")
        .unwrap();
    let amount = list[i].entry.amount.as_mut().unwrap();
    amount.minor += 100_000_000;
    let entries: Vec<_> = list.iter().map(|x| x.entry.clone()).collect();
    let hashes = baraka_journal::compute_chain(&entries).unwrap();
    db.write(|tx| {
        tx.execute_batch("DROP TRIGGER IF EXISTS journal_entries_no_update")?;
        tx.execute(
            "UPDATE journal_entries SET amount_minor = ?1 WHERE id = ?2",
            (
                list[i].entry.amount.as_ref().unwrap().minor,
                &list[i].entry.id,
            ),
        )?;
        if forge {
            let mut prev = baraka_journal::GENESIS_HASH.to_string();
            for (x, h) in list.iter().zip(&hashes) {
                tx.execute(
                    "UPDATE journal_entries SET prev_hash = ?1, hash = ?2 WHERE id = ?3",
                    (&prev, h, &x.entry.id),
                )?;
                prev.clone_from(h);
            }
        }
        Ok(())
    })
    .unwrap();
}

#[test]
fn incidents_review_protocol_and_tamper_detection() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("baraka.db");
    let e = env(Some(&path));
    let (app, uy) = (&e.app, e.uy.as_str());
    let p = active(app, uy, &e.members, mudaraba(true));

    let g = app.governance(uy, &p.id).unwrap();
    assert!(g.writable && !g.in_dispute);
    assert_eq!(g.duties.len(), 1);
    assert_eq!(g.duties[0].owner_name.as_deref(), Some("Nilufar Karimova"));
    assert_eq!(g.review_every_days, 30);
    // 01.11 + 30 kun = 01.12; bugun 02.12 — ko'rik muddati o'tgan.
    assert_eq!(g.next_review_due.as_deref(), Some("2026-12-01"));
    let r = g.review_reminder.as_ref().unwrap();
    assert_eq!(
        (r.kind.as_str(), r.state.as_str(), r.days),
        ("REVIEW", "OVERDUE", 1)
    );
    assert!(g.renewal_reminder.is_none());
    assert_eq!(g.review_date.as_deref(), Some("2027-11-01"));

    // «Bajara olmayapman» — 3-banddagi qoida darhol ko'rinadi, hodisa jurnalga yoziladi.
    let incident = |duty: &str, on: &str| IncidentInput {
        duty_id: duty.into(),
        party_id: "P2".into(),
        reason: "Kasal boʻldim, 3 kun ishlay olmayman".into(),
        occurred_on: on.into(),
        proposed_solution: Some("Zamira oʻrnimga tikadi".into()),
    };
    let err = |i: IncidentInput| app.report_duty_incident(uy, &p.id, i).unwrap_err().code;
    assert_eq!(err(incident("d9", "01.12.2026")), "UNKNOWN_DUTY");
    assert_eq!(err(incident("d1", "03.12.2026")), "FUTURE_DATE");
    let g = app
        .report_duty_incident(uy, &p.id, incident("d1", "01.12.2026"))
        .unwrap();
    let i = &g.incidents[0];
    assert_eq!(
        i.breach_clause.as_deref(),
        Some("1 kun ichida xabar beradi va oʻrniga yechim topadi")
    );
    assert!(!i.hash_code.is_empty() && i.resolved_on.is_none());
    let journal = app.journal(uy, &p.agreement_id).unwrap();
    assert!(journal.iter().any(|j| j.kind == "DUTY_INCIDENT"));

    for x in [
        entry("INCOME", Some("ORDER"), "12 000 000", "05.11.2026", None),
        entry(
            "EXPENSE",
            Some("MATERIAL"),
            "5 000 000",
            "09.11.2026",
            Some("Mato"),
        ),
    ] {
        app.add_venture_entry(uy, &p.id, x).unwrap();
    }

    // Ko'rik qoralamasi: oraliq, raqamlar, ochiq hodisalar, zanjir.
    let d = app.review_draft(uy, &p.id, "30.11.2026").unwrap();
    assert_eq!((d.no, d.from_on.as_str()), (1, "2026-11-01"));
    assert_eq!(d.totals.entries, 2);
    assert_eq!(d.totals.result.minor, "700000000");
    assert!(d.open_incidents.is_empty() && d.chain_ok);
    let d = app.review_draft(uy, &p.id, "01.12.2026").unwrap();
    assert_eq!(d.open_incidents.len(), 1);
    assert_eq!(
        app.review_draft(uy, &p.id, "03.12.2026").unwrap_err().code,
        "FUTURE_DATE"
    );
    // Bo'sh sana — yadro soati bo'yicha bugun.
    assert_eq!(app.review_draft(uy, &p.id, "").unwrap().to_on, "2026-12-02");

    let hold = |acks: Vec<ReviewAckInput>| HoldReviewInput {
        to_on: "01.12.2026".into(),
        reason: "SCHEDULED".into(),
        acks,
    };
    let herr = |i: HoldReviewInput| app.hold_review(uy, &p.id, i).unwrap_err().code;
    assert_eq!(
        herr(hold(vec![ack("P1", "AGREE", None)])),
        "ACKS_INCOMPLETE"
    );
    assert_eq!(
        herr(hold(vec![
            ack("P1", "AGREE", None),
            ack("P2", "OBJECT", None)
        ])),
        "OBJECTION_NOTE_REQUIRED"
    );
    assert_eq!(
        herr(hold(vec![
            ack("P1", "AGREE", None),
            ack("P1", "AGREE", None)
        ])),
        "DUPLICATE_ACK"
    );
    let g = app
        .hold_review(
            uy,
            &p.id,
            hold(vec![
                ack("P1", "AGREE", None),
                ack("P2", "OBJECT", Some("Mato narxi chekdan yuqori yozilgan")),
            ]),
        )
        .unwrap();
    let rv = &g.reviews[0];
    assert_eq!(
        (rv.no, rv.integrity.as_str(), rv.entries_after),
        (1, "INTACT", 0)
    );
    assert_eq!(rv.open_incidents, 1);
    assert_eq!(rv.acks[1].verdict, "OBJECT");
    // Keyingi ko'rik: 02.12 + 30 = 01.01.2027 — eslatma hali yo'q.
    assert_eq!(g.next_review_due.as_deref(), Some("2027-01-01"));
    assert!(g.review_reminder.is_none());
    let journal = app.journal(uy, &p.agreement_id).unwrap();
    assert_eq!(journal.iter().filter(|j| j.kind == "REVIEW_ACK").count(), 2);
    let review_id = rv.id.clone();
    let pdf = app.review_pdf(uy, &p.id, &review_id).unwrap();
    assert!(pdf.starts_with(b"%PDF-"));

    // Ko'rilgan sanaga yangi yozuv emas, faqat tuzatish.
    assert_eq!(
        app.add_venture_entry(
            uy,
            &p.id,
            entry("INCOME", None, "1 000", "30.11.2026", None)
        )
        .unwrap_err()
        .code,
        "PERIOD_REVIEWED"
    );
    let l = app.venture_ledger(uy, &p.id).unwrap();
    let expense = l
        .entries
        .iter()
        .find(|x| x.kind == "EXPENSE")
        .unwrap()
        .id
        .clone();
    let mut fix = entry(
        "CORRECTION",
        None,
        "6 000 000",
        "02.12.2026",
        Some("Chek boʻyicha"),
    );
    fix.corrects_entry_id = Some(expense);
    app.add_venture_entry(uy, &p.id, fix).unwrap();
    let g = app.governance(uy, &p.id).unwrap();
    assert_eq!(
        (g.reviews[0].integrity.as_str(), g.reviews[0].entries_after),
        ("INTACT", 1)
    );

    // Hodisa yechimi — alohida yozuv.
    let iid = g.incidents[0].id.clone();
    let g = app
        .resolve_duty_incident(
            uy,
            &p.id,
            &iid,
            "Zamira 3 kun tikdi, buyurtma vaqtida topshirildi",
        )
        .unwrap();
    assert_eq!(g.incidents[0].resolved_on.as_deref(), Some("2026-12-02"));
    assert_eq!(
        app.resolve_duty_incident(uy, &p.id, &iid, "yana")
            .unwrap_err()
            .code,
        "ALREADY_RESOLVED"
    );

    // O'tmishdagi yozuv bazada o'zgartirildi — bayonnoma buni aniqlaydi.
    let (ids, clock, s) = (e.ids.clone(), e.clock.clone(), scope(&e));
    drop(e);
    tamper(&path, &s, &p.agreement_id, false);
    let app = open(Some(&path), clock.clone(), ids.clone());
    let g = app.governance(&s.space_id, &p.id).unwrap();
    assert_eq!(g.reviews[0].integrity, "CHAIN_BROKEN");
    assert!(!app.venture_ledger(&s.space_id, &p.id).unwrap().chain_ok);
    drop(app);
    // Xeshlar ham qayta hisoblangan: zanjir «butun», lekin bayonnomadagi kod mos kelmaydi.
    tamper(&path, &s, &p.agreement_id, true);
    let app = open(Some(&path), clock, ids);
    let g = app.governance(&s.space_id, &p.id).unwrap();
    assert!(app.venture_ledger(&s.space_id, &p.id).unwrap().chain_ok);
    assert_eq!(g.reviews[0].integrity, "HEAD_MISMATCH");
}

#[test]
fn profit_spike_rereads_and_dispute_block_distribution() {
    let e = env(None);
    let (app, uy) = (&e.app, e.uy.as_str());
    let p = active(app, uy, &e.members, mudaraba(true));
    // Reja 8 mln (buyout'dagi kutilgan foyda), natija 18 mln ≥ 150% — «katta foyda».
    for x in [
        entry("INCOME", Some("ORDER"), "20 000 000", "05.11.2026", None),
        entry("EXPENSE", Some("MATERIAL"), "2 000 000", "09.11.2026", None),
    ] {
        app.add_venture_entry(uy, &p.id, x).unwrap();
    }
    let pv = app
        .venture_period_preview(uy, &p.id, close("30.11.2026"))
        .unwrap();
    assert!(pv.profit_spike && pv.spike_rereads.is_empty());
    let cerr = || {
        app.close_venture_period(uy, &p.id, close("30.11.2026"))
            .unwrap_err()
            .code
    };
    assert_eq!(cerr(), "PROFIT_SPIKE_ACK_REQUIRED");
    app.acknowledge_spike_reread(uy, &p.id, "P1").unwrap();
    app.acknowledge_spike_reread(uy, &p.id, "P1").unwrap();
    let pv = app
        .venture_period_preview(uy, &p.id, close("30.11.2026"))
        .unwrap();
    assert_eq!(pv.spike_rereads, vec!["P1".to_string()]);
    assert_eq!(cerr(), "PROFIT_SPIKE_ACK_REQUIRED");
    assert_eq!(
        app.acknowledge_spike_reread(uy, &p.id, "P7")
            .unwrap_err()
            .code,
        "UNKNOWN_PARTY"
    );
    app.acknowledge_spike_reread(uy, &p.id, "P2").unwrap();

    // Nizo ochildi: taqsimot bloklanadi, yozuvlar davom etadi.
    let dispute = |subject: &str| OpenDisputeInput {
        subject: subject.into(),
        clauses: vec![5, 4, 5],
        opened_by: "P1".into(),
        claims: vec![DisputeClaimInput {
            party_id: "P1".into(),
            claim: "Mato xarajati chekdan koʻp yozilgan".into(),
        }],
    };
    let mut bad = dispute("x");
    bad.clauses = vec![10];
    assert_eq!(
        app.open_partnership_dispute(uy, &p.id, bad)
            .unwrap_err()
            .code,
        "INVALID_CLAUSE"
    );
    let g = app
        .open_partnership_dispute(uy, &p.id, dispute("Xarajatlar boʻyicha kelishmovchilik"))
        .unwrap();
    assert!(g.in_dispute);
    assert_eq!(g.disputes[0].clauses, vec![4, 5]);
    assert_eq!(cerr(), "IN_DISPUTE");
    assert!(app.venture_ledger(uy, &p.id).unwrap().in_dispute);
    assert!(app.partnership(uy, &p.id).unwrap().in_dispute);
    assert!(app.partnerships(uy).unwrap()[0].in_dispute);
    app.add_venture_entry(
        uy,
        &p.id,
        entry("INCOME", None, "500 000", "01.12.2026", None),
    )
    .unwrap();
    let center = app.agreements_center(uy).unwrap();
    let c = center.iter().find(|a| a.ref_id == p.id).unwrap();
    assert_eq!((c.status.as_str(), c.open_disputes), ("IN_DISPUTE", 1));
    assert_eq!(
        app.open_partnership_dispute(uy, &p.id, dispute("Yana"))
            .unwrap_err()
            .code,
        "DISPUTE_ALREADY_OPEN"
    );
    let did = g.disputes[0].id.clone();
    let claim = |party: &str| DisputeClaimInput {
        party_id: party.into(),
        claim: "Chek bor, narx bozor narxida".into(),
    };
    let g = app.add_dispute_claim(uy, &p.id, &did, claim("P2")).unwrap();
    assert_eq!(g.disputes[0].claims.len(), 2);
    assert_eq!(
        app.add_dispute_claim(uy, &p.id, &did, claim("P2"))
            .unwrap_err()
            .code,
        "DUPLICATE_CLAIM"
    );
    let folder = app.dispute_folder_pdf(uy, &p.id, &did).unwrap();
    assert!(folder.starts_with(b"%PDF-"));

    // Hakam qarori: nizo yopiladi, taqsimot yana mumkin.
    let decision = |outcome: &str| DecisionInput {
        decided_on: "02.12.2026".into(),
        decision: "Xarajat chek boʻyicha qoladi; keyingi oydan chek har yozuvga ilova qilinadi."
            .into(),
        outcome: outcome.into(),
    };
    assert_eq!(
        app.record_arbiter_decision(uy, &p.id, &did, decision("MAYBE"))
            .unwrap_err()
            .code,
        "INVALID_OUTCOME"
    );
    let g = app
        .record_arbiter_decision(uy, &p.id, &did, decision("RESUME"))
        .unwrap();
    assert!(!g.in_dispute && !g.disputes[0].open);
    assert_eq!(
        g.disputes[0].decision.as_ref().unwrap().arbiter_name,
        "Mahalla oqsoqoli Hamid aka"
    );
    assert_eq!(
        app.record_arbiter_decision(uy, &p.id, &did, decision("RESUME"))
            .unwrap_err()
            .code,
        "DISPUTE_DECIDED"
    );
    let center = app.agreements_center(uy).unwrap();
    assert_eq!(
        center.iter().find(|a| a.ref_id == p.id).unwrap().status,
        "ACTIVE"
    );
    let l = app
        .close_venture_period(uy, &p.id, close("30.11.2026"))
        .unwrap();
    assert!(l.periods[0].profit_spike);
    assert_eq!(l.periods[0].spike_rereads.len(), 2);
    // Keyingi davr uchun qayta o'qish yangidan boshlanadi.
    let pv = app
        .venture_period_preview(uy, &p.id, close("01.12.2026"))
        .unwrap();
    assert!(pv.spike_rereads.is_empty());
    assert!(app
        .dispute_folder_pdf(uy, &p.id, &did)
        .unwrap()
        .starts_with(b"%PDF-"));
}

#[test]
fn renewal_reminder_survives_reopen_and_unchanged_renewal_is_a_version() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("baraka.db");
    let e = env(Some(&path));
    let p = active(&e.app, &e.uy, &e.members, mudaraba(true));
    // 10.10.2027: «reviewDate» (01.11.2027) gacha 22 kun — 30 kunlik oyna ichida.
    e.clock.set(at("2027-10-10T09:00:00+05:00"));
    let renewal = |app: &App, uy: &str| {
        app.agreement_reminders(uy)
            .unwrap()
            .into_iter()
            .find(|r| r.kind == "RENEWAL")
    };
    let r = renewal(&e.app, &e.uy).unwrap();
    assert_eq!(
        (r.state.as_str(), r.days, r.ref_id.as_str()),
        ("UPCOMING", 22, p.id.as_str())
    );
    assert_eq!(r.due_on, "2027-11-01");

    // Ilova yopilib, qayta ochildi — eslatma saqlangan sanalardan qayta hisoblanadi.
    let (ids, clock, uy, members) = (
        e.ids.clone(),
        e.clock.clone(),
        e.uy.clone(),
        e.members.clone(),
    );
    drop(e);
    let app = open(Some(&path), clock, ids);
    assert!(renewal(&app, &uy).is_some());
    let center = app.agreements_center(&uy).unwrap();
    let c = center.iter().find(|a| a.ref_id == p.id).unwrap();
    assert!(c.reminder.is_some());

    // «O'zgarishsiz tasdiqlash»: reviewDate +1 yil, hamma qayta imzolaydi — yangi versiya.
    let d = app.renew_partnership(&uy, &p.id).unwrap();
    assert!(d.amendment_pending);
    match &d.term {
        Answer::Answered { value } => assert_eq!(value.review_date, "2028-11-01"),
        other => panic!("{other:?}"),
    }
    assert!(renewal(&app, &uy).is_some(), "eski versiya hali kuchda");
    let d = sign_all(&app, &uy, &d);
    let last = d.history.last().unwrap();
    assert_eq!((last.no, last.in_force), (2, true));
    assert_eq!(last.change_note.as_deref(), Some("RENEWED_UNCHANGED"));
    assert!(d.history[0].change_note.is_none());
    assert!(renewal(&app, &uy).is_none());
    assert_eq!(
        app.governance(&uy, &p.id).unwrap().review_date.as_deref(),
        Some("2028-11-01")
    );
    let _ = members;
}

#[test]
fn family_agreements_need_every_adult() {
    let e = env(None);
    let (app, uy) = (&e.app, e.uy.as_str());
    let input = |items: Vec<&str>| FamilyAgreementInput {
        template_key: "CHORES".into(),
        title: "Uy yumushlari".into(),
        items: items.into_iter().map(Into::into).collect(),
        review_date: Some("04.12.2026".into()),
    };
    let mut bad = input(vec!["x"]);
    bad.template_key = "PARTY".into();
    assert_eq!(
        app.create_family_agreement(uy, bad).unwrap_err().code,
        "INVALID_TEMPLATE"
    );
    assert_eq!(
        app.create_family_agreement(uy, input(vec!["  "]))
            .unwrap_err()
            .code,
        "REQUIRED"
    );
    let f = app
        .create_family_agreement(
            uy,
            input(vec![
                "Idish — navbat bilan",
                "Shanba kuni hamma birga tozalaydi",
            ]),
        )
        .unwrap();
    assert_eq!((f.status.as_str(), f.adults.len()), ("DRAFT", 2));
    let (a, b) = (e.members[0].id.clone(), e.members[1].id.clone());
    let f = app.confirm_family_agreement(uy, &f.id, &a).unwrap();
    assert_eq!(f.status, "DRAFT");
    assert_eq!(
        app.confirm_family_agreement(uy, &f.id, "nobody")
            .unwrap_err()
            .code,
        "NOT_ADULT_MEMBER"
    );
    let f = app.confirm_family_agreement(uy, &f.id, &b).unwrap();
    assert_eq!(f.status, "ACTIVE");
    assert!(f.adults.iter().all(|x| x.agreed_on.is_some()));

    // Matn o'zgardi — tasdiqlar yangi matnga o'tmaydi.
    let f = app
        .update_family_agreement(uy, &f.id, input(vec!["Idish — navbat bilan"]))
        .unwrap();
    assert_eq!(f.status, "DRAFT");
    assert!(f.adults.iter().all(|x| x.agreed_on.is_none()));

    let r = app.agreement_reminders(uy).unwrap();
    let r = r.iter().find(|r| r.agreement_type == "FAMILY").unwrap();
    assert_eq!((r.state.as_str(), r.days), ("UPCOMING", 2));
    let center = app.agreements_center(uy).unwrap();
    let c = center
        .iter()
        .find(|c| c.agreement_type == "FAMILY")
        .unwrap();
    assert_eq!(
        (c.ref_id.as_str(), c.next_review.as_deref()),
        (f.id.as_str(), Some("2026-12-04"))
    );
    assert_eq!(app.family_agreements(uy).unwrap().len(), 1);
    app.delete_family_agreement(uy, &f.id).unwrap();
    assert!(app.family_agreements(uy).unwrap().is_empty());
}
