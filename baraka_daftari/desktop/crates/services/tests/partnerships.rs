#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, CapitalKind, Clock, Date, IdGen, MemberRole, OffsetDateTime, Outcome,
    PartnershipKind, PartnershipStatus, PartyRole, ReportPeriod,
};
use money::{Currency, Money};
use security::KdfParams;
use services::{
    members,
    partnerships::{self, NewCapital, NewPartnership, NewParty, Signer},
    setup, Ctx, Env, ServiceError,
};
use storage::Database;

const FAST: KdfParams = KdfParams::fast_for_tests();

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
        let mut db = Database::open_in_memory(&[9; 32]).unwrap();
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
        let env = Env {
            clock: &clock,
            ids: &ids,
            device_id: "dev",
        };
        members::set_pin(&mut db, &env, &ctx, &ctx.member_id, "111111", FAST).unwrap();
        Self {
            db,
            clock,
            ids,
            ctx,
        }
    }

    fn create(
        &mut self,
        new: NewPartnership,
    ) -> Result<partnerships::PartnershipView, ServiceError> {
        let env = env!(self);
        partnerships::create(&mut self.db, &env, &self.ctx, new)
    }

    fn view(&self, id: &str) -> partnerships::PartnershipView {
        partnerships::view(self.db.conn(), &env!(self), &self.ctx, id).unwrap()
    }

    fn sign(&mut self, id: &str, s: Signer) -> Result<(), ServiceError> {
        let env = env!(self);
        partnerships::sign(&mut self.db, &env, &self.ctx, id, s)
    }

    fn activate(&mut self, id: &str) -> Result<partnerships::PartnershipView, ServiceError> {
        let env = env!(self);
        partnerships::activate(&mut self.db, &env, &self.ctx, id)
    }
}

fn cash(v: i64) -> NewCapital {
    NewCapital {
        description: "Naqd pul".into(),
        kind: CapitalKind::Cash,
        value: uzs(v),
    }
}

fn party(
    name: &str,
    role: PartyRole,
    share: u32,
    capital: Vec<NewCapital>,
    member: Option<&str>,
) -> NewParty {
    NewParty {
        name: name.into(),
        role,
        share_bp: share,
        member_id: member.map(str::to_owned),
        capital,
        fixed_return: None,
    }
}

/// Tashqi kapital egasi (Karim aka) va xonadon a'zosi — ishchi (Zamira = `self`).
fn mudaraba_inbound(me: &str) -> NewPartnership {
    NewPartnership {
        name: "Tikuvchilik ustaxonasi".into(),
        kind: PartnershipKind::Mudaraba,
        term_months: 12,
        report_period: ReportPeriod::Monthly,
        end_clause: "Uskunalar qaytariladi".into(),
        dispute_clause: "Oqsoqol huzurida".into(),
        witnesses: vec!["Dilshod".into()],
        parties: vec![
            party(
                "Karim aka",
                PartyRole::CapitalProvider,
                4_000,
                vec![cash(800_000_000)],
                None,
            ),
            party("Zamira", PartyRole::Worker, 6_000, vec![], Some(me)),
        ],
    }
}

/// Xonadon a'zosi kapital **kiritadi**.
fn mudaraba_outbound(me: &str) -> NewPartnership {
    let mut n = mudaraba_inbound(me);
    n.parties = vec![
        party(
            "Men",
            PartyRole::CapitalProvider,
            4_000,
            vec![cash(800_000_000)],
            Some(me),
        ),
        party("Zamira", PartyRole::Worker, 6_000, vec![], None),
    ];
    n
}

