#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! Repository integratsiya testlari (vaqtinchalik shifrlangan baza).

use baraka_journal::{verify_chain, EntryKind, JournalAmount, JournalEntry};
use baraka_security::DbKey;
use baraka_storage::repo::{agreements, categories, household, journal};
use baraka_storage::{Database, Meta, SpaceScope, StorageError};

fn meta() -> Meta {
    Meta {
        now: "2026-10-15T10:00:00Z".into(),
        device_id: "dev-1".into(),
    }
}

fn setup() -> (Database, SpaceScope, SpaceScope) {
    let db = Database::open_in_memory(&DbKey::from_bytes([9; 32])).unwrap();
    let m = meta();
    db.write(|tx| {
        household::insert_household(
            tx,
            &household::HouseholdRow {
                id: "h1".into(),
                name: "Karimovlar".into(),
                base_currency: "UZS".into(),
                locale: "uz".into(),
                tz: "Asia/Tashkent".into(),
                month_start_day: 1,
            },
            &m,
        )?;
        household::insert_device(tx, "h1", "Telefon", "android", &m)?;
        for (id, kind) in [("s-uy", "UY"), ("s-kk", "KASBKOR")] {
            household::insert_space(
                tx,
                &household::SpaceRow {
                    id: id.into(),
                    household_id: "h1".into(),
                    kind: kind.into(),
                    name: kind.into(),
                },
                &m,
            )?;
        }
        Ok(())
    })
    .unwrap();
    let uy = SpaceScope {
        household_id: "h1".into(),
        space_id: "s-uy".into(),
    };
    let kk = SpaceScope {
        household_id: "h1".into(),
        space_id: "s-kk".into(),
    };
    (db, uy, kk)
}

fn cat(id: &str) -> categories::CategoryRow {
    categories::CategoryRow {
        id: id.into(),
        name_key: format!("category.{id}"),
        custom_name: None,
        default_necessity: Some("ZARUR".into()),
        is_system: true,
        sort_order: 0,
        version: 1,
    }
}

#[test]
fn categories_crud_soft_delete_and_space_isolation() {
    let (db, uy, kk) = setup();
    let m = meta();
    db.write(|tx| {
        categories::insert(tx, &uy, &cat("non"), &m)?;
        categories::insert(tx, &kk, &cat("mato"), &m)
    })
    .unwrap();
    assert_eq!(db.read(|c| categories::list(c, &uy)).unwrap().len(), 1);
    // Boshqa makondagi yozuvni bu makon orqali o'zgartirib bo'lmaydi.
    assert!(matches!(
        db.write(|tx| categories::rename(tx, &uy, "mato", "x", &m)),
        Err(StorageError::NotFound)
    ));
    db.write(|tx| categories::rename(tx, &uy, "non", "Non va un", &m))
        .unwrap();
    let c = db
        .read(|c| categories::get(c, &uy, "non"))
        .unwrap()
        .unwrap();
    assert_eq!(
        (c.custom_name.as_deref(), c.version),
        (Some("Non va un"), 2)
    );
    db.write(|tx| categories::soft_delete(tx, &uy, "non", &m))
        .unwrap();
    assert!(db.read(|c| categories::list(c, &uy)).unwrap().is_empty());
    assert!(matches!(
        db.write(|tx| categories::soft_delete(tx, &uy, "non", &m)),
        Err(StorageError::NotFound)
    ));
}

#[test]
fn failed_write_rolls_back() {
    let (db, uy, _) = setup();
    let m = meta();
    let r: Result<(), StorageError> = db.write(|tx| {
        categories::insert(tx, &uy, &cat("a"), &m)?;
        Err(StorageError::NotFound)
    });
    assert!(r.is_err());
    assert!(db.read(|c| categories::list(c, &uy)).unwrap().is_empty());
}

fn entry(id: &str, kind: EntryKind, minor: Option<i64>, note: &str) -> JournalEntry {
    JournalEntry {
        id: id.into(),
        agreement_id: "agr-1".into(),
        kind,
        party_id: Some("P1".into()),
        amount: minor.map(|minor| JournalAmount {
            minor,
            currency: "UZS".into(),
        }),
        date: "2026-10-01".into(),
        note: Some(note.into()),
        corrects_entry_id: None,
        refs: vec![],
    }
}

#[test]
fn journal_is_append_only_and_verifiable() {
    let (db, uy, _) = setup();
    let m = meta();
    db.write(|tx| {
        agreements::insert(
            tx,
            &uy,
            &agreements::AgreementRow {
                id: "agr-1".into(),
                agreement_type: "PARTNERSHIP".into(),
                status: "ACTIVE".into(),
                title: "Yetkazib berish".into(),
                keeper_device_id: "dev-1".into(),
            },
            &m,
        )?;
        journal::append(
            tx,
            &uy,
            &entry(
                "e1",
                EntryKind::Contribution,
                Some(300_000_000),
                "Anvar hissasi",
            ),
            &m,
        )?;
        let mut e2 = entry("e2", EntryKind::OpeningBalance, None, "boshlangʻich");
        e2.refs = vec!["sha256:ab".into()];
        journal::append(tx, &uy, &e2, &m)?;
        Ok(())
    })
    .unwrap();

    let stored = db.read(|c| journal::list(c, &uy, "agr-1")).unwrap();
    assert_eq!(stored.iter().map(|s| s.seq).collect::<Vec<_>>(), vec![1, 2]);
    assert_eq!(stored[1].prev_hash, stored[0].hash);
    let entries: Vec<_> = stored.iter().map(|s| s.entry.clone()).collect();
    let hashes: Vec<_> = stored.iter().map(|s| s.hash.clone()).collect();
    assert_eq!(verify_chain(&entries, &hashes), Ok(hashes[1].clone()));

    for sql in [
        "UPDATE journal_entries SET note = 'x' WHERE id = 'e1'",
        "DELETE FROM journal_entries WHERE id = 'e1'",
    ] {
        let r = db.write(|tx| Ok(tx.execute(sql, [])?));
        assert!(matches!(r, Err(StorageError::JournalImmutable)), "{sql}");
    }
}

#[test]
fn schema_constraints_guard_money_rules() {
    let (db, uy, _) = setup();
    let m = meta();
    // Jamg'armadan pul olish izohsiz bo'lmaydi.
    let r = db.write(|tx| {
        tx.execute(
            "INSERT INTO assets (id, household_id, space_id, type, name, unit, currency, vault_type, created_at, updated_at, origin_device_id, updated_by_device_id)
             VALUES ('v1', 'h1', 's-uy', 'VAULT', 'Kelajagim', 'UZS', 'UZS', 'QOROVUL', ?1, ?1, 'dev-1', 'dev-1')",
            [&m.now],
        )?;
        tx.execute(
            "INSERT INTO vault_transactions (id, household_id, space_id, asset_id, amount_minor, currency, reason, occurred_on, created_at, updated_at, origin_device_id, updated_by_device_id)
             VALUES ('t1', 'h1', 's-uy', 'v1', -100, 'UZS', 'WITHDRAWAL', '2026-10-15', ?1, ?1, 'dev-1', 'dev-1')",
            [&m.now],
        )?;
        Ok(())
    });
    assert!(r.is_err());
    let _ = uy;
}
