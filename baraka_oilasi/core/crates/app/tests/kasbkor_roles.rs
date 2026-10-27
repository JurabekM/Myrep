#![allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
//! K8 — ko'p qurilma va rollar (ADR-0003, docs/kasbkor/SPEC.md 12): sotuvchi qurilmasida foyda
//! ma'lumoti yo'q, sotuvchi faqat sotuv, nasiya to'lovi va smenani yozadi; egasi undan faqat
//! ruxsat etilgan yozuvlarni qabul qiladi (qoldiq, yopilgan kun); bekor qilish; hisobchi — faqat o'qish.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use baraka_app::*;
use baraka_storage::repo::sync;
use baraka_storage::{Database, Meta};
use chrono::{DateTime, Utc};
use serde_json::{json, Value};

const PASSWORD: &str = "Baraka-2026!";

fn at(ts: &str) -> DateTime<Utc> {
    DateTime::parse_from_rfc3339(ts)
        .unwrap()
        .with_timezone(&Utc)
}

struct Device {
    path: PathBuf,
    key: DbKey,
    id: String,
    clock: Arc<FixedClock>,
}

impl Device {
    fn new(dir: &Path, name: &str, key: u8) -> Self {
        Self {
            path: dir.join(format!("{name}.db")),
            key: DbKey::from_bytes([key; 32]),
            id: format!("dev-{name}"),
            clock: Arc::new(FixedClock::new(at("2026-12-02T09:00:00+05:00"))),
        }
    }

    fn app(&self) -> App {
        let app = App::open(
            &self.path,
            &self.key,
            &self.id,
            self.clock.clone(),
            Arc::new(UuidV7Gen),
        )
        .unwrap();
        app.set_interchange_kdf(64, 1, 1);
        app
    }

    fn db(&self) -> Database {
        Database::open(&self.path, &self.key).unwrap()
    }

    /// Bazadagi jadval yozuvlari (xonadon bo'yicha).
    fn rows(&self, table: &str) -> Vec<serde_json::Map<String, Value>> {
        self.db()
            .read(|c| {
                let hid: String = c.query_row("SELECT id FROM households", [], |r| r.get(0))?;
                sync::dump(c, &hid, table)
            })
            .unwrap()
    }
}

fn minor(m: &MoneyDto) -> i64 {
    m.minor.parse().unwrap()
}

fn err(r: Result<impl std::fmt::Debug, AppError>) -> String {
    r.unwrap_err().code
}

