#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K6 — Kasb-kor xodim va ta'minotchi kelishuvlari, avans, haq va ta'minotchiga qarz (docs/kasbkor/SPEC.md 7).

use std::sync::Arc;

use baraka_app::*;
use chrono::{DateTime, Utc};

fn clock(at: &str) -> Arc<FixedClock> {
    Arc::new(FixedClock::new(
        DateTime::parse_from_rfc3339(at)
            .unwrap()
            .with_timezone(&Utc),
    ))
}

fn at(c: &FixedClock, t: &str) {
    c.set(DateTime::parse_from_rfc3339(t).unwrap().with_timezone(&Utc));
}

fn app_with(c: Arc<FixedClock>) -> (App, String) {
    let app = App::open_in_memory(
        &DbKey::from_bytes([9; 32]),
        "dev-bahodir",
        c,
        Arc::new(SequentialIdGen::default()),
    )
    .unwrap();
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Bahodirlar".into(),
            device_name: "Do'kon kompyuteri".into(),
            platform: "windows".into(),
            locale: "uz".into(),
            base_currency: "UZS".into(),
            month_start_day: 1,
            spaces: vec!["UY".into(), "KASBKOR".into()],
            members: vec![NewMemberInput {
                display_name: "Bahodir".into(),
                role: "ADULT".into(),
            }],
            income_rhythm: None,
            debts_declared: false,
        })
        .unwrap();
    let kk = h
        .spaces
        .iter()
        .find(|s| s.kind == "KASBKOR")
        .unwrap()
        .id
        .clone();
    (app, kk)
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn sardor() -> KkEmployeeInput {
    KkEmployeeInput {
        name: "Sardor".into(),
        role: Some("Sotuvchi".into()),
        phone: None,
        phone_consent: false,
        duties: Some("Savdo va kassa".into()),
        hours: Some("9:00–19:00, yakshanba dam".into()),
        salary: "3 000 000".into(),
        pay_day: 5,
        notice_days: 14,
        max_advance: Some("1 500 000".into()),
        max_advance_installments: Some(3),
        started_on: Some("2026-11-01".into()),
        opening_balance: None,
        arbiter: None,
        review_on: None,
        note: None,
    }
}

fn advance(amount: &str, n: u32, start: Option<&str>, on: &str) -> KkAdvanceInput {
    KkAdvanceInput {
        amount: amount.into(),
        installments: n,
        start_on: start.map(str::to_string),
        wallet: "CASH".into(),
        occurred_on: Some(on.into()),
        note: None,
    }
}

fn wage(amount: Option<&str>, on: &str) -> KkWageInput {
    KkWageInput {
        amount: amount.map(str::to_string),
        wallet: "CARD".into(),
        occurred_on: Some(on.into()),
        note: None,
    }
}

fn sign(on: Option<&str>, from: Option<&str>) -> KkSignInput {
    KkSignInput {
        signed_on: on.map(str::to_string),
        effective_from: from.map(str::to_string),
    }
}

