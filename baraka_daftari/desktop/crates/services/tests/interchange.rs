#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::cell::Cell;

use domain::{
    date_from_str, CapitalKind, Category, Clock, IdGen, LedgerKind, OffsetDateTime,
    PartnershipKind, PartyRole, ReportPeriod,
};
use money::{Currency, Money};
use security::{container, KdfParams, SecurityError};
use services::{
    interchange::{self, ConflictKind, Resolution},
    members,
    partnerships::{self, NewCapital, NewPartnership, NewParty, Signer},
    setup,
    ventures::{self, NewEntry},
    Ctx, Env, ServiceError,
};
use storage::{interchange as doc_io, repo, Database};

const FAST: KdfParams = KdfParams::fast_for_tests();
const PW: &str = "parol-12345";

struct TestClock(Cell<OffsetDateTime>);
impl Clock for TestClock {
    fn now(&self) -> OffsetDateTime {
        self.0.get()
    }
}

struct Seq(Cell<u64>, u64);
impl IdGen for Seq {
    fn new_id(&self) -> String {
        let n = self.0.get();
        self.0.set(n + 1);
        format!("00000000-0000-7000-8000-{:012}", n + self.1)
    }
}

macro_rules! env {
    ($w:expr) => {
        Env {
            clock: &$w.clock,
            ids: &$w.ids,
            device_id: $w.device,
        }
    };
}

struct World {
    db: Database,
    clock: TestClock,
    ids: Seq,
    ctx: Option<Ctx>,
    device: &'static str,
}

fn uzs(v: i64) -> Money {
    Money::new(v, Currency::Uzs)
}

impl World {
    /// `seed` — ensure_household (standart toifalar va hokazo) bilan.
    fn new(device: &'static str, id_base: u64, seed: bool) -> Self {
        let mut db = Database::open_in_memory(&[9; 32]).unwrap();
        let clock = TestClock(Cell::new(time::macros::datetime!(2026-10-11 05:00 UTC)));
        let ids = Seq(Cell::new(1), id_base);
        let ctx = seed.then(|| {
            setup::ensure_household(
                &mut db,
                &Env {
                    clock: &clock,
                    ids: &ids,
                    device_id: device,
                },
            )
            .unwrap()
        });
        Self {
            db,
            clock,
            ids,
            ctx,
            device,
        }
    }

    fn import(&mut self, bytes: &[u8]) -> interchange::ImportReport {
        let ctx = self.ctx();
        interchange::import(&mut self.db, &ctx, bytes, PW).unwrap()
    }

    fn ctx(&self) -> Ctx {
        self.ctx.clone().unwrap()
    }

    fn tick(&self, secs: i64) {
        self.clock
            .0
            .set(self.clock.0.get() + time::Duration::seconds(secs));
    }

