#![allow(clippy::unwrap_used, clippy::expect_used)]

//! D8A: kelishuv jadvallari — o'zgarmas versiyalar, tasdiqlar va append-only jurnal (SPEC 2F.6).
//! Himoya DB darajasida (triggerlar) tekshiriladi: ilova kodi chetlab o'tilsa ham UPDATE/DELETE rad etiladi.

use std::cell::Cell;

use domain::*;
use money::{Currency, Money};
use storage::{repo, Database};

const KEY: [u8; 32] = [7; 32];
const AGREEMENT: &str = "0192a000-0000-7000-8000-0000000000a1";

struct Tick(Cell<i64>);
impl Clock for Tick {
    fn now(&self) -> OffsetDateTime {
        let n = self.0.get();
        self.0.set(n + 1);
        OffsetDateTime::from_unix_timestamp(1_800_000_000 + n).unwrap()
    }
}

struct Seq(Cell<u32>);
impl IdGen for Seq {
    fn new_id(&self) -> String {
        let n = self.0.get();
        self.0.set(n + 1);
        format!("00000000-0000-7000-8000-{n:012}")
    }
}

struct World {
    db: Database,
    clock: Tick,
    ids: Seq,
    household: String,
}

impl World {
    fn new() -> Self {
        let db = Database::open_in_memory(&KEY).unwrap();
        let clock = Tick(Cell::new(0));
        let ids = Seq(Cell::new(1));
        let mut hm = Meta::new(&ids, &clock, "", "dev-1");
        hm.household_id = hm.id.clone();
        let household = hm.id.clone();
        repo::insert(
            db.conn(),
            &Household {
                meta: hm,
                name: "Karimovlar".into(),
                base_currency: Currency::Uzs,
            },
        )
        .unwrap();
        let w = Self {
            db,
            clock,
            ids,
            household,
        };
        let mut agreement = Agreement {
            meta: w.meta(),
            agreement_type: AgreementType::Partnership,
            title: "Yetkazib berish musharakasi".into(),
            status: AgreementStatus::Draft,
            subject_kind: SubjectKind::Partnership,
            subject_id: Some("0192a000-0000-7000-8000-0000000000p1".into()),
            current_version: 1,
            effective_from: date_from_str("2026-10-01").unwrap(),
            keeper_device_id: Some("dev-1".into()),
            legacy: false,
            family_template: None,
        };
        agreement.meta.id = AGREEMENT.into();
        repo::insert(w.db.conn(), &agreement).unwrap();
        w
    }

    fn meta(&self) -> Meta {
        Meta::new(&self.ids, &self.clock, &self.household, "dev-1")
    }

    fn entry(&self, seq: u32, prev: &str, minor: i64) -> JournalEntry {
        let mut e = JournalEntry {
            meta: self.meta(),
            agreement_id: AGREEMENT.into(),
            seq,
            kind: JournalKind::Contribution,
            party_id: Some("P1".into()),
            amount: Some(Money::new(minor, Currency::Uzs)),
            entry_date: date_from_str("2026-10-01").unwrap(),
            note: "Anvar hissasi".into(),
            reference: None,
            corrects: None,
            prev_hash: prev.into(),
            hash: String::new(),
        };
        e.hash = link_hash(prev, &entry_canonical(&e.hashed().unwrap()).unwrap());
        e
    }
}

fn count(db: &Database, table: &str) -> i64 {
    db.conn()
        .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |r| r.get(0))
        .unwrap()
}

#[test]
fn journal_rows_cannot_be_updated_or_deleted() {
    let w = World::new();
    let e = w.entry(1, GENESIS_HASH, 300_000_000);
    repo::insert(w.db.conn(), &e).unwrap();

    let upd =
        w.db.conn()
            .execute("UPDATE journal_entries SET note = 'o''zgartirildi'", []);
    let err = upd
        .expect_err("jurnal UPDATE rad etilishi kerak")
        .to_string();
    assert!(err.contains("journal_append_only"), "{err}");

    let del = w.db.conn().execute("DELETE FROM journal_entries", []);
    let err = del
        .expect_err("jurnal DELETE rad etilishi kerak")
        .to_string();
    assert!(err.contains("journal_append_only"), "{err}");

    // Soft delete ham UPDATE bo'lgani uchun rad etiladi.
    let soft = repo::soft_delete::<JournalEntry>(w.db.conn(), &e.meta.id, w.clock.now());
    assert!(soft.is_err());
    assert_eq!(count(&w.db, "journal_entries"), 1);
    let stored: String =
        w.db.conn()
            .query_row("SELECT note FROM journal_entries", [], |r| r.get(0))
            .unwrap();
    assert_eq!(stored, "Anvar hissasi");
}