/// Egasi: Uy va Kasb-kor; tushum, chiqim, «egasi oldi», maosh, tovar (xarid narxi bilan), nasiya.
fn owner_setup(app: &App) -> (String, String, String, String) {
    let h = app
        .bootstrap(BootstrapInput {
            household_name: "Bahodirlar".into(),
            device_name: "Egasining kompyuteri".into(),
            platform: "linux".into(),
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
    let uy = h.spaces.iter().find(|s| s.kind == "UY").unwrap().id.clone();
    app.record_income(
        &uy,
        NewIncomeInput {
            amount: "3 000 000".into(),
            source: "Oila daromadi".into(),
            channel: "CARD".into(),
            member_id: None,
            occurred_on: Some("2026-12-01".into()),
            source_type: None,
            note: None,
        },
    )
    .unwrap();
    app.kk_set_owner_salary(&kk, "4 000 000".into()).unwrap();
    app.kk_record_sale(
        &kk,
        KkSaleInput {
            amount: "5 000 000".into(),
            channel: "CASH".into(),
            occurred_on: Some("2026-12-01".into()),
            note: Some("Egasining savdosi".into()),
        },
    )
    .unwrap();
    app.kk_record_move(
        &kk,
        KkMoveInput {
            kind: "OWNER_DRAW".into(),
            wallet: "CASH".into(),
            to_wallet: None,
            amount: "700 000".into(),
            occurred_on: Some("2026-12-01".into()),
            note: None,
        },
    )
    .unwrap();
    let cat = app.categories(&kk).unwrap()[0].id.clone();
    app.record_expense(
        &kk,
        NewExpenseInput {
            amount: "1 200 000".into(),
            category_id: cat,
            channel: "CASH".into(),
            member_id: None,
            occurred_on: Some("2026-12-01".into()),
            necessity: None,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: None,
            self_investment: false,
            learning_plan_id: None,
        },
    )
    .unwrap();
    let stock = app
        .kk_add_item(
            &kk,
            KkItemInput {
                name: "Shakar".into(),
                unit: "G".into(),
                method: None,
                sale_price: Some("15 000".into()),
                replacement_price: Some("13 500".into()),
                min_qty: None,
                frozen_days: None,
                note: None,
            },
        )
        .unwrap();
    let item = stock.items[0].id.clone();
    app.kk_stock_move(
        &kk,
        &item,
        KkStockMoveInput {
            kind: "PURCHASE".into(),
            qty: "10".into(),
            amount: Some("120 000".into()),
            wallet: Some("CASH".into()),
            occurred_on: Some("2026-12-01".into()),
            reason: None,
        },
    )
    .unwrap();
    let customers = app
        .kk_add_customer(
            &kk,
            KkCustomerInput {
                name: "Malika".into(),
                phone: None,
                phone_consent: false,
                note: None,
            },
        )
        .unwrap();
    let book = app
        .kk_add_credit_sale(
            &kk,
            KkCreditSaleInput {
                customer_id: customers[0].id.clone(),
                item: "Gilam".into(),
                cash_price: Some("600 000".into()),
                credit_price: "660 000".into(),
                installments: 3,
                sold_on: Some("2026-11-10".into()),
                first_due: Some("2026-11-10".into()),
                witness: None,
                note: None,
            },
        )
        .unwrap();
    let sale = book.sales[0].id.clone();
    app.kk_credit_payment(
        &kk,
        &sale,
        KkCreditPaymentInput {
            amount: "220 000".into(),
            wallet: "CASH".into(),
            paid_on: Some("2026-11-10".into()),
            note: None,
        },
    )
    .unwrap();
    (kk, uy, item, sale)
}

fn pair(owner: &App, dev: &Device, role: &str, kk: &str) -> App {
    let offer = owner
        .pairing_offer(PairingInput {
            role: Some(role.into()),
            space_id: Some(kk.into()),
        })
        .unwrap();
    let app = dev.app();
    app.join_household(
        &offer.bytes,
        JoinInput {
            secret: offer.code.clone(),
            device_name: "Do'kon telefoni".into(),
            platform: "android".into(),
        },
    )
    .unwrap();
    app
}

fn incremental(app: &App, peer: &str) -> Result<ExportFileDto, AppError> {
    app.export_baraka(ExportInput {
        password: PASSWORD.into(),
        mode: "INCREMENTAL".into(),
        peer_device_id: Some(peer.into()),
    })
}

fn import(app: &App, file: &ExportFileDto) -> ImportResultDto {
    app.apply_baraka(&file.bytes, PASSWORD, vec![]).unwrap()
}

fn seller_sale(
    app: &App,
    kk: &str,
    item: Option<&str>,
    qty: Option<&str>,
    amount: Option<&str>,
    ch: &str,
) -> Result<KkSellerDayDto, AppError> {
    app.kk_seller_sale(
        kk,
        KkSellerSaleInput {
            item_id: item.map(Into::into),
            qty: qty.map(Into::into),
            amount: amount.map(Into::into),
            channel: ch.into(),
            note: None,
        },
    )
}

#[test]
fn seller_device_holds_no_profit_data_and_owner_accepts_only_its_records() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "owner", 1);
    let seller_dev = Device::new(dir.path(), "seller", 2);
    let owner = owner_dev.app();
    let (kk, uy, item, sale) = owner_setup(&owner);
    // K9: egasining soat qiymati foydadan hisoblanadi — sotuvchiga yuborilmaydi.
    owner
        .kk_owner_hour_save(
            &kk,
            KkOwnerHourInput {
                income: Some("8 100 000".into()),
                minutes_per_day: 600,
                days: 26,
            },
        )
        .unwrap();
    owner
        .kk_teaching_add(
            &kk,
            KkTeachingInput {
                occurred_on: None,
                agreement_id: None,
                learner: Some("Sotuvchi".into()),
                topic: "Narx yorligʻi yozish".into(),
                minutes: Some(30),
            },
        )
        .unwrap();
    let seller = pair(&owner, &seller_dev, "SELLER", &kk);

    // Rol: ulash faylidan.
    let role = seller.device_role().unwrap();
    assert_eq!(role.role, "SELLER");
    assert_eq!(role.space_id.as_deref(), Some(kk.as_str()));

    // Sotuvchi bazasida foyda ma'lumoti fizik jihatdan yo'q.
    for t in [
        "expenses",
        "kk_moves",
        "kk_settings",
        "kk_month_closes",
        "kk_cash_days",
        "kk_equipment",
        "kk_family_labor",
        "kk_agreements",
        "kk_growth_settings",
        "kk_owner_hours",
        "kk_delegations",
        "kk_teaching_logs",
        "journal_entries",
        "members",
        "categories",
    ] {
        assert!(
            seller_dev.rows(t).is_empty(),
            "{t} sotuvchiga yuborilmasligi kerak"
        );
    }
    let spaces = seller_dev.rows("spaces");
    assert_eq!(spaces.len(), 1);
    assert_eq!(spaces[0]["id"], json!(kk));
    // Tovar: sotuv narxi bor, qayta tiklash narxi va xarid summalari yo'q.
    let items = seller_dev.rows("kk_items");
    assert_eq!(items[0]["sale_price_minor"], json!(1_500_000));
    assert_eq!(items[0]["replacement_price_minor"], Value::Null);
    assert!(seller_dev.rows("kk_stock_moves").is_empty());
    // Tushumlardan faqat nasiya to'lovi (nasiya daftari uchun); egasining savdosi va Uy daromadi yo'q.
    let incomes = seller_dev.rows("incomes");
    assert_eq!(incomes.len(), 1);
    assert_eq!(incomes[0]["amount_minor"], json!(22_000_000));
    assert!(seller_dev.rows("kk_credit_sales").len() == 1);

    // Yadro: egasi bo'limlari sotuvchiga yopiq.
    assert_eq!(err(seller.kk_overview(&kk, None)), "ROLE_FORBIDDEN");
    assert_eq!(err(seller.kk_stock(&kk)), "ROLE_FORBIDDEN");
    assert_eq!(err(seller.kk_cash_draft(&kk, None, None)), "ROLE_FORBIDDEN");
    assert_eq!(err(seller.categories(&kk)), "ROLE_FORBIDDEN");
    assert_eq!(err(seller.kk_gate(&kk)), "ROLE_FORBIDDEN");
    assert_eq!(
        err(seller.kk_learning_overview(&kk, None)),
        "ROLE_FORBIDDEN"
    );
    assert_eq!(err(seller.kk_owner_hour_suggest(&kk)), "ROLE_FORBIDDEN");
    assert_eq!(err(seller.vault(&uy)), "ROLE_FORBIDDEN");
    assert_eq!(
        err(seller.pairing_offer(PairingInput {
            role: None,
            space_id: None
        })),
        "ROLE_FORBIDDEN"
    );

    // Sotuvchi: katalog, sotuv (tovar va erkin), nasiya to'lovi, smena.
    let catalog = seller.kk_catalog(&kk).unwrap();
    assert_eq!(catalog[0].name, "Shakar");
    assert_eq!(catalog[0].sale_price.as_ref().map(minor), Some(1_500_000));
    let day = seller_sale(&seller, &kk, Some(&item), Some("2"), None, "CASH").unwrap();
    assert_eq!(minor(&day.sales[0].amount), 3_000_000);
    assert_eq!(day.sales[0].qty.as_deref(), Some("2"));
    seller_sale(&seller, &kk, None, None, Some("50 000"), "CARD").unwrap();
    let book = seller.kk_credit_book(&kk).unwrap();
    assert_eq!(minor(&book.sales[0].outstanding), 44_000_000);
    seller
        .kk_credit_payment(
            &kk,
            &sale,
            KkCreditPaymentInput {
                amount: "220 000".into(),
                wallet: "CASH".into(),
                paid_on: None,
                note: None,
            },
        )
        .unwrap();
    // Sotuvchi o'tgan sana bilan yozmaydi.
    assert_eq!(
        err(seller.kk_credit_payment(
            &kk,
            &sale,
            KkCreditPaymentInput {
                amount: "1 000".into(),
                wallet: "CASH".into(),
                paid_on: Some("2026-12-01".into()),
                note: None,
            },
        )),
        "DATE_NOT_TODAY"
    );
    let day = seller.kk_seller_day(&kk).unwrap();
    assert_eq!(day.sales.len(), 3);
    assert_eq!(minor(&day.cash), 3_000_000 + 22_000_000);
    assert_eq!(minor(&day.card), 5_000_000);

    // Smena: birinchi — ochilish kiritiladi (200 000); kutilgan 200 000 + 30 000 + 220 000.
    let input = |counted: &str, handed: &str, reason: Option<&str>| KkShiftInput {
        opening: Some("200 000".into()),
        counted: Some(counted.into()),
        handed_over: Some(handed.into()),
        reason: reason.map(Into::into),
        note: None,
    };
    let draft = seller
        .kk_shift_draft(&kk, input("440 000", "300 000", None))
        .unwrap();
    assert_eq!(minor(&draft.expected), 45_000_000);
    assert_eq!(draft.difference.as_ref().map(minor), Some(-1_000_000));
    assert!(!draft.opening_known);
    assert_eq!(
        err(seller.kk_close_shift(&kk, input("440 000", "300 000", None))),
        "REASON_REQUIRED"
    );
    assert_eq!(
        err(seller.kk_close_shift(&kk, input("440 000", "500 000", Some("CHANGE_ERROR")))),
        "HANDOVER_ABOVE_COUNTED"
    );
    let closed = seller
        .kk_close_shift(&kk, input("440 000", "300 000", Some("CHANGE_ERROR")))
        .unwrap();
    assert!(closed.closed);
    assert_eq!(
        err(seller_sale(&seller, &kk, None, None, Some("1 000"), "CASH")),
        "SHIFT_CLOSED"
    );

    // Sotuvchi → egasi.
    let file = incremental(&seller, &owner_dev.id).unwrap();
    let preview = owner.inspect_baraka(&file.bytes, PASSWORD).unwrap();
    assert!(preview.rejected.is_empty(), "{:?}", preview.rejected);
    assert!(preview.conflicts.is_empty());
    let r = import(&owner, &file);
    assert_eq!(r.rejected, 0);
    // tushum ×3, sotuv harakati, nasiya to'lovi, smena, qurilma.
    assert_eq!(r.inserted, 7, "{r:?}");

    let devices = owner.devices().unwrap();
    let s = devices.iter().find(|d| d.id == seller_dev.id).unwrap();
    assert_eq!(s.role.as_deref(), Some("SELLER"));
    let shifts = owner.kk_shifts(&kk).unwrap();
    assert_eq!(shifts.len(), 1);
    assert_eq!(shifts[0].device_name, "Do'kon telefoni");
    assert_eq!(minor(&shifts[0].difference), -1_000_000);
    assert_eq!(minor(&shifts[0].left), 14_000_000);
    // Egasida: tovar 10 kg − 2 kg; nasiya qoldig'i 440 000 − 220 000.
    let stock = owner.kk_stock(&kk).unwrap();
    assert_eq!(stock.items[0].qty, "8");
    let book = owner.kk_credit_book(&kk).unwrap();
    assert_eq!(minor(&book.sales[0].outstanding), 22_000_000);

    // Egasi → sotuvchi: yangi chiqim yuborilmaydi; sotuvchida rol endi egasining yozuvidan.
    let cat = owner.categories(&kk).unwrap()[0].id.clone();
    owner
        .record_expense(
            &kk,
            NewExpenseInput {
                amount: "90 000".into(),
                category_id: cat,
                channel: "CASH".into(),
                member_id: None,
                occurred_on: None,
                necessity: None,
                obligation_id: None,
                is_gift: false,
                is_ostentation: false,
                funded_by_debt: false,
                note: None,
                self_investment: false,
                learning_plan_id: None,
            },
        )
        .unwrap();
    let back = incremental(&owner, &seller_dev.id).unwrap();
    let r = import(&seller, &back);
    assert_eq!(r.conflicts_local + r.conflicts_remote, 0);
    assert!(seller_dev.rows("expenses").is_empty());
    assert_eq!(seller_dev.rows("device_access").len(), 1);
    assert_eq!(seller.device_role().unwrap().role, "SELLER");
}