    /// Faol mudaraba, bir davr yopilgan (dalil bilan), ikkinchisi ochiq.
    fn business(&mut self) -> String {
        let ctx = self.ctx();
        let me = ctx.member_id.clone();
        members::set_pin(&mut self.db, &env!(self), &ctx, &me, "111111", FAST).unwrap();
        let party =
            |name: &str, role, share, cap: Vec<NewCapital>, member: Option<&str>| NewParty {
                name: name.into(),
                role,
                share_bp: share,
                member_id: member.map(str::to_owned),
                capital: cap,
                fixed_return: None,
            };
        let v = partnerships::create(
            &mut self.db,
            &env!(self),
            &ctx,
            NewPartnership {
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
                        vec![NewCapital {
                            description: "Naqd".into(),
                            kind: CapitalKind::Cash,
                            value: uzs(800_000_000),
                        }],
                        None,
                    ),
                    party("Zamira", PartyRole::Worker, 6_000, vec![], Some(&me)),
                ],
            },
        )
        .unwrap();
        let pid = v.partnership.meta.id.clone();
        for p in &v.parties {
            let pin = p.party.member_id.as_ref().map(|_| "111111".to_owned());
            partnerships::sign(
                &mut self.db,
                &env!(self),
                &ctx,
                &pid,
                Signer::Party {
                    party_id: p.party.meta.id.clone(),
                    pin,
                },
            )
            .unwrap();
        }
        partnerships::family_consent(&mut self.db, &env!(self), &ctx, &pid, &me, "111111").unwrap();
        partnerships::activate(&mut self.db, &env!(self), &ctx, &pid).unwrap();

        let e = self.entry(
            &pid,
            LedgerKind::Income,
            "Buyurtma",
            1_000_000,
            "2026-10-12",
        );
        ventures::attach(
            &mut self.db,
            &env!(self),
            &ctx,
            &e,
            "chek.png",
            b"\x89PNG\r\n\x1a\nxx".to_vec(),
        )
        .unwrap();
        self.entry(&pid, LedgerKind::Expense, "Mato", 200_000, "2026-10-13");
        ventures::close_period(
            &mut self.db,
            &env!(self),
            &ctx,
            &pid,
            Some(date_from_str("2026-10-31").unwrap()),
            None,
        )
        .unwrap();
        self.entry(
            &pid,
            LedgerKind::Income,
            "Yangi buyurtma",
            300_000,
            "2026-11-02",
        );
        pid
    }

    fn entry(&mut self, pid: &str, kind: LedgerKind, d: &str, amount: i64, on: &str) -> String {
        let ctx = self.ctx();
        ventures::add_entry(
            &mut self.db,
            &env!(self),
            &ctx,
            pid,
            NewEntry {
                kind,
                description: d,
                amount: uzs(amount),
                occurred_on: Some(date_from_str(on).unwrap()),
                note: None,
                force_majeure: false,
            },
        )
        .unwrap()
        .meta
        .id
    }

    fn export(&self, incremental: bool) -> Vec<u8> {
        interchange::export_bytes(&self.db, &env!(self), &self.ctx(), PW, incremental, FAST)
            .unwrap()
    }

    /// Hujjat (sarlavha maydonlarisiz taqqoslash uchun).
    fn dump(&self) -> Vec<doc_io::TableDump> {
        let ctx = self.ctx.clone().unwrap_or_else(|| Ctx {
            household_id: repo::list_all::<domain::Household>(self.db.conn())
                .unwrap()
                .remove(0)
                .meta
                .id,
            member_id: String::new(),
            currency: Currency::Uzs,
        });
        doc_io::export(
            self.db.conn(),
            &ctx.household_id,
            "x",
            self.clock.now(),
            None,
        )
        .unwrap()
        .tables
    }
}

fn parse(bytes: &[u8]) -> doc_io::ExportDoc {
    serde_json::from_slice(&container::open(bytes, PW).unwrap()).unwrap()
}

#[test]
fn round_trip_into_a_new_database_is_one_to_one() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let bytes = a.export(false);

    let mut b = World::new("desktop", 1_000_000, false);
    let report = interchange::import_into_empty(&mut b.db, &bytes, PW).unwrap();
    assert!(report.inserted > 20, "{report:?}");
    assert!(report.conflicts.is_empty(), "{:?}", report.conflicts);
    assert_eq!(
        a.dump(),
        b.dump(),
        "eksport → yangi baza → import 1:1 bo'lishi kerak"
    );

    // Qayta import hech narsani o'zgartirmaydi.
    let again = interchange::import_into_empty(&mut b.db, &bytes, PW).unwrap();
    assert_eq!(again.inserted + again.updated, 0);
    assert!(again.unchanged > 20);
    assert_eq!(a.dump(), b.dump());

    // Dalil (BLOB) bayt-ma'bayt saqlangan.
    let blob: Vec<u8> =
        b.db.conn()
            .query_row("SELECT data FROM venture_attachments", [], |r| r.get(0))
            .unwrap();
    assert_eq!(blob, b"\x89PNG\r\n\x1a\nxx");
}

#[test]
fn secrets_and_device_settings_are_not_exported() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let d = parse(&a.export(false));
    let names: Vec<&str> = d.tables.iter().map(|t| t.name.as_str()).collect();
    assert!(!names.contains(&"member_credentials"));
    assert!(!names.contains(&"settings"));
    let plain = serde_json::to_string(&d).unwrap();
    assert!(
        !plain.contains("argon2"),
        "PIN xeshi faylga tushmasligi kerak"
    );
}

