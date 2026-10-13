#![allow(clippy::unwrap_used, clippy::expect_used)]

//! D8A: kelishuv dvigateli, jurnal va eski ma'lumotni ko'chirish (SPEC 2F.1–2F.3, 2F.6, 2F.9).

use std::cell::Cell;

use domain::{
    date_from_str, Agreement, AgreementDoc, AgreementSignKind, AgreementStatus, AgreementType,
    Answer, Arbiter, CapitalKind, Clock, Contribution, Custody, Date, Duty, ExitClause, IdGen,
    JournalKind, LossRule, OffsetDateTime, PartnershipKind, Party, PartyRole, ProfitRule,
    ProfitShare, Questions, ReportPeriod, SubjectKind, Term,
};
use money::{Currency, Money};
use services::{
    agreements::{self, AgreementSigner, NewAgreement},
    journal, members,
    partnerships::{self, NewCapital, NewPartnership, NewParty},
    setup, Ctx, Env, ServiceError,
};
use storage::{repo, Database};

struct TestClock(Cell<OffsetDateTime>);
impl Clock for TestClock {
    fn now(&self) -> OffsetDateTime {
        self.0.get()
    }
}

struct Seq(Cell<u64>);
impl IdGen for Seq {
    fn new_id(&self) -> String {
        let n = self.0.get();
        self.0.set(n + 1);
        format!("00000000-0000-7000-8000-{n:012}")
    }
}

macro_rules! env {
    ($w:expr) => {
        Env {
            clock: &$w.clock,
            ids: &$w.ids,
            device_id: "dev",
        }
    };
}

struct World {
    db: Database,
    clock: TestClock,
    ids: Seq,
    ctx: Ctx,
}

fn uzs(v: i64) -> Money {
    Money::new(v, Currency::Uzs)
}

fn d(s: &str) -> Date {
    date_from_str(s).unwrap()
}

impl World {
    fn new() -> Self {
        let mut db = Database::open_in_memory(&[5; 32]).unwrap();
        let clock = TestClock(Cell::new(time::macros::datetime!(2026-10-11 05:00 UTC)));
        let ids = Seq(Cell::new(1));
        let ctx = setup::ensure_household(
            &mut db,
            &Env {
                clock: &clock,
                ids: &ids,
                device_id: "dev",
            },
        )
        .unwrap();
        Self {
            db,
            clock,
            ids,
            ctx,
        }
    }

    fn create(&mut self, doc: AgreementDoc) -> String {
        let env = env!(self);
        let view = agreements::create(
            &mut self.db,
            &env,
            &self.ctx,
            NewAgreement {
                title: "Yetkazib berish musharakasi".into(),
                subject: None,
                doc,
            },
        )
        .unwrap();
        view.agreement.meta.id
    }
}

fn full_doc() -> AgreementDoc {
    AgreementDoc {
        agreement_type: AgreementType::Partnership,
        effective_from: d("2026-10-01"),
        witnesses: vec!["Karim aka".into()],
        questions: Questions {
            parties: Answer::Answered(vec![
                Party {
                    id: "P1".into(),
                    name: "Anvar".into(),
                    role: "Kapital egasi".into(),
                    member_id: None,
                },
                Party {
                    id: "P2".into(),
                    name: "Dilshod".into(),
                    role: "Ishchi".into(),
                    member_id: None,
                },
            ]),
            contributions: Answer::Answered(vec![
                Contribution {
                    party_id: "P1".into(),
                    description: "Pul".into(),
                    amount: Some(uzs(300_000_000)),
                },
                Contribution {
                    party_id: "P2".into(),
                    description: "Mehnat".into(),
                    amount: None,
                },
            ]),
            duties: Answer::Answered(vec![Duty {
                text: "Yetkazib berish".into(),
                owner_party_id: Some("P2".into()),
                if_not_done: "1 kun ichida xabar beradi".into(),
            }]),
            profit: Answer::Answered(ProfitRule {
                shares: vec![
                    ProfitShare {
                        party_id: "P1".into(),
                        share_bp: 5_000,
                    },
                    ProfitShare {
                        party_id: "P2".into(),
                        share_bp: 5_000,
                    },
                ],
                fixed_amount: None,
            }),
            loss: Answer::Answered(LossRule {
                text: "Kapitalga mutanosib".into(),
            }),
            custody: Answer::Answered(Custody {
                place: "Anvar hisobi".into(),
                keeper_device_id: None,
                review_every: ReportPeriod::Monthly,
            }),
            exit: Answer::Answered(ExitClause {
                text: "30 kun oldin xabar".into(),
            }),
            arbiter: Answer::Answered(Arbiter {
                name: "Usta Olim".into(),
                party_id: None,
            }),
            term: Answer::Answered(Term {
                months: Some(12),
                review_date: d("2027-10-01"),
            }),
        },
    }
}

