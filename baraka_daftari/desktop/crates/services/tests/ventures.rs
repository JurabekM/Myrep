#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, CapitalKind, Clock, Date, IdGen, JournalKind, LedgerKind, MemberRole,
    OfferAnswers, OffsetDateTime, PartnershipKind, PartyRole, ReportPeriod, Verdict,
};
use money::{Currency, Money};
use security::KdfParams;
use services::{
    crafts::{self, NewIdea},
    members,
    partnerships::{self, NewCapital, NewPartnership, NewParty, Signer},
    setup,
    ventures::{self, NewEntry},
    Ctx, Env, ServiceError,
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
    cap: Vec<NewCapital>,
    member: Option<&str>,
) -> NewParty {
    NewParty {
        name: name.into(),
        role,
        share_bp: share,
        member_id: member.map(str::to_owned),
        capital: cap,
        fixed_return: None,
    }
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

    /// Faol shartnoma: barcha tasdiqlar berilgan.
    fn activate(&mut self, new: NewPartnership) -> String {
        let me = self.ctx.member_id.clone();
        let v = partnerships::create(&mut self.db, &env!(self), &self.ctx, new).unwrap();
        let id = v.partnership.meta.id.clone();
        for p in &v.parties {
            let pin = p.party.member_id.as_ref().map(|_| "111111".to_owned());
            partnerships::sign(
                &mut self.db,
                &env!(self),
                &self.ctx,
                &id,
                Signer::Party {
                    party_id: p.party.meta.id.clone(),
                    pin,
                },
            )
            .unwrap();
        }
        for wv in &v.witnesses {
            let name = wv.name.clone();
            partnerships::sign(
                &mut self.db,
                &env!(self),
                &self.ctx,
                &id,
                Signer::Witness { name },
            )
            .unwrap();
        }
        partnerships::sign(&mut self.db, &env!(self), &self.ctx, &id, Signer::Arbiter).unwrap();
        if v.self_receives_capital {
            partnerships::family_consent(&mut self.db, &env!(self), &self.ctx, &id, &me, "111111")
                .unwrap();
        }
        if v.self_provides_capital {
            services::guard::bypass(&mut self.db, &env!(self), &self.ctx, true).unwrap();
        }
        partnerships::activate(&mut self.db, &env!(self), &self.ctx, &id).unwrap();
        id
    }

    fn entry(
        &mut self,
        pid: &str,
        kind: LedgerKind,
        desc: &str,
        amount: i64,
        on: &str,
    ) -> Result<domain::VentureEntry, ServiceError> {
        ventures::add_entry(
            &mut self.db,
            &env!(self),
            &self.ctx,
            pid,
            NewEntry {
                kind,
                description: desc,
                amount: uzs(amount),
                occurred_on: Some(d(on)),
                note: None,
                force_majeure: false,
            },
        )
    }

    fn close(&mut self, pid: &str, end: &str) -> Result<ventures::PeriodView, ServiceError> {
        self.close_acked(pid, end, false)
    }

    fn close_acked(
        &mut self,
        pid: &str,
        end: &str,
        spike_ack: bool,
    ) -> Result<ventures::PeriodView, ServiceError> {
        ventures::close_period(
            &mut self.db,
            &env!(self),
            &self.ctx,
            pid,
            Some(d(end)),
            None,
            spike_ack,
        )
    }

    fn ledger(&self, pid: &str) -> ventures::LedgerView {
        ventures::ledger(self.db.conn(), &env!(self), &self.ctx, pid).unwrap()
    }
}

/// Karim aka (tashqi kapital egasi) va xonadon a'zosi (ishchi).
/// 3, 6, 8-savollar (test uchun): vazifa (mas'ul — `owner`), pul joyi va hakam.
fn details(owner: &str) -> services::partnerships::PartnershipDetails {
    services::partnerships::PartnershipDetails {
        duties: vec![services::partnerships::DutyInput {
            text: "Yetkazib berish va hisobot".into(),
            owner_name: owner.into(),
            if_not_done: "1 kun ichida xabar beradi va o'rnini topadi".into(),
        }],
        custody_place: "Kelishilgan hisob".into(),
        arbiter_name: "Usta Olim".into(),
        review_date: None,
    }
}

fn mudaraba_worker(me: &str) -> NewPartnership {
    NewPartnership {
        details: details("Zamira"),
        name: "Ustaxona".into(),
        kind: PartnershipKind::Mudaraba,
        term_months: 12,
        report_period: ReportPeriod::Monthly,
        end_clause: "Qaytariladi".into(),
        dispute_clause: "Oqsoqol".into(),
        witnesses: vec![],
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

#[test]
fn ledger_requires_an_active_partnership_and_respects_read_only_for_capital_providers() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let draft = partnerships::create(&mut w.db, &env!(w), &w.ctx, mudaraba_worker(&me)).unwrap();
    let e = w
        .entry(
            &draft.partnership.meta.id,
            LedgerKind::Income,
            "x",
            1,
            "2026-10-12",
        )
        .unwrap_err();
    assert!(matches!(e, ServiceError::Invalid(m) if m.contains("faol")));

    // Xonadon — kapital egasi: faqat o'qish.
    let mut n = mudaraba_worker(&me);
    n.parties = vec![
        party(
            "Men",
            PartyRole::CapitalProvider,
            4_000,
            vec![cash(800_000_000)],
            Some(&me),
        ),
        party("Zamira", PartyRole::Worker, 6_000, vec![], None),
    ];
    let pid = w.activate(n);
    let e = w
        .entry(&pid, LedgerKind::Income, "x", 1, "2026-10-12")
        .unwrap_err();
    assert!(matches!(e, ServiceError::Invalid(m) if m.contains("faqat o'qish")));
    assert!(w.ledger(&pid).read_only);
}

#[test]
fn closing_a_period_distributes_profit_and_links_only_the_share_to_household_income() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    assert!(w
        .entry(&pid, LedgerKind::Income, "Buyurtma", 0, "2026-10-12")
        .is_err());
    assert!(w
        .entry(&pid, LedgerKind::Income, "  ", 5, "2026-10-12")
        .is_err());
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma 1",
        500_000_000,
        "2026-10-12",
    )
    .unwrap();
    w.entry(&pid, LedgerKind::Expense, "Mato", 200_000_000, "2026-10-15")
        .unwrap();
    assert!(
        w.close(&pid, "2026-10-14").is_err(),
        "oxirgi yozuvdan oldin yopib bo'lmaydi"
    );

    let before = services::income::month_total(
        w.db.conn(),
        &w.ctx,
        services::YearMonth::parse("2026-10").unwrap(),
    )
    .unwrap();
    assert_eq!(
        before.minor(),
        0,
        "biznes puli uy daromadiga o'z-o'zidan kirmaydi"
    );
    let closed = w.close(&pid, "2026-10-31").unwrap();
    assert_eq!(closed.net.minor(), 300_000_000);
    let shares: Vec<i64> = closed
        .distribution
        .iter()
        .map(|x| x.amount.minor())
        .collect();
    assert_eq!(shares, vec![120_000_000, 180_000_000]);
    // Faqat a'zoning ulushi (Zamira) xonadon daromadiga yozildi.
    let after = services::income::month_total(
        w.db.conn(),
        &w.ctx,
        services::YearMonth::parse("2026-10").unwrap(),
    )
    .unwrap();
    assert_eq!(after.minor(), 180_000_000);

    let l = w.ledger(&pid);
    assert_eq!(l.closed.len(), 1);
    let open = l.open.unwrap();
    assert_eq!(open.period.period_no, 2);
    assert_eq!(open.period.start_date, d("2026-11-01"));
    assert!(
        w.close(&pid, "2026-11-05").is_err(),
        "bo'sh davrni yopib bo'lmaydi"
    );
}