#[test]
fn import_into_a_seeded_database_merges_without_duplicating_defaults() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let bytes = a.export(false);

    let mut b = World::new("desktop", 5_000_000, true);
    let ctx = b.ctx();
    assert_ne!(ctx.household_id, a.ctx().household_id);
    let before = repo::list::<Category>(b.db.conn(), &ctx.household_id)
        .unwrap()
        .len();
    let report = interchange::import(&mut b.db, &ctx, &bytes, PW).unwrap();
    assert!(report.conflicts.is_empty(), "{:?}", report.conflicts);

    let cats = repo::list::<Category>(b.db.conn(), &ctx.household_id).unwrap();
    assert_eq!(cats.len(), before, "standart toifalar dublikat bo'lmasin");
    let n: i64 =
        b.db.conn()
            .query_row("SELECT count(*) FROM households", [], |r| r.get(0))
            .unwrap();
    assert_eq!(n, 1);
    let members: Vec<String> = repo::list::<domain::Member>(b.db.conn(), &ctx.household_id)
        .unwrap()
        .into_iter()
        .map(|m| m.display_name)
        .collect();
    assert_eq!(members, ["Men"]);

    // Sheriklik va yopilgan davr xonadonga bog'langan.
    let pid: String =
        b.db.conn()
            .query_row("SELECT id FROM partnerships", [], |r| r.get(0))
            .unwrap();
    let l = ventures::ledger(b.db.conn(), &env!(b), &ctx, &pid).unwrap();
    assert_eq!(l.closed.len(), 1);
    assert!(l.open.is_some());
    let wrong: i64 =
        b.db.conn()
            .query_row(
                "SELECT count(*) FROM expenses WHERE household_id != ?1",
                [&ctx.household_id],
                |r| r.get(0),
            )
            .unwrap();
    assert_eq!(wrong, 0);
}

#[test]
fn preview_changes_nothing_and_matches_the_applied_report() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let bytes = a.export(false);
    let mut b = World::new("desktop", 5_000_000, true);
    let ctx = b.ctx();
    let before = b.dump();
    let pre = interchange::preview(&b.db, &ctx, &bytes, PW).unwrap();
    assert_eq!(
        b.dump(),
        before,
        "oldindan ko'rish bazani o'zgartirmasligi kerak"
    );
    let applied = interchange::import(&mut b.db, &ctx, &bytes, PW).unwrap();
    assert_eq!(pre, applied);
    assert_ne!(b.dump(), before);
}

#[test]
fn higher_version_wins_and_tombstones_apply() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let mut b = World::new("desktop", 1_000_000, false);
    interchange::import_into_empty(&mut b.db, &a.export(false), PW).unwrap();
    // B endi A bilan bir xil xonadon; ctx'ni A'dan olamiz.
    b.ctx = Some(a.ctx());

    // A: toifa nomini o'zgartiradi (v2); keyin o'chiradi (tombstone).
    a.tick(60);
    let mut cat = repo::list::<Category>(a.db.conn(), &a.ctx().household_id)
        .unwrap()
        .remove(0);
    let cat_id = cat.meta.id.clone();
    cat.name = "Yangi nom".into();
    repo::update(a.db.conn(), &cat, a.clock.now()).unwrap();
    let r = b.import(&a.export(false));
    assert_eq!(r.updated, 1, "{r:?}");
    assert!(r.conflicts.is_empty());
    let got = repo::get::<Category>(b.db.conn(), &cat_id)
        .unwrap()
        .unwrap();
    assert_eq!(got.name, "Yangi nom");

    a.tick(60);
    let cat = repo::get::<Category>(a.db.conn(), &cat_id)
        .unwrap()
        .unwrap();
    repo::soft_delete::<Category>(a.db.conn(), &cat.meta.id, a.clock.now()).unwrap();
    let r = b.import(&a.export(false));
    assert_eq!(r.updated, 1, "{r:?}");
    assert!(repo::get::<Category>(b.db.conn(), &cat_id)
        .unwrap()
        .is_none());

    // Eski nusxa (B'ning o'zi) A'ga import qilinsa — A'ning yangi holati yutadi.
    let r = a.import(&b.export(false));
    assert_eq!(r.updated, 0);
    assert!(r.conflicts.is_empty());
}

#[test]
fn same_version_divergence_is_listed_and_resolved_by_the_later_edit() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let mut b = World::new("desktop", 1_000_000, false);
    interchange::import_into_empty(&mut b.db, &a.export(false), PW).unwrap();
    b.ctx = Some(a.ctx());

    let hid = a.ctx().household_id;
    let first = |w: &World| repo::list::<Category>(w.db.conn(), &hid).unwrap().remove(0);
    // Ikkalasi bir xil v1 dan mustaqil tahrir qiladi; B kechroq.
    a.tick(60);
    let mut ca = first(&a);
    ca.name = "A nomi".into();
    repo::update(a.db.conn(), &ca, a.clock.now()).unwrap();
    b.tick(120);
    let mut cb = first(&b);
    cb.name = "B nomi".into();
    repo::update(b.db.conn(), &cb, b.clock.now()).unwrap();

    let r = a.import(&b.export(false));
    assert_eq!(r.conflicts.len(), 1, "{r:?}");
    assert_eq!(r.conflicts[0].kind, ConflictKind::Diverged);
    assert_eq!(r.conflicts[0].resolution, Resolution::TookIncoming);
    assert_eq!(first(&a).name, "B nomi");
}

