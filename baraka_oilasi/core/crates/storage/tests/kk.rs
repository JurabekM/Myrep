#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K1: maosh o'tkazmasi atomik — Uy tomoni yozilmasa, Kasb-kor tomoni ham qolmaydi.

use baraka_security::DbKey;
use baraka_storage::repo::household::{self, HouseholdRow, SpaceRow};
use baraka_storage::repo::{incomes, kk};
use baraka_storage::{Database, Meta, SpaceScope, StorageError};

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

/// K4: nasiyada ustama, jarima yoki foiz ustuni yo'q; narx va jadval o'zgarmaydi; hodisalar va kassa
/// kuni o'zgarmas; telefon roziliksiz saqlanmaydi.
#[test]
fn credit_has_no_surcharge_and_is_immutable() {
    use baraka_storage::repo::kk_ledger;
    let (db, s) = db_with_kk();
    let m = meta();
    let cols: Vec<String> = db
        .read(|c| {
            let mut st = c.prepare("SELECT name FROM pragma_table_info('kk_credit_sales')")?;
            let rows = st.query_map([], |r| r.get::<_, String>(0))?;
            Ok(rows.collect::<Result<Vec<_>, _>>()?)
        })
        .unwrap();
    for bad in [
        "markup",
        "penalty",
        "interest",
        "fee",
        "late",
        "surcharge",
        "rate",
    ] {
        assert!(cols.iter().all(|c| !c.contains(bad)), "{bad}: {cols:?}");
    }
    let no_consent = kk_ledger::KkCustomerRow {
        id: "c0".into(),
        name: "Malika".into(),
        phone: Some("+998".into()),
        phone_consent: false,
        note: None,
    };
    assert!(db
        .write(|tx| kk_ledger::insert_customer(tx, &s, &no_consent, &m))
        .is_err());
    let customer = kk_ledger::KkCustomerRow {
        id: "c1".into(),
        phone_consent: true,
        ..no_consent
    };
    db.write(|tx| kk_ledger::insert_customer(tx, &s, &customer, &m))
        .unwrap();
    let sale = kk_ledger::KkCreditSaleRow {
        id: "s1".into(),
        customer_id: "c1".into(),
        item: "Koʻylak".into(),
        currency: "UZS".into(),
        cash_price_minor: Some(60_000_000),
        credit_price_minor: 66_000_000,
        installments: 3,
        sold_on: "2026-11-10".into(),
        first_due: "2026-11-10".into(),
        witness: None,
        note: None,
        review_week: None,
    };
    db.write(|tx| kk_ledger::insert_credit_sale(tx, &s, &sale, &m))
        .unwrap();
    let err = db
        .write(|tx| {
            Ok(tx.execute(
                "UPDATE kk_credit_sales SET credit_price_minor = 70000000",
                [],
            )?)
        })
        .unwrap_err();
    assert_eq!(err.code(), "EVIDENCE_IMMUTABLE");
    db.write(|tx| kk_ledger::set_review_week(tx, &s, "s1", Some("2026-12-25"), &m))
        .unwrap();
    let ev = kk_ledger::KkCreditEventRow {
        id: "e1".into(),
        sale_id: "s1".into(),
        kind: "EXTEND".into(),
        occurred_on: "2026-12-01".into(),
        amount_minor: None,
        months: Some(1),
        wallet: None,
        income_id: None,
        note: None,
    };
    db.write(|tx| kk_ledger::insert_credit_event(tx, &s, &ev, &m))
        .unwrap();
    let bad_payment = kk_ledger::KkCreditEventRow {
        id: "e2".into(),
        kind: "PAYMENT".into(),
        months: None,
        amount_minor: Some(100),
        ..ev.clone()
    };
    assert!(
        db.write(|tx| kk_ledger::insert_credit_event(tx, &s, &bad_payment, &m))
            .is_err(),
        "to'lov hamyonsiz va tushumsiz yozilmaydi"
    );
    for sql in [
        "UPDATE kk_credit_events SET months = 2",
        "DELETE FROM kk_credit_events",
    ] {
        assert_eq!(
            db.write(|tx| Ok(tx.execute(sql, [])?)).unwrap_err().code(),
            "EVIDENCE_IMMUTABLE"
        );
    }
    assert!(db
        .write(|tx| kk_ledger::delete_credit_sale(tx, &s, "s1", &m))
        .is_err());

    let day = kk_ledger::KkCashDayRow {
        id: "d1".into(),
        day: "2026-11-20".into(),
        currency: "UZS".into(),
        opening_minor: 50_000_000,
        expected_minor: 150_000_000,
        counted_minor: 145_000_000,
        difference_minor: -5_000_000,
        reason: None,
        note: None,
        result_json: "{}".into(),
        closed_at: m.now.clone(),
    };
    assert!(
        db.write(|tx| kk_ledger::insert_cash_day(tx, &s, &day, &m))
            .is_err(),
        "farq bor — sabab shart"
    );
    let day = kk_ledger::KkCashDayRow {
        reason: Some("UNKNOWN".into()),
        ..day
    };
    db.write(|tx| kk_ledger::insert_cash_day(tx, &s, &day, &m))
        .unwrap();
    assert_eq!(
        db.write(|tx| Ok(tx.execute("UPDATE kk_cash_days SET counted_minor = 150000000", [])?))
            .unwrap_err()
            .code(),
        "EVIDENCE_IMMUTABLE"
    );
    assert_eq!(
        db.read(|c| kk_ledger::cash_closed_until(c, &s))
            .unwrap()
            .as_deref(),
        Some("2026-11-20")
    );
}