fn musharaka(me: &str) -> NewPartnership {
    NewPartnership {
        name: "Oshxona".into(),
        kind: PartnershipKind::Musharaka,
        term_months: 24,
        report_period: ReportPeriod::Quarterly,
        end_clause: "Ulush sotib olinadi".into(),
        dispute_clause: "Kelishuv".into(),
        witnesses: vec![],
        parties: vec![
            party(
                "Karim aka",
                PartyRole::Partner,
                6_000,
                vec![cash(600_000_000)],
                None,
            ),
            party(
                "Zamira",
                PartyRole::Partner,
                4_000,
                vec![cash(400_000_000)],
                Some(me),
            ),
        ],
    }
}

#[test]
fn creation_is_validated_and_guaranteed_return_is_blocked() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();

    // Qabul mezoni: kafolatli daromad domen darajasida bloklanadi, tushuntirish bilan.
    let mut n = mudaraba_inbound(&me);
    n.parties[0].fixed_return = Some(uzs(50_000_000));
    let e = w.create(n).unwrap_err();
    assert!(matches!(e, ServiceError::Invalid(m) if m.contains("ribo yoki qarz")));

    let mut bad_sum = mudaraba_inbound(&me);
    bad_sum.parties[1].share_bp = 5_000;
    assert!(
        matches!(w.create(bad_sum).unwrap_err(), ServiceError::Invalid(m) if m.contains("100%"))
    );

    let mut no_worker = mudaraba_inbound(&me);
    no_worker.parties[1].role = PartyRole::CapitalProvider;
    assert!(w.create(no_worker).is_err());

    let mut no_capital = mudaraba_inbound(&me);
    no_capital.parties[0].capital.clear();
    assert!(w.create(no_capital).is_err());

    let mut unknown = mudaraba_inbound(&me);
    unknown.parties[1].member_id = Some("nope".into());
    assert!(w.create(unknown).is_err());

    let mut empty_clause = mudaraba_inbound(&me);
    empty_clause.dispute_clause = "  ".into();
    assert!(w.create(empty_clause).is_err());

    let mut one_party = mudaraba_inbound(&me);
    one_party.parties.truncate(1);
    assert!(w.create(one_party).is_err());

    let mut bad_term = mudaraba_inbound(&me);
    bad_term.term_months = 0;
    assert!(w.create(bad_term).is_err());

    // Hech biri saqlanmadi: shartnomasiz sheriklik yo'q.
    assert!(partnerships::list(w.db.conn(), &env!(w), &w.ctx)
        .unwrap()
        .is_empty());

    let v = w.create(mudaraba_inbound(&me)).unwrap();
    assert_eq!(v.partnership.version, 1);
    assert_eq!(v.partnership.status, PartnershipStatus::Draft);
    assert_eq!(v.total_capital.minor(), 800_000_000);
    assert_eq!(v.versions.len(), 1);
    assert!(v.self_receives_capital && !v.self_provides_capital);
}