/// Qabul mezoni (D13): yopilgan davrni o'zgartirib bo'lmaydi — xizmatda ham, bazada ham.
#[test]
fn closed_period_is_immutable_in_service_and_in_the_database() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    let e = w
        .entry(&pid, LedgerKind::Income, "Buyurtma", 100, "2026-10-12")
        .unwrap();
    let att = ventures::attach(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &e.meta.id,
        "chek.png",
        b"\x89PNG\r\n\x1a\nxxxx".to_vec(),
    )
    .unwrap();
    let closed = w.close(&pid, "2026-10-31").unwrap();

    // Xizmat qatlami.
    let env = env!(w);
    assert!(matches!(
        ventures::remove_entry(&mut w.db, &env, &w.ctx, &e.meta.id),
        Err(ServiceError::Invalid(m)) if m.contains("o'zgarmaydi")
    ));
    assert!(ventures::attach(
        &mut w.db,
        &env,
        &w.ctx,
        &e.meta.id,
        "x.png",
        b"\x89PNG\r\n\x1a\n1".to_vec()
    )
    .is_err());
    let back = w
        .entry(&pid, LedgerKind::Income, "Orqaga", 1, "2026-10-20")
        .unwrap_err();
    assert!(matches!(back, ServiceError::Invalid(m) if m.contains("o'zgarmaydi")));

    // Baza triggerlari (xizmatni chetlab o'tganda ham).
    let c = w.db.conn();
    for sql in [
        format!("UPDATE venture_entries SET amount_minor = 999 WHERE id = '{}'", e.meta.id),
        format!("DELETE FROM venture_entries WHERE id = '{}'", e.meta.id),
        "INSERT INTO venture_entries (id,household_id,created_at,updated_at,version,origin_device_id,partnership_id,period_id,kind,description,amount_minor,currency,occurred_on) \
         VALUES ('z','h','t','t',1,'d','p','".to_owned() + &closed.period.meta.id + "','INCOME','x',1,'UZS','2026-10-01')",
        format!("UPDATE venture_periods SET status = 'OPEN' WHERE id = '{}'", closed.period.meta.id),
        format!("DELETE FROM venture_periods WHERE id = '{}'", closed.period.meta.id),
        "UPDATE venture_distributions SET amount_minor = 1".to_owned(),
        "DELETE FROM venture_distributions".to_owned(),
        format!("UPDATE venture_attachments SET filename = 'x' WHERE id = '{}'", att.id),
    ] {
        let r = c.execute(&sql, []);
        assert!(r.is_err(), "trigger ishlamadi: {sql}");
        assert!(r.unwrap_err().to_string().contains("closed_period"));
    }
    // Hech narsa o'zgarmagan.
    assert_eq!(w.ledger(&pid).closed[0].income.minor(), 100);
}

#[test]
fn losses_follow_mudaraba_rules_and_negligence_needs_a_note() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    w.entry(&pid, LedgerKind::Expense, "Mato", 200_000_000, "2026-10-12")
        .unwrap();
    let env = env!(w);
    assert!(ventures::close_period(
        &mut w.db,
        &env,
        &w.ctx,
        &pid,
        Some(d("2026-10-31")),
        Some("  "),
        false,
    )
    .is_err());
    let closed = ventures::close_period(
        &mut w.db,
        &env,
        &w.ctx,
        &pid,
        Some(d("2026-10-31")),
        None,
        false,
    )
    .unwrap();
    let shares: Vec<i64> = closed
        .distribution
        .iter()
        .map(|x| x.amount.minor())
        .collect();
    assert_eq!(shares, vec![-200_000_000, 0]);
    let income = services::income::month_total(
        w.db.conn(),
        &w.ctx,
        services::YearMonth::parse("2026-10").unwrap(),
    )
    .unwrap();
    assert_eq!(income.minor(), 0, "zararda daromad yozilmaydi");

    // Beparvolik izohi bilan zarar ishchi zimmasida.
    w.entry(&pid, LedgerKind::Expense, "Ombor", 100, "2026-11-02")
        .unwrap();
    let c2 = ventures::close_period(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &pid,
        Some(d("2026-11-30")),
        Some("ombor yopilmagan"),
        false,
    )
    .unwrap();
    let s2: Vec<i64> = c2.distribution.iter().map(|x| x.amount.minor()).collect();
    assert_eq!(s2, vec![0, -100]);
}