fn sign_all(w: &mut World, id: &str) {
    for p in ["P1", "P2"] {
        let env = env!(w);
        let signer = AgreementSigner::Party {
            party_id: p.into(),
            pin: None,
        };
        agreements::sign(&mut w.db, &env, &w.ctx, id, signer).unwrap();
    }
    let env = env!(w);
    agreements::sign(
        &mut w.db,
        &env,
        &w.ctx,
        id,
        AgreementSigner::Witness {
            name: "Karim aka".into(),
        },
    )
    .unwrap();
    agreements::sign(&mut w.db, &env, &w.ctx, id, AgreementSigner::Arbiter).unwrap();
}

#[test]
fn complete_agreement_is_signed_then_activated() {
    let mut w = World::new();
    let id = w.create(full_doc());
    let v = agreements::view(w.db.conn(), &w.ctx, &id).unwrap();
    assert_eq!(v.agreement.status, AgreementStatus::Draft);
    assert!(v.completeness.is_complete(), "{:?}", v.completeness);
    assert_eq!(v.required.len(), 4, "2 tomon, 1 guvoh, 1 hakam");

    sign_all(&mut w, &id);
    let v = agreements::view(w.db.conn(), &w.ctx, &id).unwrap();
    assert_eq!(v.agreement.status, AgreementStatus::Signed);
    assert!(v.missing_signatures.is_empty());

    let env = env!(w);
    let v = agreements::activate(&mut w.db, &env, &w.ctx, &id).unwrap();
    assert_eq!(v.agreement.status, AgreementStatus::Active);
}

#[test]
fn incomplete_agreement_cannot_be_signed() {
    let mut w = World::new();
    let mut doc = full_doc();
    doc.questions.custody = Answer::Missing;
    doc.questions.term = Answer::Missing;
    let id = w.create(doc);
    let env = env!(w);
    let err = agreements::sign(
        &mut w.db,
        &env,
        &w.ctx,
        &id,
        AgreementSigner::Party {
            party_id: "P1".into(),
            pin: None,
        },
    )
    .expect_err("9/9 bo'lmasa imzolash bloklanadi");
    assert!(matches!(err, ServiceError::Invalid(_)), "{err:?}");
    let v = agreements::view(w.db.conn(), &w.ctx, &id).unwrap();
    assert_eq!(v.completeness.missing, vec![6, 9]);
    assert_eq!(v.agreement.status, AgreementStatus::Draft);
}

#[test]
fn duty_without_owner_blocks_signing() {
    let mut w = World::new();
    let mut doc = full_doc();
    doc.questions.duties = Answer::Answered(vec![Duty {
        text: "Hamma ishlaydi".into(),
        owner_party_id: None,
        if_not_done: "Xabar beradi".into(),
    }]);
    let id = w.create(doc);
    let v = agreements::view(w.db.conn(), &w.ctx, &id).unwrap();
    assert!(v
        .completeness
        .errors
        .iter()
        .any(|i| i.code == "DUTY_WITHOUT_OWNER"));
    let env = env!(w);
    assert!(agreements::sign(
        &mut w.db,
        &env,
        &w.ctx,
        &id,
        AgreementSigner::Party {
            party_id: "P1".into(),
            pin: None,
        },
    )
    .is_err());
}