#[test]
fn activation_needs_every_signature_witness_and_family_consent() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let v = w.create(mudaraba_inbound(&me)).unwrap();
    let id = v.partnership.meta.id.clone();
    let (karim, zamira) = (
        v.parties[0].party.meta.id.clone(),
        v.parties[1].party.meta.id.clone(),
    );
    assert_eq!(v.blocker, Some("PARTY_SIGNATURES"));
    assert!(w.activate(&id).is_err());

    // Tashqi tomon — qo'lda tasdiq; a'zo tomon PIN talab qiladi.
    w.sign(
        &id,
        Signer::Party {
            party_id: karim,
            pin: None,
        },
    )
    .unwrap();
    assert!(matches!(
        w.sign(
            &id,
            Signer::Party {
                party_id: zamira.clone(),
                pin: None
            }
        ),
        Err(ServiceError::NoPin)
    ));
    assert!(matches!(
        w.sign(
            &id,
            Signer::Party {
                party_id: zamira.clone(),
                pin: Some("000000".into())
            }
        ),
        Err(ServiceError::WrongPin)
    ));
    w.sign(
        &id,
        Signer::Party {
            party_id: zamira,
            pin: Some("111111".into()),
        },
    )
    .unwrap();
    assert_eq!(w.view(&id).blocker, Some("WITNESS_SIGNATURES"));

    assert!(w
        .sign(
            &id,
            Signer::Witness {
                name: "Begona".into()
            }
        )
        .is_err());
    w.sign(
        &id,
        Signer::Witness {
            name: "Dilshod".into(),
        },
    )
    .unwrap();
    // Kapital qabul qilinadi → barcha kattalarning oilaviy roziligi kerak.
    let v = w.view(&id);
    assert_eq!(v.blocker, Some("FAMILY_CONSENT"));
    assert_eq!(v.consents.len(), 1);

    let child = members::add(&mut w.db, &env!(w), &w.ctx, "Bola", MemberRole::Child).unwrap();
    assert!(partnerships::family_consent(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        &child.meta.id,
        "123456"
    )
    .is_err());
    assert!(partnerships::family_consent(&mut w.db, &env!(w), &w.ctx, &id, &me, "999999").is_err());
    partnerships::family_consent(&mut w.db, &env!(w), &w.ctx, &id, &me, "111111").unwrap();
    assert_eq!(w.view(&id).blocker, None);

    // Ikkinchi kattaning roziligi ham kerak bo'lib qoladi.
    let wife = members::add(&mut w.db, &env!(w), &w.ctx, "Rafiqa", MemberRole::Adult).unwrap();
    assert_eq!(w.view(&id).blocker, Some("FAMILY_CONSENT"));
    members::set_pin(&mut w.db, &env!(w), &w.ctx, &wife.meta.id, "222222", FAST).unwrap();
    partnerships::family_consent(&mut w.db, &env!(w), &w.ctx, &id, &wife.meta.id, "222222")
        .unwrap();

    let v = partnerships::activate(&mut w.db, &env!(w), &w.ctx, &id).unwrap();
    assert_eq!(v.partnership.status, PartnershipStatus::Active);
    assert!(
        partnerships::activate(&mut w.db, &env!(w), &w.ctx, &id).is_err(),
        "faqat qoralama"
    );
}

#[test]
fn providing_capital_is_subject_to_the_readiness_gate() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let v = w.create(mudaraba_outbound(&me)).unwrap();
    let id = v.partnership.meta.id.clone();
    assert!(v.self_provides_capital && !v.self_receives_capital);
    let (mine, other) = (
        v.parties[0].party.meta.id.clone(),
        v.parties[1].party.meta.id.clone(),
    );
    w.sign(
        &id,
        Signer::Party {
            party_id: mine,
            pin: Some("111111".into()),
        },
    )
    .unwrap();
    w.sign(
        &id,
        Signer::Party {
            party_id: other,
            pin: None,
        },
    )
    .unwrap();
    w.sign(
        &id,
        Signer::Witness {
            name: "Dilshod".into(),
        },
    )
    .unwrap();
    // Qorovul pul yo'q → darvoza yopiq.
    assert_eq!(w.view(&id).blocker, Some("GATE_CLOSED"));
    assert!(w.activate(&id).is_err());
    // Ongli chetlab o'tish darvozani ochadi.
    services::guard::bypass(&mut w.db, &env!(w), &w.ctx, true).unwrap();
    assert_eq!(w.view(&id).blocker, None);
    w.activate(&id).unwrap();
}

#[test]
fn receiving_capital_is_not_gated() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let v = w.create(mudaraba_inbound(&me)).unwrap();
    // Qorovul pul yo'q, lekin kapital qabul qilish darvozaga bo'ysunmaydi: to'siq faqat tasdiqlar.
    assert_ne!(v.blocker, Some("GATE_CLOSED"));
}