#[test]
fn attachments_are_validated_and_force_majeure_is_recorded() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    let fm = ventures::add_entry(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &pid,
        NewEntry {
            kind: LedgerKind::Expense,
            description: "Omborni suv bosdi",
            amount: uzs(50_000_000),
            occurred_on: Some(d("2026-10-12")),
            note: Some("kuchli yomg'ir"),
            force_majeure: true,
        },
    )
    .unwrap();
    assert!(fm.force_majeure);
    let bad_kind = ventures::add_entry(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &pid,
        NewEntry {
            kind: LedgerKind::Income,
            description: "x",
            amount: uzs(1),
            occurred_on: None,
            note: None,
            force_majeure: true,
        },
    );
    assert!(bad_kind.is_err());

    let png = b"\x89PNG\r\n\x1a\nDATA".to_vec();
    let env = env!(w);
    assert!(ventures::attach(
        &mut w.db,
        &env,
        &w.ctx,
        &fm.meta.id,
        "a.exe",
        b"MZ....".to_vec()
    )
    .is_err());
    assert!(ventures::attach(&mut w.db, &env, &w.ctx, &fm.meta.id, "a.png", vec![]).is_err());
    let mut huge = b"%PDF-".to_vec();
    huge.resize(ventures::MAX_ATTACHMENT_BYTES + 1, 0);
    assert!(ventures::attach(&mut w.db, &env, &w.ctx, &fm.meta.id, "big.pdf", huge).is_err());
    let a = ventures::attach(
        &mut w.db,
        &env,
        &w.ctx,
        &fm.meta.id,
        "../../etc/passwd\\chek.png",
        png.clone(),
    )
    .unwrap();
    assert_eq!(
        (a.filename.as_str(), a.mime.as_str()),
        ("chek.png", "image/png")
    );
    let (name, mime, data) = ventures::attachment_data(w.db.conn(), &w.ctx, &a.id).unwrap();
    assert_eq!(
        (name.as_str(), mime.as_str(), data),
        ("chek.png", "image/png", png.clone())
    );
    for i in 0..4 {
        ventures::attach(
            &mut w.db,
            &env,
            &w.ctx,
            &fm.meta.id,
            &format!("{i}.png"),
            png.clone(),
        )
        .unwrap();
    }
    assert!(
        ventures::attach(&mut w.db, &env, &w.ctx, &fm.meta.id, "6.png", png).is_err(),
        "5 tadan ortiq emas"
    );

    // Hisobot faqat yopilgan davr uchun.
    let open_id = w.ledger(&pid).open.unwrap().period.meta.id;
    assert!(ventures::report_pdf(w.db.conn(), &env, &w.ctx, &open_id).is_err());
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma",
        100_000_000,
        "2026-10-20",
    )
    .unwrap();
    let closed = w.close(&pid, "2026-10-31").unwrap();
    let pdf = ventures::report_pdf(w.db.conn(), &env!(w), &w.ctx, &closed.period.meta.id).unwrap();
    assert!(pdf.starts_with(b"%PDF-"));
}

#[test]
fn buyout_is_applied_automatically_when_a_period_closes() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let n = NewPartnership {
        details: details("Zamira"),
        name: "Oshxona".into(),
        kind: PartnershipKind::Musharaka,
        term_months: 24,
        report_period: ReportPeriod::Monthly,
        end_clause: "Sotib olinadi".into(),
        dispute_clause: "Oqsoqol".into(),
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
                Some(&me),
            ),
        ],
    };
    let pid = w.activate(n);
    let v = partnerships::view(w.db.conn(), &env!(w), &w.ctx, &pid).unwrap();
    // Karim ulushi (600M) 6 davrda sotib olinadi: davrga 100M.
    partnerships::set_buyout(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &pid,
        &v.parties[0].party.meta.id,
        6,
        Some(d("2026-10-31")),
    )
    .unwrap();
    w.entry(
        &pid,
        LedgerKind::Income,
        "Savdo",
        1_000_000_000,
        "2026-10-12",
    )
    .unwrap();
    let closed = w.close(&pid, "2026-10-31").unwrap();
    // Foyda 1 000M: 60/40 → 600M / 400M. Zamira (to'lovchi) 100M ni Karimga o'tkazadi.
    let shares: Vec<i64> = closed
        .distribution
        .iter()
        .map(|x| x.amount.minor())
        .collect();
    assert_eq!(shares, vec![700_000_000, 300_000_000]);
    let deltas: Vec<i64> = closed
        .distribution
        .iter()
        .map(|x| x.buyout_delta.minor())
        .collect();
    assert_eq!(deltas, vec![100_000_000, -100_000_000]);
    let b = partnerships::buyout_view(w.db.conn(), &env!(w), &w.ctx, &pid)
        .unwrap()
        .unwrap();
    assert_eq!(b.actual.rows[0].remaining.minor(), 500_000_000);
    // Xonadon daromadiga Zamiraning buyoutdan keyingi ulushi yoziladi.
    let income = services::income::month_total(
        w.db.conn(),
        &w.ctx,
        services::YearMonth::parse("2026-10").unwrap(),
    )
    .unwrap();
    assert_eq!(income.minor(), 300_000_000);
}

#[test]
fn craft_ideas_give_three_scenarios_payback_and_a_contract_draft() {
    let mut w = World::new();
    let env = env!(w);
    let idea = crafts::add_idea(
        &mut w.db,
        &env,
        &w.ctx,
        NewIdea {
            name: "Tikuvchilik".into(),
            note: Some("overlock + stol".into()),
            capex: vec![
                ("Overlock".into(), uzs(500_000_000)),
                ("Bichish stoli".into(), uzs(200_000_000)),
                ("Mato".into(), uzs(100_000_000)),
            ],
            income: [uzs(300_000_000), uzs(500_000_000), uzs(700_000_000)],
            expense: [uzs(200_000_000), uzs(250_000_000), uzs(300_000_000)],
            share_bp: Some(6_000),
        },
    )
    .unwrap();
    assert_eq!(idea.capex_total.minor(), 800_000_000);
    let nets: Vec<i64> = idea.scenarios.iter().map(|s| s.net.minor()).collect();
    assert_eq!(nets, vec![100_000_000, 250_000_000, 400_000_000]);
    let after: Vec<i64> = idea
        .scenarios
        .iter()
        .map(|s| s.net_after_share.minor())
        .collect();
    assert_eq!(after, vec![60_000_000, 150_000_000, 240_000_000]);
    let pb: Vec<Option<u32>> = idea.scenarios.iter().map(|s| s.payback_months).collect();
    assert_eq!(pb, vec![Some(14), Some(6), Some(4)]);

    assert!(crafts::add_idea(
        &mut w.db,
        &env!(w),
        &w.ctx,
        NewIdea {
            name: " ".into(),
            note: None,
            capex: vec![],
            income: [uzs(1); 3],
            expense: [uzs(1); 3],
            share_bp: None
        }
    )
    .is_err());

    let draft = crafts::idea_to_contract_draft(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &idea.idea.meta.id,
        "Karim aka",
    )
    .unwrap();
    assert_eq!(draft.partnership.kind, PartnershipKind::Mudaraba);
    assert_eq!(draft.total_capital.minor(), 800_000_000);
    assert_eq!(draft.parties[0].party.share_bp, 4_000);
    assert_eq!(draft.parties[1].party.share_bp, 6_000);
    assert!(draft.self_receives_capital);

    let empty = crafts::add_idea(
        &mut w.db,
        &env!(w),
        &w.ctx,
        NewIdea {
            name: "Bo'sh".into(),
            note: None,
            capex: vec![],
            income: [uzs(1); 3],
            expense: [uzs(1); 3],
            share_bp: None,
        },
    )
    .unwrap();
    assert!(
        crafts::idea_to_contract_draft(&mut w.db, &env!(w), &w.ctx, &empty.idea.meta.id, "X")
            .is_err()
    );
    crafts::remove_idea(&mut w.db, &env!(w), &w.ctx, &idea.idea.meta.id).unwrap();
    assert_eq!(crafts::list_ideas(w.db.conn(), &w.ctx).unwrap().len(), 1);
}