#[test]
fn closed_periods_and_signed_contracts_are_never_changed_by_import() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let mut b = World::new("desktop", 1_000_000, false);
    interchange::import_into_empty(&mut b.db, &a.export(false), PW).unwrap();
    b.ctx = Some(a.ctx());
    let before = b.dump();

    // Buzilgan/yomon niyatli fayl: yopilgan davrga yozuv, taqsimot summasi, imzolangan shartnoma matni.
    let mut doc = parse(&a.export(false));
    let get =
        |d: &mut doc_io::ExportDoc, n: &str| d.tables.iter().position(|t| t.name == n).unwrap();
    let i = get(&mut doc, "venture_entries");
    let mut forged = doc.tables[i].rows[0].clone();
    forged.insert("id".into(), "ffffffff-0000-7000-8000-000000000001".into());
    forged.insert("description".into(), "Soxta".into());
    doc.tables[i].rows.push(forged);
    let i = get(&mut doc, "venture_distributions");
    doc.tables[i].rows[0].insert("amount_minor".into(), 1.into());
    doc.tables[i].rows[0].insert("version".into(), 9.into());
    let i = get(&mut doc, "partnership_versions");
    doc.tables[i].rows[0].insert("snapshot".into(), "O'zgartirilgan shartnoma".into());
    let i = get(&mut doc, "venture_periods");
    let closed_idx = doc.tables[i]
        .rows
        .iter()
        .position(|r| r["status"] == "CLOSED")
        .unwrap();
    doc.tables[i].rows[closed_idx].insert("net_minor".into(), 5.into());
    doc.tables[i].rows[closed_idx].insert("version".into(), 9.into());
    let forged_bytes = container::seal(&serde_json::to_vec(&doc).unwrap(), PW, FAST).unwrap();

    let r = b.import(&forged_bytes);
    let kinds: Vec<_> = r.conflicts.iter().map(|c| c.kind).collect();
    assert!(kinds.contains(&ConflictKind::ClosedPeriod), "{r:?}");
    assert!(kinds.contains(&ConflictKind::SignedContract), "{r:?}");
    assert!(r
        .conflicts
        .iter()
        .all(|c| c.resolution != Resolution::TookIncoming));
    assert_eq!(
        b.dump(),
        before,
        "yopilgan davr va shartnoma o'zgarmagan bo'lishi kerak"
    );
}

#[test]
fn a_period_closed_on_the_other_device_arrives_with_its_entries_and_distribution() {
    // Telefon davrni yopdi; desktopda hali ochiq (yozuvlari bilan) — import yopilgan holatni olib keladi.
    let mut a = World::new("phone", 0, true);
    let pid = a.business();
    let mut b = World::new("desktop", 1_000_000, false);
    // Yopishdan oldingi holat: A'ning to'liq eksportidan davrni "ochiq" qilib B'ga yozamiz.
    let doc = parse(&a.export(false));
    let i = doc
        .tables
        .iter()
        .position(|t| t.name == "venture_periods")
        .unwrap();
    let closed_idx = doc.tables[i]
        .rows
        .iter()
        .position(|r| r["status"] == "CLOSED")
        .unwrap();
    let closed_id = doc.tables[i].rows[closed_idx]["id"].clone();
    let mut open_doc = doc.clone();
    open_doc.tables[i].rows[closed_idx].insert("status".into(), "OPEN".into());
    open_doc.tables[i].rows[closed_idx].insert("net_minor".into(), serde_json::Value::Null);
    open_doc.tables[i].rows[closed_idx].insert("version".into(), 1.into());
    let j = open_doc
        .tables
        .iter()
        .position(|t| t.name == "venture_distributions")
        .unwrap();
    open_doc.tables[j].rows.clear();
    let open_bytes = container::seal(&serde_json::to_vec(&open_doc).unwrap(), PW, FAST).unwrap();
    interchange::import_into_empty(&mut b.db, &open_bytes, PW).unwrap();
    b.ctx = Some(a.ctx());
    let status: String =
        b.db.conn()
            .query_row(
                "SELECT status FROM venture_periods WHERE id = ?1",
                [closed_id.as_str().unwrap()],
                |r| r.get(0),
            )
            .unwrap();
    assert_eq!(status, "OPEN");

    let r = b.import(&a.export(false));
    assert!(
        r.conflicts.iter().all(|c| c.kind != ConflictKind::Rejected),
        "{r:?}"
    );
    assert_eq!(a.dump(), b.dump());
    let l = ventures::ledger(b.db.conn(), &env!(b), &b.ctx(), &pid).unwrap();
    assert_eq!(l.closed.len(), 1);
}