#[test]
fn owner_rejects_forbidden_and_invalid_seller_records() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "owner", 1);
    let seller_dev = Device::new(dir.path(), "seller", 2);
    let owner = owner_dev.app();
    let (kk, _uy, item, _sale) = owner_setup(&owner);
    let seller = pair(&owner, &seller_dev, "SELLER", &kk);
    // Birinchi fayl — egasi qurilmani rolga bog'laydi.
    import(&owner, &incremental(&seller, &owner_dev.id).unwrap());

    // Qoldiqdan ko'p sotuv (10 kg bor, 12 kg sotildi) — egasida rad etiladi, tushumi bilan birga.
    seller_sale(&seller, &kk, Some(&item), Some("12"), None, "CASH").unwrap();
    // Ilovasi o'zgartirilgan sotuvchi chiqim yozdi (to'g'ridan-to'g'ri bazaga).
    let db = seller_dev.db();
    db.write(|tx| {
        let hid: String = tx.query_row("SELECT id FROM households", [], |r| r.get(0))?;
        let m = Meta {
            now: "2026-12-02T04:00:00.000Z".into(),
            device_id: seller_dev.id.clone(),
        };
        tx.execute(
            "INSERT INTO categories (id, household_id, space_id, name_key, created_at, updated_at,
                origin_device_id, updated_by_device_id) VALUES ('cat-x', ?1, ?2, 'x', ?3, ?3, ?4, ?4)",
            [hid.as_str(), kk.as_str(), m.now.as_str(), m.device_id.as_str()],
        )?;
        Ok(())
    })
    .unwrap();
    drop(db);
    let file = incremental(&seller, &owner_dev.id).unwrap();
    let preview = owner.inspect_baraka(&file.bytes, PASSWORD).unwrap();
    let reasons: Vec<(&str, &str)> = preview
        .rejected
        .iter()
        .map(|r| (r.table.as_str(), r.reason.as_str()))
        .collect();
    assert!(
        reasons.contains(&("kk_stock_moves", "INSUFFICIENT_STOCK")),
        "{reasons:?}"
    );
    assert!(
        reasons.contains(&("incomes", "LINKED_REJECTED")),
        "{reasons:?}"
    );
    assert!(
        reasons.contains(&("categories", "ROLE_FORBIDDEN")),
        "{reasons:?}"
    );
    let r = import(&owner, &file);
    assert_eq!(r.rejected, 3);
    assert_eq!(owner.kk_stock(&kk).unwrap().items[0].qty, "10");
    // Rad etilgan sotuv tushumga kirmagan: faqat egasining 5 000 000 savdosi.
    assert_eq!(
        minor(&owner.kk_overview(&kk, None).unwrap().revenue),
        500_000_000
    );

    // Yopilgan kassa kuniga tushgan sotuv rad etiladi.
    seller_sale(&seller, &kk, None, None, Some("40 000"), "CASH").unwrap();
    owner
        .kk_close_cash_day(
            &kk,
            KkCashCloseInput {
                day: "2026-12-02".into(),
                counted: owner
                    .kk_cash_draft(&kk, Some("2026-12-02".into()), None)
                    .unwrap()
                    .expected
                    .plain,
                reason: None,
                note: None,
            },
        )
        .unwrap();
    let file = incremental(&seller, &owner_dev.id).unwrap();
    let preview = owner.inspect_baraka(&file.bytes, PASSWORD).unwrap();
    // Oldingi rad etilganlar ham (egasi hali «qabul qildim» demagan) qayta keladi va yana rad etiladi.
    let closed: Vec<&RejectedItemDto> = preview
        .rejected
        .iter()
        .filter(|r| r.reason == "CASH_DAY_CLOSED")
        .collect();
    // Yangi 40 000 va oldingi 12 kg sotuv (tushumi va harakati) — endi yopilgan kun sababi bilan.
    assert_eq!(closed.len(), 3);
    assert_eq!(closed.iter().filter(|r| r.table == "incomes").count(), 2);
    assert_eq!(preview.rejected.len(), 4);

    // Bekor qilish: endi eksport ham, import ham yo'q.
    owner.revoke_device(&seller_dev.id).unwrap();
    assert!(owner.devices().unwrap().iter().any(|d| d.revoked));
    assert_eq!(err(incremental(&owner, &seller_dev.id)), "DEVICE_REVOKED");
    assert_eq!(
        err(owner.inspect_baraka(&file.bytes, PASSWORD)),
        "DEVICE_REVOKED"
    );
}