#[test]
fn new_version_returns_to_draft_and_old_signatures_do_not_carry() {
    let mut w = World::new();
    let id = w.create(full_doc());
    sign_all(&mut w, &id);
    assert_eq!(
        agreements::view(w.db.conn(), &w.ctx, &id)
            .unwrap()
            .agreement
            .status,
        AgreementStatus::Signed
    );

    let mut changed = full_doc();
    changed.questions.exit = Answer::Answered(ExitClause {
        text: "60 kun oldin xabar".into(),
    });
    let env = env!(w);
    let v = agreements::save_version(
        &mut w.db,
        &env,
        &w.ctx,
        &id,
        changed,
        Some("Chiqish muddati"),
    )
    .unwrap();
    assert_eq!(v.agreement.status, AgreementStatus::Draft);
    assert_eq!(v.agreement.current_version, 2);
    assert!(v.signatures.is_empty(), "eski versiya tasdiqlari o'tmasin");
    assert_eq!(v.missing_signatures.len(), 4);
    assert_eq!(v.versions.len(), 2);
    assert_eq!(v.versions[0].change_note, None);
    assert_eq!(
        v.versions[1].change_note.as_deref(),
        Some("Chiqish muddati")
    );
    assert_ne!(v.versions[0].content_hash, v.versions[1].content_hash);

    sign_all(&mut w, &id);
    let v = agreements::view(w.db.conn(), &w.ctx, &id).unwrap();
    assert_eq!(v.agreement.status, AgreementStatus::Signed);
    assert_eq!(v.signatures.len(), 4);
}

#[test]
fn closed_agreement_is_not_changed() {
    let mut w = World::new();
    let id = w.create(full_doc());
    let env = env!(w);
    agreements::close(&mut w.db, &env, &w.ctx, &id).unwrap();
    let err = agreements::save_version(&mut w.db, &env, &w.ctx, &id, full_doc(), None)
        .expect_err("yopilgan kelishuv o'zgarmaydi");
    assert!(matches!(err, ServiceError::Invalid(_)));
}

#[test]
fn turning_a_partnership_into_a_loan_is_refused() {
    let mut w = World::new();
    let id = w.create(full_doc());
    let mut doc = full_doc();
    doc.agreement_type = AgreementType::Loan;
    let env = env!(w);
    assert!(agreements::save_version(&mut w.db, &env, &w.ctx, &id, doc, None).is_err());
}

#[test]
fn one_agreement_per_subject() {
    let mut w = World::new();
    let env = env!(w);
    let new = |subject: &str| NewAgreement {
        title: "Qarz".into(),
        subject: Some((SubjectKind::Debt, subject.into())),
        doc: full_doc(),
    };
    agreements::create(&mut w.db, &env, &w.ctx, new("debt-1")).unwrap();
    let err = agreements::create(&mut w.db, &env, &w.ctx, new("debt-1"))
        .expect_err("bitta obyekt — bitta kelishuv");
    assert!(matches!(err, ServiceError::Invalid(_)));
}

fn record(w: &mut World, agreement_id: &str, note: &str, minor: i64) -> domain::JournalEntry {
    let env = env!(w);
    let ctx = w.ctx.clone();
    let agreement: Agreement = repo::get(w.db.conn(), agreement_id).unwrap().unwrap();
    w.db.transaction::<domain::JournalEntry, ServiceError>(|tx| {
        journal::append(
            tx,
            &env,
            &ctx,
            &agreement,
            journal::NewEntry {
                kind: JournalKind::VentureIncome,
                party_id: None,
                amount: Some(uzs(minor)),
                date: d("2026-10-05"),
                note,
                reference: None,
                corrects: None,
            },
        )
    })
    .unwrap()
}