/// Qabul mezoni (D12): versiya o'zgarganda imzolar qayta so'raladi.
#[test]
fn revising_bumps_the_version_and_requires_new_signatures() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    // Xonadon a'zosi kapital kiritadi → darvoza (ongli chetlab o'tish bilan ochamiz).
    services::guard::bypass(&mut w.db, &env!(w), &w.ctx, true).unwrap();
    let v = w.create(musharaka(&me)).unwrap();
    let id = v.partnership.meta.id.clone();
    for p in &v.parties {
        let pin = p.party.member_id.as_ref().map(|_| "111111".to_owned());
        w.sign(
            &id,
            Signer::Party {
                party_id: p.party.meta.id.clone(),
                pin,
            },
        )
        .unwrap();
    }
    assert_eq!(w.view(&id).blocker, None);
    let activated = w.activate(&id).unwrap();
    assert_eq!(activated.partnership.status, PartnershipStatus::Active);

    let mut changed = musharaka(&me);
    changed.term_months = 36;
    let v2 = partnerships::revise(&mut w.db, &env!(w), &w.ctx, &id, changed).unwrap();
    assert_eq!(v2.partnership.version, 2);
    assert_eq!(
        v2.partnership.status,
        PartnershipStatus::Draft,
        "faol qoralamaga qaytadi"
    );
    assert!(v2.parties.iter().all(|p| !p.signed), "eski imzolar kuchsiz");
    assert_eq!(v2.blocker, Some("PARTY_SIGNATURES"));
    assert_eq!(v2.versions.len(), 2);
    assert!(
        v2.versions[0].snapshot.contains("1-versiya")
            && v2.versions[1].snapshot.contains("2-versiya")
    );
    assert!(w.activate(&id).is_err());
    assert_eq!(
        v2.parties.len(),
        2,
        "eski tomonlar o'chirilgan, yangilari qo'shilgan"
    );

    // Yaroqsiz o'zgartirish versiyani oshirmaydi.
    let mut bad = musharaka(&me);
    bad.parties[0].fixed_return = Some(uzs(1));
    assert!(partnerships::revise(&mut w.db, &env!(w), &w.ctx, &id, bad).is_err());
    assert_eq!(w.view(&id).partnership.version, 2);

    // Tugagan sheriklikni o'zgartirib bo'lmaydi.
    partnerships::end(&mut w.db, &env!(w), &w.ctx, &id).unwrap();
    assert!(partnerships::revise(&mut w.db, &env!(w), &w.ctx, &id, musharaka(&me)).is_err());
}

#[test]
fn distribution_preview_follows_the_rules() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let id = w.create(mudaraba_inbound(&me)).unwrap().partnership.meta.id;
    let c = w.db.conn();
    let profit = partnerships::preview_distribution(
        c,
        &env!(w),
        &w.ctx,
        &id,
        Outcome::Profit,
        uzs(300_000_000),
        None,
    )
    .unwrap();
    assert_eq!(profit[0], ("Karim aka".to_owned(), uzs(120_000_000)));
    assert_eq!(profit[1], ("Zamira".to_owned(), uzs(180_000_000)));
    let loss = partnerships::preview_distribution(
        c,
        &env!(w),
        &w.ctx,
        &id,
        Outcome::Loss,
        uzs(200_000_000),
        None,
    )
    .unwrap();
    assert_eq!((loss[0].1.minor(), loss[1].1.minor()), (-200_000_000, 0));
    // Beparvolik: izoh majburiy; izoh bilan zarar ishchi zimmasida.
    assert!(partnerships::preview_distribution(
        c,
        &env!(w),
        &w.ctx,
        &id,
        Outcome::Loss,
        uzs(100),
        Some("  ")
    )
    .is_err());
    let neg = partnerships::preview_distribution(
        c,
        &env!(w),
        &w.ctx,
        &id,
        Outcome::Loss,
        uzs(100),
        Some("ombor yopilmagan"),
    )
    .unwrap();
    assert_eq!((neg[0].1.minor(), neg[1].1.minor()), (0, -100));

    let m = w.create(musharaka(&me)).unwrap().partnership.meta.id;
    let loss = partnerships::preview_distribution(
        w.db.conn(),
        &env!(w),
        &w.ctx,
        &m,
        Outcome::Loss,
        uzs(100_000_000),
        None,
    )
    .unwrap();
    assert_eq!(
        (loss[0].1.minor(), loss[1].1.minor()),
        (-60_000_000, -40_000_000)
    );
    assert!(partnerships::preview_distribution(
        w.db.conn(),
        &env!(w),
        &w.ctx,
        &m,
        Outcome::Loss,
        uzs(1),
        Some("x")
    )
    .is_err());
}