#[test]
fn offer_check_table_is_applied() {
    let ok = OfferAnswers {
        guaranteed_profit: false,
        loss_shared: true,
        real_goods_or_work: true,
        requires_recruiting: false,
        pressure_to_hurry: false,
        written_contract: true,
    };
    assert_eq!(crafts::check_offer(ok).verdict, Verdict::Green);
    assert_eq!(
        crafts::check_offer(OfferAnswers {
            guaranteed_profit: true,
            ..ok
        })
        .verdict,
        Verdict::Red
    );
    assert_eq!(
        crafts::check_offer(OfferAnswers {
            pressure_to_hurry: true,
            ..ok
        })
        .verdict,
        Verdict::Yellow
    );
    let _ = MemberRole::Adult;
}

fn agreement_of(w: &World, pid: &str) -> String {
    services::agreements::agreement_of_partnership(w.db.conn(), &w.ctx, pid)
        .unwrap()
        .unwrap()
        .meta
        .id
}

fn party_id(w: &World, pid: &str, name: &str) -> String {
    let v = services::partnerships::view(w.db.conn(), &env!(w), &w.ctx, pid).unwrap();
    v.parties
        .iter()
        .find(|p| p.party.name == name)
        .unwrap()
        .party
        .meta
        .id
        .clone()
}

fn invalid_message(e: &ServiceError) -> &'static str {
    match e {
        ServiceError::Invalid(m) => m,
        other => panic!("kutilgan xato emas: {other:?}"),
    }
}

/// SPEC 2F.8: nizo ochiq bo'lsa taqsimot bloklanadi; hakam qarori bilan nizo yopiladi va davr yopiladi.
#[test]
fn dispute_blocks_distribution_until_the_arbiter_decides() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma 1",
        500_000_000,
        "2026-10-12",
    )
    .unwrap();
    let agreement = agreement_of(&w, &pid);
    let karim = party_id(&w, &pid, "Karim aka");
    services::events::open_dispute(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        &karim,
        "Foyda hisobi",
        "Ulush 60/40 emas, 50/50 bo'lishi kerak edi",
    )
    .unwrap();
    let blocked = w.close(&pid, "2026-10-14").unwrap_err();
    assert!(invalid_message(&blocked).contains("nizoli kelishuvda"));
    services::events::resolve_dispute(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        "Hakam: foyda shartnoma bo'yicha qayta hisoblansin",
    )
    .unwrap();
    w.close(&pid, "2026-10-14").unwrap();
    let kinds: Vec<_> = services::journal::entries(w.db.conn(), &w.ctx, &agreement)
        .unwrap()
        .iter()
        .map(|e| e.kind)
        .collect();
    assert!(kinds.contains(&JournalKind::DisputeOpened));
    assert!(kinds.contains(&JournalKind::DisputeResolved));
}

/// SPEC 2F.7: davr foydasi oxirgi 3 davr o'rtachasidan 200%+ bo'lsa, tasdiqsiz yopilmaydi; tasdiq jurnalga tushadi.
#[test]
fn profit_spike_needs_acknowledgement_and_is_journaled() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    for (on, end) in [
        ("2026-10-12", "2026-10-14"),
        ("2026-10-16", "2026-10-20"),
        ("2026-10-22", "2026-10-25"),
    ] {
        w.entry(&pid, LedgerKind::Income, "Buyurtma", 100_000_000, on)
            .unwrap();
        w.close(&pid, end).unwrap();
    }
    assert!(
        !w.ledger(&pid).spike_alert,
        "tarix yetarli, lekin hali foyda oddiy"
    );
    w.entry(
        &pid,
        LedgerKind::Income,
        "Katta buyurtma",
        1_000_000_000,
        "2026-10-27",
    )
    .unwrap();
    assert!(w.ledger(&pid).spike_alert);
    let refused = w.close(&pid, "2026-10-30").unwrap_err();
    assert!(invalid_message(&refused).contains("katta foyda"));
    w.close_acked(&pid, "2026-10-30", true).unwrap();
    let agreement = agreement_of(&w, &pid);
    let ack = services::journal::entries(w.db.conn(), &w.ctx, &agreement)
        .unwrap()
        .into_iter()
        .any(|e| e.kind == JournalKind::ProfitAlertAck);
    assert!(ack, "tasdiq jurnalga yozilishi kerak");
}

/// SPEC 2F.4: «bajara olmayapman» — mas'ul tomon nomidan, band bilan birga jurnalga yoziladi.
#[test]
fn duty_incident_is_journaled_for_the_owner_with_the_clause() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    let agreement = agreement_of(&w, &pid);
    let zamira = party_id(&w, &pid, "Zamira");
    let e = services::events::report_duty_incident(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        0,
        "Yo'l yopiq edi, hisobot kechikdi",
        "Ertaga topshiraman",
    )
    .unwrap();
    assert_eq!(e.kind, JournalKind::DutyIncident);
    assert_eq!(e.party_id.as_deref(), Some(zamira.as_str()));
    assert_eq!(e.reference.as_deref(), Some("v1/duty:0"));
    assert!(e.note.contains("Taklif: Ertaga topshiraman"));
    let no_such =
        services::events::report_duty_incident(&mut w.db, &env!(w), &w.ctx, &agreement, 7, "x", "")
            .unwrap_err();
    assert_eq!(invalid_message(&no_such), "bunday vazifa bandi yo'q");
}