/// K5: tovar harakatlari o'zgarmas; qoidalar DB darajasida ham (miqdor butun, sabab va narx majburiy).
#[test]
fn stock_moves_are_checked_and_immutable() {
    use baraka_storage::repo::kk_stock;
    let (db, s) = db_with_kk();
    let m = meta();
    let item = kk_stock::KkItemRow {
        id: "i1".into(),
        name: "Shakar".into(),
        unit: "G".into(),
        method: "AVERAGE".into(),
        currency: "UZS".into(),
        sale_price_minor: None,
        replacement_price_minor: None,
        min_qty: None,
        frozen_days: 90,
        note: None,
    };
    db.write(|tx| kk_stock::insert_item(tx, &s, &item, &m))
        .unwrap();
    let bad_unit = kk_stock::KkItemRow {
        id: "i2".into(),
        unit: "KG".into(),
        ..item.clone()
    };
    assert!(db
        .write(|tx| kk_stock::insert_item(tx, &s, &bad_unit, &m))
        .is_err());
    let purchase = kk_stock::KkStockMoveRow {
        id: "m1".into(),
        item_id: "i1".into(),
        kind: "PURCHASE".into(),
        occurred_on: "2026-11-01".into(),
        qty: 50_000,
        amount_minor: Some(55_000_000),
        wallet: None,
        income_id: None,
        reason: None,
    };
    db.write(|tx| kk_stock::insert_move(tx, &s, &purchase, &m))
        .unwrap();
    let bad = [
        kk_stock::KkStockMoveRow {
            id: "b1".into(),
            amount_minor: None,
            ..purchase.clone()
        },
        kk_stock::KkStockMoveRow {
            id: "b2".into(),
            qty: -1,
            ..purchase.clone()
        },
        kk_stock::KkStockMoveRow {
            id: "b3".into(),
            kind: "WRITE_OFF".into(),
            amount_minor: None,
            ..purchase.clone()
        },
        kk_stock::KkStockMoveRow {
            id: "b4".into(),
            kind: "SALE".into(),
            wallet: Some("CASH".into()),
            ..purchase.clone()
        },
        kk_stock::KkStockMoveRow {
            id: "b5".into(),
            kind: "ADJUST".into(),
            qty: 100,
            amount_minor: None,
            reason: Some("topildi".into()),
            ..purchase.clone()
        },
    ];
    for b in &bad {
        assert!(
            db.write(|tx| kk_stock::insert_move(tx, &s, b, &m)).is_err(),
            "{}",
            b.id
        );
    }
    let shortage = kk_stock::KkStockMoveRow {
        id: "m2".into(),
        kind: "ADJUST".into(),
        qty: -500,
        amount_minor: None,
        reason: Some("toʻkilgan".into()),
        ..purchase.clone()
    };
    db.write(|tx| kk_stock::insert_move(tx, &s, &shortage, &m))
        .unwrap();
    assert_eq!(
        db.read(|c| kk_stock::moves(c, &s))
            .unwrap()
            .iter()
            .map(|r| r.qty)
            .collect::<Vec<_>>(),
        [50_000, -500]
    );
    for sql in [
        "UPDATE kk_stock_moves SET qty = 1",
        "DELETE FROM kk_stock_moves",
    ] {
        let err = db.write(|tx| Ok(tx.execute(sql, [])?)).unwrap_err();
        assert_eq!(err.code(), "EVIDENCE_IMMUTABLE", "{sql}");
    }
    // Harakati bor tovar o'chirilmaydi.
    assert!(db
        .write(|tx| kk_stock::delete_item(tx, &s, "i1", &m))
        .is_err());
}