#[test]
fn journal_chain_verifies_and_detects_a_tampered_entry() {
    let mut w = World::new();
    let id = w.create(full_doc());
    let first = record(&mut w, &id, "Birinchi kirim", 100_000);
    record(&mut w, &id, "Ikkinchi kirim", 200_000);
    record(&mut w, &id, "Uchinchi kirim", 300_000);
    assert_eq!(first.seq, 1);
    assert_eq!(first.prev_hash, domain::GENESIS_HASH);

    let ok = journal::verify(w.db.conn(), &w.ctx, &id).unwrap();
    assert_eq!(ok.length, 3);
    assert_eq!(ok.broken_seq, None);

    // Ilova trigger'larni chetlab o'tgan holat (masalan, fayl bilan qo'lda tahrir): zanjir buzilishi topilishi shart.
    w.db.conn()
        .execute_batch("DROP TRIGGER trg_journal_upd;")
        .unwrap();
    w.db.conn()
        .execute(
            "UPDATE journal_entries SET amount_minor = 999 WHERE agreement_id = ?1 AND seq = 2",
            [&id],
        )
        .unwrap();
    let bad = journal::verify(w.db.conn(), &w.ctx, &id).unwrap();
    assert_eq!(
        bad.broken_seq,
        Some(2),
        "birinchi buzilgan yozuv 2-yozuv bo'lishi kerak"
    );
}

#[test]
fn only_the_keeper_device_writes_the_journal() {
    let mut w = World::new();
    let id = w.create(full_doc());
    let agreement: Agreement = repo::get(w.db.conn(), &id).unwrap().unwrap();
    let other = Env {
        clock: &w.clock,
        ids: &w.ids,
        device_id: "telefon",
    };
    let err = journal::append(
        w.db.conn(),
        &other,
        &w.ctx,
        &agreement,
        journal::NewEntry {
            kind: JournalKind::VentureIncome,
            party_id: None,
            amount: Some(uzs(1)),
            date: d("2026-10-05"),
            note: "Begona qurilma",
            reference: None,
            corrects: None,
        },
    )
    .expect_err("faqat hisob yurituvchi qurilma yozadi");
    assert!(matches!(err, ServiceError::Invalid(_)));
}

#[test]
fn correction_must_point_to_an_existing_entry() {
    let mut w = World::new();
    let id = w.create(full_doc());
    let first = record(&mut w, &id, "Kirim", 100_000);
    let agreement: Agreement = repo::get(w.db.conn(), &id).unwrap().unwrap();
    let env = env!(w);
    assert!(journal::append(w.db.conn(), &env, &w.ctx, &agreement, correction(None, "x")).is_err());
    assert!(journal::append(
        w.db.conn(),
        &env,
        &w.ctx,
        &agreement,
        correction(Some("yo'q"), "x")
    )
    .is_err());
    let ok = journal::append(
        w.db.conn(),
        &env,
        &w.ctx,
        &agreement,
        correction(Some(first.meta.id.as_str()), "Noto'g'ri kiritilgan"),
    )
    .unwrap();
    assert_eq!(ok.corrects.as_deref(), Some(first.meta.id.as_str()));
    assert_eq!(
        journal::verify(w.db.conn(), &w.ctx, &id)
            .unwrap()
            .broken_seq,
        None
    );
}

fn correction<'a>(corrects: Option<&'a str>, note: &'a str) -> journal::NewEntry<'a> {
    journal::NewEntry {
        kind: JournalKind::Correction,
        party_id: None,
        amount: Some(uzs(100_000)),
        date: d("2026-10-06"),
        note,
        reference: None,
        corrects,
    }
}

fn cash(v: i64) -> NewCapital {
    NewCapital {
        description: "Naqd pul".into(),
        kind: CapitalKind::Cash,
        value: uzs(v),
    }
}

fn musharaka(w: &mut World) -> String {
    let env = env!(w);
    let new = NewPartnership {
        details: Default::default(),
        name: "Yetkazib berish".into(),
        kind: PartnershipKind::Musharaka,
        term_months: 12,
        report_period: ReportPeriod::Monthly,
        end_clause: "Muddat tugagach hisob-kitob".into(),
        dispute_clause: "Hakam hal qiladi".into(),
        witnesses: vec!["Karim aka".into()],
        parties: vec![
            NewParty {
                name: "Anvar".into(),
                role: PartyRole::Partner,
                share_bp: 5_000,
                member_id: None,
                capital: vec![cash(300_000_000)],
                fixed_return: None,
            },
            NewParty {
                name: "Dilshod".into(),
                role: PartyRole::Partner,
                share_bp: 5_000,
                member_id: None,
                capital: vec![cash(300_000_000)],
                fixed_return: None,
            },
        ],
    };
    let v = partnerships::create(&mut w.db, &env, &w.ctx, new).unwrap();
    v.partnership.meta.id
}

