//! «Anvar» ssenariysi (DESKTOP_PROMPT D15): daromad → audit → havas chegarasi → obuna bekor qilish →
//! qarz → 70/20/10 → payoff → qarz yopilishi → darvoza ochilishi → sheriklik → taqsimot → eksport.
//! Xizmatlar qatlamida boshidan oxirigacha (UI/Windows'siz); haqiqiy oyna E2E — `desktop/e2e/`.
#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, BillingPeriod, BudgetMode, CapitalKind, Clock, CreditorType, GateReason, IdGen,
    IncomeSourceType, LedgerKind, OffsetDateTime, PartnershipKind, PartnershipStatus, PartyRole,
    PaymentChannel, ReportPeriod, ScheduleKind,
};
use money::{Currency, Money};
use security::KdfParams;
use services::{
    audit, categories, debts, guard, havas, income, interchange, members,
    partnerships::{self, NewCapital, NewPartnership, NewParty, Signer},
    payoff, recovery, setup, subscriptions, vault,
    ventures::{self, NewEntry},
    Ctx, Env, ServiceError, YearMonth,
};
use storage::{interchange as doc_io, Database};

const FAST: KdfParams = KdfParams::fast_for_tests();
const PIN: &str = "111111";

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
            device_id: "anvar-pc",
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

fn d(s: &str) -> domain::Date {
    date_from_str(s).unwrap()
}

fn party(name: &str, role: PartyRole, share: u32, cap: i64, member: Option<&str>) -> NewParty {
    NewParty {
        name: name.into(),
        role,
        share_bp: share,
        member_id: member.map(str::to_owned),
        capital: if cap > 0 {
            vec![NewCapital {
                description: "Naqd pul".into(),
                kind: CapitalKind::Cash,
                value: uzs(cap),
            }]
        } else {
            vec![]
        },
        fixed_return: None,
    }
}

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

fn mudaraba(name: &str, parties: Vec<NewParty>) -> NewPartnership {
    let owner = parties
        .iter()
        .find(|p| p.role == PartyRole::Worker)
        .map_or_else(String::new, |p| p.name.clone());
    NewPartnership {
        details: details(&owner),
        name: name.into(),
        kind: PartnershipKind::Mudaraba,
        term_months: 12,
        report_period: ReportPeriod::Monthly,
        end_clause: "Qaytariladi".into(),
        dispute_clause: "Oqsoqol".into(),
        witnesses: vec![],
        parties,
    }
}

impl World {
    fn sign_all(&mut self, id: &str) {
        let me = self.ctx.member_id.clone();
        let v = partnerships::view(self.db.conn(), &env!(self), &self.ctx, id).unwrap();
        for p in &v.parties {
            let pin = p.party.member_id.as_ref().map(|_| PIN.to_owned());
            partnerships::sign(
                &mut self.db,
                &env!(self),
                &self.ctx,
                id,
                Signer::Party {
                    party_id: p.party.meta.id.clone(),
                    pin,
                },
            )
            .unwrap();
        }
        for w in &v.witnesses {
            let name = w.name.clone();
            partnerships::sign(
                &mut self.db,
                &env!(self),
                &self.ctx,
                id,
                Signer::Witness { name },
            )
            .unwrap();
        }
        partnerships::sign(&mut self.db, &env!(self), &self.ctx, id, Signer::Arbiter).unwrap();
        if v.self_receives_capital {
            partnerships::family_consent(&mut self.db, &env!(self), &self.ctx, id, &me, PIN)
                .unwrap();
        }
    }
}