/// K6: xodim va ta'minotchi jadvallarida foiz, ustama yoki jarima ustuni yo'q; imzolangan versiya,
/// yetkazish va to'lov o'zgarmas; telefon — faqat rozilik bilan.
#[test]
fn staff_and_supply_have_no_penalty_and_are_immutable() {
    use baraka_storage::repo::kk_staff;
    let (db, s) = db_with_kk();
    let m = meta();
    for table in [
        "kk_agreements",
        "kk_agreement_versions",
        "kk_staff_events",
        "kk_supply_deliveries",
        "kk_supply_payments",
    ] {
        let cols: Vec<String> = db
            .read(|c| {
                let mut st =
                    c.prepare(&format!("SELECT name FROM pragma_table_info('{table}')"))?;
                let rows = st.query_map([], |r| r.get::<_, String>(0))?;
                Ok(rows.collect::<Result<Vec<_>, _>>()?)
            })
            .unwrap();
        for bad in [
            "markup",
            "penalty",
            "interest",
            "fee",
            "late",
            "surcharge",
            "rate",
        ] {
            assert!(
                cols.iter().all(|c| c.split('_').all(|w| w != bad)),
                "{table}.{bad}: {cols:?}"
            );
        }
    }
    let row = kk_staff::KkAgreementRow {
        id: "a1".into(),
        kind: "SUPPLY".into(),
        party_name: "Ulgurji baza".into(),
        phone: Some("+998".into()),
        phone_consent: false,
        status: "DRAFT".into(),
        currency: "UZS".into(),
        terms_json: "{}".into(),
        started_on: "2026-11-01".into(),
        ended_on: None,
        opening_balance_minor: 0,
    };
    assert!(db
        .write(|tx| kk_staff::insert_agreement(tx, &s, &row, &m))
        .is_err());
    let row = kk_staff::KkAgreementRow {
        phone_consent: true,
        ..row
    };
    db.write(|tx| kk_staff::insert_agreement(tx, &s, &row, &m))
        .unwrap();
    let ended_without_date = kk_staff::KkAgreementRow {
        status: "ENDED".into(),
        ..row.clone()
    };
    assert!(db
        .write(|tx| kk_staff::update_agreement(tx, &s, &ended_without_date, &m))
        .is_err());
    let v = kk_staff::KkAgreementVersionRow {
        id: "v1".into(),
        agreement_id: "a1".into(),
        seq: 1,
        terms_json: "{}".into(),
        terms_hash: "h".into(),
        template_version: 1,
        template_review: "PENDING".into(),
        effective_from: "2026-11-01".into(),
        signed_on: "2026-11-01".into(),
    };
    db.write(|tx| kk_staff::insert_version(tx, &s, &v, &m))
        .unwrap();
    let d = kk_staff::KkDeliveryRow {
        id: "d1".into(),
        agreement_id: "a1".into(),
        delivered_on: "2026-11-01".into(),
        amount_minor: 125_000_000,
        currency: "UZS".into(),
        due_days: 30,
        stock_move_id: None,
        note: None,
    };
    db.write(|tx| kk_staff::insert_delivery(tx, &s, &d, &m))
        .unwrap();
    let too_long = kk_staff::KkDeliveryRow {
        id: "d2".into(),
        due_days: 400,
        ..d.clone()
    };
    assert!(db
        .write(|tx| kk_staff::insert_delivery(tx, &s, &too_long, &m))
        .is_err());
    let p = kk_staff::KkSupplyPaymentRow {
        id: "p1".into(),
        agreement_id: "a1".into(),
        paid_on: "2026-11-10".into(),
        amount_minor: 50_000_000,
        currency: "UZS".into(),
        wallet: "CARD".into(),
        expense_id: None,
        note: None,
    };
    db.write(|tx| kk_staff::insert_supply_payment(tx, &s, &p, &m))
        .unwrap();
    for sql in [
        "UPDATE kk_agreement_versions SET terms_json = '{\"salary\":1}'",
        "DELETE FROM kk_agreement_versions",
        "UPDATE kk_supply_deliveries SET amount_minor = 1",
        "DELETE FROM kk_supply_payments",
    ] {
        let err = db.write(|tx| Ok(tx.execute(sql, [])?)).unwrap_err();
        assert_eq!(err.code(), "EVIDENCE_IMMUTABLE", "{sql}");
    }
    // Imzolangan yoki yozuvi bor kelishuv o'chirilmaydi.
    assert!(db
        .write(|tx| kk_staff::delete_agreement(tx, &s, "a1", &m))
        .is_err());
}

