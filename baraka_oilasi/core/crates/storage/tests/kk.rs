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