/// SPEC 2F.5, 2F.6: oylik ko'rik — barcha tomonlar javob beradi, yakunda zanjir boshi qayd etiladi.
#[test]
fn monthly_review_records_answers_and_seals_the_chain_head() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma 1",
        500_000_000,
        "2026-10-12",
    )
    .unwrap();
    let agreement = agreement_of(&w, &pid);
    let karim = party_id(&w, &pid, "Karim aka");
    let zamira = party_id(&w, &pid, "Zamira");
    services::review::record_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        "2026-10",
        &karim,
        services::review::ReviewAnswer::Agree,
    )
    .unwrap();
    let early =
        services::review::close(&mut w.db, &env!(w), &w.ctx, &agreement, "2026-10").unwrap_err();
    assert!(invalid_message(&early).contains("barcha tomonlar"));
    let blank = services::review::record_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        "2026-10",
        &zamira,
        services::review::ReviewAnswer::Object("  ".into()),
    )
    .unwrap_err();
    assert!(invalid_message(&blank).contains("izoh"));
    services::review::record_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        "2026-10",
        &zamira,
        services::review::ReviewAnswer::Object("Yo'l xarajati hisobga olinmagan".into()),
    )
    .unwrap();
    let open = services::review::view(w.db.conn(), &w.ctx, &agreement, "2026-10").unwrap();
    assert!(!open.closed);
    assert_eq!(open.ledger.len(), 1);
    let zam = open.parties.iter().find(|p| p.party_id == zamira).unwrap();
    assert_eq!(zam.agree, Some(false));
    assert_eq!(zam.note.as_deref(), Some("Yo'l xarajati hisobga olinmagan"));
    services::review::close(&mut w.db, &env!(w), &w.ctx, &agreement, "2026-10").unwrap();
    let sealed = services::review::view(w.db.conn(), &w.ctx, &agreement, "2026-10").unwrap();
    assert!(sealed.closed);
    assert_eq!(sealed.head_matches, Some(true));
    let after = services::review::record_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        "2026-10",
        &karim,
        services::review::ReviewAnswer::Agree,
    )
    .unwrap_err();
    assert!(invalid_message(&after).contains("yakunlangan"));
    let pdf = services::review::pdf(w.db.conn(), &w.ctx, &agreement, "2026-10").unwrap();
    assert!(pdf.starts_with(b"%PDF"));
}

/// SPEC 2F.6, D13A qabul mezoni: yozuv o'zgartirilsa, bayonnomadagi zanjir boshi bilan solishtirilganda aniqlanadi.
#[test]
fn tampering_is_detected_against_the_recorded_chain_head() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    let income = w
        .entry(
            &pid,
            LedgerKind::Income,
            "Buyurtma 1",
            500_000_000,
            "2026-10-12",
        )
        .unwrap();
    let agreement = agreement_of(&w, &pid);
    for who in [
        party_id(&w, &pid, "Karim aka"),
        party_id(&w, &pid, "Zamira"),
    ] {
        services::review::record_answer(
            &mut w.db,
            &env!(w),
            &w.ctx,
            &agreement,
            "2026-10",
            &who,
            services::review::ReviewAnswer::Agree,
        )
        .unwrap();
    }
    services::review::close(&mut w.db, &env!(w), &w.ctx, &agreement, "2026-10").unwrap();
    let before = services::review::view(w.db.conn(), &w.ctx, &agreement, "2026-10").unwrap();
    assert_eq!(before.head_matches, Some(true));
    assert!(before.chain.broken_seq.is_none());

    // Sinov uchun: triggerni o'chirib, yozuvning matnini o'zgartiramiz (xesh ustuni o'zgarmaydi).
    w.db.conn()
        .execute_batch("DROP TRIGGER trg_journal_upd;")
        .unwrap();
    let journal_id: String =
        w.db.conn()
            .query_row(
                "SELECT id FROM journal_entries WHERE reference = ?1",
                [income.meta.id.as_str()],
                |r| r.get(0),
            )
            .unwrap();
    let changed =
        w.db.conn()
            .execute(
                "UPDATE journal_entries SET note = 'Soxta izoh' WHERE id = ?1",
                [journal_id.as_str()],
            )
            .unwrap();
    assert_eq!(changed, 1, "tekshiriladigan yozuv topilishi kerak");

    let after = services::review::view(w.db.conn(), &w.ctx, &agreement, "2026-10").unwrap();
    assert!(
        after.chain.broken_seq.is_some(),
        "zanjir buzilishi aniqlanishi kerak"
    );
    assert_eq!(
        after.head_matches,
        Some(false),
        "bayonnoma boshi mos kelmasligi kerak"
    );
    let doc = services::review::pdf(w.db.conn(), &w.ctx, &agreement, "2026-10").unwrap();
    assert!(doc.starts_with(b"%PDF"));
}

/// SPEC 2F.8: hakam ish papkasi — nizo ochilgach PDF chiqadi (mundarija bilan); nizo bo'lmasa ham xato emas.
#[test]
fn arbiter_folder_pdf_is_produced_while_a_dispute_is_open() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma 1",
        500_000_000,
        "2026-10-12",
    )
    .unwrap();
    let agreement = agreement_of(&w, &pid);
    let karim = party_id(&w, &pid, "Karim aka");
    services::events::open_dispute(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        &karim,
        "Foyda hisobi",
        "Ulush 60/40 emas, 50/50 bo'lishi kerak edi",
    )
    .unwrap();
    let pdf = services::events::folder_pdf(w.db.conn(), &w.ctx, &agreement).unwrap();
    assert!(pdf.starts_with(b"%PDF"));
}

/// D13A: markaz yangilash eslatmasini (30 kun ichida) va joriy oy ko'rigi holatini ko'rsatadi.
#[test]
fn agreement_center_shows_the_yearly_reminder_and_the_monthly_state() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let mut input = mudaraba_worker(&me);
    input.details.review_date = Some(d("2026-10-20"));
    w.activate(input);
    let rows = services::events::center(w.db.conn(), &env!(w), &w.ctx).unwrap();
    let row = rows.iter().find(|r| r.title == "Ustaxona").unwrap();
    assert_eq!(row.days_to_review, Some(9));
    assert_eq!(row.monthly_closed, Some(false));
    assert!(!row.dispute_open);
}