/// Sardor: haq 3 000 000; noyabrda 1 000 000 avans, dekabrdan 2 oyda (foizsiz, jarimasiz).
#[test]
fn employee_advance_wages_and_versions() {
    let c = clock("2026-11-20T18:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    let s = app.kk_add_employee(&kk, sardor()).unwrap();
    assert_eq!(s.template_review, "PENDING");
    let e = &s.employees[0];
    let id = e.id.clone();
    assert_eq!(e.agreement.status, "DRAFT");
    assert!(e.agreement.can_sign && e.agreement.missing.is_empty());
    assert_eq!(e.agreement.review_on, "2027-11-01");

    // Kelishuv imzolanmaguncha avans yo'q.
    assert_eq!(
        app.kk_staff_advance(
            &kk,
            &id,
            advance("1 000 000", 2, Some("2026-12-01"), "2026-11-15")
        )
        .unwrap_err()
        .code,
        "AGREEMENT_NOT_SIGNED"
    );
    app.kk_sign_agreement(&kk, &id, sign(Some("2026-11-01"), None))
        .unwrap();
    assert_eq!(
        app.kk_sign_agreement(&kk, &id, sign(None, None))
            .unwrap_err()
            .code,
        "NOTHING_TO_SIGN"
    );
    let s = app
        .kk_staff_advance(
            &kk,
            &id,
            advance("1 000 000", 2, Some("2026-12-01"), "2026-11-15"),
        )
        .unwrap();
    let e = &s.employees[0];
    assert_eq!(e.agreement.effective_from.as_deref(), Some("2026-11-01"));
    assert_eq!(minor(&e.advances_outstanding), 100_000_000);
    assert_eq!(
        e.advances[0]
            .schedule
            .iter()
            .map(|x| (x.date.as_str(), minor(&x.amount)))
            .collect::<Vec<_>>(),
        [("2026-12-01", 50_000_000), ("2027-01-01", 50_000_000)]
    );
    // Noyabr haqi hali to'lanmagan, lekin oy tugamagan: hozir to'lanadigani 0.
    assert_eq!((minor(&e.balance), minor(&e.due_now)), (300_000_000, 0));
    // Avans — Kasb-kor chiqimi (naqd kassadan).
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.expenses), 100_000_000);
    assert_eq!(minor(&o.cash), -100_000_000);

    // Kelishilgan qoida: qoldiq 1 500 000 dan oshmaydi, ko'pi bilan 3 oyda.
    for (amount, n, code) in [
        ("600 000", 2, "ADVANCE_ABOVE_LIMIT"),
        ("100 000", 4, "INVALID_INSTALLMENTS"),
    ] {
        assert_eq!(
            app.kk_staff_advance(&kk, &id, advance(amount, n, None, "2026-11-16"))
                .unwrap_err()
                .code,
            code
        );
    }
    assert_eq!(
        app.kk_staff_advance(
            &kk,
            &id,
            advance("100 000", 1, Some("2026-10-01"), "2026-11-16")
        )
        .unwrap_err()
        .code,
        "INVALID_START"
    );

    // 5-dekabr: noyabr haqi to'lanadi (standart summa — o'tgan oy qoldig'i).
    at(&c, "2026-12-05T10:00:00+05:00");
    let s = app
        .kk_staff_pay(&kk, &id, wage(None, "2026-12-05"))
        .unwrap();
    let e = &s.employees[0];
    assert_eq!(minor(&e.events[0].amount), 300_000_000);
    assert_eq!(minor(&e.due_now), 0);
    // Dekabr: 3 000 000 − 500 000 ushlandi.
    assert_eq!(
        (minor(&e.months[0].deducted), minor(&e.months[0].net)),
        (50_000_000, 250_000_000)
    );
    assert_eq!(
        app.kk_staff_pay(&kk, &id, wage(None, "2026-12-06"))
            .unwrap_err()
            .code,
        "NOTHING_OWED"
    );

    // Haq oshdi: yangi shartlar imzolanguncha eski haq amal qiladi.
    let mut raise = sardor();
    raise.salary = "3 300 000".into();
    let s = app.kk_update_employee(&kk, &id, raise).unwrap();
    assert!(s.employees[0].agreement.unsigned_changes);
    app.kk_sign_agreement(&kk, &id, sign(Some("2026-12-20"), Some("2027-01-01")))
        .unwrap();
    at(&c, "2027-01-05T10:00:00+05:00");
    let s = app
        .kk_staff_pay(&kk, &id, wage(None, "2027-01-05"))
        .unwrap();
    let e = &s.employees[0];
    assert_eq!(e.agreement.signed_versions, 2);
    assert_eq!(minor(&e.events[0].amount), 250_000_000);
    assert_eq!(minor(&e.months[0].salary), 330_000_000);
    assert_eq!(minor(&e.months[1].salary), 300_000_000);

    // Varaqcha va kelishuv PDF.
    let pdf = app.kk_payslip_pdf(&kk, &id, "2026-12-15".into()).unwrap();
    assert!(pdf.starts_with(b"%PDF"));
    assert!(app.kk_agreement_pdf(&kk, &id).unwrap().starts_with(b"%PDF"));

    // Bog'langan chiqim alohida o'chirilmaydi; imzolangan kelishuv o'chirilmaydi — tugatiladi.
    let exp = app
        .kk_overview(&kk, None)
        .unwrap()
        .entries
        .into_iter()
        .find(|x| x.kind == "EXPENSE")
        .unwrap();
    assert_eq!(
        app.delete_expense(&kk, &exp.id).unwrap_err().code,
        "LINKED_RECORD"
    );
    assert_eq!(
        app.kk_delete_agreement(&kk, &id).unwrap_err().code,
        "AGREEMENT_SIGNED"
    );
    app.kk_end_agreement(&kk, &id, Some("2027-01-31".into()))
        .unwrap();
    assert_eq!(
        app.kk_staff_advance(&kk, &id, advance("100 000", 1, None, "2027-01-10"))
            .unwrap_err()
            .code,
        "AGREEMENT_ENDED"
    );
}