/// K7: konvertdan foydalanish, tarozi, zakot va inventarizatsiya snapshot'lari o'zgarmas; qoidalar DB da ham.
#[test]
fn growth_records_are_checked_and_immutable() {
    use baraka_storage::repo::kk_growth;
    let (db, s) = db_with_kk();
    let m = meta();
    let tax_use = kk_growth::KkFundUseRow {
        id: "u0".into(),
        fund: "TAX".into(),
        used_on: "2026-11-05".into(),
        amount_minor: 100,
        currency: "UZS".into(),
        note: None,
    };
    assert!(
        db.write(|tx| kk_growth::insert_fund_use(tx, &s, &tax_use, &m))
            .is_err(),
        "soliq zaxirasi — faqat «Soliq» chiqimi bilan"
    );
    let reserve = kk_growth::KkFundUseRow {
        id: "u1".into(),
        fund: "RESERVE".into(),
        ..tax_use
    };
    db.write(|tx| kk_growth::insert_fund_use(tx, &s, &reserve, &m))
        .unwrap();
    db.write(|tx| {
        kk_growth::insert_scale_check(
            tx,
            &s,
            &kk_growth::KkScaleCheckRow {
                id: "c1".into(),
                checked_on: "2026-11-05".into(),
                result: "OK".into(),
                note: None,
            },
            &m,
        )
    })
    .unwrap();
    let calc = kk_growth::KkZakatCalcRow {
        id: "z1".into(),
        calculated_on: "2026-11-20".into(),
        hijri_date: "1448-06-09".into(),
        currency: "UZS".into(),
        inputs_json: "{}".into(),
        base_minor: 10_000_000_000,
        nisab_minor: 9_350_000_000,
        zakat_minor: 250_000_000,
        reason: None,
    };
    db.write(|tx| kk_growth::insert_zakat_calc(tx, &s, &calc, &m))
        .unwrap();
    let below_with_zakat = kk_growth::KkZakatCalcRow {
        id: "z2".into(),
        reason: Some("BELOW_NISAB".into()),
        ..calc
    };
    assert!(db
        .write(|tx| kk_growth::insert_zakat_calc(tx, &s, &below_with_zakat, &m))
        .is_err());
    let half_zakat_day = kk_growth::KkGrowthSettingsRow {
        reserve_months: 3,
        max_bad_bp: 1000,
        zakat_month: Some(9),
        zakat_day: None,
        gold_price_minor: None,
        nisab_grams: 85,
        stock_valuation: "REPLACEMENT".into(),
        scale_reminder: false,
        currency: "UZS".into(),
    };
    assert!(db
        .write(|tx| kk_growth::upsert_growth_settings(tx, &s, "g1", &half_zakat_day, &m))
        .is_err());
    for sql in [
        "UPDATE kk_fund_uses SET amount_minor = 1",
        "DELETE FROM kk_scale_checks",
        "UPDATE kk_zakat_calcs SET zakat_minor = 0",
        "DELETE FROM kk_zakat_calcs",
    ] {
        let err = db.write(|tx| Ok(tx.execute(sql, [])?)).unwrap_err();
        assert_eq!(err.code(), "EVIDENCE_IMMUTABLE", "{sql}");
    }
}