#[test]
fn anvar_full_journey() {
    let mut db = Database::open_in_memory(&[9; 32]).unwrap();
    let clock = TestClock(Cell::new(time::macros::datetime!(2026-10-07 05:00 UTC)));
    let ids = Seq(Cell::new(1));
    let ctx = setup::ensure_household(
        &mut db,
        &Env {
            clock: &clock,
            ids: &ids,
            device_id: "anvar-pc",
        },
    )
    .unwrap();
    let mut w = World {
        db,
        clock,
        ids,
        ctx,
    };
    let me = w.ctx.member_id.clone();
    members::set_pin(&mut w.db, &env!(w), &w.ctx, &me, PIN, FAST).unwrap();

    // 1) AUDIT: uch oy xarajatlari (Oziq-ovqat va Kiyim — ehtiyoj, «Gazak» — havas).
    for ym in [(2026, 7), (2026, 8), (2026, 9)] {
        let ym = YearMonth {
            year: ym.0,
            month: time::Month::try_from(u8::try_from(ym.1).unwrap()).unwrap(),
        };
        for (cat, amount) in [
            ("Oziq-ovqat", 1_000_000),
            ("Kiyim", 500_000),
            ("Gazak va ichimlik", 300_000),
        ] {
            let c = categories::by_name(w.db.conn(), &w.ctx, cat)
                .unwrap()
                .unwrap()
                .meta
                .id;
            audit::set_category_total(&mut w.db, &env!(w), &w.ctx, ym, &c, uzs(amount)).unwrap();
        }
    }
    let sept = YearMonth {
        year: 2026,
        month: time::Month::September,
    };
    let ov = audit::overview(w.db.conn(), &w.ctx, sept).unwrap();
    assert_eq!(ov.expenses, uzs(1_800_000));

    // 2) HAVAS CHEGARASI: yagona kattaning PIN'i bilan kelishiladi.
    havas::propose(&mut w.db, &env!(w), &w.ctx, &me, PIN, uzs(200_000)).unwrap();
    let (effective, pending) = havas::effective_and_pending(w.db.conn(), &w.ctx).unwrap();
    assert_eq!(effective.unwrap().amount, uzs(200_000));
    assert!(pending.is_none());
    let rep = havas::report(w.db.conn(), &w.ctx, sept).unwrap();
    assert_eq!(rep.limit, Some(uzs(200_000)));
    assert_eq!(rep.spent, uzs(300_000), "havas chegaradan oshgan");

    // 3) OBUNA BEKOR QILISH: bir oylik narx «qutqarilgan pul»ga yoziladi.
    let sub = subscriptions::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        "Kino",
        uzs(5_000_000),
        BillingPeriod::Monthly,
        None,
    )
    .unwrap();
    let rescue = subscriptions::cancel(&mut w.db, &env!(w), &w.ctx, &sub.meta.id)
        .unwrap()
        .unwrap();
    assert_eq!(rescue.amount, uzs(5_000_000));

    // 4) DAROMAD: taklif qilingan ulush (5%) «Kelajagim»ga.
    let sug = income::suggest(w.db.conn(), &env!(w), &w.ctx, uzs(20_000_000)).unwrap();
    assert_eq!(sug.share, uzs(1_000_000));
    let rec = income::record(
        &mut w.db,
        &env!(w),
        &w.ctx,
        income::NewIncome {
            amount: uzs(20_000_000),
            source: "ORDER".into(),
            channel: PaymentChannel::Cash,
            received_on: None,
            share: None,
            member_id: None,
            source_type: Some(IncomeSourceType::Ter),
        },
    )
    .unwrap();
    assert_eq!(rec.share, uzs(1_000_000));
    assert_eq!(vault::balance(w.db.conn(), &w.ctx).unwrap(), uzs(1_000_000));

    // 5) QARZ (ustamali) → darvoza yopiq va sababi aniq.
    let debt = debts::add(
        &mut w.db,
        &env!(w),
        &w.ctx,
        debts::NewDebt {
            creditor: "Do'kon".into(),
            creditor_type: CreditorType::Shop,
            reason: Some("Mato".into()),
            principal: uzs(30_000_000),
            schedule_kind: ScheduleKind::FixedMarkup,
            schedule: debts::ScheduleInput::FixedMarkup {
                markup: uzs(3_000_000),
                months: 3,
                first_due: d("2026-11-07"),
            },
            borrowed_on: None,
            early_repayment_terms: None,
            check: None,
        },
    )
    .unwrap();
    let gate = guard::gate(w.db.conn(), &env!(w), &w.ctx).unwrap();
    assert!(!gate.open);
    assert!(gate.reasons.contains(&GateReason::InterestDebtNoPlan));
    assert!(gate.reasons.contains(&GateReason::GuardBelowTarget));

    // Sheriklik: Anvar kapital kiritadi (mudaraba) — darvoza yopiq ekan, faollashtirib bo'lmaydi.
    let p = partnerships::create(
        &mut w.db,
        &env!(w),
        &w.ctx,
        mudaraba(
            "Tikuv sexi",
            vec![
                party(
                    "Anvar",
                    PartyRole::CapitalProvider,
                    4_000,
                    5_000_000,
                    Some(&me),
                ),
                party("Zamira", PartyRole::Worker, 6_000, 0, None),
            ],
        ),
    )
    .unwrap();
    let p1 = p.partnership.meta.id.clone();
    w.sign_all(&p1);
    assert!(matches!(
        partnerships::activate(&mut w.db, &env!(w), &w.ctx, &p1),
        Err(ServiceError::Invalid(_))
    ));

    // 6) «QARZDAN CHIQISH» 70/20/10.
    recovery::set_mode(&mut w.db, &env!(w), &w.ctx, BudgetMode::DebtRecovery).unwrap();
    let st = recovery::status(&mut w.db, &env!(w), &w.ctx).unwrap();
    let a = st.amounts.unwrap();
    assert_eq!(
        (a.living.minor(), a.extra.minor(), a.savings.minor()),
        (14_000_000, 4_000_000, 2_000_000)
    );

    // 7) PAYOFF: oylik qo'shimcha to'lov muddatni qisqartiradi.
    let plan = payoff::plan(w.db.conn(), &env!(w), &w.ctx, a.extra, uzs(0))
        .unwrap()
        .unwrap();
    assert!(plan.accelerated_months < plan.baseline_months, "{plan:?}");
    assert!(plan.months_saved >= 1);

    // 8) QARZ YOPILISHI: uchta to'lov; rejim avtomatik STANDARD'ga qaytadi.
    for _ in 0..3 {
        debts::pay(
            &mut w.db,
            &env!(w),
            &w.ctx,
            &debt.debt.meta.id,
            uzs(11_000_000),
            None,
            None,
        )
        .unwrap();
    }
    let closed = debts::get(w.db.conn(), &env!(w), &w.ctx, &debt.debt.meta.id).unwrap();
    assert!(!closed.active());
    recovery::sync(&mut w.db, &env!(w), &w.ctx).unwrap();
    assert_eq!(
        recovery::mode(w.db.conn(), &w.ctx).unwrap(),
        BudgetMode::Standard
    );

    // 9) DARVOZA OCHILISHI: qarz yo'q, «Qorovul» maqsadga yetdi.
    assert!(!guard::gate(w.db.conn(), &env!(w), &w.ctx).unwrap().open);
    vault::set_opening_balance(&mut w.db, &env!(w), &w.ctx, uzs(9_000_000)).unwrap();
    let gate = guard::gate(w.db.conn(), &env!(w), &w.ctx).unwrap();
    assert!(gate.open && gate.rules_open && !gate.bypassed, "{gate:?}");

    // 10) SHERIKLIK: endi faollashadi.
    let v = partnerships::activate(&mut w.db, &env!(w), &w.ctx, &p1).unwrap();
    assert_eq!(v.partnership.status, PartnershipStatus::Active);

    // 11) TAQSIMOT: Anvar ishchi bo'lgan ikkinchi sheriklikda davr yopiladi.
    let q = partnerships::create(
        &mut w.db,
        &env!(w),
        &w.ctx,
        mudaraba(
            "Ustaxona",
            vec![
                party(
                    "Karim aka",
                    PartyRole::CapitalProvider,
                    4_000,
                    800_000_000,
                    None,
                ),
                party("Anvar", PartyRole::Worker, 6_000, 0, Some(&me)),
            ],
        ),
    )
    .unwrap();
    let p2 = q.partnership.meta.id.clone();
    w.sign_all(&p2);
    partnerships::activate(&mut w.db, &env!(w), &w.ctx, &p2).unwrap();
    for (kind, desc, amount, on) in [
        (LedgerKind::Income, "Buyurtma", 10_000_000, "2026-10-12"),
        (LedgerKind::Expense, "Mato", 2_000_000, "2026-10-13"),
    ] {
        ventures::add_entry(
            &mut w.db,
            &env!(w),
            &w.ctx,
            &p2,
            NewEntry {
                kind,
                description: desc,
                amount: uzs(amount),
                occurred_on: Some(d(on)),
                note: None,
                force_majeure: false,
            },
        )
        .unwrap();
    }
    let period = ventures::close_period(
        &mut w.db,
        &env!(w),
        &w.ctx,
        &p2,
        Some(d("2026-10-31")),
        None,
    )
    .unwrap();
    // Sof foyda 8 000 000: Anvar 60% = 4 800 000, Karim aka 40% = 3 200 000.
    let mine = period
        .distribution
        .iter()
        .find(|x| x.role == PartyRole::Worker)
        .unwrap();
    assert_eq!(mine.amount, uzs(4_800_000));
    assert_eq!(
        period
            .distribution
            .iter()
            .map(|x| x.amount.minor())
            .sum::<i64>(),
        8_000_000
    );

    // 12) EKSPORT → yangi qurilma → 1:1.
    let bytes =
        interchange::export_bytes(&w.db, &env!(w), &w.ctx, "anvar-parol-1", false, FAST).unwrap();
    let mut fresh = Database::open_in_memory(&[5; 32]).unwrap();
    let report = interchange::import_into_empty(&mut fresh, &bytes, "anvar-parol-1").unwrap();
    assert!(report.conflicts.is_empty(), "{:?}", report.conflicts);
    let dump = |db: &Database| {
        doc_io::export(db.conn(), &w.ctx.household_id, "x", w.clock.now(), None)
            .unwrap()
            .tables
    };
    assert_eq!(dump(&w.db), dump(&fresh));
    assert!(matches!(
        interchange::import_into_empty(&mut fresh, &bytes, "xato-parol-12"),
        Err(ServiceError::WrongPassword)
    ));
}