#[test]
fn incremental_export_contains_only_changes_after_the_last_export() {
    let mut a = World::new("phone", 0, true);
    let pid = a.business();
    // Oldin eksport bo'lmagan: to'liq.
    let full = parse(&a.export(true));
    assert!(full.since.is_none());
    interchange::mark_exported(&a.db, &env!(a), &a.ctx()).unwrap();

    a.tick(3600);
    a.entry(&pid, LedgerKind::Expense, "Ip", 50_000, "2026-11-03");
    let inc = parse(&a.export(true));
    assert!(inc.since.is_some());
    let rows: usize = inc.tables.iter().map(|t| t.rows.len()).sum();
    assert_eq!(
        rows,
        1,
        "{:?}",
        inc.tables
            .iter()
            .filter(|t| !t.rows.is_empty())
            .map(|t| &t.name)
            .collect::<Vec<_>>()
    );

    // Inkremental fayl ikkinchi qurilmaga (oldin to'liq olgan) qo'llanadi.
    let mut b = World::new("desktop", 1_000_000, false);
    interchange::import_into_empty(
        &mut b.db,
        &container::seal(&serde_json::to_vec(&full).unwrap(), PW, FAST).unwrap(),
        PW,
    )
    .unwrap();
    b.ctx = Some(a.ctx());
    let r = b.import(&a.export(true));
    assert_eq!(r.inserted, 1, "{r:?}");
    assert_eq!(a.dump(), b.dump());
}

#[test]
fn wrong_password_weak_password_and_garbage_give_clear_errors() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let bytes = a.export(false);
    let mut b = World::new("desktop", 5_000_000, true);
    let ctx = b.ctx();
    let before = b.dump();

    assert!(matches!(
        interchange::import(&mut b.db, &ctx, &bytes, "boshqa-parol"),
        Err(ServiceError::WrongPassword)
    ));
    assert!(matches!(
        interchange::preview(&b.db, &ctx, &bytes, "boshqa-parol"),
        Err(ServiceError::WrongPassword)
    ));
    assert!(matches!(
        interchange::import(&mut b.db, &ctx, b"bu fayl emas", PW),
        Err(ServiceError::BadFile(_))
    ));
    assert!(matches!(
        interchange::export_bytes(&a.db, &env!(a), &a.ctx(), "qisqa", false, FAST),
        Err(ServiceError::WeakPassword)
    ));
    assert_eq!(b.dump(), before);

    // Yangiroq format versiyasi.
    let mut doc = parse(&bytes);
    doc.format_version = 99;
    let newer = container::seal(&serde_json::to_vec(&doc).unwrap(), PW, FAST).unwrap();
    assert!(matches!(
        interchange::import(&mut b.db, &ctx, &newer, PW),
        Err(ServiceError::BadFile(m)) if m.contains("yangiroq")
    ));
    // Boshqa JSON.
    let other = container::seal(b"{\"a\":1}", PW, FAST).unwrap();
    assert!(matches!(
        interchange::import(&mut b.db, &ctx, &other, PW),
        Err(ServiceError::BadFile(_))
    ));
    assert_eq!(
        container::open(&bytes, "x").unwrap_err(),
        SecurityError::WrongPassword
    );
    assert_eq!(b.dump(), before);
}

#[test]
fn unknown_columns_or_tables_are_rejected_without_changes() {
    let mut a = World::new("phone", 0, true);
    a.business();
    let mut b = World::new("desktop", 5_000_000, true);
    let ctx = b.ctx();
    let before = b.dump();
    let mut doc = parse(&a.export(false));
    doc.tables[0].rows[0].insert("x\"; DROP TABLE expenses; --".into(), 1.into());
    let bytes = container::seal(&serde_json::to_vec(&doc).unwrap(), PW, FAST).unwrap();
    assert!(matches!(
        interchange::import(&mut b.db, &ctx, &bytes, PW),
        Err(ServiceError::BadFile(_))
    ));
    let mut doc = parse(&a.export(false));
    doc.tables.push(doc_io::TableDump {
        name: "sqlite_master".into(),
        rows: vec![],
    });
    let bytes = container::seal(&serde_json::to_vec(&doc).unwrap(), PW, FAST).unwrap();
    assert!(matches!(
        interchange::import(&mut b.db, &ctx, &bytes, PW),
        Err(ServiceError::BadFile(_))
    ));
    assert_eq!(b.dump(), before);
}