#[test]
fn incomplete_agreement_cannot_be_signed() {
    let (app, kk) = app_with(clock("2026-11-20T18:00:00+05:00"));
    let mut input = sardor();
    input.duties = Some("  ".into());
    input.phone = Some("+998 90 000 00 00".into());
    assert_eq!(
        app.kk_add_employee(&kk, input.clone()).unwrap_err().code,
        "PHONE_CONSENT_REQUIRED"
    );
    input.phone_consent = true;
    let s = app.kk_add_employee(&kk, input).unwrap();
    let e = &s.employees[0];
    assert_eq!(e.agreement.missing, ["duties"]);
    assert_eq!(
        app.kk_sign_agreement(&kk, &e.id, sign(None, None))
            .unwrap_err()
            .code,
        "AGREEMENT_INCOMPLETE"
    );
    let mut bad = sardor();
    bad.pay_day = 31;
    assert_eq!(
        app.kk_add_employee(&kk, bad).unwrap_err().code,
        "INVALID_PAY_DAY"
    );
    // Imzolanmagan, yozuvsiz kelishuv o'chiriladi.
    app.kk_delete_agreement(&kk, &e.id).unwrap();
    assert!(app.kk_staff(&kk).unwrap().employees.is_empty());
}

fn supplier(item_id: Option<String>) -> KkSupplierInput {
    KkSupplierInput {
        name: "Ulgurji baza".into(),
        phone: None,
        phone_consent: false,
        goods: Some("Shakar".into()),
        item_id,
        unit_price: Some("12 500".into()),
        payment_days: 30,
        delivery: Some("Do'konga, haftada bir".into()),
        returns: None,
        started_on: Some("2026-11-01".into()),
        arbiter: None,
        review_on: None,
        note: None,
    }
}

fn pay(amount: Option<&str>, on: &str) -> KkSupplyPaymentInput {
    KkSupplyPaymentInput {
        amount: amount.map(str::to_string),
        wallet: "CARD".into(),
        paid_on: Some(on.into()),
        note: None,
    }
}