#[test]
fn legacy_partnership_is_adopted_once_with_signatures_and_opening_balance() {
    let mut w = World::new();
    let pid = musharaka(&mut w);
    let env = env!(w);
    let first_party = partnerships::view(w.db.conn(), &env, &w.ctx, &pid)
        .unwrap()
        .parties[0]
        .party
        .meta
        .id
        .clone();

    // D8A dan oldingi baza: sheriklik va tasdiq bor, kelishuv yozuvlari yo'q.
    let agreement_id = agreements::agreement_of_partnership(w.db.conn(), &w.ctx, &pid)
        .unwrap()
        .unwrap()
        .meta
        .id;
    w.db.conn()
        .execute_batch("DROP TRIGGER trg_agv_del; DROP TRIGGER trg_ags_del;")
        .unwrap();
    w.db.conn()
        .execute(
            &format!("DELETE FROM agreement_versions WHERE agreement_id = '{agreement_id}'"),
            [],
        )
        .unwrap();
    w.db.conn()
        .execute(
            &format!("DELETE FROM agreements WHERE id = '{agreement_id}'"),
            [],
        )
        .unwrap();
    let legacy_sig = w.ids.new_id();
    let household = w.ctx.household_id.clone();
    w.db.conn()
        .execute(
            &format!(
                "INSERT INTO partnership_signatures (id, household_id, created_at, updated_at, deleted_at, \
                 version, origin_device_id, partnership_id, contract_version, kind, signer, signer_name) \
                 VALUES ('{legacy_sig}', '{household}', '2026-10-11T05:00:00Z', '2026-10-11T05:00:00Z', NULL, 1, 'dev', '{pid}', 1, 'PARTY', \
                 '{first_party}', 'Anvar')"
            ),
            [],
        )
        .unwrap();

    assert_eq!(
        agreements::adopt_legacy(&mut w.db, &env, &w.ctx).unwrap(),
        1
    );
    assert_eq!(
        agreements::adopt_legacy(&mut w.db, &env, &w.ctx).unwrap(),
        0,
        "ikkinchi chaqiruvda hech narsa qo'shilmasin"
    );

    let list = agreements::list(w.db.conn(), &w.ctx).unwrap();
    assert_eq!(list.len(), 1);
    let v = &list[0];
    assert!(v.agreement.legacy);
    assert_eq!(v.agreement.subject_kind, SubjectKind::Partnership);
    assert_eq!(v.agreement.subject_id.as_deref(), Some(pid.as_str()));
    assert!(v.doc.is_none(), "eski versiya matn holida");
    assert_eq!(v.completeness.missing, (1..=9).collect::<Vec<u8>>());
    assert_eq!(v.signatures.len(), 1);
    assert_eq!(v.signatures[0].kind, AgreementSignKind::Party);
    assert_eq!(v.chain.length, 1);
    assert_eq!(v.chain.broken_seq, None);

    let entries = journal::entries(w.db.conn(), &w.ctx, &v.agreement.meta.id).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].kind, JournalKind::OpeningBalance);
    assert_eq!(entries[0].amount, Some(uzs(600_000_000)));

    // Eski matnli kelishuv 9/9 yangi versiyasiz imzolanmaydi (OPEN_QUESTIONS 87).
    let err = agreements::sign(
        &mut w.db,
        &env,
        &w.ctx,
        &v.agreement.meta.id,
        AgreementSigner::Arbiter,
    )
    .expect_err("eski versiya imzolanmaydi");
    assert!(matches!(err, ServiceError::Invalid(_)));

    // Yangi 9/9 versiya yaratilgach, imzolash ochiladi.
    let doc = full_doc();
    let agreement_id = v.agreement.meta.id.clone();
    agreements::save_version(
        &mut w.db,
        &env,
        &w.ctx,
        &agreement_id,
        doc,
        Some("9/9 ga yangilash"),
    )
    .unwrap();
    let after = agreements::view(w.db.conn(), &w.ctx, &agreement_id).unwrap();
    assert!(after.completeness.is_complete(), "{:?}", after.completeness);
}