/// D14: import oldidan jurnal zanjirini tekshiradi; mahalliy zanjirdan ayrilgan (fork) bo'lsa, hech narsa yozilmaydi.
#[test]
fn journal_fork_stops_the_import_and_nothing_is_written() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma 1",
        500_000_000,
        "2026-10-12",
    )
    .unwrap();
    let agreement = agreement_of(&w, &pid);
    let now = domain::Clock::now(&w.clock);
    let doc =
        storage::interchange::export(w.db.conn(), &w.ctx.household_id, "dev", now, None).unwrap();
    // Mahalliy zanjir boshqa yo'l bilan o'zgargan (fork): birinchi yozuvning xeshi.
    w.db.conn()
        .execute_batch("DROP TRIGGER trg_journal_upd;")
        .unwrap();
    w.db.conn()
        .execute(
            "UPDATE journal_entries SET hash = ?1 WHERE agreement_id = ?2 AND seq = 1",
            [("f".repeat(64)).as_str(), agreement.as_str()],
        )
        .unwrap();
    let report = storage::interchange::apply(w.db.conn(), &doc, Some(&w.ctx.household_id)).unwrap();
    assert!(report
        .conflicts
        .iter()
        .any(|c| c.kind == storage::interchange::ConflictKind::Journal));
    assert_eq!((report.inserted, report.updated), (0, 0));
    assert_eq!(report.forks.len(), 1);
    let fork = &report.forks[0];
    assert_eq!(fork.agreement_id, agreement);
    assert_eq!(fork.diverged_seq, 1);
    assert_eq!(fork.local.first_seq, 1);
    assert_eq!(fork.local.count, fork.incoming.count);
    assert_eq!(fork.incoming.last_seq, fork.incoming.count);
    assert_eq!(fork.local.head.len(), 64);
}

/// SPEC 2F.8, D14: ayrilib ketgan kelishuvning mahalliy nusxasida tomon nizo ochadi; taqsimot bloklanadi.
#[test]
fn fork_can_be_opened_as_a_dispute_on_the_local_copy() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma 1",
        500_000_000,
        "2026-10-12",
    )
    .unwrap();
    let agreement = agreement_of(&w, &pid);
    let karim = party_id(&w, &pid, "Karim aka");
    let now = domain::Clock::now(&w.clock);
    let doc =
        storage::interchange::export(w.db.conn(), &w.ctx.household_id, "dev", now, None).unwrap();
    w.db.conn()
        .execute_batch("DROP TRIGGER trg_journal_upd;")
        .unwrap();
    w.db.conn()
        .execute(
            "UPDATE journal_entries SET hash = ?1 WHERE agreement_id = ?2 AND seq = 1",
            [("f".repeat(64)).as_str(), agreement.as_str()],
        )
        .unwrap();
    let report = storage::interchange::apply(w.db.conn(), &doc, Some(&w.ctx.household_id)).unwrap();
    assert_eq!(report.forks.len(), 1);
    services::events::open_dispute(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &agreement,
        &karim,
        "Kelishuv jurnali ayrilib ketdi",
        "Ikki nusxa farq qilyapti; hakam belgilasin.",
    )
    .unwrap();
    let view = services::agreements::view(w.db.conn(), &w.ctx, &agreement).unwrap();
    assert_eq!(view.agreement.status, domain::AgreementStatus::InDispute);
    let entries = services::journal::entries(w.db.conn(), &w.ctx, &agreement).unwrap();
    assert!(entries
        .iter()
        .any(|e| e.kind == domain::JournalKind::DisputeOpened));
}

/// D14: kelgan jurnal yozuvi o'zgartirilgan bo'lsa, zanjir tekshiruvi importni rad etadi.
#[test]
fn tampered_incoming_journal_is_refused() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    w.entry(
        &pid,
        LedgerKind::Income,
        "Buyurtma 1",
        500_000_000,
        "2026-10-12",
    )
    .unwrap();
    let now = domain::Clock::now(&w.clock);
    let mut doc =
        storage::interchange::export(w.db.conn(), &w.ctx.household_id, "dev", now, None).unwrap();
    let rows = &mut doc
        .tables
        .iter_mut()
        .find(|t| t.name == "journal_entries")
        .unwrap()
        .rows;
    rows[0].insert("note".into(), "Soxta izoh".into());
    let refused = storage::interchange::apply(w.db.conn(), &doc, Some(&w.ctx.household_id));
    assert!(refused.is_err(), "o'zgartirilgan zanjir rad etilishi kerak");
}

/// SPEC 2F.10: oilaviy kelishuv — faqat kattalarning PIN bilan tasdig'i; bola tasdiqlay olmaydi, tomon imzosi o'tmaydi.
#[test]
fn family_agreement_is_confirmed_by_adult_pins_only() {
    use services::family_agreements::{self as family, FamilyDuty, NewFamilyAgreement};
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let dilshod = services::members::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        "Dilshod",
        domain::MemberRole::Adult,
    )
    .unwrap()
    .meta
    .id;
    members::set_pin(&mut w.db, &env!(w), &w.ctx, &dilshod, "222222", FAST).unwrap();
    let kid = services::members::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        "Bola",
        domain::MemberRole::Child,
    )
    .unwrap()
    .meta
    .id;
    let created = family::create(
        &mut w.db,
        &env!(w),
        &w.ctx,
        NewFamilyAgreement {
            title: "Uy ishlari".into(),
            adult_ids: vec![me.clone(), dilshod.clone()],
            duties: vec![
                FamilyDuty {
                    text: "Ovqat pishirish".into(),
                    owner_member_id: dilshod.clone(),
                    if_not_done: "Ertasi kuni o'zi tuzatadi".into(),
                },
                FamilyDuty {
                    text: "Hovli tozalash".into(),
                    owner_member_id: me.clone(),
                    if_not_done: "Dam olish kuni bajariladi".into(),
                },
            ],
            custody_place: "Uy xazinasi".into(),
            review_date: None,
            template: None,
        },
    )
    .unwrap();
    let id = created.agreement.meta.id.clone();
    assert!(
        created.completeness.is_complete(),
        "{:?}",
        created.completeness
    );
    assert!(family::consent(&mut w.db, &env!(w), &w.ctx, &id, &kid, "000000").is_err());
    assert!(family::consent(&mut w.db, &env!(w), &w.ctx, &id, &dilshod, "000000").is_err());
    let by_party = services::agreements::sign(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        services::agreements::AgreementSigner::Party {
            party_id: me.clone(),
            pin: Some("111111".into()),
        },
    );
    assert!(by_party.is_err(), "oilada tomon imzosi o'tmasin");
    family::consent(&mut w.db, &env!(w), &w.ctx, &id, &me, "111111").unwrap();
    let both = family::consent(&mut w.db, &env!(w), &w.ctx, &id, &dilshod, "222222").unwrap();
    assert_eq!(both.agreement.status, domain::AgreementStatus::Signed);
    let active = family::activate(&mut w.db, &env!(w), &w.ctx, &id).unwrap();
    assert_eq!(active.agreement.status, domain::AgreementStatus::Active);
    assert_eq!(family::list(w.db.conn(), &w.ctx).unwrap().len(), 1);
}

