#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! Repository integratsiya testlari (vaqtinchalik shifrlangan baza).

use baraka_journal::{verify_chain, EntryKind, JournalAmount, JournalEntry};
use baraka_security::DbKey;
use baraka_storage::repo::{
    agreements, categories, governance, household, journal, partnerships, ventures,
};
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
fn agreement_versions_and_signatures_are_immutable() {
    let (db, uy, _) = setup();
    let m = meta();
    db.write(|tx| {
        agreements::insert(
            tx,
            &uy,
            &agreements::AgreementRow {
                id: "agr-1".into(),
                agreement_type: "PARTNERSHIP".into(),
                status: "DRAFT".into(),
                title: "Tikuv".into(),
                keeper_device_id: "dev-1".into(),
            },
            &m,
        )?;
        partnerships::insert_version(
            tx,
            &uy,
            "agr-1",
            &partnerships::VersionRow {
                id: "v1".into(),
                version_no: 1,
                payload_json: "{}".into(),
                payload_hash: "ab".into(),
                change_note: None,
                created_at: m.now.clone(),
            },
            &m,
        )?;
        partnerships::insert_signature(
            tx,
            &uy,
            &partnerships::SignatureRow {
                id: "g1".into(),
                version_id: "v1".into(),
                signer_key: "arbiter".into(),
                signer_role: "ARBITER".into(),
                signer_name: "Hasan Yusupov".into(),
                strokes_json: "[]".into(),
                signed_at: m.now.clone(),
            },
            &m,
        )
    })
    .unwrap();
    // Bir imzochi bir versiyani ikki marta imzolay olmaydi.
    let dup = db.write(|tx| {
        partnerships::insert_signature(
            tx,
            &uy,
            &partnerships::SignatureRow {
                id: "g2".into(),
                version_id: "v1".into(),
                signer_key: "arbiter".into(),
                signer_role: "ARBITER".into(),
                signer_name: "x".into(),
                strokes_json: "[]".into(),
                signed_at: m.now.clone(),
            },
            &m,
        )
    });
    assert!(dup.is_err());
    for sql in [
        "UPDATE agreement_versions SET payload_json = 'x' WHERE id = 'v1'",
        "DELETE FROM agreement_versions WHERE id = 'v1'",
        "UPDATE agreement_signatures SET signer_name = 'x' WHERE id = 'g1'",
        "DELETE FROM agreement_signatures WHERE id = 'g1'",
    ] {
        let r = db.write(|tx| Ok(tx.execute(sql, [])?));
        assert!(matches!(r, Err(StorageError::EvidenceImmutable)), "{sql}");
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

#[test]
fn venture_ledger_and_closed_periods_are_immutable() {
    let (db, uy, _) = setup();
    let m = meta();
    let je = |id: &str, kind: EntryKind, date: &str| JournalEntry {
        id: id.into(),
        agreement_id: "agr-v".into(),
        kind,
        party_id: None,
        amount: Some(JournalAmount {
            minor: 100,
            currency: "UZS".into(),
        }),
        date: date.into(),
        note: None,
        corrects_entry_id: None,
        refs: Vec::new(),
    };
    let entry = |id: &str, jid: &str, date: &str| ventures::EntryRow {
        id: id.into(),
        partnership_id: "p-v".into(),
        journal_entry_id: jid.into(),
        kind: "INCOME".into(),
        category: None,
        amount_minor: 100,
        currency: "UZS".into(),
        occurred_on: date.into(),
        note: None,
        corrects_entry_id: None,
        created_at: m.now.clone(),
    };
    db.write(|tx| {
        agreements::insert(
            tx,
            &uy,
            &agreements::AgreementRow {
                id: "agr-v".into(),
                agreement_type: "PARTNERSHIP".into(),
                status: "ACTIVE".into(),
                title: "Tikuv".into(),
                keeper_device_id: "dev-1".into(),
            },
            &m,
        )?;
        partnerships::insert(
            tx,
            &uy,
            &partnerships::PartnershipRow {
                id: "p-v".into(),
                agreement_id: "agr-v".into(),
                kind: "MUDARABA".into(),
                title: "Tikuv".into(),
                status: "ACTIVE".into(),
                currency: "UZS".into(),
                signed_version: Some(1),
                not_debt_ack_on: None,
                gate_json: None,
                activated_on: Some("2026-11-01".into()),
                closed_on: None,
            },
            &m,
        )?;
        journal::append(tx, &uy, &je("j1", EntryKind::Revenue, "2026-11-05"), &m)?;
        ventures::insert_entry(tx, &uy, &entry("e1", "j1", "2026-11-05"), &m)?;
        ventures::insert_attachment(
            tx,
            &uy,
            &ventures::AttachmentRow {
                meta: ventures::AttachmentMeta {
                    id: "a1".into(),
                    entry_id: "e1".into(),
                    file_name: "chek.png".into(),
                    mime: "image/png".into(),
                    size_bytes: 3,
                    sha256: "ab".into(),
                },
                bytes: vec![1, 2, 3],
            },
            &m,
        )?;
        ventures::insert_period(
            tx,
            &uy,
            &ventures::PeriodRow {
                id: "per-1".into(),
                partnership_id: "p-v".into(),
                period_no: 1,
                start_on: "2026-11-01".into(),
                end_on: "2026-11-30".into(),
                currency: "UZS".into(),
                result_minor: 100,
                loss_policy: "CAPITAL_FIRST".into(),
                signed_version: 1,
                result_json: "{}".into(),
                chain_head: "ab".into(),
                closed_at: m.now.clone(),
            },
            &m,
        )
    })
    .unwrap();
    assert_eq!(
        db.read(|c| ventures::entries(c, &uy, "p-v")).unwrap().len(),
        1
    );
    let att = db
        .read(|c| ventures::attachment(c, &uy, "p-v", "a1"))
        .unwrap()
        .unwrap();
    assert_eq!(att.bytes, vec![1, 2, 3]);
    // Yopilgan davr ichidagi sanaga yozuv qo'shilmaydi; keyingi kunga — mumkin.
    let late = db.write(|tx| {
        journal::append(tx, &uy, &je("j2", EntryKind::Revenue, "2026-11-30"), &m)?;
        ventures::insert_entry(tx, &uy, &entry("e2", "j2", "2026-11-30"), &m)
    });
    assert!(matches!(late, Err(StorageError::PeriodClosed)));
    db.write(|tx| {
        journal::append(tx, &uy, &je("j3", EntryKind::Revenue, "2026-12-01"), &m)?;
        ventures::insert_entry(tx, &uy, &entry("e3", "j3", "2026-12-01"), &m)
    })
    .unwrap();
    for sql in [
        "UPDATE venture_entries SET amount_minor = 1 WHERE id = 'e1'",
        "DELETE FROM venture_entries WHERE id = 'e1'",
        "UPDATE venture_attachments SET bytes = x'00' WHERE id = 'a1'",
        "DELETE FROM venture_attachments WHERE id = 'a1'",
        "UPDATE venture_periods SET result_minor = 1 WHERE id = 'per-1'",
        "DELETE FROM venture_periods WHERE id = 'per-1'",
    ] {
        let r = db.write(|tx| Ok(tx.execute(sql, [])?));
        assert!(matches!(r, Err(StorageError::EvidenceImmutable)), "{sql}");
    }
}

#[test]
fn governance_records_are_immutable() {
    let (db, uy, _) = setup();
    let m = meta();
    db.write(|tx| {
        agreements::insert(
            tx,
            &uy,
            &agreements::AgreementRow {
                id: "agr-g".into(),
                agreement_type: "PARTNERSHIP".into(),
                status: "ACTIVE".into(),
                title: "Tikuv".into(),
                keeper_device_id: "dev-1".into(),
            },
            &m,
        )?;
        partnerships::insert(
            tx,
            &uy,
            &partnerships::PartnershipRow {
                id: "p-g".into(),
                agreement_id: "agr-g".into(),
                kind: "MUDARABA".into(),
                title: "Tikuv".into(),
                status: "ACTIVE".into(),
                currency: "UZS".into(),
                signed_version: Some(1),
                not_debt_ack_on: None,
                gate_json: None,
                activated_on: Some("2026-11-01".into()),
                closed_on: None,
            },
            &m,
        )?;
        governance::insert_dispute(
            tx,
            &uy,
            &governance::DisputeRow {
                id: "d1".into(),
                partnership_id: "p-g".into(),
                opened_on: "2026-12-01".into(),
                opened_by_party: "P1".into(),
                subject: "Foyda".into(),
                clauses_json: "[4]".into(),
            },
            &m,
        )?;
        governance::insert_decision(
            tx,
            &uy,
            &governance::DecisionRow {
                dispute_id: "d1".into(),
                decided_on: "2026-12-05".into(),
                arbiter_name: "Hamid aka".into(),
                decision: "Davom etadi".into(),
                outcome: "RESUME".into(),
            },
            &m,
        )
    })
    .unwrap();
    assert_eq!(
        db.read(|c| governance::decision(c, &uy, "d1"))
            .unwrap()
            .unwrap()
            .outcome,
        "RESUME"
    );
    // Ikkinchi qaror — yo'q (bitta nizoga bitta qaror).
    let again = db.write(|tx| {
        governance::insert_decision(
            tx,
            &uy,
            &governance::DecisionRow {
                dispute_id: "d1".into(),
                decided_on: "2026-12-06".into(),
                arbiter_name: "x".into(),
                decision: "x".into(),
                outcome: "AMEND".into(),
            },
            &m,
        )
    });
    assert!(again.is_err());
    for sql in [
        "UPDATE disputes SET subject = 'x' WHERE id = 'd1'",
        "DELETE FROM disputes WHERE id = 'd1'",
        "UPDATE arbiter_decisions SET outcome = 'AMEND' WHERE dispute_id = 'd1'",
        "DELETE FROM arbiter_decisions WHERE dispute_id = 'd1'",
    ] {
        let r = db.write(|tx| Ok(tx.execute(sql, [])?));
        assert!(matches!(r, Err(StorageError::EvidenceImmutable)), "{sql}");
    }
}