/// SPEC 7.1 `SUPPLY`: 100 kg shakar 12 500 dan (qotirilgan), 30 kunlik muddat; to'lov eng erta muddatdan,
/// kechikish jarimasiz.
#[test]
fn supplier_delivery_into_stock_and_payable() {
    let c = clock("2026-11-20T18:00:00+05:00");
    let (app, kk) = app_with(c.clone());
    let item = app
        .kk_add_item(
            &kk,
            KkItemInput {
                name: "Shakar".into(),
                unit: "G".into(),
                method: None,
                sale_price: None,
                replacement_price: None,
                min_qty: None,
                frozen_days: None,
                note: None,
            },
        )
        .unwrap()
        .items[0]
        .id
        .clone();
    let s = app
        .kk_add_supplier(&kk, supplier(Some(item.clone())))
        .unwrap();
    let id = s.suppliers[0].id.clone();
    let delivery = KkDeliveryInput {
        delivered_on: Some("2026-11-01".into()),
        qty: Some("100".into()),
        amount: None,
        note: None,
    };
    assert_eq!(
        app.kk_supply_delivery(&kk, &id, delivery.clone())
            .unwrap_err()
            .code,
        "AGREEMENT_NOT_SIGNED"
    );
    app.kk_sign_agreement(&kk, &id, sign(Some("2026-11-01"), None))
        .unwrap();
    let s = app.kk_supply_delivery(&kk, &id, delivery).unwrap();
    let sup = &s.suppliers[0];
    assert_eq!(minor(&sup.outstanding), 125_000_000);
    assert_eq!(sup.deliveries[0].due_on, "2026-12-01");
    assert_eq!(sup.deliveries[0].qty.as_deref(), Some("100"));
    // Tovar qoldig'iga hamyonsiz xarid sifatida kirdi.
    let st = app.kk_stock(&kk).unwrap();
    assert_eq!(
        (st.items[0].qty.as_str(), minor(&st.items[0].value)),
        ("100", 125_000_000)
    );
    let s = app
        .kk_supply_payment(&kk, &id, pay(Some("500 000"), "2026-11-10"))
        .unwrap();
    assert_eq!(minor(&s.outstanding), 75_000_000);
    assert!(!s.suppliers[0].payments[0].as_expense);
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.stock_purchases), 50_000_000);
    assert_eq!(minor(&o.card), -50_000_000);
    assert_eq!(minor(&o.cash_flow), 0);
    assert_eq!(minor(&o.payables), 75_000_000);
    assert!(o.entries.iter().any(|e| e.kind == "SUPPLIER_PAYMENT"));
    assert_eq!(
        app.kk_supply_payment(&kk, &id, pay(Some("800 000"), "2026-11-11"))
            .unwrap_err()
            .code,
        "EXCEEDS_OUTSTANDING"
    );

    // Muddatdan 4 kun o'tdi: qoldiq o'sha-o'sha, jarima yo'q.
    at(&c, "2026-12-05T10:00:00+05:00");
    let s = app.kk_suppliers(&kk).unwrap();
    assert_eq!(
        (minor(&s.overdue), s.suppliers[0].deliveries[0].overdue_days),
        (75_000_000, 4)
    );
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.payables_overdue), 75_000_000);
    // Summasiz to'lov — eng yaqin muddatdagi qoldiq.
    let s = app
        .kk_supply_payment(&kk, &id, pay(None, "2026-12-05"))
        .unwrap();
    assert_eq!(minor(&s.outstanding), 0);
}

#[test]
fn supplier_without_item_pays_as_expense() {
    let (app, kk) = app_with(clock("2026-11-20T18:00:00+05:00"));
    let mut input = supplier(None);
    input.name = "Mato do'koni".into();
    input.goods = Some("Atlas mato".into());
    input.unit_price = None;
    input.payment_days = 0;
    let id = app.kk_add_supplier(&kk, input).unwrap().suppliers[0]
        .id
        .clone();
    app.kk_sign_agreement(&kk, &id, sign(None, None)).unwrap();
    let no_amount = KkDeliveryInput {
        delivered_on: Some("2026-11-20".into()),
        qty: None,
        amount: None,
        note: None,
    };
    assert_eq!(
        app.kk_supply_delivery(&kk, &id, no_amount.clone())
            .unwrap_err()
            .field
            .as_deref(),
        Some("amount")
    );
    app.kk_supply_delivery(
        &kk,
        &id,
        KkDeliveryInput {
            amount: Some("2 000 000".into()),
            ..no_amount
        },
    )
    .unwrap();
    let s = app
        .kk_supply_payment(&kk, &id, pay(None, "2026-11-20"))
        .unwrap();
    assert!(s.suppliers[0].payments[0].as_expense);
    let o = app.kk_overview(&kk, None).unwrap();
    assert_eq!(minor(&o.expenses), 200_000_000);
    assert_eq!(minor(&o.payables), 0);
    assert!(app.kk_agreement_pdf(&kk, &id).unwrap().starts_with(b"%PDF"));
}