/// SPEC 2F.10, D13A: oilaviy oylik ko'rik. Javob faqat kattaning o'z PIN'i bilan yoziladi; boshqa katta
/// nomidan, PIN'siz yoki oddiy ko'rik yo'li orqali yozilmaydi. Ikki javobdan keyin ko'rik yopiladi.
#[test]
fn family_review_needs_each_adults_own_pin() {
    use services::family_agreements::{
        self as family, FamilyDuty, FamilyReply, NewFamilyAgreement,
    };
    use services::review::ReviewAnswer;
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let dilshod = services::members::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        "Dilshod",
        domain::MemberRole::Adult,
    )
    .unwrap()
    .meta
    .id;
    members::set_pin(&mut w.db, &env!(w), &w.ctx, &dilshod, "222222", FAST).unwrap();
    let kid = services::members::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        "Bola",
        domain::MemberRole::Child,
    )
    .unwrap()
    .meta
    .id;
    let id = family::create(
        &mut w.db,
        &env!(w),
        &w.ctx,
        NewFamilyAgreement {
            title: "Uy ishlari".into(),
            adult_ids: vec![me.clone(), dilshod.clone()],
            duties: vec![FamilyDuty {
                text: "Ovqat pishirish".into(),
                owner_member_id: dilshod.clone(),
                if_not_done: "Ertasi kuni o'zi tuzatadi".into(),
            }],
            custody_place: "Uy xazinasi".into(),
            review_date: None,
            template: None,
        },
    )
    .unwrap()
    .agreement
    .meta
    .id;
    family::consent(&mut w.db, &env!(w), &w.ctx, &id, &me, "111111").unwrap();
    family::consent(&mut w.db, &env!(w), &w.ctx, &id, &dilshod, "222222").unwrap();
    family::activate(&mut w.db, &env!(w), &w.ctx, &id).unwrap();
    let period = "2026-10";
    let reply = |member: &str, pin: &str, answer: ReviewAnswer| FamilyReply {
        member_id: member.to_owned(),
        pin: pin.to_owned(),
        answer,
    };
    // Izohsiz e'tiroz PIN tekshirilishidan oldin rad etiladi
    let blank = family::review_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        period,
        reply(&dilshod, "222222", ReviewAnswer::Object(" ".into())),
    )
    .unwrap_err();
    assert!(invalid_message(&blank).contains("izoh"));
    // Dilshod nomidan «me» PIN'i bilan yozib bo'lmaydi
    let forged = family::review_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        period,
        reply(&dilshod, "111111", ReviewAnswer::Agree),
    )
    .unwrap_err();
    assert!(matches!(forged, ServiceError::WrongPin));
    // Bola kattalar qatorida emas
    let child = family::review_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        period,
        reply(&kid, "000000", ReviewAnswer::Agree),
    )
    .unwrap_err();
    assert!(invalid_message(&child).contains("tomon"));
    // Oddiy (sheriklik) ko'rik yo'li oilaviy kelishuvda ishlamaydi
    let plain = services::review::record_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        period,
        &dilshod,
        ReviewAnswer::Agree,
    )
    .unwrap_err();
    assert!(invalid_message(&plain).contains("PIN"));
    family::review_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        period,
        reply(&me, "111111", ReviewAnswer::Agree),
    )
    .unwrap();
    family::review_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        period,
        reply(
            &dilshod,
            "222222",
            ReviewAnswer::Object("Ovqat kechikdi".into()),
        ),
    )
    .unwrap();
    let open = services::review::view(w.db.conn(), &w.ctx, &id, period).unwrap();
    let objector = open.parties.iter().find(|p| p.party_id == dilshod).unwrap();
    assert_eq!(objector.agree, Some(false));
    assert_eq!(objector.note.as_deref(), Some("Ovqat kechikdi"));
    services::review::close(&mut w.db, &env!(w), &w.ctx, &id, period).unwrap();
    let sealed = services::review::view(w.db.conn(), &w.ctx, &id, period).unwrap();
    assert!(sealed.closed);
    assert_eq!(sealed.head_matches, Some(true));
    let late = family::review_answer(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        period,
        reply(&me, "111111", ReviewAnswer::Agree),
    )
    .unwrap_err();
    assert!(invalid_message(&late).contains("yakunlangan"));
    let pdf = services::review::pdf(w.db.conn(), &w.ctx, &id, period).unwrap();
    assert!(pdf.starts_with(b"%PDF"));
}

