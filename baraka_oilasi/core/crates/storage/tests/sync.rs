#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! U14: sinxronlanadigan jadvallar ro'yxati bazaga mos, yozuvlar aynan ko'chiriladi,
//! o'zgarmas jadvalga mavjud yozuvni qayta yozib bo'lmaydi.

use baraka_interchange::tables::{sync_tables, TableMode};
use baraka_security::DbKey;
use baraka_storage::repo::{household, sync};
use baraka_storage::{Database, Meta, StorageError};
use serde_json::json;

fn meta(device: &str) -> Meta {
    Meta {
        now: "2026-10-16T09:00:00.000Z".into(),
        device_id: device.into(),
    }
}

fn db_with_household() -> Database {
    let db = Database::open_in_memory(&DbKey::from_bytes([3; 32])).unwrap();
    let m = meta("dev-1");
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
        household::insert_device(tx, "h1", "Telefon", "android", &m)
    })
    .unwrap();
    db
}

#[test]
fn registry_covers_every_table() {
    let db = db_with_household();
    let local: Vec<String> = db
        .read(|c| {
            let mut st =
                c.prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")?;
            let rows = st.query_map([], |r| r.get::<_, String>(0))?;
            Ok(rows.collect::<Result<Vec<_>, _>>()?)
        })
        .unwrap();
    let bookkeeping = [
        "sync_peers",
        "quick_entry_queue",
        "sync_exports",
        "sync_pending",
        "sync_base",
        "sync_imports",
        "device_settings",
        "local_device_role",
    ];
    let synced: Vec<String> = local
        .into_iter()
        .filter(|t| !bookkeeping.contains(&t.as_str()) && !t.starts_with("sqlite_"))
        .collect();
    let registry: Vec<String> = sync_tables().iter().map(|t| t.name.clone()).collect();
    // Tartib ham bir xil: import ota yozuvlardan boshlanadi (migratsiyalar tartibi).
    assert_eq!(registry, synced);
    // O'zgarmas jadvallar ro'yxati: `updated_at` yo'q jadvallar.
    for t in sync_tables() {
        let cols = db.read(|c| sync::columns(c, &t.name)).unwrap();
        let mutable = cols.iter().any(|c| c == "updated_at");
        assert_eq!(t.mode == TableMode::Mutable, mutable, "{}", t.name);
        assert!(cols.contains(&t.primary_key), "{}", t.name);
    }
}

#[test]
fn rows_copy_verbatim_between_databases() {
    let a = db_with_household();
    let b = Database::open_in_memory(&DbKey::from_bytes([4; 32])).unwrap();
    for t in ["households", "devices"] {
        let rows = a.read(|c| sync::dump(c, "h1", t)).unwrap();
        b.write(|tx| {
            sync::defer_foreign_keys(tx)?;
            for r in &rows {
                sync::write(tx, t, r)?;
            }
            Ok(())
        })
        .unwrap();
        assert_eq!(b.read(|c| sync::dump(c, "h1", t)).unwrap(), rows);
    }
    // MUTABLE: mavjud yozuv to'liq almashtiriladi.
    let mut dev = a
        .read(|c| sync::get(c, "h1", "devices", "dev-1"))
        .unwrap()
        .unwrap();
    dev.insert("name".into(), json!("Feruzaning telefoni"));
    dev.insert("version".into(), json!(2));
    b.write(|tx| sync::write(tx, "devices", &dev)).unwrap();
    assert_eq!(
        b.read(|c| sync::get(c, "h1", "devices", "dev-1")).unwrap(),
        Some(dev.clone())
    );
    // Noma'lum ustun yoki jadval — sxema mos emas.
    let mut extra = dev.clone();
    extra.insert("hacked".into(), json!(1));
    assert!(matches!(
        b.write(|tx| sync::write(tx, "devices", &extra)),
        Err(StorageError::SchemaMismatch)
    ));
    assert!(matches!(
        b.read(|c| sync::dump(c, "h1", "sqlite_master")),
        Err(StorageError::SchemaMismatch)
    ));
    // Boshqa xonadon yozuvi ko'rinmaydi.
    assert!(b
        .read(|c| sync::get(c, "h2", "devices", "dev-1"))
        .unwrap()
        .is_none());
}

#[test]
fn append_only_rows_cannot_be_rewritten() {
    let db = db_with_household();
    let m = meta("dev-1");
    let entry = json!({
        "id": "j1", "household_id": "h1", "space_id": "s1", "agreement_id": "a1", "seq": 1,
        "kind": "REVENUE", "party_id": null, "amount_minor": 100, "currency": "UZS",
        "entry_date": "2026-11-05", "note": null, "corrects_entry_id": null, "refs_json": null,
        "prev_hash": "0", "hash": "x", "created_at": m.now, "origin_device_id": "dev-1"
    });
    let row = entry.as_object().unwrap().clone();
    let r = db.write(|tx| {
        sync::defer_foreign_keys(tx)?;
        sync::write(tx, "journal_entries", &row)?;
        sync::write(tx, "journal_entries", &row)
    });
    // Ikkinchi yozish — birlamchi kalit to'qnashuvi: o'zgarmas jadvalga UPSERT yo'q.
    assert!(r.is_err());
}

#[test]
fn pending_rows_are_acked_in_order() {
    let db = db_with_household();
    let m = meta("dev-1");
    let rows = |h: &str| vec![("incomes".to_string(), "i1".to_string(), h.to_string())];
    db.write(|tx| {
        sync::record_export(tx, "h1", "e-pair", None, "PAIRING", 1, &rows("h0"), &m)?;
        sync::record_export(
            tx,
            "h1",
            "e1",
            Some("dev-2"),
            "INCREMENTAL",
            1,
            &rows("h1"),
            &m,
        )?;
        sync::record_export(
            tx,
            "h1",
            "e2",
            Some("dev-2"),
            "INCREMENTAL",
            1,
            &rows("h2"),
            &m,
        )?;
        sync::record_export(
            tx,
            "h1",
            "e3",
            Some("dev-3"),
            "INCREMENTAL",
            1,
            &rows("h3"),
            &m,
        )
    })
    .unwrap();
    // dev-2 e1 ni tasdiqladi: ulash fayli va e1 (e2 hali emas, dev-3 ning e3 i aralashmaydi).
    let acked = db
        .read(|c| sync::acked_pending(c, "h1", "dev-2", "e1"))
        .unwrap();
    let hashes: Vec<&str> = acked.iter().map(|x| x.2.as_str()).collect();
    assert_eq!(hashes, ["h1"]);
    let pair = db
        .read(|c| sync::acked_pending(c, "h1", "dev-2", "e-pair"))
        .unwrap();
    assert_eq!(pair.len(), 1);
    // Begona qurilmaning eksportini tasdiqlab bo'lmaydi.
    assert!(db
        .read(|c| sync::acked_pending(c, "h1", "dev-3", "e2"))
        .unwrap()
        .is_empty());
    db.write(|tx| sync::close_acked(tx, "h1", "dev-2", "e2"))
        .unwrap();
    assert!(db
        .read(|c| sync::acked_pending(c, "h1", "dev-2", "e2"))
        .unwrap()
        .is_empty());
    assert_eq!(
        db.read(|c| sync::acked_pending(c, "h1", "dev-3", "e3"))
            .unwrap()
            .len(),
        1
    );
}