#[test]
fn shifts_and_device_roles_are_checked() {
    use baraka_storage::repo::roles;
    let (db, s) = db_with_kk();
    let m = meta();
    db.write(|tx| household::insert_device(tx, "h", "Do'kon telefoni", "android", &m))
        .unwrap();
    let shift = roles::KkShiftRow {
        id: "s1".into(),
        device_id: "dev-1".into(),
        day: "2026-11-20".into(),
        currency: "UZS".into(),
        opening_minor: 20_000_000,
        cash_sales_minor: 3_000_000,
        credit_payments_minor: 22_000_000,
        card_in_minor: 5_000_000,
        expected_minor: 45_000_000,
        counted_minor: 44_000_000,
        difference_minor: -1_000_000,
        reason: Some("CHANGE_ERROR".into()),
        handed_over_minor: 30_000_000,
        note: None,
        closed_at: m.now.clone(),
    };
    // Kutilgan = ochilish + naqd tushum + naqd nasiya to'lovlari; topshirilgan ≤ sanalgan; farq — sabab bilan.
    for bad in [
        roles::KkShiftRow {
            expected_minor: 46_000_000,
            difference_minor: -2_000_000,
            ..shift.clone()
        },
        roles::KkShiftRow {
            handed_over_minor: 45_000_000,
            ..shift.clone()
        },
        roles::KkShiftRow {
            reason: None,
            ..shift.clone()
        },
    ] {
        assert!(db
            .write(|tx| roles::insert_shift(tx, &s, &bad, &m))
            .is_err());
    }
    db.write(|tx| roles::insert_shift(tx, &s, &shift, &m))
        .unwrap();
    // Qurilmada kuniga bitta, o'zgarmas.
    let again = roles::KkShiftRow {
        id: "s2".into(),
        ..shift.clone()
    };
    assert!(db
        .write(|tx| roles::insert_shift(tx, &s, &again, &m))
        .is_err());
    let upd = db.write(|tx| {
        tx.execute("UPDATE kk_shifts SET counted_minor = 45000000", [])?;
        Ok(())
    });
    assert!(matches!(upd, Err(StorageError::EvidenceImmutable)));
    // Rol: faqat SELLER / ACCOUNTANT, kalit — qurilma.
    let access = roles::DeviceAccessRow {
        device_id: "dev-1".into(),
        role: "OWNER".into(),
        space_id: "kk".into(),
        revoked_at: None,
    };
    assert!(db
        .write(|tx| roles::insert_access(tx, "h", &access, &m))
        .is_err());
    let seller = roles::DeviceAccessRow {
        role: "SELLER".into(),
        ..access
    };
    db.write(|tx| roles::insert_access(tx, "h", &seller, &m))
        .unwrap();
    assert!(db
        .write(|tx| roles::revoke_access(tx, "h", "dev-1", &m))
        .unwrap());
    assert!(!db
        .write(|tx| roles::revoke_access(tx, "h", "dev-1", &m))
        .unwrap());
    // Hisobchi qurilmasi: oddiy yozuv yo'q, sinxronlash importi bor.
    db.set_read_only(true);
    assert!(matches!(
        db.write(|tx| roles::insert_shift(tx, &s, &again, &m)),
        Err(StorageError::ReadOnly)
    ));
    assert!(db.write_sync(|_| Ok(())).is_ok());
}