#[test]
fn buyout_plan_tracks_planned_and_actual_ownership() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let v = w.create(musharaka(&me)).unwrap();
    let id = v.partnership.meta.id.clone();
    let karim = v.parties[0].party.meta.id.clone();

    // Mudarabada buyout yo'q.
    let md = w.create(mudaraba_inbound(&me)).unwrap();
    assert!(partnerships::set_buyout(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &md.partnership.meta.id,
        &md.parties[0].party.meta.id,
        6,
        None
    )
    .is_err());
    assert!(partnerships::set_buyout(&mut w.db, &env!(w), &w.ctx, &id, &karim, 0, None).is_err());
    assert!(partnerships::set_buyout(&mut w.db, &env!(w), &w.ctx, &id, "nope", 6, None).is_err());

    let b = partnerships::set_buyout(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        &karim,
        6,
        Some(d("2026-11-30")),
    )
    .unwrap();
    assert_eq!(b.total_value.minor(), 1_000_000_000);
    assert_eq!(b.stake.minor(), 600_000_000);
    assert_eq!(b.planned.rows.len(), 6);
    assert_eq!(b.planned.rows[0].remaining.minor(), 500_000_000);
    assert_eq!(b.planned.rows[0].provider_bp, 5_000);
    assert!(b.planned.completed);
    assert_eq!(b.planned_dates[1], d("2026-12-30"));
    assert_eq!(b.planned_dates[3], d("2027-02-28"));

    partnerships::record_buyout_payment(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        uzs(150_000_000),
        Some(d("2026-12-01")),
    )
    .unwrap();
    let b = partnerships::buyout_view(w.db.conn(), &env!(w), &w.ctx, &id)
        .unwrap()
        .unwrap();
    assert_eq!(b.actual.rows[0].remaining.minor(), 450_000_000);
    assert_eq!(
        (b.actual.rows[0].provider_bp, b.actual.rows[0].worker_bp),
        (4_500, 5_500)
    );
    assert!(!b.actual.completed);
    assert!(partnerships::record_buyout_payment(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        uzs(450_000_001),
        None
    )
    .is_err());
    partnerships::record_buyout_payment(&mut w.db, &env!(w), &w.ctx, &id, uzs(450_000_000), None)
        .unwrap();
    assert!(
        partnerships::buyout_view(w.db.conn(), &env!(w), &w.ctx, &id)
            .unwrap()
            .unwrap()
            .actual
            .completed
    );
    assert!(
        partnerships::record_buyout_payment(&mut w.db, &env!(w), &w.ctx, &id, uzs(1), None)
            .is_err()
    );
}

#[test]
fn contract_pdf_renders_with_buyout_and_signatures() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let v = w.create(musharaka(&me)).unwrap();
    let id = v.partnership.meta.id.clone();
    partnerships::set_buyout(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        &v.parties[0].party.meta.id,
        6,
        None,
    )
    .unwrap();
    w.sign(
        &id,
        Signer::Party {
            party_id: v.parties[0].party.meta.id.clone(),
            pin: None,
        },
    )
    .unwrap();
    let pdf = partnerships::contract_pdf(w.db.conn(), &env!(w), &w.ctx, &id).unwrap();
    assert!(pdf.starts_with(b"%PDF-"));
    assert!(partnerships::contract_pdf(w.db.conn(), &env!(w), &w.ctx, "nope").is_err());
}