#[test]
fn accountant_reads_only_its_business_space() {
    let dir = tempfile::tempdir().unwrap();
    let owner_dev = Device::new(dir.path(), "owner", 1);
    let acc_dev = Device::new(dir.path(), "accountant", 3);
    let owner = owner_dev.app();
    let (kk, _uy, _item, _sale) = owner_setup(&owner);
    let acc = pair(&owner, &acc_dev, "ACCOUNTANT", &kk);
    assert_eq!(acc.device_role().unwrap().role, "ACCOUNTANT");
    // Biznes ma'lumoti to'liq (foyda ham), Uy makoni yo'q.
    let o = acc.kk_overview(&kk, Some("2026-12-01".into())).unwrap();
    assert_eq!(
        minor(&o.revenue),
        minor(
            &owner
                .kk_overview(&kk, Some("2026-12-01".into()))
                .unwrap()
                .revenue
        )
    );
    assert_eq!(acc_dev.rows("spaces").len(), 1);
    assert!(acc_dev
        .rows("incomes")
        .iter()
        .all(|r| r["space_id"] == json!(kk)));
    // Yozish — yo'q; sozlamada faqat qurilma tili.
    assert_eq!(
        err(acc.kk_record_sale(
            &kk,
            KkSaleInput {
                amount: "1 000".into(),
                channel: "CASH".into(),
                occurred_on: None,
                note: None,
            },
        )),
        "ROLE_READ_ONLY"
    );
    acc.update_settings(SettingsInput {
        locale: Some("ru".into()),
        income_rhythm: None,
        debts_declared: false,
    })
    .unwrap();
    // Egasidan yangilanish keladi (import — faqat o'qish rejimida ham).
    owner
        .kk_record_sale(
            &kk,
            KkSaleInput {
                amount: "10 000".into(),
                channel: "CARD".into(),
                occurred_on: None,
                note: None,
            },
        )
        .unwrap();
    // Hisobchining birinchi fayli — egasi uni rolga bog'laydi.
    let r = import(&owner, &incremental(&acc, &owner_dev.id).unwrap());
    assert_eq!(r.rejected, 0);
    let r = import(&acc, &incremental(&owner, &acc_dev.id).unwrap());
    assert!(r.inserted >= 1);
}
