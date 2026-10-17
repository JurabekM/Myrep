#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K1: maosh o'tkazmasi atomik — Uy tomoni yozilmasa, Kasb-kor tomoni ham qolmaydi.

use baraka_security::DbKey;
use baraka_storage::repo::household::{self, HouseholdRow, SpaceRow};
use baraka_storage::repo::{incomes, kk};
use baraka_storage::{Database, Meta, SpaceScope};

fn meta() -> Meta {
    Meta {
        now: "2026-11-20T05:00:00.000Z".into(),
        device_id: "dev-1".into(),
    }
}

#[test]
fn salary_transfer_is_atomic() {
    let db = Database::open_in_memory(&DbKey::from_bytes([1; 32])).unwrap();
    let m = meta();
    db.write(|tx| {
        household::insert_household(
            tx,
            &HouseholdRow {
                id: "h".into(),
                name: "x".into(),
                base_currency: "UZS".into(),
                locale: "uz".into(),
                tz: "Asia/Tashkent".into(),
                month_start_day: 1,
            },
            &m,
        )?;
        household::insert_space(
            tx,
            &SpaceRow {
                id: "kk".into(),
                household_id: "h".into(),
                kind: "KASBKOR".into(),
                name: "KASBKOR".into(),
            },
            &m,
        )
    })
    .unwrap();
    let kk_scope = SpaceScope {
        household_id: "h".into(),
        space_id: "kk".into(),
    };
    // Uy makoni yo'q (FK) — ikkinchi yozuv xato beradi.
    let missing_uy = SpaceScope {
        household_id: "h".into(),
        space_id: "uy-missing".into(),
    };
    let mv = kk::KkMoveRow {
        id: "m1".into(),
        kind: "OWNER_SALARY".into(),
        wallet: "CASH".into(),
        to_wallet: None,
        amount_minor: 100,
        currency: "UZS".into(),
        occurred_on: "2026-11-20".into(),
        note: None,
        transfer_id: Some("t1".into()),
    };
    let income = incomes::IncomeRow {
        id: "i1".into(),
        member_id: None,
        amount_minor: 100,
        currency: "UZS".into(),
        source: "Kasb-kor".into(),
        channel: "CASH".into(),
        source_type: Some("TER".into()),
        occurred_on: "2026-11-20".into(),
        note: None,
    };
    let r = db.write(|tx| {
        kk::insert_move(tx, &kk_scope, &mv, &m)?;
        incomes::insert_with_transfer(tx, &missing_uy, &income, "t1", &m)
    });
    assert!(r.is_err());
    let left = db
        .read(|c| kk::moves_between(c, &kk_scope, "0000-01-01", "9999-12-31"))
        .unwrap();
    assert!(left.is_empty(), "Kasb-kor tomoni qaytarilishi kerak");
    // Salary harakati transfer_id siz yozilmaydi (DB CHECK).
    let mut bad = mv.clone();
    bad.transfer_id = None;
    assert!(db
        .write(|tx| kk::insert_move(tx, &kk_scope, &bad, &m))
        .is_err());
}

fn db_with_kk() -> (Database, SpaceScope) {
    let db = Database::open_in_memory(&DbKey::from_bytes([2; 32])).unwrap();
    let m = meta();
    db.write(|tx| {
        household::insert_household(
            tx,
            &HouseholdRow {
                id: "h".into(),
                name: "x".into(),
                base_currency: "UZS".into(),
                locale: "uz".into(),
                tz: "Asia/Tashkent".into(),
                month_start_day: 1,
            },
            &m,
        )?;
        household::insert_space(
            tx,
            &SpaceRow {
                id: "kk".into(),
                household_id: "h".into(),
                kind: "KASBKOR".into(),
                name: "KASBKOR".into(),
            },
            &m,
        )
    })
    .unwrap();
    let s = SpaceScope {
        household_id: "h".into(),
        space_id: "kk".into(),
    };
    (db, s)
}