/// SPEC 2F.4, D13A: oilaviy vazifa hodisasini faqat shu bandning mas'ul kattasi, o'z PIN'i bilan yozadi.
#[test]
fn family_duty_incident_is_written_by_the_owner_with_the_pin() {
    use services::family_agreements::{
        self as family, FamilyDuty, FamilyIncident, NewFamilyAgreement,
    };
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let dilshod = services::members::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        "Dilshod",
        domain::MemberRole::Adult,
    )
    .unwrap()
    .meta
    .id;
    members::set_pin(&mut w.db, &env!(w), &w.ctx, &dilshod, "222222", FAST).unwrap();
    let id = family::create(
        &mut w.db,
        &env!(w),
        &w.ctx,
        NewFamilyAgreement {
            title: "Uy ishlari".into(),
            adult_ids: vec![me.clone(), dilshod.clone()],
            duties: vec![FamilyDuty {
                text: "Ovqat pishirish".into(),
                owner_member_id: dilshod.clone(),
                if_not_done: "Ertasi kuni o'zi tuzatadi".into(),
            }],
            custody_place: "Uy xazinasi".into(),
            review_date: None,
            template: None,
        },
    )
    .unwrap()
    .agreement
    .meta
    .id;
    family::consent(&mut w.db, &env!(w), &w.ctx, &id, &me, "111111").unwrap();
    family::consent(&mut w.db, &env!(w), &w.ctx, &id, &dilshod, "222222").unwrap();
    family::activate(&mut w.db, &env!(w), &w.ctx, &id).unwrap();
    let incident = |member: &str, pin: &str, reason: &str| FamilyIncident {
        member_id: member.to_owned(),
        pin: pin.to_owned(),
        duty_index: 0,
        reason: reason.to_owned(),
        proposal: "Ertaga o'zim pishiraman".to_owned(),
    };
    // Boshqa katta bandning mas'uli emas: PIN'i to'g'ri bo'lsa ham yozilmaydi
    let other = family::report_incident(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        incident(&me, "111111", "Kechikdi"),
    )
    .unwrap_err();
    assert!(invalid_message(&other).contains("mas'ul"));
    // Sabab bo'sh bo'lsa, PIN tekshirilishidan oldin rad etiladi
    let blank = family::report_incident(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        incident(&dilshod, "222222", "  "),
    )
    .unwrap_err();
    assert!(invalid_message(&blank).contains("sabab"));
    // Noto'g'ri PIN: hech narsa yozilmaydi
    let forged = family::report_incident(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        incident(&dilshod, "111111", "Kechikdi"),
    )
    .unwrap_err();
    assert!(matches!(forged, ServiceError::WrongPin));
    // Oddiy (sheriklik) yo'li oilaviy kelishuvda ishlamaydi
    let plain =
        services::events::report_duty_incident(&mut w.db, &env!(w), &w.ctx, &id, 0, "Kechikdi", "")
            .unwrap_err();
    assert!(invalid_message(&plain).contains("PIN"));
    let entry = family::report_incident(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &id,
        incident(&dilshod, "222222", "Ovqat tayyor emas"),
    )
    .unwrap();
    assert!(matches!(entry.kind, domain::JournalKind::DutyIncident));
    assert_eq!(entry.party_id.as_deref(), Some(dilshod.as_str()));
    assert_eq!(
        entry.note,
        "Ovqat tayyor emas. Taklif: Ertaga o'zim pishiraman"
    );
    let all = services::journal::entries(w.db.conn(), &w.ctx, &id).unwrap();
    assert_eq!(
        all.iter()
            .filter(|e| e.kind == domain::JournalKind::DutyIncident)
            .count(),
        1
    );
}

/// SPEC 2B.3, 2F.10: «havas chegarasi» shabloni havas moduli bilan bog'lanadi. Shablon saqlanadi, chegara
/// nusxalanmaydi va faol chegara faqat barcha kattalar o'z PIN'i bilan rozi bo'lgach ko'rinadi.
#[test]
fn family_desire_limit_reads_the_havas_limit_only_after_every_adult_consents() {
    use domain::FamilyTemplate;
    use services::family_agreements::{self as family, FamilyDuty, NewFamilyAgreement};
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let dilshod = services::members::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        "Dilshod",
        domain::MemberRole::Adult,
    )
    .unwrap()
    .meta
    .id;
    members::set_pin(&mut w.db, &env!(w), &w.ctx, &dilshod, "222222", FAST).unwrap();
    let id = family::create(
        &mut w.db,
        &env!(w),
        &w.ctx,
        NewFamilyAgreement {
            title: "Havas chegarasi".into(),
            adult_ids: vec![me.clone(), dilshod.clone()],
            duties: vec![FamilyDuty {
                text: "Oylik havas chegarasiga rioya qilish".into(),
                owner_member_id: me.clone(),
                if_not_done: "Oila kengashida birga qayta ko'rib chiqiladi".into(),
            }],
            custody_place: "Uy xazinasi".into(),
            review_date: None,
            template: Some(FamilyTemplate::DesireLimit),
        },
    )
    .unwrap()
    .agreement
    .meta
    .id;
    family::consent(&mut w.db, &env!(w), &w.ctx, &id, &me, "111111").unwrap();
    family::consent(&mut w.db, &env!(w), &w.ctx, &id, &dilshod, "222222").unwrap();
    family::activate(&mut w.db, &env!(w), &w.ctx, &id).unwrap();
    let stored = family::list(w.db.conn(), &w.ctx).unwrap();
    assert_eq!(
        stored[0].agreement.family_template,
        Some(FamilyTemplate::DesireLimit)
    );
    let none = family::havas_link(w.db.conn(), &w.ctx).unwrap();
    assert_eq!((none.limit, none.pending), (None, false));
    // Men taklif qilaman: Dilshod hali rozi emas, chegara faol emas, lekin kutilmoqda
    let proposal =
        services::havas::propose(&mut w.db, &env!(w), &w.ctx, &me, "111111", uzs(1_500_000))
            .unwrap();
    let waiting = family::havas_link(w.db.conn(), &w.ctx).unwrap();
    assert_eq!((waiting.limit, waiting.pending), (None, true));
    // Dilshod rozi bo'lgach chegara faol bo'ladi
    services::havas::consent(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &proposal.meta.id,
        &dilshod,
        "222222",
    )
    .unwrap();
    let active = family::havas_link(w.db.conn(), &w.ctx).unwrap();
    assert_eq!(
        (active.limit, active.pending),
        (Some(uzs(1_500_000)), false)
    );
}

/// D13A: «o'zgarishsiz tasdiqlash» yangi versiya — barcha tomonlar qayta tasdiqlaydi, faol sheriklik qoralamaga qaytadi.
#[test]
fn yearly_confirmation_is_a_new_version_that_needs_new_signatures() {
    let mut w = World::new();
    let me = w.ctx.member_id.clone();
    let pid = w.activate(mudaraba_worker(&me));
    let v = services::partnerships::confirm_unchanged(&mut w.db, &env!(w), &w.ctx, &pid).unwrap();
    assert_eq!(v.partnership.version, 2);
    assert_eq!(v.partnership.status, domain::PartnershipStatus::Draft);
    let agreement = agreement_of(&w, &pid);
    let av = services::agreements::view(w.db.conn(), &w.ctx, &agreement).unwrap();
    assert_eq!(av.agreement.current_version, 2);
    assert!(
        !av.missing_signatures.is_empty(),
        "tomonlar qayta imzolashi kerak"
    );
    assert!(av
        .versions
        .iter()
        .any(|x| x.change_note.as_deref() == Some("O'zgarishsiz tasdiqlash")));
}