#[test]
fn journal_entry_round_trips_through_the_repository() {
    let w = World::new();
    let e = w.entry(1, GENESIS_HASH, 300_000_000);
    repo::insert(w.db.conn(), &e).unwrap();
    let back: JournalEntry = repo::get(w.db.conn(), &e.meta.id).unwrap().unwrap();
    assert_eq!(back, e);
    // Summasiz yozuv (OPENING_BALANCE bo'lmagan holat) ham saqlanadi.
    let mut plain = w.entry(2, &e.hash, 0);
    plain.amount = None;
    plain.party_id = None;
    plain.kind = JournalKind::PeriodClosed;
    plain.hash = link_hash(&e.hash, &entry_canonical(&plain.hashed().unwrap()).unwrap());
    repo::insert(w.db.conn(), &plain).unwrap();
    let back: JournalEntry = repo::get(w.db.conn(), &plain.meta.id).unwrap().unwrap();
    assert_eq!(back.amount, None);
    assert_eq!(back, plain);
}

#[test]
fn journal_sequence_is_unique_per_agreement() {
    let w = World::new();
    let e1 = w.entry(1, GENESIS_HASH, 1);
    repo::insert(w.db.conn(), &e1).unwrap();
    let dup = w.entry(1, GENESIS_HASH, 2);
    assert!(
        repo::insert(w.db.conn(), &dup).is_err(),
        "bir xil seq ikki marta yozilmasin"
    );
}

#[test]
fn journal_rejects_mismatched_amount_and_currency() {
    let w = World::new();
    let bad = w
        .db
        .conn()
        .execute(
            "INSERT INTO journal_entries (id, household_id, created_at, updated_at, version, origin_device_id,
               agreement_id, seq, kind, entry_date, note, prev_hash, hash, amount_minor, amount_currency)
             VALUES ('x1', ?1, 't', 't', 1, 'd', ?2, 1, 'CONTRIBUTION', '2026-10-01', 'n', ?3, ?3, 5, NULL)",
            rusqlite::params![w.household, AGREEMENT, GENESIS_HASH],
        );
    assert!(bad.is_err(), "summa va valyuta birga bo'lishi shart");
}

#[test]
fn agreement_versions_and_signatures_are_immutable() {
    let w = World::new();
    let v = AgreementVersion {
        meta: w.meta(),
        agreement_id: AGREEMENT.into(),
        version_no: 1,
        content: "{}".into(),
        content_hash: sha256_hex("{}"),
        change_note: None,
    };
    repo::insert(w.db.conn(), &v).unwrap();
    let s = AgreementSignature {
        meta: w.meta(),
        agreement_id: AGREEMENT.into(),
        version_no: 1,
        kind: AgreementSignKind::Party,
        signer_key: "P1".into(),
        signer_name: "Anvar".into(),
        method: SignMethod::InApp,
    };
    repo::insert(w.db.conn(), &s).unwrap();

    let err =
        w.db.conn()
            .execute("UPDATE agreement_versions SET content = 'x'", [])
            .expect_err("versiya o'zgarmas")
            .to_string();
    assert!(err.contains("agreement_version_immutable"), "{err}");
    let err =
        w.db.conn()
            .execute("DELETE FROM agreement_signatures", [])
            .expect_err("imzo o'chirilmasin")
            .to_string();
    assert!(err.contains("agreement_signature_immutable"), "{err}");
    let err =
        w.db.conn()
            .execute("UPDATE agreement_signatures SET signer_name = 'Boshqa'", [])
            .expect_err("imzo o'zgarmasin")
            .to_string();
    assert!(err.contains("agreement_signature_immutable"), "{err}");
}

#[test]
fn one_signature_per_party_per_version() {
    let w = World::new();
    let sig = |key: &str| AgreementSignature {
        meta: w.meta(),
        agreement_id: AGREEMENT.into(),
        version_no: 1,
        kind: AgreementSignKind::Party,
        signer_key: key.into(),
        signer_name: "Anvar".into(),
        method: SignMethod::InApp,
    };
    repo::insert(w.db.conn(), &sig("P1")).unwrap();
    assert!(repo::insert(w.db.conn(), &sig("P1")).is_err());
    repo::insert(w.db.conn(), &sig("P2")).unwrap();
}

#[test]
fn one_agreement_per_subject() {
    let w = World::new();
    let mut again = Agreement {
        meta: w.meta(),
        agreement_type: AgreementType::Partnership,
        title: "Takror".into(),
        status: AgreementStatus::Draft,
        subject_kind: SubjectKind::Partnership,
        subject_id: Some("0192a000-0000-7000-8000-0000000000p1".into()),
        current_version: 1,
        effective_from: date_from_str("2026-10-01").unwrap(),
        keeper_device_id: None,
        legacy: true,
        family_template: None,
    };
    assert!(
        repo::insert(w.db.conn(), &again).is_err(),
        "bitta obyektga ikki kelishuv bo'lmasin"
    );
    again.subject_kind = SubjectKind::Unlinked;
    again.subject_id = None;
    repo::insert(w.db.conn(), &again).unwrap();
    assert_eq!(count(&w.db, "agreements"), 2);
}

#[test]
fn agreement_round_trips_and_keeps_legacy_flag() {
    let w = World::new();
    let back: Agreement = repo::get(w.db.conn(), AGREEMENT).unwrap().unwrap();
    assert_eq!(back.title, "Yetkazib berish musharakasi");
    assert_eq!(back.status, AgreementStatus::Draft);
    assert!(!back.legacy);
    assert_eq!(back.effective_from, date_from_str("2026-10-01").unwrap());
}