#[test]
fn family_member_consent_needs_the_adult_pin() {
    let mut w = World::new();
    let id = w.create(full_doc());
    let env = env!(w);
    members::set_pin(
        &mut w.db,
        &env,
        &w.ctx,
        &w.ctx.member_id,
        "111111",
        security::KdfParams::fast_for_tests(),
    )
    .unwrap();
    let err = agreements::sign(
        &mut w.db,
        &env,
        &w.ctx,
        &id,
        AgreementSigner::FamilyConsent {
            member_id: w.ctx.member_id.clone(),
            pin: "000000".into(),
        },
    )
    .expect_err("noto'g'ri PIN bilan rozilik bo'lmaydi");
    assert!(matches!(err, ServiceError::WrongPin), "{err:?}");
}

#[test]
fn signed_agreement_renders_a_pdf_and_drafts_refuse() {
    let mut w = World::new();
    let id = w.create(full_doc());
    // Qoralama: 9/9 bo'lsa ham imzolanmagan — PDF bor, lekin tasdiqsiz belgi bilan.
    let draft = agreements::pdf(w.db.conn(), &w.ctx, &id).unwrap();
    assert!(draft.starts_with(b"%PDF"));
    sign_all(&mut w, &id);
    let signed = agreements::pdf(w.db.conn(), &w.ctx, &id).unwrap();
    assert!(signed.starts_with(b"%PDF"));
    assert_ne!(draft, signed, "tasdiqlar PDF'da aks etsin");
}

#[test]
fn incomplete_legacy_agreement_has_no_pdf() {
    let mut w = World::new();
    let mut doc = full_doc();
    doc.questions.arbiter = Answer::Missing;
    let id = w.create(doc);
    // Savol javobsiz bo'lsa ham PDF chiqadi (qoralama); eski matnli versiya esa chiqmaydi.
    assert!(agreements::pdf(w.db.conn(), &w.ctx, &id).is_ok());
}

#[test]
fn debt_payment_is_journaled_when_the_debt_has_an_agreement() {
    use services::debts::{self, NewDebt, ScheduleInput};
    let mut w = World::new();
    let env = env!(w);
    let debt = debts::add(
        &mut w.db,
        &env,
        &w.ctx,
        NewDebt {
            creditor: "Bank".into(),
            creditor_type: domain::CreditorType::Bank,
            reason: Some("avtokredit".into()),
            principal: uzs(300_000_000),
            schedule_kind: domain::ScheduleKind::Manual,
            schedule: ScheduleInput::Rows(vec![
                (d("2026-11-07"), uzs(150_000_000)),
                (d("2026-12-07"), uzs(150_000_000)),
            ]),
            borrowed_on: None,
            early_repayment_terms: None,
            check: None,
        },
    )
    .unwrap();
    let debt_id = debt.debt.meta.id.clone();
    let agreement = {
        let env = env!(w);
        agreements::create(
            &mut w.db,
            &env,
            &w.ctx,
            NewAgreement {
                title: "Bank krediti".into(),
                subject: Some((SubjectKind::Debt, debt_id.clone())),
                doc: full_doc(),
            },
        )
        .unwrap()
    };
    let agreement_id = agreement.agreement.meta.id.clone();

    let env = env!(w);
    debts::pay(
        &mut w.db,
        &env,
        &w.ctx,
        &debt_id,
        uzs(150_000_000),
        None,
        None,
    )
    .unwrap();

    let entries = journal::entries(w.db.conn(), &w.ctx, &agreement_id).unwrap();
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].kind, JournalKind::Payment);
    assert_eq!(entries[0].amount, Some(uzs(150_000_000)));
    assert_eq!(
        journal::verify(w.db.conn(), &w.ctx, &agreement_id)
            .unwrap()
            .broken_seq,
        None
    );
}