/// K2: uskuna jadvali qoidalari DB darajasida ham; chiqib ketish bir marta.
#[test]
fn equipment_constraints_and_single_disposal() {
    let (db, s) = db_with_kk();
    let m = meta();
    let row = kk::KkEquipmentRow {
        id: "e1".into(),
        name: "Overlok".into(),
        cost_minor: 100_000,
        salvage_minor: 0,
        useful_months: 12,
        currency: "UZS".into(),
        acquired_on: "2026-11-01".into(),
        wallet: Some("CARD".into()),
        disposed_on: None,
        disposal_proceeds_minor: None,
        disposal_wallet: None,
    };
    for bad in [
        kk::KkEquipmentRow {
            salvage_minor: 100_001,
            ..row.clone()
        },
        kk::KkEquipmentRow {
            useful_months: 0,
            ..row.clone()
        },
        kk::KkEquipmentRow {
            wallet: Some("SAFE".into()),
            ..row.clone()
        },
    ] {
        assert!(db
            .write(|tx| kk::insert_equipment(tx, &s, &bad, &m))
            .is_err());
    }
    db.write(|tx| kk::insert_equipment(tx, &s, &row, &m))
        .unwrap();
    // Yaroqsiz bo'ldi (pul tushmadi) — hamyon yozilmaydi; xariddan oldin chiqib keta olmaydi.
    assert!(db
        .write(|tx| kk::dispose_equipment(tx, &s, "e1", "2026-10-01", 0, None, &m))
        .is_err());
    assert!(db
        .write(|tx| kk::dispose_equipment(tx, &s, "e1", "2026-12-01", 0, Some("CASH"), &m))
        .is_err());
    db.write(|tx| kk::dispose_equipment(tx, &s, "e1", "2026-12-01", 0, None, &m))
        .unwrap();
    assert!(db
        .write(|tx| kk::dispose_equipment(tx, &s, "e1", "2026-12-02", 500, Some("CASH"), &m))
        .is_err());
    let rows = db.read(|c| kk::equipment(c, &s)).unwrap();
    assert_eq!(rows[0].disposal_proceeds_minor, Some(0));
    db.write(|tx| kk::delete_equipment(tx, &s, "e1", &m))
        .unwrap();
    assert!(db.read(|c| kk::equipment(c, &s)).unwrap().is_empty());
}

/// K3: «Hisob kuni» bayonnomasi o'zgarmas; bir davr bir marta; manfiy qolgan izohsiz yozilmaydi.
#[test]
fn month_close_is_immutable() {
    let (db, s) = db_with_kk();
    let m = meta();
    let row = kk::KkCloseRow {
        id: "c1".into(),
        period_start: "2026-11-01".into(),
        period_end: "2026-11-30".into(),
        currency: "UZS".into(),
        remaining_minor: 100,
        carry_minor: 0,
        reserve_minor: 30,
        explanation: None,
        result_json: "{}".into(),
        prev_hash: "0".into(),
        content_hash: "h1".into(),
        closed_at: m.now.clone(),
    };
    db.write(|tx| kk::insert_close(tx, &s, &row, &m)).unwrap();
    let dup = kk::KkCloseRow {
        id: "c2".into(),
        ..row.clone()
    };
    assert!(db.write(|tx| kk::insert_close(tx, &s, &dup, &m)).is_err());
    let negative = kk::KkCloseRow {
        id: "c3".into(),
        period_start: "2026-12-01".into(),
        period_end: "2026-12-31".into(),
        remaining_minor: -1,
        ..row.clone()
    };
    assert!(db
        .write(|tx| kk::insert_close(tx, &s, &negative, &m))
        .is_err());
    for sql in [
        "UPDATE kk_month_closes SET remaining_minor = 0",
        "DELETE FROM kk_month_closes",
    ] {
        let err = db.write(|tx| Ok(tx.execute(sql, [])?)).unwrap_err();
        assert_eq!(err.code(), "EVIDENCE_IMMUTABLE");
    }
    assert_eq!(
        db.read(|c| kk::closed_until(c, &s)).unwrap().as_deref(),
        Some("2026-11-30")
    );
}
